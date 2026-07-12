"""
micro_ui.py — Interfaz Streamlit para MASSIVE Micro
Pestaña de simulación inversa de grupos pequeños
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from micro_schemas import GroupProfile, MemberProfile
from micro_engine import analyze_group, MicroSocialArchitect


def render_micro_tab():
    """Renderiza la pestaña Micro en la UI de MASSIVE."""
    st.markdown("### 🔬 Micro — Familias de Futuros")
    st.markdown(
        "Simulación inversa para grupos pequeños: ejecuta cientos de simulaciones, "
        "descubre las **familias de futuros** posibles para el grupo, "
        "e identifica **qué parámetros determinan** en qué familia cae."
    )
    st.caption(
        "No predice 'qué va a pasar'. Revela las bifurcaciones del sistema."
    )

    # --- Configuración del grupo ---
    with st.expander("⚙️ Configurar Grupo", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            n_members = st.number_input("Miembros", min_value=3, max_value=15, value=5)
            context = st.selectbox(
                "Contexto",
                ["friends", "family", "work", "couple", "neighbors", "custom"],
                index=2,
                format_func=lambda x: {
                    "friends": "Amigos", "family": "Familia", "work": "Trabajo",
                    "couple": "Pareja", "neighbors": "Vecinos", "custom": "Personalizado",
                }.get(x, x),
            )
        with c2:
            comm_freq = st.slider("Frecuencia de comunicación", 0.0, 1.0, 0.4, 0.05,
                                  help="Qué tanto interactúan los miembros")
            hier_tol = st.slider("Tolerancia jerárquica", 0.0, 1.0, 0.3, 0.05,
                                 help="Qué tan aceptada es la autoridad")
        with c3:
            ext_pressure = st.slider("Presión externa", 0.0, 1.0, 0.15, 0.05,
                                     help="Influencia del exterior sobre el grupo")
            diversity = st.slider("Diversidad de opinión", 0.0, 1.0, 0.3, 0.05,
                                  help="Qué tan diferentes son las opiniones iniciales")

    # --- Miembros individuales ---
    with st.expander("👥 Perfiles de Miembros (opcional)"):
        st.caption("Ajusta sesgos individuales. Si no se configuran, se usan valores neutros.")
        members = []
        cols = st.columns(min(n_members, 5))
        for i in range(n_members):
            col = cols[i % len(cols)]
            with col:
                st.markdown(f"**Miembro {i+1}**")
                name = st.text_input(f"Nombre {i}", key=f"m_name_{i}", label_visibility="collapsed",
                                     placeholder=f"M{i+1}")
                role = st.selectbox(
                    f"Rol {i}", ["", "líder", "mediador", "introvertido", "rebelde",
                                 "conciliador", "saboteador", "seguidor"],
                    key=f"m_role_{i}", label_visibility="collapsed",
                )
                coop = st.slider(f"Coop {i}", 0.0, 1.0, 0.5, 0.1, key=f"m_coop_{i}",
                                 label_visibility="collapsed")
                trust = st.slider(f"Trust {i}", 0.0, 1.0, 0.5, 0.1, key=f"m_trust_{i}",
                                  label_visibility="collapsed")
                members.append(MemberProfile(
                    name=name or f"M{i+1}",
                    role=role or "miembro",
                    cooperation_bias=coop,
                    trust_bias=trust,
                ))

    # --- Configuración del ensemble ---
    with st.expander("🎲 Configuración del Ensemble"):
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            n_sims = st.number_input("Número de simulaciones", min_value=50, max_value=5000,
                                     value=200, step=50,
                                     help="Más simulaciones = mejor detección de familias, pero más lento")
        with ec2:
            n_steps = st.number_input("Pasos por simulación", min_value=20, max_value=500,
                                      value=100, step=20)
        with ec3:
            n_clusters = st.number_input("Clusters (0=auto)", min_value=0, max_value=10,
                                         value=0)

        st.caption(
            "Parámetros a variar: "
            "**Coupling** (comunicación), "
            "**Presión externa**, "
            "**Ruido inicial** (incertidumbre)"
        )

    profile = GroupProfile(
        n_members=n_members,
        context=context,
        communication_frequency=comm_freq,
        hierarchy_tolerance=hier_tol,
        external_pressure=ext_pressure,
        diversity_of_opinion=diversity,
        members=members,
    )

    if st.button("🔬 Ejecutar Análisis de Futuros", type="primary", use_container_width=True):
        with st.spinner(f"Ejecutando {n_sims} simulaciones en paralelo..."):
            try:
                result = analyze_group(
                    profile=profile,
                    n_simulations=n_sims,
                    steps_per_sim=n_steps,
                    n_clusters=n_clusters,
                    use_dask=True,
                )
                st.session_state["micro_result"] = result
                st.success(f"Análisis completado — {len(result['families'])} familias de futuros encontradas")
            except Exception as e:
                st.error(f"Error en el análisis: {e}")
                import traceback
                st.code(traceback.format_exc())

    # --- Mostrar resultados ---
    if "micro_result" in st.session_state and st.session_state["micro_result"] is not None:
        result = st.session_state["micro_result"]
        families = result["families"]
        bif = result["bifurcation"]
        architect = result.get("architect")
        labels = result.get("labels", np.array([]))

        if not families:
            st.warning("No se encontraron familias diferenciadas. Intenta con más simulaciones o mayor variación paramétrica.")
            return

        # --- Métricas principales ---
        st.markdown("---")
        st.markdown("### 📊 Resumen del Análisis")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Simulaciones", result["n_simulations"])
        with m2:
            st.metric("Familias encontradas", len(families))
        with m3:
            max_fam = max(families, key=lambda f: f["proportion"])
            st.metric("Familia dominante", f"{max_fam['label'][:16]}", f"{max_fam['proportion']:.0%}")
        with m4:
            stability = max(f["mean_features"].get("stability", 0) for f in families) if families else 0
            st.metric("Inestabilidad máxima", f"{stability:.3f}",
                      delta="⚠️" if stability > 0.05 else "✅",
                      delta_color="inverse")

        # --- Familias de futuros ---
        st.markdown("### 🌌 Familias de Futuros")
        st.caption(
            "Cada familia es un cluster de trayectorias con dinámica similar. "
            "Revelan los **futuros posibles** del grupo bajo diferentes condiciones."
        )

        for i, fam in enumerate(families):
            with st.container():
                risk_badge = ""
                if fam["risk_flags"]:
                    risk_badge = " ⚠️ " + " | ".join(fam["risk_flags"])

                st.markdown(
                    f"""<div class="metric-card">
                    <div class="metric-label">Familia {fam['id']} · {fam['proportion']:.0%} de las simulaciones</div>
                    <div class="metric-value" style="font-size:1.2rem">{fam['label']}</div>
                    <div style="color:#8ba7c0;font-size:0.85rem">{fam['description']}{risk_badge}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

                # Radar chart de features
                feat_keys = ["polarization", "cooperation", "trust", "hierarchy_mean", "opinion_delta"]
                feat_labels = ["Polarización", "Cooperación", "Confianza", "Jerarquía", "Cambio"]
                feat_vals = [fam["mean_features"].get(k, 0) for k in feat_keys]

                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=feat_vals + [feat_vals[0]],
                    theta=feat_labels + [feat_labels[0]],
                    fill="toself",
                    name=fam['label'],
                    line=dict(color=["#5ccfe6", "#ff8f40", "#bae67e", "#c3a6ff", "#ff6b6b"][i % 5]),
                ))
                fig_radar.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#0a0e14",
                    plot_bgcolor="#0d1520",
                    margin=dict(l=40, r=40, t=10, b=10),
                    height=250,
                    showlegend=False,
                )
                st.plotly_chart(fig_radar, use_container_width=True)

                # Parámetros arquetípicos
                if fam["archetype_params"]:
                    st.caption(
                        "Parámetros típicos: "
                        + " · ".join(
                            f"{k}={v:.2f}" for k, v in fam["archetype_params"].items()
                        )
                    )

        # --- Mapa de bifurcación ---
        st.markdown("### 🔀 Mapa de Bifurcación")
        st.caption(
            "Qué parámetros determinan en qué familia de futuros cae el grupo. "
            "A mayor importancia, más impacto tiene ese parámetro en la dinámica."
        )

        if bif.get("param_importances"):
            params_df = pd.DataFrame([
                {"Parámetro": k, "Importancia": v}
                for k, v in sorted(bif["param_importances"].items(), key=lambda x: -x[1])
            ])
            fig_imp = go.Figure()
            fig_imp.add_trace(go.Bar(
                x=params_df["Importancia"],
                y=params_df["Parámetro"],
                orientation="h",
                marker=dict(color="#5ccfe6"),
                text=[f"{v:.1%}" for v in params_df["Importancia"]],
                textposition="outside",
            ))
            fig_imp.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0a0e14",
                plot_bgcolor="#0d1520",
                height=200,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Importancia (0-1)",
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_imp, use_container_width=True)

            st.markdown("**Lectura:**")
            param_labels = {
                "coupling": "**Coupling** — la frecuencia con que los miembros se comunican. "
                            "Alta importancia significa que mejorar la comunicación cambia radicalmente el futuro del grupo.",
                "external_pressure": "**Presión externa** — influencias del exterior (jefe, familia, sociedad). "
                                     "Alta importancia = el grupo es muy sensible a su entorno.",
                "initial_noise": "**Ruido inicial** — incertidumbre en las relaciones al inicio. "
                                 "Alta importancia = el grupo es sensible a cómo empieza.",
            }
            top_param = params_df.iloc[0]["Parámetro"]
            st.info(param_labels.get(top_param, f"**{top_param}** es el factor más determinante."))

        # --- Transiciones entre familias ---
        if len(families) >= 2 and architect:
            st.markdown("### 🔄 Arquitecto Social Micro")
            st.caption(
                "Selecciona dos familias: la actual y la deseada. "
                "El sistema te dice qué parámetros cambiar para transicionar."
            )

            col_from, col_to = st.columns(2)
            with col_from:
                from_id = st.selectbox(
                    "Familia actual",
                    options=[f["id"] for f in families],
                    format_func=lambda fid: f"#{fid}: {next(f['label'] for f in families if f['id']==fid)}",
                )
            with col_to:
                to_id = st.selectbox(
                    "Familia deseada",
                    options=[f["id"] for f in families if f["id"] != from_id],
                    format_func=lambda fid: f"#{fid}: {next(f['label'] for f in families if f['id']==fid)}",
                )

            if st.button("🔍 Encontrar Transición"):
                transition = architect.find_transition(families, bif, from_id, to_id)
                if "error" in transition:
                    st.error(transition["error"])
                else:
                    st.markdown(
                        f"""<div class="metric-card">
                        <div class="metric-label">Transición: {transition.get('from_label','?')} → {transition.get('to_label','?')}</div>
                        <div class="metric-value" style="font-size:0.9rem">{transition.get('recommendation','')}</div>
                        <div style="color:#3d5166;font-size:0.75rem">Costo de transición: {transition.get('cost',0):.3f}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                    # Narrativa
                    if st.button("💬 Generar Narrativa"):
                        narrative = architect.suggest_narrative(transition)
                        st.info(narrative)

        # --- Distribución paramétrica por familia ---
        if len(families) >= 2 and len(result.get("param_records", [])) > 0:
            st.markdown("### 📈 Distribución de Parámetros por Familia")
            st.caption("Cómo se distribuyen los parámetros en cada familia. Útil para entender qué separa a cada grupo.")

            param_keys = list(result["param_records"][0].keys())
            param_records = result["param_records"]
            labels_arr = labels if len(labels) == len(param_records) else np.array([])

            if len(param_records) > 0 and len(labels_arr) > 0:
                df_params = pd.DataFrame(param_records)
                df_params["familia"] = labels_arr

                fig_box = go.Figure()
                colors = ["#5ccfe6", "#ff8f40", "#bae67e", "#c3a6ff", "#ff6b6b"]
                for i, pk in enumerate(param_keys):
                    for fid in sorted(df_params["familia"].unique()):
                        if fid < 0:
                            continue
                        subset = df_params[df_params["familia"] == fid][pk]
                        if len(subset) < 2:
                            continue
                        fig_box.add_trace(go.Box(
                            y=subset,
                            name=f"{pk} [F{fid}]",
                            marker_color=colors[fid % len(colors)],
                            boxmean=True,
                        ))
                fig_box.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#0a0e14",
                    plot_bgcolor="#0d1520",
                    height=300,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=False,
                )
                st.plotly_chart(fig_box, use_container_width=True)

    else:
        st.info("Configura el grupo y ejecuta el análisis para ver resultados.")
