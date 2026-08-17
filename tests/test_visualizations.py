import plotly.graph_objects as go

from visualizations import generate_social_network_viz


def test_generate_social_network_viz_success():
    """
    Test that the synthetic network visualization constructs a valid Plotly Figure
    without throwing matrix inversion or dimension mismatch errors.
    """
    opinion_media = 0.5
    confianza = 0.8
    # Keep n_nodes low for fast unit tests

    fig = generate_social_network_viz(opinion_media, confianza, n_nodes=10, is_bipolar=False)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # 1 edge trace, 1 node trace
    assert fig.layout.title.text == "Topología de Red Endógena (Simulación Abstracción)"


def test_generate_social_network_viz_bipolar():
    """
    Test bipolar topology rendering
    """
    fig = generate_social_network_viz(0.0, 0.2, n_nodes=10, is_bipolar=True)
    assert isinstance(fig, go.Figure)
