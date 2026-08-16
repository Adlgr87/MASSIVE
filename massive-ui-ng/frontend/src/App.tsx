import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import ChatPanel from "./components/ChatPanel";
import DraftEditor, { type DraftState } from "./components/DraftEditor";
import GuidedForm from "./components/GuidedForm";
import LiveControls from "./components/LiveControls";
import LiveView from "./components/LiveView";
import ResultsPanel from "./components/ResultsPanel";
import StatusBar from "./components/StatusBar";
import { t, type Language } from "./i18n";
import type {
  Audience,
  ChatMessage,
  ConfigDraft,
  ConversationResponse,
  Engine,
  LiveState,
  RunListItem,
  SimulateRequest,
  SimulateResponse,
  StatusResponse,
} from "./types";

function mergeDraft(prev: ConfigDraft | null, next: ConfigDraft): ConfigDraft {
  if (!prev) return next;
  return {
    ...prev,
    ...next,
    estado_inicial: { ...(prev.estado_inicial ?? {}), ...(next.estado_inicial ?? {}) },
    config: { ...(prev.config ?? {}), ...(next.config ?? {}) },
  };
}

function greeting(lang: Language, status: StatusResponse | null): string {
  const modeNote = status?.llm.configured
    ? lang === "es"
      ? "Tengo un LLM conectado, así que puedo interpretar libremente tus escenarios."
      : "I have an LLM connected, so I can freely interpret your scenarios."
    : lang === "es"
      ? "Ahora mismo estoy en modo heurístico (sin API key de LLM configurada): interpretaré tu escenario con reglas deterministas y te diré cada supuesto que haga."
      : "I am currently in heuristic mode (no LLM API key configured): I will interpret your scenario with deterministic rules and tell you every assumption I make.";
  if (lang === "es") {
    return (
      "¡Hola! Soy el **traductor de MASSIVE** 🌊\n\n" +
      "Descríbeme tu situación con tus propias palabras — una campaña, un conflicto, " +
      "una elección, un problema en tu empresa — y yo:\n" +
      "1. La convierto en parámetros de simulación (opinión inicial, propaganda, confianza, mecanismos).\n" +
      "2. Te digo **qué asumí y por qué**, con un nivel de confianza.\n" +
      "3. Te pregunto solo lo que de verdad falta.\n" +
      "4. Ejecuto la simulación y te explico los resultados en lenguaje claro (y también en técnico).\n\n" +
      modeNote +
      "\n\nEscribe tu escenario 👇"
    );
  }
  return (
    "Hi! I am the **MASSIVE translator** 🌊\n\n" +
    "Describe your situation in your own words — a campaign, a conflict, an election, " +
    "a problem at your company — and I will:\n" +
    "1. Turn it into simulation parameters (initial opinion, propaganda, trust, mechanisms).\n" +
    "2. Tell you **what I assumed and why**, with a confidence level.\n" +
    "3. Ask only what is truly missing.\n" +
    "4. Run the simulation and explain the results in plain language (and in technical terms too).\n\n" +
    modeNote +
    "\n\nType your scenario 👇"
  );
}

export default function App() {
  const [lang, setLang] = useState<Language>("es");
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [turn, setTurn] = useState<ConversationResponse | null>(null);
  const [draft, setDraft] = useState<ConfigDraft | null>(null);
  const [thinking, setThinking] = useState(false);
  const [streamingText, setStreamingText] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runElapsed, setRunElapsed] = useState<number | null>(null);
  const [tab, setTab] = useState<"chat" | "guided" | "live">("chat");
  const [live, setLive] = useState<LiveState>({ status: "idle", engine: "energy", snapshot: null, error: null });
  const [audience, setAudience] = useState<Audience>("general");
  const [activeRun, setActiveRun] = useState<SimulateResponse | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [statusLoaded, setStatusLoaded] = useState(false);
  const greeted = useRef(false);

  useEffect(() => {
    api
      .status()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setStatusLoaded(true));
    api.runs().then(setRuns).catch(() => setRuns([]));
  }, []);

  useEffect(() => {
    if (!greeted.current && statusLoaded && messages.length === 0) {
      greeted.current = true;
      setMessages([{ role: "assistant", content: greeting(lang, status) }]);
    }
  }, [statusLoaded, status, lang, messages.length]);

  // ── Conversation (streaming with graceful fallback) ────────────────────
  const sendMessage = useCallback(
    async (text: string) => {
      setError(null);
      const msgs: ChatMessage[] = [...messages, { role: "user", content: text }];
      setMessages(msgs);
      setThinking(true);
      setStreamingText(null);

      const applyTurn = (resp: ConversationResponse) => {
        setTurn(resp);
        setMessages((prev) => [...prev, { role: "assistant", content: resp.reply }]);
        if (resp.config_draft && Object.keys(resp.config_draft).length > 0) {
          setDraft((prev) => mergeDraft(prev, resp.config_draft as ConfigDraft));
        }
      };

      let gotDone = false;
      try {
        await api.conversationStream(msgs, lang, (event, data) => {
          if (event === "token") {
            setStreamingText((s) => (s ?? "") + String(data?.text ?? ""));
          } else if (event === "done") {
            gotDone = true;
            applyTurn(data as ConversationResponse);
          } else if (event === "error") {
            throw new Error(String(data?.detail ?? "stream error"));
          }
        });
        if (!gotDone) {
          applyTurn(await api.conversation(msgs, lang));
        }
      } catch (streamErr) {
        // Degrade gracefully to the non-streaming endpoint.
        try {
          applyTurn(await api.conversation(msgs, lang));
        } catch (fallbackErr) {
          setError(
            `${t("errorGeneric", lang)}: ${
              fallbackErr instanceof Error ? fallbackErr.message : String(fallbackErr)
            }`
          );
        }
      } finally {
        setThinking(false);
        setStreamingText(null);
      }
    },
    [messages, lang]
  );

  // ── Simulation (streaming progress with graceful fallback) ─────────────
  const runSimulation = useCallback(
    async (req: SimulateRequest) => {
      setRunning(true);
      setError(null);
      setRunElapsed(null);

      const applyRes = (res: SimulateResponse) => {
        setActiveRun(res);
        setActiveRunId(res.run_id);
        setRuns((prev) => [
          {
            run_id: res.run_id,
            engine: res.engine,
            language: res.language,
            headline: `${res.engine}: ${(res.summary.opinion_inicial ?? 0).toFixed(2)} → ${(
              res.summary.opinion_final ?? 0
            ).toFixed(2)}`,
            final_opinion: res.summary.opinion_final ?? null,
            dominant_rule: res.summary.regla_dominante ?? null,
            mode: res.mode,
          },
          ...prev.filter((r) => r.run_id !== res.run_id),
        ]);
      };

      let gotDone = false;
      try {
        await api.simulateStream(req, (event, data) => {
          if (event === "progress") {
            setRunElapsed(typeof data?.elapsed === "number" ? data.elapsed : null);
          } else if (event === "done") {
            gotDone = true;
            applyRes(data as SimulateResponse);
          } else if (event === "error") {
            throw new Error(String(data?.detail ?? "simulation failed"));
          }
        });
        if (!gotDone) {
          applyRes(await api.simulate(req));
        }
      } catch (streamErr) {
        try {
          applyRes(await api.simulate(req));
        } catch (fallbackErr) {
          setError(
            `${t("errorGeneric", lang)}: ${
              fallbackErr instanceof Error ? fallbackErr.message : String(fallbackErr)
            }`
          );
        }
      } finally {
        setRunning(false);
        setRunElapsed(null);
      }
    },
    [lang]
  );

  const runFromDraft = useCallback(
    (s: DraftState) => {
      const toNum = (v: string) => {
        const n = Number(v);
        return Number.isFinite(n) ? n : 0;
      };
      const seed = s.seed.trim() === "" ? null : toNum(s.seed);
      const req: SimulateRequest = {
        engine: s.engine as Engine,
        escenario: "campana",
        pasos: s.pasos,
        estado_inicial: Object.fromEntries(Object.entries(s.estado).map(([k, v]) => [k, toNum(v)])),
        config: { ...Object.fromEntries(Object.entries(s.extra).map(([k, v]) => [k, toNum(v)])) },
        seed,
        scientific: s.scientific,
        language: lang,
        audience,
      };
      runSimulation(req);
    },
    [audience, lang, runSimulation]
  );

  const loadRun = useCallback(
    async (id: string) => {
      setError(null);
      try {
        const res = await api.run(id, lang, audience);
        setActiveRun(res);
        setActiveRunId(id);
      } catch (e) {
        setError(`${t("errorGeneric", lang)}: ${e instanceof Error ? e.message : String(e)}`);
      }
    },
    [lang, audience]
  );

  const deleteRun = useCallback(
    async (id: string) => {
      try {
        await api.deleteRun(id);
        setRuns((prev) => prev.filter((r) => r.run_id !== id));
        if (activeRunId === id) {
          setActiveRun(null);
          setActiveRunId(null);
        }
      } catch (e) {
        setError(`${t("errorGeneric", lang)}: ${e instanceof Error ? e.message : String(e)}`);
      }
    },
    [activeRunId, lang]
  );

  const regenerate = useCallback(async () => {
    if (!activeRunId) return;
    setError(null);
    try {
      const res = await api.explain(activeRunId, lang, audience);
      setActiveRun((prev) =>
        prev ? { ...prev, narrative: res.narrative, highlights: res.highlights ?? [] } : prev
      );
    } catch (e) {
      setError(`${t("errorGeneric", lang)}: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [activeRunId, lang, audience]);

  // Audience/language changes re-narrate the active run.
  useEffect(() => {
    if (activeRunId) {
      loadRun(activeRunId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audience, lang]);

  const onExample = useCallback(
    (text: string) => {
      setTab("chat");
      sendMessage(text);
    },
    [sendMessage]
  );

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-logo">
          <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
            <rect width="30" height="30" rx="6" fill="#0d1520" stroke="#1a2535" />
            <path
              d="M4 18 Q 7 10, 11 15 T 17 15 T 23 12 T 27 16"
              fill="none"
              stroke="#5ccfe6"
              strokeWidth="2.4"
              strokeLinecap="round"
            />
          </svg>
          <div>
            <div className="app-title">
              MASSIVE<span>_UI</span>
            </div>
            <div className="app-tagline">{t("tagline", lang)}</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn lang-btn"
            onClick={() => setLang((l) => (l === "es" ? "en" : "es"))}
            title={lang === "es" ? "Switch to English" : "Cambiar a español"}
          >
            {lang === "es" ? "ES ▾ EN" : "EN ▾ ES"}
          </button>
          <StatusBar status={status} lang={lang} />
        </div>
      </header>

      <div className="main-grid">
        <div className="col col-left">
          <div className="tabs">
            <button className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>
              {t("chatTab", lang)}
            </button>
            <button className={`tab ${tab === "guided" ? "active" : ""}`} onClick={() => setTab("guided")}>
              {t("guidedTab", lang)}
            </button>
            <button className={`tab ${tab === "live" ? "active" : ""}`} onClick={() => setTab("live")}>
              {t("liveTab", lang)}
            </button>
          </div>

          {error && <div className="error-bar">⚠ {error}</div>}

          {tab === "live" ? (
            <LiveControls lang={lang} live={live} onState={setLive} />
          ) : tab === "chat" ? (
            <>
              <ChatPanel
                messages={messages}
                thinking={thinking}
                streamingText={streamingText}
                turn={turn}
                lang={lang}
                onSend={sendMessage}
                onAsk={(q) => sendMessage(q)}
              />
              {draft && (
                <div style={{ borderTop: "1px solid var(--border)", overflowY: "auto", maxHeight: "46%" }}>
                  <DraftEditor
                    draft={draft}
                    lang={lang}
                    running={running}
                    elapsed={runElapsed}
                    onRun={runFromDraft}
                    onDiscard={() => {
                      setDraft(null);
                      setTurn(null);
                    }}
                  />
                </div>
              )}
            </>
          ) : (
            <GuidedForm lang={lang} running={running} elapsed={runElapsed} onRun={runSimulation} />
          )}
        </div>

        <div className="col col-right">
          {tab === "live" ? (
            <LiveView lang={lang} live={live} bipolar={live.range_type !== "unipolar"} />
          ) : (
            <ResultsPanel
              run={activeRun}
              runs={runs}
              lang={lang}
              audience={audience}
              onAudience={setAudience}
              onRegenerate={regenerate}
              onExample={onExample}
              onLoadRun={loadRun}
              onDeleteRun={deleteRun}
            />
          )}
        </div>
      </div>
    </div>
  );
}
