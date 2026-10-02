/**
 * Minimal line chart rendered as inline SVG.
 *
 * Deliberately dependency-free: adding a charting library (recharts, plotly,
 * d3) to draw one polyline would add hundreds of kilobytes to the bundle for
 * a single view. If the UI later needs axes, zooming, tooltips and multiple
 * series, revisit that decision then rather than pre-emptively.
 */

type TrajectoryChartProps = {
  /** Y values in plot order. */
  values: number[];
  /** Accessible description of what is being plotted. */
  label: string;
  /** Fixed y-domain. Falls back to the data range when omitted. */
  domain?: [number, number];
  height?: number;
};

const WIDTH = 600;

export function TrajectoryChart({
  values,
  label,
  domain,
  height = 180,
}: TrajectoryChartProps) {
  const finite = values.filter((v) => Number.isFinite(v));

  if (finite.length < 2) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground"
        style={{ height }}
      >
        Not enough data points to plot
      </div>
    );
  }

  const [lo, hi] = domain ?? [Math.min(...finite), Math.max(...finite)];
  // Guard against a zero-height domain (constant series), which would
  // otherwise divide by zero and collapse every point onto one line.
  const span = hi - lo || 1;

  const padding = { top: 8, right: 8, bottom: 20, left: 36 };
  const plotW = WIDTH - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  const toX = (i: number) => padding.left + (i / (finite.length - 1)) * plotW;
  const toY = (v: number) => padding.top + plotH - ((v - lo) / span) * plotH;

  const points = finite.map((v, i) => `${toX(i).toFixed(2)},${toY(v).toFixed(2)}`).join(' ');

  // Horizontal reference line at zero, when zero is inside the domain.
  const zeroY = lo <= 0 && hi >= 0 ? toY(0) : null;

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${height}`}
      className="w-full"
      role="img"
      aria-label={`${label}: ${finite.length} points, from ${finite[0].toFixed(3)} to ${finite[finite.length - 1].toFixed(3)}`}
      preserveAspectRatio="none"
    >
      <rect
        x={padding.left}
        y={padding.top}
        width={plotW}
        height={plotH}
        className="fill-muted/30"
      />

      {zeroY !== null && (
        <line
          x1={padding.left}
          x2={padding.left + plotW}
          y1={zeroY}
          y2={zeroY}
          className="stroke-muted-foreground/40"
          strokeDasharray="4 4"
          strokeWidth={1}
        />
      )}

      <polyline points={points} fill="none" className="stroke-primary" strokeWidth={2} />

      <text x={4} y={padding.top + 10} className="fill-muted-foreground" fontSize={11}>
        {hi.toFixed(2)}
      </text>
      <text x={4} y={padding.top + plotH} className="fill-muted-foreground" fontSize={11}>
        {lo.toFixed(2)}
      </text>
      <text
        x={padding.left}
        y={height - 4}
        className="fill-muted-foreground"
        fontSize={11}
      >
        step 0
      </text>
      <text
        x={WIDTH - padding.right}
        y={height - 4}
        textAnchor="end"
        className="fill-muted-foreground"
        fontSize={11}
      >
        step {finite.length - 1}
      </text>
    </svg>
  );
}

export default TrajectoryChart;
