import networkx as nx
import plotly.graph_objects as go
import numpy as np

def generate_social_network_viz(opinion_mean, confianza, amalgama=False, n_nodes=80, is_bipolar=False):
    """
    Genera una visualización de Plotly de una topología de red sintética
    que representa visualmente el estado macroscópico del simulador MASSIVE.
    """
    G = nx.Graph()
    opinions = []
    
    # Controlamos la dispersión basada en la confianza y polarización implícita
    # Si la opinión está muy al extremo y la confianza es baja, la red suele estar fracturada
    polarizacion_inferida = 1.0 - confianza if not amalgama else 0.2

    for i in range(n_nodes):
        if np.random.rand() < polarizacion_inferida and not amalgama:
            # Comportamiento fragmentado polarizado
            extremo = 1.0 if np.random.rand() > 0.5 else 0.0
            if is_bipolar: extremo = 1.0 if extremo > 0.5 else -1.0
            op = np.random.normal(loc=extremo, scale=0.15)
        else:
            # Comportamiento de consenso normal
            op = np.random.normal(loc=opinion_mean, scale=max(0.05, (1.0 - confianza) * 0.4))
        
        if is_bipolar:
            op = np.clip(op, -1.0, 1.0)
        else:
            op = np.clip(op, 0.0, 1.0)
            
        opinions.append(op)
        G.add_node(i, opinion=op)
        
    # Generar aristas basándose en homofilia (confianza y similitud de opinión)
    # Vectorizado con NumPy para evitar el bucle O(N²) en Python puro.
    # Nota: usa matrices N×N — para n_nodes ≤ 2000 el uso de RAM es negligible
    # (<32 MB); evitar valores mayores en producción si la RAM es limitada.
    op_arr = np.array(opinions)
    diffs = np.abs(op_arr[:, None] - op_arr[None, :])
    probs = np.exp(-diffs * (5.0 * (1.1 - confianza))) * 0.15
    rng_matrix = np.random.rand(n_nodes, n_nodes)
    mask = np.triu(rng_matrix < probs, k=1)
    G.add_edges_from(zip(*np.where(mask)))
                
    # Calcular layout de nodos (físicas de atracción)
    pos = nx.spring_layout(G, k=0.18, iterations=35)
    
    # Extraer arrays para Plotly
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.6, color='#2a364a'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

    colors = opinions
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        text=[f"Agente {i} | Ideología: {op:.2f}" for i, op in enumerate(opinions)],
        marker=dict(
            showscale=True,
            colorscale='RdBu' if is_bipolar else 'Blues',
            reversescale=False,
            color=colors,
            size=12,
            colorbar=dict(
                thickness=12,
                title=dict(
                    text='Ideología',
                    side='right',
                    font=dict(color='#5ccfe6', size=12),
                ),
                xanchor='left',
                tickfont=dict(color='#8ba7c0', size=10),
            ),
            line_width=1.5,
            line_color='#0a0e14'
        ))

    fig = go.Figure(data=[edge_trace, node_trace],
             layout=go.Layout(
                title=dict(
                    text='Topología de Red Endógena (Simulación Abstracción)',
                    font=dict(size=14, color='#5ccfe6', family='monospace'),
                ),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20,l=5,r=5,t=40),
                plot_bgcolor='#0d1520',
                paper_bgcolor='#0d1520',
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                )
    return fig
