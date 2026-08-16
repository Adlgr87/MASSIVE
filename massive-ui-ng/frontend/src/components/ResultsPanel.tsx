import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Audience, Highlight, RunListItem, SimulateResponse } from "../types";
import { t, type Language } from "../i18n";

// ── Regime color map ──────────────────────────────────────────────────────
const RULE_COLORS: Record<string, string> = {
  lineal: "#5ccfe6",
  umbral: "#ff8f40",
  memoria: "#c3a6ff",
  backlash: "#ff5f56",
  polarizacion: "#ff7edb",
  hk: "#bae67e",
  contagio_competitivo: "#7fe0c3",
  umbral_heterogeneo: "#ffd580",
  homofilia: "#ff9ecd",
  replicador: "#c3a6ff",
  nash: "#5ccfe6",
  bayesiana: "#7fe0c3",
  sir: "#ff8f40",
  langevin_energy: "#5ccfe6",
  multilayer_langevin: "#c3a6ff",
  super_agents_langevin: "#bae67e",
};
const fallbackColor = (i: number) => `hsl(${(i * 47) % 360}, 60%, 65%)`;

// ── Tiny, safe markdown renderer (headings, bold, lists, code) ───────────
function MiniMarkdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const out: React.ReactNode[] = [];
  let list: string[] = [];
  let key = 0;
  const flushList = () => {
    if (list.length) {
      out.push(
        <ul key={`ul-${key++}`}>
          {list.map((li, i) => (
            <li key={i}>
              <Inline text={li} />
            </li>
          ))}
        </ul>
      );
      list = [];
    }
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("- ") || line.startsWith("* ")) {
      list.push(line.slice(2));
      continue;
    }
    flushList();
    if (!line.trim()) continue;
    if (line.startsWith("## ")) {
      out.push(
        <h2 key={`h-${key++}`}>
          <Inline text={line.slice(3)} />
        </h2>
      );
    } else if (line.startsWith("---")) {
      out.push(<hr key={`hr-${key++}`} style={{ border: "none", borderTop: "1px solid var(--border)", margin: "12px 0" }} />);
    } else {
      out.push(
        <p key={`p-${key++}`}>
          <Inline text={line} />
        </p>
      );
    }
  }
  flushList();
  return <>{out}</>;
}

function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith("**") && p.endsWith("**")) return <strong key={i}>{p.slice(2, -2)}</strong>;
        if (p.startsWith("`") && p.endsWith("`")) {
          return (
            <code key={i} className="mono" style={{ color: "var(--accent)", fontSize: "0.92em" }}>
              {p.slice(1, -1)}
            </code>
          );
        }
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

// ── Highlights ────────────────────────────────────────────────────────────
export function HighlightCards({ highlights }: { highlights: Highlight[] }) {
  if (!highlights?.length) return null;
  return (
    <div className="hl-grid">
      {highlights.map((h, i) => (
        <div className="hl-card" key={i}>
          <div className="k">{h.label}</div>
          <div className="v" style={{ color: i === 0 ? "var(--accent)" : "var(--text)" }}>
            {h.value}
          </div>
          <div className="m">{h.meaning}</div>
        </div>
      ))}
    </div>
  );
}

// ── Series → chart data ───────────────────────────────────────────────────
function toChartData(run: SimulateResponse) {
  const s = run.series ?? {};
  const t = (s.t as number[]) ?? [];
  const opinion = (s.opinion as number[]) ?? [];
  const rows = t.map((step, i) => {
    const row: Record<string, number | string> = { t: step };
    if (opinion[i] !== undefined) row.opinion = opinion[i];
    const keys: Record<string, string> = {
      propaganda: "propaganda",
      confianza: "confianza",
      std_opinion: "std_opinion",
      polarization: "polarization",
      active_fraction: "active_fraction",
      cooperation: "cooperation",
    };
    for (const [src, dst] of Object.entries(keys)) {
      const arr = s[src] as number[] | undefined;
      if (arr && arr[i] !== undefined) row[dst] = arr[i];
    }
    return row;
  });
  return rows;
}

const SERIES_META: Record<string, { color: string; labelKey: string }> = {
  opinion: { color: "#5ccfe6", labelKey: "opinionLabel" },
  propaganda: { color: "#ff8f40", labelKey: "propagandaLabel" },
  confianza: { color: "#c3a6ff", labelKey: "trustLabel" },
  std_opinion: { color: "#3d5166", labelKey: "stdLabel" },
  polarization: { color: "#ff7edb", labelKey: "polarizationLabel" },
  active_fraction: { color: "#bae67e", labelKey: "activeLabel" },
  cooperation: { color: "#7fe0c3", labelKey: "cooperationLabel" },
};

function RunCharts({ run, lang }: { run: SimulateResponse; lang: Language }) {
  const data = useMemo(() => toChartData(run), [run]);
  const seriesKeys = useMemo(() => {
    if (!data.length) return [];
    const k = Object.keys(data[0]).filter((x) => x !== "t");
    // Keep opinion first, then at most 3 companions.
    const opinionIdx = k.indexOf("opinion");
    const ordered = opinionIdx >= 0 ? ["opinion", ...k.filter((x) => x !== "opinion")] : k;
    return ordered.slice(0, 4);
  }, [data]);

  const rules = (run.series.regla_nombre as (string | null)[]) ?? [];
  const razones = (run.series.razon as (string | null)[]) ?? [];
  const legend = useMemo(() => {
    const uniq = new Map<string, string>();
    rules.forEach((r) => {
      if (r && !uniq.has(r)) uniq.set(r, RULE_COLORS[r] ?? fallbackColor(uniq.size));
    });
    return [...uniq.entries()];
  }, [rules]);

  return (
    <>
      <div className="chart-card">
        <div className="panel-title">{t("charts", lang)}</div>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data} margin={{ top: 6, right: 14, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="#1a2535" strokeDasharray="3 3" />
            <XAxis dataKey="t" stroke="#3d5166" tick={{ fontSize: 11 }} />
            <YAxis domain={[-1.05, 1.05]} stroke="#3d5166" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: "#0d1520",
                border: "1px solid #1a2535",
                borderRadius: 6,
                fontFamily: "var(--mono)",
                fontSize: 12,
              }}
              labelStyle={{ color: "#6b7f96" }}
            />
            <Legend wrapperStyle={{ fontSize: 11.5 }} />
            {seriesKeys.map((k) => (
              <Line
                key={k}
                type="monotone"
                dataKey={k}
                stroke={SERIES_META[k]?.color ?? fallbackColor(seriesKeys.indexOf(k))}
                name={t(SERIES_META[k]?.labelKey ?? k, lang)}
                dot={false}
                strokeWidth={k === "opinion" ? 2.4 : 1.6}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {rules.length > 1 && (
        <div className="chart-card">
          <div className="panel-title">{t("regimes", lang)}</div>
          <div className="rule-strip">
            {rules.map((r, i) => (
              <div
                key={i}
                className="rule-seg"
                style={{ background: r ? RULE_COLORS[r] ?? fallbackColor(i) : "#1a2535" }}
                title={r ? `${r} — ${razones[i] ?? ""}` : "sin régimen"}
              />
            ))}
          </div>
          <div className="rule-legend">
            {legend.map(([name, color]) => (
              <span key={name}>
                <span className="swatch" style={{ background: color }} />
                {name}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

// ── Main results panel ────────────────────────────────────────────────────
export default function ResultsPanel({
  run,
  runs,
  lang,
  audience,
  onAudience,
  onRegenerate,
  onExample,
  onLoadRun,
  onDeleteRun,
}: {
  run: SimulateResponse | null;
  runs: RunListItem[];
  lang: Language;
  audience: Audience;
  onAudience: (a: Audience) => void;
  onRegenerate: () => void;
  onExample: (text: string) => void;
  onLoadRun: (id: string) => void;
  onDeleteRun: (id: string) => void;
}) {
  if (!run) {
    return (
      <div className="empty-state">
        <div style={{ fontSize: 42, marginBottom: 10 }}>🌊</div>
        <h2>{t("emptyTitle", lang)}</h2>
        <p style={{ maxWidth: 460, margin: "10px auto 26px" }}>{t("emptySub", lang)}</p>
        {[t("example1", lang), t("example2", lang), t("example3", lang)].map((ex, i) => (
          <button key={i} className="example-card" onClick={() => onExample(ex)} style={{ maxWidth: 560, margin: "8px auto" }}>
            “{ex}”
          </button>
        ))}
        {runs.length > 0 && (
          <div style={{ maxWidth: 560, margin: "20px auto", textAlign: "left" }}>
            <div className="panel-title">{t("history", lang)}</div>
            <RunList runs={runs} activeId={null} onLoadRun={onLoadRun} onDeleteRun={onDeleteRun} lang={lang} />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="results-pad">
      <div className="run-head">
        <span className="run-title">🌊 {run.engine}</span>
        <span className="badge" style={{ color: "var(--accent)", borderColor: "#5ccfe644", background: "#5ccfe60d" }}>
          {run.mode === "llm" ? t("modeLLM", lang) : t("modeHeuristic", lang)}
        </span>
        <span className="badge" style={{ color: "var(--textDim)", borderColor: "var(--border)" }}>
          {run.run_id}
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          <label style={{ fontSize: 12, color: "var(--textDim)" }}>{t("audience", lang)}</label>
          <select
            value={audience}
            onChange={(e) => onAudience(e.target.value as Audience)}
            style={{
              background: "var(--bg)",
              border: "1px solid var(--border)",
              color: "var(--text)",
              borderRadius: 6,
              padding: "5px 8px",
              fontSize: 12.5,
            }}
          >
            <option value="general">{t("general", lang)}</option>
            <option value="tecnico">{t("tecnico", lang)}</option>
          </select>
          <button className="btn" onClick={onRegenerate} style={{ fontSize: 12 }}>
            {t("regenerate", lang)}
          </button>
        </div>
      </div>

      <HighlightCards highlights={run.highlights} />
      <RunCharts run={run} lang={lang} />

      <div className="narrative">
        <MiniMarkdown text={run.narrative} />
        <div style={{ fontSize: 11, color: "var(--textDim)", marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
          {t("notePreview", lang)}
        </div>
      </div>

      <details className="tech">
        <summary>{t("technical", lang)}</summary>
        <pre>{JSON.stringify({ summary: run.summary, scientific_report: run.scientific_report, meta: run.meta }, null, 2)}</pre>
      </details>

      <div style={{ marginTop: 6 }}>
        <div className="panel-title">{t("history", lang)}</div>
        <RunList runs={runs} activeId={run.run_id} onLoadRun={onLoadRun} onDeleteRun={onDeleteRun} lang={lang} />
      </div>
    </div>
  );
}

function RunList({
  runs,
  activeId,
  onLoadRun,
  onDeleteRun,
  lang,
}: {
  runs: RunListItem[];
  activeId: string | null;
  onLoadRun: (id: string) => void;
  onDeleteRun: (id: string) => void;
  lang: Language;
}) {
  if (!runs.length) return <div style={{ color: "var(--textDim)", fontSize: 12.5 }}>{t("noRuns", lang)}</div>;
  return (
    <div className="runlist">
      {runs.slice(0, 12).map((r) => (
        <div key={r.run_id} className={`run-item ${r.run_id === activeId ? "active" : ""}`} onClick={() => onLoadRun(r.run_id)}>
          <span className="badge" style={{ color: "var(--textDim)", borderColor: "var(--border)" }}>
            {r.engine}
          </span>
          <span className="headline">{r.headline}</span>
          <span className="sub">{r.dominant_rule ?? ""}</span>
          <button
            className="btn"
            style={{ padding: "2px 7px", fontSize: 11, flexShrink: 0 }}
            title={lang === "es" ? "Eliminar corrida" : "Delete run"}
            onClick={(e) => {
              e.stopPropagation();
              onDeleteRun(r.run_id);
            }}
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
