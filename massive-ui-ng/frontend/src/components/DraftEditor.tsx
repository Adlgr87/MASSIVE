import { useEffect, useRef, useState } from "react";
import type { AssumptionItem, ConfigDraft, ConversationResponse, Engine } from "../types";
import { t, type Language } from "../i18n";

function confColor(c: number) {
  return c > 0.7 ? "#bae67e" : c > 0.4 ? "#ff8f40" : "#ff5f56";
}

export function AssumptionsPanel({
  assumptions,
  lang,
}: {
  assumptions: AssumptionItem[];
  lang: Language;
}) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");

  if (!assumptions.length) return null;

  const startEdit = (index: number, value: string) => {
    setEditingIndex(index);
    setEditValue(value);
  };

  return (
    <div className="panel-card assumptions-panel">
      <div className="panel-title">{t("assumptions", lang)}</div>
      {assumptions.map((a, i) => (
        <div key={i} className="assume" style={{ borderLeftColor: confColor(a.confidence) }}>
          <div className="assume-left">
            <span className="param">{a.parameter}</span>
            {editingIndex === i ? (
              <input
                className="assume-input"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={() => setEditingIndex(null)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setEditingIndex(null);
                }}
                autoFocus
              />
            ) : (
              <span
                className="val"
                style={{ color: confColor(a.confidence), cursor: "pointer" }}
                onClick={() => startEdit(i, a.value)}
                title={t("editAssume", lang)}
              >
                {a.value}
              </span>
            )}
            <span className="why">{a.reason}</span>
          </div>
          <div className="assume-right">
            <span title={`confidence ${Math.round(a.confidence * 100)}%`} style={{ fontSize: 11 }}>
              {Math.round(a.confidence * 100)}%
            </span>
            <div className="conf-bar">
              <div
                style={{
                  width: `${Math.round(a.confidence * 100)}%`,
                  background: confColor(a.confidence),
                  transition: "width 0.3s ease",
                }}
              />
            </div>
          </div>
        </div>
      ))}
      <div className="assume-hint">{t("assumptionsHint", lang)}</div>
    </div>
  );
}

export function QuestionsPanel({ questions, onAsk, lang }: { questions: string[]; onAsk: (q: string) => void; lang: Language }) {
  if (!questions.length) return null;
  return (
    <div className="panel-card questions-panel">
      <div className="panel-title">{t("questions", lang)}</div>
      {questions.map((q, i) => (
        <button
          key={i}
          className="qchip"
          onClick={() => onAsk(q)}
          title={q}
        >
          <span className="qchip-text">{q}</span>
          <span className="qchip-arrow">➤</span>
        </button>
      ))}
      <div style={{ fontSize: 11, color: "var(--textDim)", marginTop: 8 }}>{t("questionsHint", lang)}</div>
    </div>
  );
}

// ── Draft editor: every editable value maps to the simulate payload ─────

export interface DraftState {
  engine: Engine;
  pasos: number;
  seed: string;
  scientific: boolean;
  estado: Record<string, string>; // opinion, propaganda, confianza, grupos…
  extra: Record<string, string>; // config keys shown as editable strings
}

export function draftToState(draft: ConfigDraft | null): DraftState {
  const est = draft?.estado_inicial ?? {};
  const cfg = draft?.config ?? {};
  return {
    engine: "scalar",
    pasos: draft?.pasos ?? 60,
    seed: cfg.seed != null ? String(cfg.seed) : "42",
    scientific: true,
    estado: {
      opinion: est.opinion != null ? String(est.opinion) : "0.50",
      propaganda: est.propaganda != null ? String(est.propaganda) : "0.60",
      confianza: est.confianza != null ? String(est.confianza) : "0.50",
      opinion_grupo_a: est.opinion_grupo_a != null ? String(est.opinion_grupo_a) : "0.65",
      opinion_grupo_b: est.opinion_grupo_b != null ? String(est.opinion_grupo_b) : "0.35",
    },
    extra: Object.fromEntries(
      Object.entries(cfg)
        .filter(([k]) => !["seed", "proveedor", "rango", "factbook_country", "modelo_matematico"].includes(k))
        .map(([k, v]) => [k, typeof v === "number" ? String(v) : typeof v === "string" ? v : String(v)])
    ),
  };
}

export default function DraftEditor({
  draft,
  lang,
  running = false,
  elapsed = null,
  onRun,
  onDiscard,
}: {
  draft: ConfigDraft | null;
  lang: Language;
  running?: boolean;
  elapsed?: number | null;
  onRun: (s: DraftState) => void;
  onDiscard: () => void;
}) {
  const [state, setState] = useState<DraftState>(() => draftToState(draft));
  const [isValidating, setIsValidating] = useState(false);
  const prevDraft = useRef(draft);

  useEffect(() => {
    if (draft !== prevDraft.current) {
      prevDraft.current = draft;
      setState(draftToState(draft));
    }
  }, [draft]);

  if (!draft) return null;
  const est = draft.estado_inicial ?? {};
  const cfg = draft.config ?? {};

  const setEst = (k: string, v: string) => setState((s) => ({ ...s, estado: { ...s.estado, [k]: v } }));
  const setExtra = (k: string, v: string) => setState((s) => ({ ...s, extra: { ...s.extra, [k]: v } }));

  const extraKeys = Object.keys(state.extra);
  const metaKeys = ["rango", "modelo_matematico", "factbook_country", "proveedor"];

  const validateDraft = (): boolean => {
    const opinion = parseFloat(state.estado.opinion ?? "0.5");
    const pasos = state.pasos;
    return opinion >= 0 && opinion <= 1 && pasos >= 5 && pasos <= 500;
  };

  const handleRun = () => {
    if (!validateDraft()) {
      alert(lang === "es" ? "Valores de configuración inválidos" : "Invalid configuration values");
      return;
    }
    onRun(state);
  };

  return (
    <div className="panel-card draft-editor" style={{ borderColor: "#5ccfe655" }}>
      <div className="panel-title">{t("editDraft", lang)}</div>

      <div className="field-grid">
        <div className="field">
          <label>{t("engine", lang)}</label>
          <select
            value={state.engine}
            onChange={(e) => setState((s) => ({ ...s, engine: e.target.value as Engine }))}
            disabled={running}
          >
            <option value="scalar">{t("engineScalar", lang)}</option>
            <option value="energy">{t("engineEnergy", lang)}</option>
            <option value="multilayer">{t("engineMultilayer", lang)}</option>
            <option value="massive">{t("engineMassive", lang)}</option>
          </select>
        </div>

        <div className="field">
          <label>{t("steps", lang)}</label>
          <input
            type="number"
            min={5}
            max={500}
            value={state.pasos}
            onChange={(e) => setState((s) => ({ ...s, pasos: Number(e.target.value) }))}
            disabled={running}
          />
        </div>

        <div className="field">
          <label>{t("opinion", lang)}</label>
          <input
            type="number"
            min={-1}
            max={1}
            step={0.01}
            value={state.estado.opinion ?? ""}
            onChange={(e) => setEst("opinion", e.target.value)}
            disabled={running}
          />
        </div>

        <div className="field">
          <label>{t("propaganda", lang)}</label>
          <input
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={state.estado.propaganda ?? ""}
            onChange={(e) => setEst("propaganda", e.target.value)}
            disabled={running}
          />
        </div>
      </div>

      {metaKeys.some((k) => cfg[k] != null) && (
        <div className="config-meta">
          {metaKeys
            .filter((k) => cfg[k] != null)
            .map((k) => (
              <div key={k} className="meta-row">
                <span className="meta-key">{k}</span>
                <span className="meta-value">{String(cfg[k])}</span>
              </div>
            ))}
        </div>
      )}

      {extraKeys.length > 0 && (
        <div className="field-grid" style={{ marginTop: 10 }}>
          {extraKeys.map((k) => (
            <div className="field" key={k}>
              <label>{k}</label>
              <input
                value={state.extra[k]}
                onChange={(e) => setExtra(k, e.target.value)}
                disabled={running}
              />
            </div>
          ))}
        </div>
      )}

      <div className="field-row">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={state.scientific}
            onChange={(e) => setState((s) => ({ ...s, scientific: e.target.checked }))}
            disabled={running}
          />
          {t("scientific", lang)}
        </label>
        <button
          className="btn run"
          onClick={handleRun}
          disabled={running || !validateDraft()}
        >
          {running ? (
            <>
              <span className="spinner" style={{ width: 12, height: 12, marginRight: 6 }} />
              {t("thinking", lang)}
              {elapsed != null ? ` (${elapsed.toFixed(1)}s)` : ""}
            </>
          ) : (
            t("runSim", lang)
          )}
        </button>
        <button className="btn" onClick={onDiscard} disabled={running}>
          {t("discard", lang)}
        </button>
      </div>

      {!validateDraft() && (
        <div className="validation-hint">
          {lang === "es"
            ? "Revisa los valores: opinión ∈ [0,1], pasos ∈ [5,500]"
            : "Check values: opinion ∈ [0,1], steps ∈ [5,500]"}
        </div>
      )}
    </div>
  );
}
