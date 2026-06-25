# MASSIVE — Frontera `simulator.py` ↔ `multilayer_engine.py`

## Propósito

Aislar y documentar la relación entre `simulator.py` y `multilayer_engine.py`, que en el estado actual del proyecto constituye una frontera importante, útil y potencialmente frágil.

Este documento implementa el **Slice 4 — Aislamiento documental de la frontera `simulator` ↔ `multilayer_engine`**.

---

## 1. Tesis

La relación entre `simulator.py` y `multilayer_engine.py` no es una simple dependencia unidireccional.

Lo observado en el código muestra:
- dependencia directa del simulador hacia `MultilayerEngine`,
- dependencia puntual del motor multicapa hacia `simulator`,
- y un patrón más amplio donde ambos participan del ecosistema integrado de MASSIVE.

Por tanto:

> esta frontera debe tratarse como una frontera de acoplamiento sensible, no como una relación trivial entre módulos independientes.

---

## 2. Dependencia desde `simulator.py` hacia `multilayer_engine.py`

## 2.1. Import directo del tipo principal

### Evidencia
En `simulator.py`:
- `from multilayer_engine import MultilayerEngine`

### Implicación
El simulador reconoce al motor multicapa como dependencia estructural, no solo opcional.

---

## 2.2. Uso dentro de `IntegratedSimulator`

### Evidencia
`IntegratedSimulator.__init__` crea una instancia de `MultilayerEngine`.

Parámetros observados:
- `N`
- `dt`
- `coupling`
- `layer_config`
- `seed`

### Implicación
El motor multicapa forma parte del coordinador de dinámica integrada, no solo de la UI multicapa.

---

## 2.3. Sincronización de estado

### Evidencia
En `IntegratedSimulator.step()`:
- `self.multilayer_engine.update_opinions(self.massive_engine.agents.copy())`

### Implicación
`IntegratedSimulator` usa al motor multicapa como receptor y validador de estado actualizado.

Esto significa que existe un contrato implícito sobre:
- shape del array,
- rango de opinión,
- rango de dimensiones restantes,
- compatibilidad entre el estado de `MassiveEngine` y el de `MultilayerEngine`.

---

## 2.4. Topología dinámica

### Evidencia
En `IntegratedSimulator.update_network_topology()`:
- itera por `self.multilayer_engine.layers.keys()`
- llama `self.multilayer_engine.dynamic_rewiring(...)`

### Implicación
El simulador conoce y usa la estructura de capas internas del motor multicapa.

Eso genera un acoplamiento no solo al API público del motor, sino también a su semántica de capas.

---

## 2.5. Integración con butterfly diagnostics

### Evidencia
En `IntegratedSimulator.run_butterfly_diagnostic()`:
- pasa `self.multilayer_engine.graphs` al snapshot del benchmark

### Implicación
El simulador depende de la propiedad `graphs` como frontera pública del motor multicapa para diagnósticos externos.

---

## 3. Dependencia desde `multilayer_engine.py` hacia `simulator.py`

## 3.1. Consulta de `PROVEEDORES` en `targeted_llm_bias`

### Evidencia
Dentro de `targeted_llm_bias`, `multilayer_engine.py` hace:
- `from simulator import PROVEEDORES as _PROVEEDORES`

### Uso
Obtiene `base_url` del proveedor seleccionado.

### Implicación
Existe dependencia inversa del motor multicapa hacia una constante del simulador.

Esto vuelve la frontera parcialmente bidireccional.

---

## 3.2. Naturaleza del acoplamiento inverso

Este acoplamiento no afecta todo el motor, pero sí una función pública/operativa del módulo:
- `targeted_llm_bias`

Eso basta para volver frágil una reubicación o separación de `PROVEEDORES` si no se deja wrapper.

---

## 4. Fronteras públicas del `MultilayerEngine` consumidas por el simulador

Según la evidencia observada, `simulator.py` consume al menos estas superficies del motor multicapa:

- constructor `MultilayerEngine(...)`
- `update_opinions(...)`
- `dynamic_rewiring(...)`
- propiedad `graphs`
- acceso a `layers.keys()`

### Implicación
La frontera real no es solo “importar el engine”, sino depender de varias capacidades públicas y semipúblicas.

---

## 5. Contratos implícitos entre ambos módulos

## 5.1. Contrato de shape del estado

### Evidencia
`update_opinions()` valida shape `(N, K)`.

### Implicación
El estado producido por `MassiveEngine` y consumido por `MultilayerEngine` debe respetar:
- número de agentes `N`
- número de dimensiones `K`
- layout de columnas

Este contrato es invisible a simple vista, pero es estructural.

---

## 5.2. Contrato de clipping y rangos

### Evidencia
`update_opinions()` hace:
- clip de opinión a `[x_min, x_max]`
- clip del resto de dimensiones a `[0, 1]`

### Implicación
El simulador puede empujar estado al motor multicapa, pero el motor se reserva la validación final del rango.

Hay un contrato de coherencia matemática entre ambos.

---

## 5.3. Contrato de semántica de capas

### Evidencia
`dynamic_rewiring()` espera nombres de capa conocidos.
`graphs` expone capas como matrices CSR.
`IntegratedSimulator` itera sobre `self.multilayer_engine.layers.keys()`.

### Implicación
El simulador depende de que el motor multicapa mantenga una semántica estable de capas.

---

## 5.4. Contrato de infraestructura LLM parcial

### Evidencia
`targeted_llm_bias()` depende de `PROVEEDORES`.

### Implicación
La infraestructura de proveedores está acoplada entre ambos módulos, aunque de forma puntual.

---

## 6. Consumers externos que amplían la sensibilidad de la frontera

No solo el simulador depende del motor multicapa. También hay otros consumers que elevan la sensibilidad de esta frontera:

### `app.py`
Usa:
- `MultilayerEngine`
- `generate_attributes`
- constantes como `COL_OPINION`, `COL_COOP`, `K`
- `targeted_llm_bias`

### `cfc_trainer.py`
Usa:
- `generate_attributes`
- `compute_theta`

### `tests/test_multilayer.py`
Valida:
- comportamiento del engine
- normalización de pesos
- clipping
- rendimiento
- shape del estado
- generadores de red
- utilidades numéricas

### `massive_engine.py`
Usa:
- `multi_potential_gradient`
- `multilayer_langevin_step`
- generadores de red multicapa

### Implicación
Aunque este slice se centra en la frontera con `simulator.py`, el módulo `multilayer_engine.py` ya es nodo relevante para varios dominios. Tocar esta frontera puede irradiar efectos indirectos.

---

## 7. Riesgos específicos

## Riesgo 1 — Separar `MultilayerEngine` del simulador sin wrapper adecuado
Rompería el coordinador `IntegratedSimulator` y probablemente parte de diagnósticos/topología.

## Riesgo 2 — Mover `PROVEEDORES` sin adaptación
Podría romper `targeted_llm_bias()` en `multilayer_engine.py`.

## Riesgo 3 — Cambiar shape del estado integrado
Rompería `update_opinions()` y su validación del estado `(N, K)`.

## Riesgo 4 — Cambiar semántica de capas
Rompería `dynamic_rewiring()`, `graphs` y el uso de topology updates.

## Riesgo 5 — Tocar esta frontera sin considerar a `massive_engine.py`
`massive_engine.py` también depende de varias primitivas del módulo multicapa, así que la frontera real es parte de una triada:
- `simulator.py`
- `multilayer_engine.py`
- `massive_engine.py`

---

## 8. Opciones futuras seguras (solo conceptuales, no para ejecutar aún)

## Opción A — Encapsular config de proveedores en un módulo estable
Objetivo:
- que `multilayer_engine.py` no tenga que importar `PROVEEDORES` desde `simulator.py`

Condición:
- mantener reexport o wrapper estable durante transición

## Opción B — Definir interfaz explícita del motor multicapa consumida por el simulador
Objetivo:
- formalizar qué subset del API usa `IntegratedSimulator`

Condición:
- no cambiar el engine completo, solo documentar o encapsular su superficie usada

## Opción C — Documentar o tipar el estado `(N, K)` compartido
Objetivo:
- hacer explícito el contrato de shape y clipping entre engines

Condición:
- coexistir primero con el estado actual, no reemplazarlo de golpe

## Opción D — Separar helpers públicos del multicapa de los acoplamientos UI/LLM
Objetivo:
- distinguir mejor entre núcleo numérico y utilidades orientadas a narrativa/UX

Condición:
- hacerlo por slices pequeños, porque `app.py`, `cfc_trainer.py` y `massive_engine.py` también consumen este módulo

---

## 9. Reglas derivadas para consolidación

1. No intervenir esta frontera como primer slice técnico.
2. Si se toca `PROVEEDORES`, validar también `targeted_llm_bias()`.
3. Si se toca `MultilayerEngine`, validar también:
   - `IntegratedSimulator`
   - `massive_engine.py`
   - `app.py`
   - `cfc_trainer.py`
   - `tests/test_multilayer.py`
4. Tratar `update_opinions()`, `graphs` y `dynamic_rewiring()` como frontera pública efectiva.
5. Considerar esta relación como parte de una triada con `massive_engine.py`, no como un vínculo aislado.

---

## 10. Conclusión

La frontera `simulator.py` ↔ `multilayer_engine.py` es útil pero delicada.

No es solo una dependencia de implementación. Es una frontera donde confluyen:
- simulación integrada,
- topología dinámica,
- clipping y shape del estado,
- diagnósticos,
- configuración de proveedores,
- y consumers externos adicionales.

Por eso, cualquier consolidación futura debe tratar esta frontera con slices pequeños, wrappers estables y validación cruzada explícita.
