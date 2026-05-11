"""
cfc_trainer.py — Pipeline de generación de datasets y entrenamiento de modelos CfC.

Genera datasets usando el simulador MASSIVE con proveedor='heurístico'
(sin necesidad de API) y entrena los modelos CfC por knowledge distillation:
el selector heurístico actúa como 'profesor'.

Uso rápido::

    from cfc_trainer import generate_regime_dataset, train_regime_selector
    train_regime_selector(generate_regime_dataset(n_simulations=10_000))

    from cfc_trainer import generate_tau_dataset, train_tau_matrix
    train_tau_matrix(generate_tau_dataset(n_samples=5_000))

Los modelos entrenados se guardan en models/ y son cargados automáticamente
por CfCRouter al iniciar MASSIVE.

Autor: MASSIVE Research
"""

import logging
from pathlib import Path

import numpy as np

log = logging.getLogger("massive")

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)


# ============================================================
# GENERADORES DE DATASETS
# ============================================================

def generate_regime_dataset(
    n_simulations: int = 10_000,
    window_size: int = 6,
    pasos: int = 60,
) -> Path:
    """
    Genera un dataset de selección de régimen usando el simulador heurístico.

    El selector heurístico existente actúa como profesor (knowledge distillation).
    Cada muestra es (ventana_historial, vector_estado) → régimen_elegido.

    Args:
        n_simulations: Número de simulaciones a ejecutar.
        window_size:   Pasos de historial por muestra.
        pasos:         Pasos de tiempo por simulación.

    Returns:
        Path al archivo .pt con el dataset guardado.
    """
    try:
        import torch
    except ImportError:
        raise ImportError(
            "PyTorch no instalado. Ejecuta: pip install torch>=2.2.0"
        )

    from simulator import simular, DEFAULT_CONFIG

    X_hist, X_state, Y = [], [], []
    cfg = {**DEFAULT_CONFIG, "proveedor": "heurístico", "pasos": pasos}

    rng = np.random.default_rng(42)

    for i in range(n_simulations):
        cfg["opinion_inicial"] = float(rng.uniform(0.1, 0.9))
        cfg["propaganda"] = float(rng.uniform(0.2, 0.8))
        cfg["confianza"] = float(rng.uniform(0.2, 0.8))
        cfg["opinion_grupo_a"] = float(rng.uniform(0.5, 0.95))
        cfg["opinion_grupo_b"] = float(rng.uniform(0.05, 0.5))

        estado_ini = {
            "opinion": cfg["opinion_inicial"],
            "propaganda": cfg["propaganda"],
            "confianza": cfg["confianza"],
            "opinion_grupo_a": cfg["opinion_grupo_a"],
            "opinion_grupo_b": cfg["opinion_grupo_b"],
            "pertenencia_grupo": float(rng.uniform(0.4, 0.8)),
        }

        historial = simular(
            estado_ini,
            escenario="campana",
            pasos=pasos,
            cada_n_pasos=5,
            config=cfg,
            verbose=False,
        )

        traj = [h["opinion"] for h in historial]
        regimes = [h.get("_regla", 0) for h in historial]

        for t in range(window_size, len(traj)):
            X_hist.append(traj[t - window_size:t])
            X_state.append([
                traj[t - 1],
                cfg["propaganda"],
                cfg["confianza"],
                cfg["opinion_grupo_a"],
                cfg["opinion_grupo_b"],
                0.4,   # trust placeholder
                0.0,   # ews_variance placeholder
                0.0,   # ews_autocorr placeholder
            ])
            Y.append(regimes[t - 1])

        if (i + 1) % 1000 == 0:
            log.info(f"[CfC trainer] {i + 1}/{n_simulations} simulaciones — {len(Y):,} muestras")

    path = MODELS_DIR / "dataset_regimes.pt"
    torch.save(
        {
            "X_hist": torch.tensor(X_hist, dtype=torch.float32),
            "X_state": torch.tensor(X_state, dtype=torch.float32),
            "Y": torch.tensor(Y, dtype=torch.long),
        },
        path,
    )
    log.info(f"[CfC trainer] Dataset guardado: {len(Y):,} muestras → {path}")
    return path


def generate_tau_dataset(
    n_samples: int = 5_000,
) -> Path:
    """
    Genera un dataset de matrices τ sociodemográficas desde multilayer_engine.

    Crea agentes sintéticos con atributos aleatorios y calcula la modulación
    theta usando la función compute_theta() existente como etiqueta.

    Args:
        n_samples: Número de agentes sintéticos a generar.

    Returns:
        Path al archivo .pt con el dataset guardado.
    """
    try:
        import torch
    except ImportError:
        raise ImportError(
            "PyTorch no instalado. Ejecuta: pip install torch>=2.2.0"
        )

    from multilayer_engine import generate_attributes, compute_theta

    rng = np.random.default_rng(0)

    # Atributos: religion, education, age_norm, gender
    attrs_df = generate_attributes(n_samples, seed=0)
    theta = compute_theta(attrs_df)  # (N, K=5)

    # Normalizar theta a escala [0, 1] por columna para entrenamiento estable
    theta_min = theta.min(axis=0, keepdims=True)
    theta_max = theta.max(axis=0, keepdims=True)
    theta_norm = (theta - theta_min) / (theta_max - theta_min + 1e-8)

    attrs_array = np.stack([
        attrs_df["religion"].to_numpy(dtype=np.float32),
        attrs_df["education"].to_numpy(dtype=np.float32),
        (attrs_df["age_group"].to_numpy(dtype=np.float32) / 3.0),  # norm a [0,1]
        attrs_df["gender"].to_numpy(dtype=np.float32),
    ], axis=1)

    path = MODELS_DIR / "dataset_tau.pt"
    torch.save(
        {
            "X_attrs": torch.tensor(attrs_array, dtype=torch.float32),
            "Y_tau": torch.tensor(theta_norm.astype(np.float32)),
        },
        path,
    )
    log.info(f"[CfC trainer] Dataset tau guardado: {n_samples:,} agentes → {path}")
    return path


# ============================================================
# ENTRENADORES
# ============================================================

def train_regime_selector(
    dataset_path: Path,
    epochs: int = 30,
    lr: float = 3e-4,
    batch_size: int = 256,
) -> Path:
    """
    Entrena el selector de régimen CfC por knowledge distillation.

    Args:
        dataset_path: Path al dataset generado por generate_regime_dataset().
        epochs:       Número de épocas de entrenamiento.
        lr:           Tasa de aprendizaje Adam.
        batch_size:   Tamaño de lote.

    Returns:
        Path al modelo entrenado guardado.
    """
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError:
        raise ImportError(
            "PyTorch no instalado. Ejecuta: pip install torch>=2.2.0"
        )

    from cfc_engine import CfCRegimeSelector

    data = torch.load(dataset_path, weights_only=True)
    dl = DataLoader(
        TensorDataset(data["X_hist"], data["X_state"], data["Y"]),
        batch_size=batch_size,
        shuffle=True,
    )

    model = CfCRegimeSelector(window_size=6, state_dim=8, hidden=64)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()

    model.train()
    for ep in range(epochs):
        total_loss = 0.0
        n_batches = 0
        for Xh, Xs, Yb in dl:
            logits = model(Xh, Xs)
            loss = loss_fn(logits, Yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1

        if ep % 5 == 0 or ep == epochs - 1:
            log.info(
                f"[CfC trainer] Selector epoch {ep:02d}/{epochs} "
                f"| loss {total_loss / max(n_batches, 1):.4f}"
            )

    path = MODELS_DIR / "cfc_selector.pt"
    torch.save(model.state_dict(), path)
    log.info(f"[CfC trainer] Selector guardado → {path}")
    return path


def train_tau_matrix(
    dataset_path: Path,
    epochs: int = 50,
    lr: float = 1e-3,
    batch_size: int = 256,
) -> Path:
    """
    Entrena el generador de matriz τ sociodemográfica CfC.

    Args:
        dataset_path: Path al dataset generado por generate_tau_dataset().
        epochs:       Número de épocas de entrenamiento.
        lr:           Tasa de aprendizaje Adam.
        batch_size:   Tamaño de lote.

    Returns:
        Path al modelo entrenado guardado.
    """
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError:
        raise ImportError(
            "PyTorch no instalado. Ejecuta: pip install torch>=2.2.0"
        )

    from cfc_engine import CfCTauMatrix

    data = torch.load(dataset_path, weights_only=True)
    dl = DataLoader(
        TensorDataset(data["X_attrs"], data["Y_tau"]),
        batch_size=batch_size,
        shuffle=True,
    )

    model = CfCTauMatrix(attr_dim=4, behavior_dim=5)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    for ep in range(epochs):
        total_loss = 0.0
        n_batches = 0
        for Xa, Yt in dl:
            pred = model(Xa)
            loss = loss_fn(pred, Yt)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1

        if ep % 10 == 0 or ep == epochs - 1:
            log.info(
                f"[CfC trainer] Tau epoch {ep:02d}/{epochs} "
                f"| MSE {total_loss / max(n_batches, 1):.6f}"
            )

    path = MODELS_DIR / "cfc_tau.pt"
    torch.save(model.state_dict(), path)
    log.info(f"[CfC trainer] Tau matrix guardada → {path}")
    return path


# ============================================================
# ENTRYPOINT CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Entrenar modelos CfC para MASSIVE"
    )
    parser.add_argument(
        "--component",
        choices=["selector", "tau", "all"],
        default="all",
        help="Qué componente entrenar (default: all)",
    )
    parser.add_argument(
        "--n-sims",
        type=int,
        default=10_000,
        help="Simulaciones para el dataset de selector (default: 10000)",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=5_000,
        help="Agentes para el dataset de tau (default: 5000)",
    )
    parser.add_argument(
        "--epochs-selector",
        type=int,
        default=30,
        help="Épocas para entrenar el selector (default: 30)",
    )
    parser.add_argument(
        "--epochs-tau",
        type=int,
        default=50,
        help="Épocas para entrenar tau (default: 50)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if args.component in ("selector", "all"):
        log.info("[CfC] Generando dataset de regímenes...")
        ds_path = generate_regime_dataset(n_simulations=args.n_sims)
        log.info("[CfC] Entrenando selector de régimen...")
        train_regime_selector(ds_path, epochs=args.epochs_selector)

    if args.component in ("tau", "all"):
        log.info("[CfC] Generando dataset tau...")
        dt_path = generate_tau_dataset(n_samples=args.n_samples)
        log.info("[CfC] Entrenando matriz tau...")
        train_tau_matrix(dt_path, epochs=args.epochs_tau)

    log.info("[CfC] Entrenamiento completo. Modelos disponibles en models/")
