from social_architect import evaluar_resultado

CONSENSUS_SUCCESS_THRESHOLD = 90


def test_evaluar_resultado_consenso():
    # Opinions tightly clustered around neutral (0.5) to represent genuine consensus
    objetivo = "consenso"
    historial = [
        {"opinion": 0.49},
        {"opinion": 0.50},
        {"opinion": 0.51},
        {"opinion": 0.50},
        {"opinion": 0.49},
    ]
    config = {}

    score, feedback = evaluar_resultado(historial, objetivo, config)

    assert score >= CONSENSUS_SUCCESS_THRESHOLD
    assert "éxito" in feedback.lower() or "convergió" in feedback.lower()


def test_evaluar_resultado_falla_polarizacion():
    # Simulate a network that should have reached consensus but remained extremely partisan
    objetivo = "despolarizar"
    historial = [
        {"opinion": 0.9},
        {"opinion": 0.95},
    ]
    config = {}

    score, feedback = evaluar_resultado(historial, objetivo, config)

    assert score < CONSENSUS_SUCCESS_THRESHOLD
    assert len(feedback) > 0


def test_parsear_estrategia_json_regex():
    # Verify that the JSON extraction regex works correctly on LLM-style output
    json_text = """
    ```json
    {
      "falso_json": false,
      "estrategias": [
        {"time_start": 0, "time_end": 5, "model_name": "lineal", "parameters": {}, "fase_rationale": "Init"}
      ]
    }
    ```
    """
    import re

    match = re.search(r"```json\s*(.*?)\s*```", json_text, re.DOTALL)
    assert match is not None
    assert "falso_json" in match.group(1)
