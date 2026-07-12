import { useState, useRef, useCallback } from "react";

// ── Paleta MASSIVE (IBM Plex, oscuro) ─────────────────────────────────────
const C = {
  bg:      "#0a0e14",
  panel:   "#0d1520",
  border:  "#1a2535",
  accent:  "#5ccfe6",
  green:   "#bae67e",
  orange:  "#ff8f40",
  purple:  "#c3a6ff",
  red:     "#ff3333",
  muted:   "#3d5166",
  text:    "#c5cdd9",
  textDim: "#6b7f96",
};

// ── Helpers ────────────────────────────────────────────────────────────────
const sleep = ms => new Promise(r => setTimeout(r, ms));

const TAG_COLORS = {
  pdf: C.orange, json: C.green, csv: C.accent,
  xlsx: C.purple, img: "#ffd580", txt: C.muted,
};

function Badge({ type }) {
  return (
    <span style={{
      fontFamily: "'IBM Plex Mono', monospace",
      fontSize: 10, padding: "2px 8px", borderRadius: 3,
      background: TAG_COLORS[type] + "22",
      color: TAG_COLORS[type], border: `1px solid ${TAG_COLORS[type]}44`,
      letterSpacing: 1, textTransform: "uppercase",
    }}>{type}</span>
  );
}

function Chip({ label, value, confidence }) {
  const col = confidence > 0.7 ? C.green : confidence > 0.4 ? C.orange : C.red;
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "6px 12px", borderRadius: 4, marginBottom: 6,
      background: C.bg, border: `1px solid ${C.border}`,
      borderLeft: `3px solid ${col}`,
    }}>
      <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: C.muted, letterSpacing: 1 }}>
        {label}
      </span>
      <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 13, fontWeight: 700, color: col }}>
        {typeof value === "number" ? value.toFixed(2) : String(value)}
      </span>
    </div>
  );
}

function Spinner({ small }) {
  return (
    <span style={{
      display: "inline-block",
      width: small ? 12 : 18, height: small ? 12 : 18,
      border: `2px solid ${C.muted}`,
      borderTopColor: C.accent,
      borderRadius: "50%",
      animation: "spin 0.7s linear infinite",
      flexShrink: 0,
    }} />
  );
}

// ── Archivos de ejemplo (simulan uploads reales) ──────────────────────────
const SAMPLE_FILES = [
  {
    id: "pdf1", name: "Encuesta_Polarizacion_CDMX_2025.pdf", type: "pdf",
    size: "2.4 MB", pages: 34,
    preview: `ESTUDIO DE OPINIÓN PÚBLICA — CIUDAD DE MÉXICO, Q3 2025

Muestra: 4,200 ciudadanos. Margen de error: ±1.5%

HALLAZGOS PRINCIPALES:
• Índice de polarización política: 78/100 (crítico)
• Confianza en instituciones gubernamentales: 18%
• Identificación con narrativa oficial: 23% (apoyo), 61% (rechazo), 16% (neutro)
• Homofilia digital: 84% de usuarios solo interactúa con afines en redes
• Sesgo de confirmación estimado (escala Nickerson): 0.71

DISTRIBUCIÓN POR GRUPOS:
• Grupo A (oficialismo): μ_opinión = +0.72, σ = 0.18, 31% de la muestra
• Grupo B (oposición):   μ_opinión = -0.81, σ = 0.14, 52% de la muestra
• Indecisos:             μ_opinión = +0.04, σ = 0.31, 17% de la muestra

SERIE TEMPORAL (índice bipolar, últimos 6 trimestres):
Q2-2024: -0.21 | Q3-2024: -0.38 | Q4-2024: -0.52
Q1-2025: -0.61 | Q2-2025: -0.68 | Q3-2025: -0.74

Recomendación: Simulación con modelo Hegselmann-Krause (epsilon=0.15).`,
  },
  {
    id: "json1", name: "config_simulacion_barcelona.json", type: "json",
    size: "18 KB",
    preview: JSON.stringify({
      estudio: "Movimiento independentista catalán — modelo post-referéndum",
      fecha: "2025-11",
      parametros_empiricos: {
        opinion_inicial: -0.12,
        confianza_institucional: 0.24,
        narrativa_oficial: 0.35,
        grupos: {
          independentistas: { opinion: 0.88, peso_poblacional: 0.47 },
          unionistas:       { opinion: -0.76, peso_poblacional: 0.43 },
          indecisos:        { opinion: 0.05, peso_poblacional: 0.10 }
        },
        mecanismos: {
          sesgo_confirmacion: 0.65,
          homofilia_estimada: 0.79,
          influencia_redes_sociales: 0.71
        }
      },
      red_social: {
        nodos_estimados: 5800000,
        tipo_topologia: "scale-free",
        coeficiente_clustering: 0.38,
        comunidades_detectadas: 4
      },
      modelo_recomendado: "competitive_contagion",
      horizonte_simulacion_pasos: 200
    }, null, 2),
  },
  {
    id: "csv1", name: "serie_temporal_aprobacion.csv", type: "csv",
    size: "156 KB",
    preview: `fecha,aprobacion_gobierno,confianza_institucional,polarizacion_index,grupo_afin,grupo_opuesto
2024-01,0.31,0.28,0.52,0.65,-0.58
2024-02,0.29,0.26,0.55,0.67,-0.61
2024-03,0.27,0.24,0.58,0.70,-0.63
2024-04,0.24,0.22,0.62,0.72,-0.67
2024-05,0.22,0.20,0.66,0.75,-0.71
2024-06,0.19,0.18,0.71,0.78,-0.74
2024-07,0.17,0.17,0.74,0.80,-0.77
2024-08,0.16,0.16,0.77,0.82,-0.79
2024-09,0.15,0.15,0.79,0.84,-0.81
2024-10,0.14,0.14,0.81,0.85,-0.82
2024-11,0.13,0.13,0.83,0.86,-0.83
2024-12,0.12,0.12,0.84,0.87,-0.84`,
  },
];

// ── Llamada a Anthropic API ───────────────────────────────────────────────
async function callClaude(systemPrompt, userMessage, onChunk) {
  const apiKey = import.meta.env.VITE_ANTHROPIC_API_KEY || "";
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1000,
      system: systemPrompt,
      messages: [{ role: "user", content: userMessage }],
    }),
  });
  const data = await res.json();
  const text = data.content?.[0]?.text || "";
  if (onChunk) {
    for (const ch of text) { onChunk(ch); await sleep(8); }
  }
  return text;
}

// ── Prompts especializados ────────────────────────────────────────────────
const PROMPTS = {
  extract: `Eres el motor de extracción de MASSIVE, simulador de dinámica social.
Analiza el contenido del documento y extrae parámetros de simulación.
Devuelve JSON con esta estructura exacta (sin markdown):
{
  "opinion_inicial": number|null (-1 a 1),
  "confianza": number|null (0 a 1),
  "propaganda": number|null (-1 a 1),
  "opinion_grupo_a": number|null (-1 a 1),
  "opinion_grupo_b": number|null (-1 a 1),
  "identidad_grupo": number|null (0 a 1),
  "sesgo_confirmacion": number|null (0 a 1),
  "homofilia": number|null (0 a 1),
  "pasos": number|null (10-500),
  "regla_sugerida": string|null,
  "archetype_sugerido": string|null,
  "confianza_extraccion": number (0-1),
  "resumen": string (2 oraciones sobre qué encontraste),
  "advertencias": string[]
}`,

  wizard: `Eres el Asistente de Configuración de MASSIVE.
El usuario describe un escenario social en lenguaje natural.
Convierte su descripción en parámetros de simulación.
Devuelve JSON sin markdown:
{
  "opinion_inicial": number|null,
  "confianza": number|null,
  "propaganda": number|null,
  "opinion_grupo_a": number|null,
  "opinion_grupo_b": number|null,
  "identidad_grupo": number|null,
  "sesgo_confirmacion": number|null,
  "homofilia": number|null,
  "pasos": number|null,
  "regla_sugerida": string|null,
  "confianza_extraccion": number,
  "razon": string,
  "advertencias": string[]
}`,

  explain: `Eres un experto en dinámica social que explica parámetros de simulación.
Responde en español con JSON sin markdown:
{
  "analogia": string (analogía cotidiana en 1 oración),
  "efecto": string (qué pasa en la simulación con este valor),
  "consejo": string (cuándo subirlo o bajarlo)
}`,

  narrate: `Eres un analista de ciencias sociales. Genera una síntesis narrativa de resultados de simulación.
Responde en español, formato conversacional pero profesional.
Estructura: diagnóstico (qué ocurrió), mecanismo dominante, implicaciones prácticas, 1 recomendación concreta.
Máximo 150 palabras.`,

  chat: `Eres el Asistente Universal de MASSIVE, simulador híbrido de dinámica social.
Ayudas a usuarios (desde expertos hasta no técnicos) a:
- Entender los parámetros de simulación
- Interpretar resultados
- Configurar escenarios
- Traducir entre lenguaje coloquial y científico

Responde siempre en español, de forma concisa y útil.
Cuando el usuario pida configurar algo, ofrece valores numéricos concretos.`,
};

// ── Componente principal ──────────────────────────────────────────────────
export default function MASSIVEInterpreter() {
  const [activeTab, setActiveTab]       = useState("upload");
  const [uploadedFile, setUploadedFile] = useState(null);
  const [extracting, setExtracting]     = useState(false);
  const [extracted, setExtracted]       = useState(null);
  const [chatHistory, setChatHistory]   = useState([]);
  const [chatInput, setChatInput]       = useState("");
  const [chatLoading, setChatLoading]   = useState(false);
  const [narration, setNarration]       = useState("");
  const [narrateLoading, setNarrateLoading] = useState(false);
  const [isDragging, setIsDragging]     = useState(false);
  const chatEndRef = useRef(null);

  // ── Extracción desde archivo de ejemplo ──────────────────────────────
  const handleExtract = useCallback(async (file) => {
    setUploadedFile(file);
    setExtracting(true);
    setExtracted(null);
    setNarration("");
    setActiveTab("extract");
    try {
      const raw = await callClaude(
        PROMPTS.extract,
        `CONTENIDO DEL ARCHIVO: ${file.name}\n\n${file.preview}`
      );
      let clean = raw.trim();
      if (clean.startsWith("```")) {
        clean = clean.replace(/```json?\n?/, "").replace(/```$/, "");
      }
      const parsed = JSON.parse(clean);
      setExtracted(parsed);
    } catch (e) {
      setExtracted({ error: String(e), resumen: "Error al extraer parámetros." });
    }
    setExtracting(false);
  }, []);

  // ── Chat ──────────────────────────────────────────────────────────────
  const sendChat = useCallback(async (msg) => {
    if (!msg.trim()) return;
    const userMsg = { role: "user", text: msg };
    setChatHistory(h => [...h, userMsg]);
    setChatInput("");
    setChatLoading(true);

    const context = extracted
      ? `\n\nContexto actual de simulación:\n${JSON.stringify(extracted, null, 2)}`
      : "";

    let response = "";
    const botMsg = { role: "assistant", text: "" };
    setChatHistory(h => [...h, botMsg]);

    await callClaude(
      PROMPTS.chat + context,
      msg,
      (ch) => {
        response += ch;
        setChatHistory(h => {
          const copy = [...h];
          copy[copy.length - 1] = { role: "assistant", text: response };
          return copy;
        });
      }
    );
    setChatLoading(false);
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
  }, [extracted]);

  // ── Narración de resultados ───────────────────────────────────────────
  const handleNarrate = useCallback(async () => {
    if (!extracted) return;
    setNarrateLoading(true);
    setNarration("");
    const res = await callClaude(
      PROMPTS.narrate,
      `Parámetros extraídos:\n${JSON.stringify(extracted, null, 2)}\n\nArchivo: ${uploadedFile?.name || "desconocido"}`,
      (ch) => setNarration(n => n + ch)
    );
    setNarrateLoading(false);
  }, [extracted, uploadedFile]);

  // ── UI helpers ────────────────────────────────────────────────────────
  const TABS = [
    { id: "upload",   label: "📂 Fuentes" },
    { id: "extract",  label: "⚙️ Extracción" },
    { id: "chat",     label: "💬 Asistente" },
    { id: "narrate",  label: "📋 Síntesis" },
  ];

  const paramLabel = {
    opinion_inicial: "Opinión inicial", confianza: "Confianza institucional",
    propaganda: "Narrativa dominante", opinion_grupo_a: "Grupo A (afín)",
    opinion_grupo_b: "Grupo B (opuesto)", identidad_grupo: "Identidad de grupo",
    sesgo_confirmacion: "Sesgo confirmación", homofilia: "Homofilia",
    pasos: "Pasos de simulación", regla_sugerida: "Modelo sugerido",
    archetype_sugerido: "Arquetipo sugerido",
  };

  return (
    <div style={{
      fontFamily: "'IBM Plex Sans', sans-serif",
      background: C.bg, color: C.text, minHeight: "100vh",
      display: "flex", flexDirection: "column",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
        ::-webkit-scrollbar { width:6px; height:6px; }
        ::-webkit-scrollbar-track { background: #0d1520; }
        ::-webkit-scrollbar-thumb { background: #1a2535; border-radius:3px; }
        .file-card:hover { border-color: ${C.accent}88 !important; background: ${C.accent}08 !important; cursor:pointer; }
        .tab-btn:hover { color: ${C.accent} !important; }
        .send-btn:hover { background: ${C.accent}22 !important; }
        textarea:focus { outline: none; border-color: ${C.accent}88 !important; }
        .chip-row { animation: fadeIn .3s ease; }
      `}</style>

      {/* Header */}
      <div style={{
        borderBottom: `1px solid ${C.border}`,
        padding: "16px 28px",
        display: "flex", alignItems: "center", gap: 16,
      }}>
        <div style={{
          fontFamily: "'IBM Plex Mono',monospace", fontSize: 22,
          fontWeight: 700, color: C.accent, letterSpacing: -0.5,
        }}>MASSIVE</div>
        <div style={{
          fontFamily: "'IBM Plex Mono',monospace", fontSize: 10,
          color: C.muted, letterSpacing: 3, textTransform: "uppercase",
        }}>Universal Interpreter Layer · UIL v1.0</div>
        {uploadedFile && (
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <Badge type={uploadedFile.type} />
            <span style={{ fontSize: 12, color: C.textDim }}>{uploadedFile.name}</span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex", borderBottom: `1px solid ${C.border}`,
        padding: "0 28px",
      }}>
        {TABS.map(t => (
          <button key={t.id} className="tab-btn" onClick={() => setActiveTab(t.id)} style={{
            background: "none", border: "none", cursor: "pointer",
            fontFamily: "'IBM Plex Mono',monospace", fontSize: 12,
            color: activeTab === t.id ? C.accent : C.muted,
            padding: "12px 20px", letterSpacing: 1,
            borderBottom: activeTab === t.id ? `2px solid ${C.accent}` : "2px solid transparent",
            transition: "all .15s",
          }}>{t.label}</button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: "24px 28px", overflowY: "auto" }}>

        {/* ── TAB: UPLOAD ─────────────────────────────────────────────── */}
        {activeTab === "upload" && (
          <div>
            <div style={{
              fontFamily: "'IBM Plex Mono',monospace", fontSize: 11,
              color: C.muted, letterSpacing: 2, textTransform: "uppercase",
              marginBottom: 20,
            }}>
              Selecciona un archivo de ejemplo para analizar
            </div>

            {/* Drop zone simulado */}
            <div
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={e => { e.preventDefault(); setIsDragging(false); }}
              style={{
                border: `2px dashed ${isDragging ? C.accent : C.border}`,
                borderRadius: 8, padding: "24px 20px",
                textAlign: "center", marginBottom: 24,
                background: isDragging ? `${C.accent}08` : C.panel,
                transition: "all .2s",
              }}
            >
              <div style={{ fontSize: 32, marginBottom: 8 }}>📁</div>
              <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, color: C.muted }}>
                Arrastra PDF · JSON · CSV · XLSX · imágenes
              </div>
              <div style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>
                (en producción MASSIVE acepta uploads reales vía Streamlit)
              </div>
            </div>

            {/* Archivos de ejemplo */}
            <div style={{
              fontFamily: "'IBM Plex Mono',monospace", fontSize: 10,
              color: C.muted, letterSpacing: 2, marginBottom: 12,
            }}>ARCHIVOS DE EJEMPLO REALES</div>

            {SAMPLE_FILES.map(f => (
              <div
                key={f.id}
                className="file-card"
                onClick={() => handleExtract(f)}
                style={{
                  background: C.panel,
                  border: uploadedFile?.id === f.id
                    ? `1px solid ${C.accent}66` : `1px solid ${C.border}`,
                  borderRadius: 6, padding: "14px 18px",
                  marginBottom: 10, transition: "all .15s",
                  display: "flex", alignItems: "flex-start", gap: 16,
                }}
              >
                <div style={{ paddingTop: 2 }}>
                  <Badge type={f.type} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
                    {f.name}
                  </div>
                  <div style={{ fontSize: 12, color: C.textDim }}>
                    {f.size}
                    {f.pages ? ` · ${f.pages} páginas` : ""}
                    {" · "}
                    <span style={{ fontFamily: "'IBM Plex Mono',monospace", color: C.muted }}>
                      {f.preview.slice(0, 80).replace(/\n/g, " ")}…
                    </span>
                  </div>
                </div>
                <div style={{
                  fontFamily: "'IBM Plex Mono',monospace", fontSize: 10,
                  color: C.accent, letterSpacing: 1, paddingTop: 2,
                }}>ANALIZAR →</div>
              </div>
            ))}
          </div>
        )}

        {/* ── TAB: EXTRACCIÓN ─────────────────────────────────────────── */}
        {activeTab === "extract" && (
          <div>
            {extracting && (
              <div style={{
                display: "flex", alignItems: "center", gap: 14,
                padding: "24px 0",
              }}>
                <Spinner />
                <div>
                  <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 13, color: C.accent }}>
                    Analizando documento…
                  </div>
                  <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>
                    Extrayendo series temporales, parámetros sociodemográficos y configuración de red
                  </div>
                </div>
              </div>
            )}

            {!extracting && !extracted && (
              <div style={{
                textAlign: "center", padding: "60px 0",
                color: C.muted, fontFamily: "'IBM Plex Mono',monospace", fontSize: 12,
              }}>
                Selecciona un archivo en la pestaña Fuentes
              </div>
            )}

            {extracted && !extracted.error && (
              <div style={{ animation: "fadeIn .4s ease" }}>
                {/* Resumen */}
                <div style={{
                  background: `${C.accent}11`, border: `1px solid ${C.accent}33`,
                  borderRadius: 6, padding: "14px 18px", marginBottom: 20,
                }}>
                  <div style={{
                    fontFamily: "'IBM Plex Mono',monospace", fontSize: 10,
                    color: C.accent, letterSpacing: 2, marginBottom: 6,
                  }}>SÍNTESIS DEL DOCUMENTO</div>
                  <div style={{ fontSize: 13, lineHeight: 1.6 }}>{extracted.resumen}</div>
                  <div style={{
                    display: "flex", gap: 16, marginTop: 10,
                    fontFamily: "'IBM Plex Mono',monospace", fontSize: 11,
                  }}>
                    <span style={{ color: C.muted }}>Confianza extracción:</span>
                    <span style={{
                      color: extracted.confianza_extraccion > 0.7 ? C.green
                           : extracted.confianza_extraccion > 0.4 ? C.orange : C.red,
                      fontWeight: 700,
                    }}>
                      {(extracted.confianza_extraccion * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {/* Parámetros extraídos */}
                <div style={{
                  fontFamily: "'IBM Plex Mono',monospace", fontSize: 10,
                  color: C.muted, letterSpacing: 2, marginBottom: 12,
                }}>PARÁMETROS EXTRAÍDOS</div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 20 }}>
                  {Object.entries(paramLabel).map(([key, label]) => {
                    const val = extracted[key];
                    if (val === null || val === undefined) return null;
                    return (
                      <div key={key} className="chip-row">
                        <Chip
                          label={label}
                          value={val}
                          confidence={extracted.confianza_extraccion}
                        />
                      </div>
                    );
                  })}
                </div>

                {/* Advertencias */}
                {extracted.advertencias?.length > 0 && (
                  <div style={{
                    background: `${C.orange}11`, border: `1px solid ${C.orange}33`,
                    borderRadius: 6, padding: "12px 16px", marginBottom: 16,
                  }}>
                    <div style={{
                      fontFamily: "'IBM Plex Mono',monospace", fontSize: 10,
                      color: C.orange, letterSpacing: 2, marginBottom: 8,
                    }}>ADVERTENCIAS</div>
                    {extracted.advertencias.map((w, i) => (
                      <div key={i} style={{ fontSize: 12, color: C.text, marginBottom: 4 }}>
                        · {w}
                      </div>
                    ))}
                  </div>
                )}

                {/* Acciones */}
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button
                    onClick={handleNarrate}
                    style={{
                      background: "none", border: `1px solid ${C.accent}`,
                      color: C.accent, padding: "8px 20px", borderRadius: 4,
                      fontFamily: "'IBM Plex Mono',monospace", fontSize: 11,
                      cursor: "pointer", letterSpacing: 1, textTransform: "uppercase",
                    }}
                  >
                    📋 Generar síntesis narrativa
                  </button>
                  <button
                    onClick={() => {
                      setChatHistory([{
                        role: "assistant",
                        text: `He analizado **${uploadedFile?.name}** y extraído ${Object.values(extracted).filter(v=>v!==null && typeof v !== 'object' && !Array.isArray(v)).length} parámetros de simulación. ¿Quieres que te explique algún parámetro o que ajustemos la configuración?`,
                      }]);
                      setActiveTab("chat");
                    }}
                    style={{
                      background: "none", border: `1px solid ${C.purple}`,
                      color: C.purple, padding: "8px 20px", borderRadius: 4,
                      fontFamily: "'IBM Plex Mono',monospace", fontSize: 11,
                      cursor: "pointer", letterSpacing: 1, textTransform: "uppercase",
                    }}
                  >
                    💬 Continuar con asistente
                  </button>
                </div>
              </div>
            )}

            {extracted?.error && (
              <div style={{
                background: `${C.red}11`, border: `1px solid ${C.red}33`,
                borderRadius: 6, padding: 16,
                fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, color: C.red,
              }}>
                Error: {extracted.error}
              </div>
            )}
          </div>
        )}

        {/* ── TAB: CHAT ─────────────────────────────────────────────────── */}
        {activeTab === "chat" && (
          <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 200px)" }}>
            <div style={{ flex: 1, overflowY: "auto", paddingBottom: 16 }}>
              {chatHistory.length === 0 && (
                <div style={{ padding: "40px 0" }}>
                  <div style={{
                    fontFamily: "'IBM Plex Mono',monospace", fontSize: 13,
                    color: C.accent, marginBottom: 16,
                  }}>
                    Asistente Universal MASSIVE
                  </div>
                  <div style={{ fontSize: 13, color: C.textDim, lineHeight: 1.7, marginBottom: 24 }}>
                    Puedo ayudarte a configurar simulaciones, explicar parámetros en lenguaje sencillo,
                    traducir entre términos coloquiales y científicos, o interpretar resultados.
                  </div>
                  {/* Sugerencias */}
                  {[
                    "¿Qué significa sesgo de confirmación de 0.7?",
                    "Hay mucha polarización en mi ciudad, ¿cómo lo configuro?",
                    "¿Qué modelo matemático usar para elecciones polarizadas?",
                    "Explícame la homofilia como si tuviera 12 años",
                  ].map((s, i) => (
                    <div
                      key={i}
                      onClick={() => sendChat(s)}
                      style={{
                        background: C.panel, border: `1px solid ${C.border}`,
                        borderRadius: 4, padding: "10px 14px", marginBottom: 8,
                        cursor: "pointer", fontSize: 12, color: C.text,
                        transition: "all .15s",
                      }}
                      onMouseEnter={e => e.currentTarget.style.borderColor = C.accent + "66"}
                      onMouseLeave={e => e.currentTarget.style.borderColor = C.border}
                    >
                      {s}
                    </div>
                  ))}
                </div>
              )}

              {chatHistory.map((msg, i) => (
                <div key={i} style={{
                  display: "flex",
                  justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                  marginBottom: 12, animation: "fadeIn .25s ease",
                }}>
                  <div style={{
                    maxWidth: "75%", padding: "10px 14px", borderRadius: 6,
                    background: msg.role === "user" ? `${C.accent}22` : C.panel,
                    border: `1px solid ${msg.role === "user" ? C.accent + "44" : C.border}`,
                    fontSize: 13, lineHeight: 1.65,
                    fontFamily: msg.role === "user" ? undefined : undefined,
                  }}>
                    {msg.text || (msg.role === "assistant" && <Spinner small />)}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div style={{
              borderTop: `1px solid ${C.border}`,
              paddingTop: 14, display: "flex", gap: 10,
            }}>
              <textarea
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendChat(chatInput);
                  }
                }}
                placeholder="Pregunta algo o describe tu escenario…"
                rows={2}
                style={{
                  flex: 1, background: C.panel, border: `1px solid ${C.border}`,
                  borderRadius: 4, padding: "10px 14px", color: C.text,
                  fontSize: 13, resize: "none",
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  transition: "border-color .15s",
                }}
              />
              <button
                className="send-btn"
                onClick={() => sendChat(chatInput)}
                disabled={chatLoading || !chatInput.trim()}
                style={{
                  background: "none", border: `1px solid ${C.accent}`,
                  color: C.accent, padding: "0 18px", borderRadius: 4,
                  cursor: "pointer", fontFamily: "'IBM Plex Mono',monospace",
                  fontSize: 11, letterSpacing: 1, transition: "all .15s",
                  opacity: chatLoading || !chatInput.trim() ? 0.4 : 1,
                }}
              >
                {chatLoading ? <Spinner small /> : "ENVIAR"}
              </button>
            </div>
          </div>
        )}

        {/* ── TAB: SÍNTESIS ──────────────────────────────────────────────── */}
        {activeTab === "narrate" && (
          <div>
            {!extracted && (
              <div style={{
                textAlign: "center", padding: "60px 0",
                color: C.muted, fontFamily: "'IBM Plex Mono',monospace", fontSize: 12,
              }}>
                Primero extrae parámetros desde la pestaña Extracción
              </div>
            )}

            {extracted && !narration && !narrateLoading && (
              <div style={{ textAlign: "center", padding: "40px 0" }}>
                <div style={{ fontSize: 13, color: C.textDim, marginBottom: 20 }}>
                  Genera una síntesis narrativa de los parámetros extraídos de
                  <span style={{ color: C.accent }}> {uploadedFile?.name}</span>
                </div>
                <button
                  onClick={handleNarrate}
                  style={{
                    background: "none", border: `1px solid ${C.accent}`,
                    color: C.accent, padding: "10px 28px", borderRadius: 4,
                    fontFamily: "'IBM Plex Mono',monospace", fontSize: 12,
                    cursor: "pointer", letterSpacing: 1, textTransform: "uppercase",
                  }}
                >
                  ▶ Generar síntesis
                </button>
              </div>
            )}

            {narrateLoading && (
              <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "24px 0" }}>
                <Spinner />
                <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, color: C.accent }}>
                  Generando análisis narrativo…
                </span>
              </div>
            )}

            {narration && (
              <div style={{ animation: "fadeIn .4s ease" }}>
                <div style={{
                  fontFamily: "'IBM Plex Mono',monospace", fontSize: 10,
                  color: C.muted, letterSpacing: 2, marginBottom: 16,
                }}>SÍNTESIS NARRATIVA · {uploadedFile?.name}</div>

                <div style={{
                  background: C.panel, border: `1px solid ${C.border}`,
                  borderLeft: `3px solid ${C.accent}`,
                  borderRadius: 6, padding: "20px 24px",
                  fontSize: 14, lineHeight: 1.8, color: C.text,
                  whiteSpace: "pre-wrap",
                }}>
                  {narration}
                </div>

                <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
                  <button
                    onClick={handleNarrate}
                    style={{
                      background: "none", border: `1px solid ${C.border}`,
                      color: C.textDim, padding: "8px 16px", borderRadius: 4,
                      fontFamily: "'IBM Plex Mono',monospace", fontSize: 11,
                      cursor: "pointer", letterSpacing: 1,
                    }}
                  >
                    ↺ Regenerar
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer status */}
      <div style={{
        borderTop: `1px solid ${C.border}`,
        padding: "8px 28px",
        display: "flex", alignItems: "center", gap: 20,
        fontFamily: "'IBM Plex Mono',monospace", fontSize: 10,
        color: C.muted,
      }}>
        <span style={{ color: C.green }}>● ONLINE</span>
        <span>claude-sonnet-4</span>
        {extracted && (
          <>
            <span>·</span>
            <span style={{ color: C.accent }}>
              {Object.values(extracted).filter(v => v !== null && typeof v !== "object" && !Array.isArray(v)).length} campos extraídos
            </span>
          </>
        )}
        <span style={{ marginLeft: "auto" }}>Many behaving as One.</span>
      </div>
    </div>
  );
}

