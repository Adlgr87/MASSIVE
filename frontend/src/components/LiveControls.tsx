import { useEffect, useRef, useState } from "react";
import { openLiveStream, type LiveConnection } from "../live";
import { t, type Language } from "../i18n";
import type { LiveSnapshot, LiveState } from "../types";

const ARCHETYPES: Record<string, { es: string; en: string }> = {
  polarizacion_extrema: { es: "⚡ Polarización extrema", en: "⚡ Extreme polarization" },
  polarizacion_moderada: { es: "🔀 División moderada", en: "🔀 Moderate division" },
  consenso_moderado: { es: "🤝 Consenso moderado", en: "🤝 Moderate consensus" },
  consenso_forzado: { es: "🔒 Uniformidad forzada", en: "🔒 Forced uniformity" },
  fragmentacion_3_grupos: { es: "🔺 Tres facciones", en: "🔺 Three factions" },
  fragmentacion_4_grupos: { es: "🔷 Cuatro tribus", en: "🔷 Four tribes" },
  caos_social: { es: "🌪️ Caos social", en: "🌪️ Social chaos" },
  radicalizacion_progresiva: { es: "📈 Radicalización progresiva", en: "📈 Progressive radicalization" },
};

export default function LiveControls({
  lang,
  live,
  onState,
}: {
  lang: Language;
  live: LiveState;
  onState: (s: LiveState | ((prev: LiveState) => LiveState)) => void;
}) {
  const [engine, setEngine] = useState<"energy" | "massive">("energy");
  const [nAgents, setNAgents] = useState("60");
  const [connectivity, setConnectivity] = useState("0.25");
  const [rangeType, setRangeType] = useState<"bipolar" | "unipolar">("bipolar");
  const [seed, setSeed] = useState("42");
  const [pasos, setPasos] = useState("150");
  const [userGoal, setUserGoal] = useState("polarizacion_moderada");
  const [shockValue, setShockValue] = useState("0.35");
  const [shockFraction, setShockFraction] = useState("0.25");
  const connRef = useRef<LiveConnection | null>(null);

  useEffect(() => {
    return () => {
      connRef.current?.close();
    };
  }, []);

  const num = (s: string, fallback: number) => {
    const v = Number(s);
    return Number.isFinite(v) ? v : fallback;
  };

  const start = () => {
    connRef.current?.close();
    onState({ status: "connecting", engine, range_type: rangeType, snapshot: null, error: null });
    connRef.current = openLiveStream(
      {
        engine,
        n_agents: Math.round(num(nAgents, 60)),
        connectivity: num(connectivity, 0.25),
        range_type: rangeType,
        seed: Math.round(num(seed, 42)),
        pasos: Math.round(num(pasos, 150)),
        user_goal: userGoal,
      },
      {
        onOpen: () =>
          onState({ status: "running", engine, range_type: rangeType, snapshot: null, error: null }),
        onSnapshot: (snap: LiveSnapshot) =>
          onState((prev) => ({ ...prev, status: "running", snapshot: snap })),
        onEvent: (event, detail) => {
          if (event === "started") {
            onState((prev) => ({ ...prev, status: "running" }));
          } else if (event === "stopped") {
            onState((prev) => ({ ...prev, status: "stopped" }));
          } else if (event === "error") {
            onState((prev) => ({ ...prev, status: "error", error: detail ?? "ws-error" }));
          }
        },
        onClose: () => onState((prev) => (prev.status === "error" ? prev : { ...prev, status: "stopped" })),
        onError: (err) => onState((prev) => ({ ...prev, status: "error", error: err })),
      }
    );
  };

  const stop = () => {
    connRef.current?.send({ action: "stop" });
  };

  const shock = () => {
    connRef.current?.send({
      action: "shock",
      value: num(shockValue, 0.35),
      fraction: num(shockFraction, 0.25),
    });
  };

  const running = live.status === "running" || live.status === "connecting";

  return (
    <div style={{ overflowY: "auto", flex: 1 }}>
      <div className="panel-card" style={{ borderColor: "#ff8f4055" }}>
        <div className="panel-title">{t("liveTab", lang)}</div>
        <div className="field-grid">
          <div className="field">
            <label>{t("engine", lang)}</label>
            <select value={engine} onChange={(e) => setEngine(e.target.value as "energy" | "massive")} disabled={running}>
              <option value="energy">{t("engineEnergy", lang)}</option>
              <option value="massive">{t("engineMassive", lang)}</option>
            </select>
          </div>
          <div className="field">
            <label>{t("liveArchetype", lang)}</label>
            <select value={userGoal} onChange={(e) => setUserGoal(e.target.value)} disabled={running || engine !== "energy"}>
              {Object.entries(ARCHETYPES).map(([k, v]) => (
                <option key={k} value={k}>
                  {v[lang]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>{t("nAgents", lang)}</label>
            <input value={nAgents} onChange={(e) => setNAgents(e.target.value)} disabled={running} />
          </div>
          <div className="field">
            <label>{t("steps", lang)}</label>
            <input type="number" min={10} max={600} value={pasos} onChange={(e) => setPasos(e.target.value)} disabled={running} />
          </div>
          {engine === "energy" && (
            <>
              <div className="field">
                <label>{t("connectivity", lang)}</label>
                <input value={connectivity} onChange={(e) => setConnectivity(e.target.value)} disabled={running} />
              </div>
              <div className="field">
                <label>{t("rangeType", lang)}</label>
                <select value={rangeType} onChange={(e) => setRangeType(e.target.value as "bipolar" | "unipolar")} disabled={running}>
                  <option value="bipolar">[-1, 1] bipolar</option>
                  <option value="unipolar">[0, 1] unipolar</option>
                </select>
              </div>
            </>
          )}
          <div className="field">
            <label>{t("seed", lang)}</label>
            <input value={seed} onChange={(e) => setSeed(e.target.value)} disabled={running} />
          </div>
        </div>

        {engine === "massive" && running && (
          <div className="field-grid" style={{ marginTop: 10 }}>
            <div className="field">
              <label>{t("shockValue", lang)}</label>
              <input value={shockValue} onChange={(e) => setShockValue(e.target.value)} />
            </div>
            <div className="field">
              <label>{t("shockFraction", lang)}</label>
              <input value={shockFraction} onChange={(e) => setShockFraction(e.target.value)} />
            </div>
            <div className="field-row">
              <button className="btn" style={{ borderColor: "#ff8f4055", color: "var(--orange)" }} onClick={shock}>
                ⚡ {t("shock", lang)}
              </button>
            </div>
          </div>
        )}

        <div className="field-row">
          {!running ? (
            <button className="btn run" onClick={start}>
              ▶ {t("liveStart", lang)}
            </button>
          ) : (
            <button className="btn" style={{ borderColor: "#ff5f5655", color: "var(--red)" }} onClick={stop}>
              ■ {t("liveStop", lang)}
            </button>
          )}
          <span className="pill" style={{ marginLeft: "auto" }}>
            <span className="dot" />
            {live.status === "running"
              ? t("liveRunning", lang)
              : live.status === "connecting"
                ? t("liveConnecting", lang)
                : live.status === "error"
                  ? t("liveError", lang)
                  : live.status === "stopped"
                    ? t("liveStopped", lang)
                    : t("liveIdle", lang)}
          </span>
        </div>
        {live.error && (
          <div className="error-bar" style={{ margin: "10px 0 0" }}>
            ⚠ {live.error}
          </div>
        )}
        <div style={{ fontSize: 11, color: "var(--textDim)", marginTop: 10 }}>
          {lang === "es"
            ? "Vista en vivo: cada tick se transmite por WebSocket. En el motor de energía verás la red de agentes; en el masivo, métricas agregadas con la opción de aplicar un shock externo a mitad de la corrida."
            : "Live view: every tick streams over WebSocket. The energy engine renders the agent network; the massive engine streams aggregate metrics and lets you apply an external shock mid-run."}
        </div>
      </div>
    </div>
  );
}
