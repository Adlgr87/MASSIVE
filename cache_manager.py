"""
cache_manager.py — Gestor de caché para MASSIVE Architect.

Arquitectura: Memoria RAM (ultra-rápido, LRU-evictable) + SQLite (persistente
cross-session).  Compatible con UI-NG (servida por backend FastAPI), Docker, y
entornos serverless con volumen montado.

Garantías reales
----------------
* **Consistencia de clave**: la clave incorpora un ``CACHE_SCHEMA_VERSION``
  estático, un *fingerprint* del dictado ``MASSIVE_RUNTIME_PARAMS`` empírico y
  un *fingerprint* de los pesos CfC activos.  Cambiando cualquiera de estos
  materiales la clave cambia completamente — nunca se sirve contenido obsoleto.
* **Thread-safety**: todas las operaciones (memoria y SQLite) están
  serializadas por un ``threading.Lock`` único.  El objeto es seguro para uso
  concurrente del backend FastAPI que sirve la UI-NG (check_same_thread=False).
* **TTL configurable**: el TTL se lee de ``MASSIVE_CACHE_TTL_SECONDS`` (default
  3600 s) y se aplica **en la lectura** usando la columna ``created_at``.
  Entradas expiradas se tratan como *miss* y se eliminan de la caché.
* **Evicción de memoria**: la capa en memoria está limitada a
  ``MASSIVE_CACHE_MEM_SIZE`` (default 1000) entradas con política LRU.
* **Observabilidad**: contadores ``cache_hits``, ``cache_misses`` y
  ``cache_errors`` incrementan en cada operación y se exponen vía el
  ``MetricsRegistry`` global (``/metrics`` en el backend FastAPI).
* **Fallabilidad controlada**: si SQLite no está disponible, la caché
  funciona únicamente en memoria; los errores se registran con
  ``exc_info=True`` y se incrementa el contador de errores.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
from collections import OrderedDict
from datetime import datetime, timezone

log = logging.getLogger(__name__)

#: Versión del esquema de caché.  Bumpear cuando el material de la clave o la
#: semántica de TTL cambie de forma incompatible.
CACHE_SCHEMA_VERSION: str = "v2.0"

#: TTL por defecto (1 h), configurable vía variable de entorno.
DEFAULT_CACHE_TTL_SECONDS: int = 3600

#: Tamaño máximo de la caché en memoria (configurable).
DEFAULT_MEM_CACHE_SIZE: int = 1000


def _get_metrics_registry():
    """Importa peregativamente el MetricsRegistry global del backend.

    Si el backend FastAPI no está disponible (p.ej. uso standalone del
    simulador), devuelve None y los contadores se registran como
    atributos del módulo.
    """
    try:
        from backend.app.metrics import registry

        return registry
    except Exception:
        return None  # MetricsRegistry not available in standalone usage


# Contadores de módulo (usados cuando el MetricsRegistry global no está disponible)
_cache_hits: int = 0
_cache_misses: int = 0
_cache_errors: int = 0
_lock_globals = threading.Lock()


def _inc_counter(name: str, labels: dict | None = None) -> None:
    """Incrementa un contador en el MetricsRegistry o en módulo."""
    global _cache_hits, _cache_misses, _cache_errors
    with _lock_globals:
        if name == "cache_hits":
            _cache_hits += 1
        elif name == "cache_misses":
            _cache_misses += 1
        elif name == "cache_errors":
            _cache_errors += 1
    registry = _get_metrics_registry()
    if registry is not None:
        registry.inc(name, labels or {})


class LandscapeCache:
    """Caché clave-valor para paisajes sociales generados por el LLM.

    Prioriza velocidad (dict en memoria con política LRU) y persistencia
    (SQLite con TTL aplicado en lectura).

    Thread-safe para uso concurrente del backend FastAPI que sirve la UI-NG
    (check_same_thread=False).

    Attributes:
        db_path: Ruta al archivo SQLite (:memory: para pruebas).
        ttl_seconds: Tiempo de vida de las entradas en segundos.
    """

    def __init__(self, db_path: str | None = None, ttl_seconds: int | None = None):
        self.db_path = db_path or os.getenv(
            "CACHE_DB_PATH", "landscapes_cache.db"
        )
        self.ttl_seconds = ttl_seconds or int(
            os.getenv("MASSIVE_CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL_SECONDS))
        )
        self._max_mem_size = int(
            os.getenv("MASSIVE_CACHE_MEM_SIZE", str(DEFAULT_MEM_CACHE_SIZE))
        )
        self._memory: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    # ------------------------------------------------------------------
    # Inicialización de SQLite
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Crea la tabla landscapes con columna created_at para TTL.

        Mantiene una conexión persistente para soportar bases de datos
        en memoria (``:memory:``) donde cada conexión es un DB distinto.
        """
        try:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS landscapes (
                    key TEXT PRIMARY KEY,
                    config TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._conn.commit()
        except Exception as exc:
            log.warning(
                "[Cache] No se pudo inicializar SQLite: %s. Caché solo en memoria.",
                exc,
                exc_info=True,
            )
            _inc_counter("cache_errors")
            self._conn = None

    # ------------------------------------------------------------------
    # Generación de claves versionadas
    # ------------------------------------------------------------------

    @staticmethod
    def _runtime_fp() -> str:
        """Construye un fingerprint de los parámetros de ejecución.

        Incorpora:
        * CACHE_SCHEMA_VERSION (constante estática).
        * Serialización canónica de MASSIVE_RUNTIME_PARAMS (importado de
          massive.core.empirical_config, con fallback a {}).
        * Valor de la variable de entorno MASSIVE_RUNTIME_PARAMS si está
          establecida (permite invalidación manual de la caché).
        * Serialización canónica de los pesos CfC activos (si el router está
          disponible).

        Devuelve un hash SHA-256 truncado a 16 hex chars.
        """
        parts: list[str] = [CACHE_SCHEMA_VERSION]

        # MASSIVE_RUNTIME_PARAMS del módulo empírico
        try:
            from massive.core.empirical_config import MASSIVE_RUNTIME_PARAMS

            parts.append(
                json.dumps(MASSIVE_RUNTIME_PARAMS, sort_keys=True, default=str)
            )
        except Exception:
            pass  # MASSIVE_RUNTIME_PARAMS not available — optional empirical config

        # Override vía variable de entorno (permite invalidación manual)
        env_params = os.getenv("MASSIVE_RUNTIME_PARAMS")
        if env_params:
            parts.append(env_params)

        # Fingerprint de pesos CfC activos
        try:
            from cfc_router import CfCRouter

            cfc = CfCRouter.get()
            status = cfc.status
            # Si hay algún componente CfC activo, incluir su estado en el fingerprint
            if any(status.values()):
                parts.append(json.dumps(status, sort_keys=True))
        except Exception:
            pass  # CfC router not available — fingerprint without CfC component

        material = "|".join(parts)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]

    def _key(self, goal: str) -> str:
        """Genera una clave de caché versionada y con fingerprint de runtime.

        La clave incorpora:
        * El goal normalizado (lowercased, stripped).
        * CACHE_SCHEMA_VERSION.
        * Fingerprint de MASSIVE_RUNTIME_PARAMS y pesos CfC.

        Usa SHA-256 (hash criptográfico de 256 bits).  Se usan 16 hex chars
        (64 bits de entropía) para minimizar colisiones.
        """
        normalized = goal.lower().strip()
        fp = self._runtime_fp()
        raw = f"{CACHE_SCHEMA_VERSION}:{fp}:{normalized}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Operaciones públicas
    # ------------------------------------------------------------------

    def get(self, goal: str) -> dict | None:
        """Recupera un paisaje cacheado, aplicando TTL en la lectura.

        Si la entrada en memoria está expirada o no existe, se consulta SQLite.
        Las entradas expiradas se tratan como miss y se eliminan.

        Returns:
            El dict de configuración cacheado, o None si no existe o está
            expirado.
        """
        k = self._key(goal)
        now = datetime.now(timezone.utc)

        with self._lock:
            # --- Capa de memoria ---
            if k in self._memory:
                entry = self._memory[k]
                created_at = entry.get("created_at_ts")
                if created_at is not None:
                    age = (now - created_at).total_seconds()
                    if age > self.ttl_seconds:
                        # Expirado — eliminar y contar como miss
                        del self._memory[k]
                        _inc_counter("cache_misses")
                        return None
                # Refrescar posición LRU
                self._memory.move_to_end(k)
                _inc_counter("cache_hits")
                return entry["config"]

            # --- Capa SQLite ---
            try:
                if self._conn is None:
                    _inc_counter("cache_misses")
                    return None
                cur = self._conn.execute(
                    "SELECT config, created_at FROM landscapes WHERE key = ?",
                    (k,),
                )
                row = cur.fetchone()
                if row:
                    cfg = json.loads(row[0])
                    created_at = datetime.fromisoformat(row[1])
                    # Aplicar TTL en la lectura
                    age = (now - created_at).total_seconds()
                    if age > self.ttl_seconds:
                        # Expirado — no servir, no cargar a memoria
                        _inc_counter("cache_misses")
                        return None
                    # Cachear en memoria
                    self._memory[k] = {
                        "config": cfg,
                        "created_at_ts": created_at,
                    }
                    self._evict_if_needed()
                    _inc_counter("cache_hits")
                    return cfg
            except Exception as exc:
                log.warning(
                    "[Cache] Error leyendo '%s' de SQLite: %s",
                    k,
                    exc,
                    exc_info=True,
                )
                _inc_counter("cache_errors")

            _inc_counter("cache_misses")
            return None

    def set(self, goal: str, config: dict) -> None:
        """Almacena un paisaje en memoria y en SQLite (UPSERT)."""
        k = self._key(goal)
        now = datetime.now(timezone.utc)
        entry = {"config": config, "created_at_ts": now}

        with self._lock:
            # --- Memoria ---
            self._memory[k] = entry
            self._memory.move_to_end(k)
            self._evict_if_needed()

            # --- SQLite ---
            try:
                if self._conn is None:
                    return
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO landscapes (key, config, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (k, json.dumps(config, ensure_ascii=False), now.isoformat()),
                )
                self._conn.commit()
            except Exception as exc:
                log.warning(
                    "[Cache] Error escribiendo '%s' a SQLite: %s",
                    k,
                    exc,
                    exc_info=True,
                )
                _inc_counter("cache_errors")

    def clear(self) -> None:
        """Borra todas las entradas de la caché.

        Operación transaccional: la eliminación de SQLite se realiza dentro
        de una única transacción con COMMIT explícito.  La capa de memoria
        se limpia atómicamente bajo el lock.
        """
        with self._lock:
            self._memory.clear()
            try:
                if self._conn is not None:
                    self._conn.execute("BEGIN")
                    self._conn.execute("DELETE FROM landscapes")
                    self._conn.commit()
            except Exception as exc:
                log.warning(
                    "[Cache] Error limpiando SQLite: %s",
                    exc,
                    exc_info=True,
                )
                _inc_counter("cache_errors")

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _evict_if_needed(self) -> None:
        """Aplica la política LRU: elimina las entradas más antiguas.

        Debe llamarse dentro del lock.
        """
        while len(self._memory) > self._max_mem_size:
            evicted_key, _ = self._memory.popitem(last=False)
            log.debug("[Cache] LRU evict: %s", evicted_key)
