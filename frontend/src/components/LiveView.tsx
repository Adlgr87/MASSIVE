import { useEffect, useRef, useState } from "react";
import { t, type Language } from "../i18n";
import type { LiveSnapshot, LiveState } from "../types";

// ── Opinion → color scales (dark theme) ───────────────────────────────────
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const hexLerp = (c1: number[], c2: number[], t: number) =>
  `rgb(${Math.round(lerp(c1[0], c2[0], t))},${Math.round(lerp(c1[1], c2[1], t))},${Math.round(lerp(c1[2], c2[2], t))})`;

const RED = [255, 95, 86];
const GRAY = [61, 81, 102];
const CYAN = [92, 207, 230];
const GREEN = [186, 230, 126];
const ORANGE = [255, 143, 64];

function opinionColor(v: number, bipolar: boolean): string {
  if (bipolar) {
    const t = Math.max(0, Math.min(1, (v + 1) / 2));
    return t < 0.5
      ? hexLerp(RED, GRAY, t * 2)
      : hexLerp(GRAY, CYAN, (t - 0.5) * 2);
  }
  const t = Math.max(0, Math.min(1, v));
  return hexLerp(GRAY, GREEN, t);
}

// ── Network canvas (energy engine: agents as nodes, animated edges) ───────
function NetworkCanvas({ snap, bipolar }: { snap: LiveSnapshot; bipolar: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationRef = useRef<number | null>(null);
  const frameCountRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const pad = 30;
    const px = (x: number) => pad + ((x + 1) / 2) * (W - 2 * pad);
    const py = (y: number) => pad + ((y + 1) / 2) * (H - 2 * pad);

    const agents = snap.agents ?? [];
    const n = agents.length;

    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      frameCountRef.current += 1;

      // Animated edges
      const connectivity = snap.metrics ? Math.min(0.4, 0.02 + 0.25 * snap.metrics.fragmentation_index) : 0.1;
      const degree = Math.max(2, Math.round(n * connectivity));
      ctx.strokeStyle = "#16202e";
      ctx.lineWidth = 0.6;
      ctx.globalAlpha = 0.6 + 0.1 * Math.sin(frameCountRef.current * 0.05);

      for (let i = 0; i < n; i++) {
        for (let d = 1; d <= degree; d++) {
          const j = (i * 7 + d * 13) % n;
          if (j === i) continue;
          ctx.beginPath();
          ctx.moveTo(px(agents[i].x), py(agents[i].y));
          ctx.lineTo(px(agents[j].x), py(agents[j].x));
          ctx.stroke();
        }
      }

      ctx.globalAlpha = 1;

      // Nodes
      for (const a of agents) {
        ctx.beginPath();
        ctx.arc(px(a.x), py(a.y), 4.2, 0, Math.PI * 2);
        ctx.fillStyle = opinionColor(a.opinion, bipolar);
        ctx.fill();
        // Glow effect
        ctx.shadowBlur = 4;
        ctx.shadowColor = opinionColor(a.opinion, bipolar);
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [snap, bipolar]);

  return (
    <div className="network-canvas-container">
      <canvas ref={canvasRef} width={640} height={400} className="network-canvas" />
      <div className="canvas-overlay">
        <span className="stat-badge">{(snap.agents ?? []).length} agents</span>
        <span className="stat-badge">tick {snap.tick}</span>
      </div>
    </div>
  );
}

// ── Sparkline canvas (massive engine: mean opinion + active fraction) ─────
function SparklineCanvas({ history }: { history: { t: number; mean: number; active: number }[] }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    if (history.length < 2) return;

    const pad = 24;
    const tMax = Math.max(...history.map((h) => h.t), 1);
    const px = (t: number) => pad + (t / tMax) * (W - 2 * pad);
    const py = (v: number) => H / 2 - (v / 2) * (H - 2 * pad);

    // Grid
    ctx.strokeStyle = "#16202e";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad, H / 2);
    ctx.lineTo(W - pad, H / 2);
    ctx.stroke();

    // Grid lines
    for (let i = 1; i <= 4; i++) {
      const y = pad + (i / 5) * (H - 2 * pad);
      ctx.strokeStyle = "#16202e";
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 0.3;
      ctx.beginPath();
      ctx.moveTo(pad, y);
      ctx.lineTo(W - pad, y);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    const line = (vals: number[], color: string, scale: (v: number) => number) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      history.forEach((h, i) => {
        const x = px(h.t);
        const y = py(scale(vals[i]));
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    };

    line(history.map((h) => h.mean), "rgb(255,143,64)", (v) => v);
    line(history.map((h) => h.active), "rgb(186,230,126)", (v) => v * 2 - 1);
  }, [history]);

  return (
    <div className="sparkline-container">
      <canvas ref={canvasRef} width={640} height={260} className="sparkline-canvas" />
      <div className="sparkline-legend">
        <span className="legend-item" style={{ color: "rgb(255,143,64)" }}>Opinión media</span>
        <span className="legend-item" style={{ color: "rgb(186,230,126)" }}>Fracción activa</span>
      </div>
    </div>
  );
}

// ── Tooltip interactivo ───────────────────────────────────────────────────
function LiveTooltip({ snap, lang }: { snap: LiveSnapshot; lang: Language }) {
  const m = snap.metrics;

  return (
    <div className="live-tooltip">
      <div className="tooltip-item">
        <span className="tooltip-dot" style={{ background: "rgb(255,143,64)" }} />
        <span className="tooltip-label">{t("meanLabel", lang)}:</span>
        <span className="tooltip-value">{m.mean_opinion.toFixed(3)}</span>
      </div>
      <div className="tooltip-item">
        <span className="tooltip-dot" style={{ background: "rgb(92,207,230)" }} />
        <span className="tooltip-label">{t("stdLabel", lang)}:</span>
        <span className="tooltip-value">{m.std_opinion.toFixed(3)}</span>
      </div>
      <div className="tooltip-item">
        <span className="tooltip-dot" style={{ background: "rgb(255,95,86)" }} />
        <span className="tooltip-label">{t("polarizationLabel", lang)}:</span>
        <span className="tooltip-value">{m.polarization.toFixed(3)}</span>
      </div>
      <div className="tooltip-item">
        <span className="tooltip-dot" style={{ background: "rgb(186,230,126)" }} />
        <span className="tooltip-label">{t("consensusLabel", lang)}:</span>
        <span className="tooltip-value">{Math.round(m.consensus_rate * 100)}%</span>
      </div>
      <div className="tooltip-item">
        <span className="tooltip-dot" style={{ background: "rgb(92,207,230)" }} />
        <span className="tooltip-label">{t("activeAgentsLabel", lang)}:</span>
        <span className="tooltip-value">{String(m.active_agents)}</span>
      </div>
      <div className="tooltip-rule">{m.dominant_rule}</div>
    </div>
  );
}

// ── Main live view ────────────────────────────────────────────────────────
export default function LiveView({ lang, live, bipolar }: { lang: Language; live: LiveState; bipolar: boolean }) {
  const historyRef = useRef<{ t: number; mean: number; active: number }[]>([]);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
  const snap = live.snapshot;

  useEffect(() => {
    if (snap && live.engine === "massive") {
      const h = historyRef.current;
      h.push({ t: snap.tick, mean: snap.metrics.mean_opinion, active: snap.metrics.active_agents / 1 });
      if (h.length > 400) h.splice(0, h.length - 400);
    }
  }, [snap, live.engine]);

  const handleMouseMove = (e: React.MouseEvent) => {
    setTooltipPos({ x: e.clientX, y: e.clientY });
  };

  if (!snap) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🔴</div>
        <h2>{t("liveTab", lang)}</h2>
        <p className="empty-state-text">
          {lang === "es"
            ? "Configura el motor en el panel izquierdo y pulsa 'Iniciar'. Cada tick de la simulación llegará en tiempo real por WebSocket."
            : "Configure the engine in the left panel and press 'Start'. Every simulation tick arrives in real time over WebSocket."}
        </p>
      </div>
    );
  }

  const m = snap.metrics;
  const pct = (v: number) => `${Math.round(v * 100)}%`;

  const cards: { k: string; v: string; color?: string }[] = [
    { k: t("meanLabel", lang) ?? "Mean", v: m.mean_opinion.toFixed(3), color: "rgb(255,143,64)" },
    { k: t("stdLabel", lang), v: m.std_opinion.toFixed(3) },
    { k: t("polarizationLabel", lang), v: m.polarization.toFixed(3), color: "rgb(255,95,86)" },
    { k: t("consensusLabel", lang), v: pct(m.consensus_rate), color: "rgb(186,230,126)" },
    { k: t("fragmentationLabel", lang), v: pct(m.fragmentation_index) },
    { k: t("activeAgentsLabel", lang), v: String(m.active_agents), color: "rgb(92,207,230)" },
  ];

  return (
    <div className="results-pad live-view" onMouseMove={handleMouseMove} onMouseLeave={() => setTooltipPos(null)}>
      <div className="run-head live-head">
        <span className="run-title">🔴 {live.engine}</span>
        <span className="badge" style={{ color: "#ff8f40", borderColor: "#ff8f4044", background: "#ff8f400d" }}>
          LIVE
        </span>
        <span className="badge" style={{ color: "var(--textDim)", borderColor: "var(--border)" }}>
          tick {snap.tick}
        </span>
        <span className="badge" style={{ color: "var(--accent)", borderColor: "#5ccfe644", background: "#5ccfe60d" }}>
          {m.dominant_rule}
        </span>
        {tooltipPos && <LiveTooltip snap={snap} lang={lang} />}
      </div>

      <div className="hl-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))" }}>
        {cards.map((c, i) => (
          <div key={i} className="hl-card" style={{ borderLeft: c.color ? `3px solid ${c.color}` : undefined }}>
            <div className="k">{c.k}</div>
            <div className="v" style={{ fontSize: 15, color: c.color ?? undefined }}>{c.v}</div>
          </div>
        ))}
      </div>

      <div className="chart-card">
        {live.engine === "energy" && snap.agents ? (
          <>
            <div className="panel-title">
              {t("networkView", lang)} · {snap.agents.length} {t("agentsLabel", lang)}
            </div>
            <NetworkCanvas snap={snap} bipolar={bipolar} />
            <div className="rule-legend">
              <span><span className="swatch" style={{ background: "rgb(255,95,86)" }} />−1</span>
              <span><span className="swatch" style={{ background: "rgb(61,81,102)" }} />0</span>
              <span><span className="swatch" style={{ background: "rgb(92,207,230)" }} />+1</span>
              <span className="legend-divider">|</span>
              <span><span className="swatch" style={{ background: "rgb(186,230,126)" }} />consenso</span>
              <span style={{ marginLeft: 8, color: "var(--textDim)" }}>{t("opinionScale", lang)}</span>
            </div>
          </>
        ) : (
          <>
            <div className="panel-title">{t("streamingMetrics", lang)}</div>
            <SparklineCanvas history={historyRef.current} />
          </>
        )}
      </div>
    </div>
  );
}
