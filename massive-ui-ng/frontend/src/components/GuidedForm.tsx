import { useState } from "react";
import type { Engine, SimulateRequest } from "../types";
import { t, type Language } from "../i18n";

export default function GuidedForm({
  lang,
  running = false,
  elapsed = null,
  onRun,
}: {
  lang: Language;
  running?: boolean;
  elapsed?: number | null;
  onRun: (req: SimulateRequest) => void;
}) {
  const [engine, setEngine] = useState<Engine>("scalar");
  const [pasos, setPasos] = useState(60);
  const [seed, setSeed] = useState("42");
  const [scientific, setScientific] = useState(true);
  const [opinion, setOpinion] = useState("0.50");
  const [propaganda, setPropaganda] = useState("0.60");
  const [confianza, setConfianza] = useState("0.50");
  const [rango, setRango] = useState("[0, 1] — Probabilístico");
  const [nAgents, setNAgents] = useState("100");
  const [rangeType, setRangeType] = useState<"bipolar" | "unipolar">("bipolar");
  const [connectivity, setConnectivity] = useState("0.30");
  const [quantize, setQuantize] = useState(true);
  const [eventDriven, setEventDriven] = useState(true);
  const [layerWeights, setLayerWeights] = useState("0.4, 0.3, 0.3");

  const num = (s: string, fallback: number) => {
    const v = Number(s);
    return Number.isFinite(v) ? v : fallback;
  };

  const run = () => {
    const config: Record<string, unknown> = { rango };
    const seedN = num(seed, 42);
    config.seed = seedN;

    const base = {
      engine,
      pasos,
      seed: seedN,
      scientific,
      language: lang,
      audience: "general" as const,
      estado_inicial: {
        opinion: num(opinion, 0.5),
        propaganda: num(propaganda, 0.6),
        confianza: num(confianza, 0.5),
      },
      config,
      escenario: "campana",
    };

    const req: SimulateRequest = { ...base };
    if (engine === "energy") {
      req.n_agents = Math.round(num(nAgents, 50));
      req.connectivity = num(connectivity, 0.3);
      req.range_type = rangeType;
    } else if (engine === "multilayer") {
      req.n_agents = Math.round(num(nAgents, 100));
      req.layer_weights = layerWeights.split(",").map((s) => num(s.trim(), 0.3)).slice(0, 3);
    } else if (engine === "massive") {
      req.n_agents = Math.round(num(nAgents, 10000));
      req.quantize = quantize;
      req.event_driven = eventDriven;
    }
    onRun(req);
  };

  const engineFields = () => {
    if (engine === "energy") {
      return (
        <>
          <div className="field">
            <label>{t("rangeType", lang)}</label>
            <select value={rangeType} onChange={(e) => setRangeType(e.target.value as "bipolar" | "unipolar")}>
              <option value="bipolar">[-1, 1] bipolar</option>
              <option value="unipolar">[0, 1] unipolar</option>
            </select>
          </div>
          <div className="field">
            <label>{t("connectivity", lang)}</label>
            <input value={connectivity} onChange={(e) => setConnectivity(e.target.value)} />
          </div>
        </>
      );
    }
    if (engine === "multilayer") {
      return (
        <div className="field">
          <label>{t("layerWeights", lang)}</label>
          <input value={layerWeights} onChange={(e) => setLayerWeights(e.target.value)} />
        </div>
      );
    }
    if (engine === "massive") {
      return (
        <>
          <div className="field" style={{ display: "flex", flexDirection: "row", gap: 14, alignItems: "center" }}>
            <label style={{ display: "flex", gap: 5, alignItems: "center" }}>
              <input type="checkbox" checked={quantize} onChange={(e) => setQuantize(e.target.checked)} />
              {t("quantize", lang)}
            </label>
            <label style={{ display: "flex", gap: 5, alignItems: "center" }}>
              <input type="checkbox" checked={eventDriven} onChange={(e) => setEventDriven(e.target.checked)} />
              {t("eventDriven", lang)}
            </label>
          </div>
        </>
      );
    }
    return null;
  };

  return (
    <div style={{ overflowY: "auto", flex: 1 }}>
      <div className="panel-card">
        <div className="panel-title">{t("guidedTab", lang)}</div>
        <div className="field-grid">
          <div className="field">
            <label>{t("engine", lang)}</label>
            <select value={engine} onChange={(e) => setEngine(e.target.value as Engine)}>
              <option value="scalar">{t("engineScalar", lang)}</option>
              <option value="energy">{t("engineEnergy", lang)}</option>
              <option value="multilayer">{t("engineMultilayer", lang)}</option>
              <option value="massive">{t("engineMassive", lang)}</option>
            </select>
          </div>
          <div className="field">
            <label>{t("steps", lang)}</label>
            <input type="number" min={5} max={500} value={pasos} onChange={(e) => setPasos(Number(e.target.value))} />
          </div>
          <div className="field">
            <label>{t("opinion", lang)}</label>
            <input value={opinion} onChange={(e) => setOpinion(e.target.value)} />
          </div>
          <div className="field">
            <label>{t("propaganda", lang)}</label>
            <input value={propaganda} onChange={(e) => setPropaganda(e.target.value)} />
          </div>
          <div className="field">
            <label>{t("trust", lang)}</label>
            <input value={confianza} onChange={(e) => setConfianza(e.target.value)} />
          </div>
          <div className="field">
            <label>{t("range", lang)}</label>
            <select value={rango} onChange={(e) => setRango(e.target.value)}>
              <option value="[0, 1] — Probabilístico">{t("range01", lang)}</option>
              <option value="[-1, 1] — Bipolar">{t("range11", lang)}</option>
            </select>
          </div>
          {engine !== "scalar" && (
            <div className="field">
              <label>{t("nAgents", lang)}</label>
              <input value={nAgents} onChange={(e) => setNAgents(e.target.value)} />
            </div>
          )}
          {engineFields()}
          <div className="field">
            <label>{t("seed", lang)}</label>
            <input value={seed} onChange={(e) => setSeed(e.target.value)} />
          </div>
        </div>
        <div className="field-row">
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5 }}>
            <input type="checkbox" checked={scientific} onChange={(e) => setScientific(e.target.checked)} />
            {t("scientific", lang)}
          </label>
          <button className="btn run" onClick={run} disabled={running}>
            {running ? (
              <>
                <span className="spinner" style={{ width: 12, height: 12, marginRight: 6 }} />
                {t("thinking", lang)}
                {elapsed != null ? ` (${elapsed.toFixed(1)}s)` : ""}
              </>
            ) : (
              t("simulate", lang)
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
