import TrajectoryChart from '@/components/TrajectoryChart';
import type { EnergyResult } from '@/services/api';

type Props = {
  result: EnergyResult;
};

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

const fmt = (n: unknown, digits = 3) =>
  typeof n === 'number' && Number.isFinite(n) ? n.toFixed(digits) : '—';

export function ResultsPanel({ result }: Props) {
  const { summary, metrics_timeline: timeline, final_state: finalState } = result;

  // The timeline is a list of per-step metric dicts; pull the mean-opinion
  // series out defensively since the engine may label it either way.
  const meanSeries = (timeline ?? [])
    .map((row) => {
      const v = row.mean_opinion ?? row.media ?? row.mean;
      return typeof v === 'number' ? v : Number.NaN;
    })
    .filter((v) => Number.isFinite(v));

  const polarizationSeries = (timeline ?? [])
    .map((row) => {
      const v = row.polarization ?? row.polarizacion;
      return typeof v === 'number' ? v : Number.NaN;
    })
    .filter((v) => Number.isFinite(v));

  // The engine reports the opinion range as a literal like "[-1.0, 1.0]"
  // (not the "bipolar"/"unipolar" keyword used in the request), so parse the
  // bounds out of it and only fall back to the bipolar default if that fails.
  const opinionDomain: [number, number] = (() => {
    const match = String(summary?.rango ?? '').match(
      /(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)/,
    );
    if (match) {
      const lo = Number(match[1]);
      const hi = Number(match[2]);
      if (Number.isFinite(lo) && Number.isFinite(hi) && hi > lo) return [lo, hi];
    }
    return [-1, 1];
  })();

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-3 text-lg font-semibold">Summary</h3>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="Initial opinion" value={fmt(summary?.opinion_inicial)} />
          <Stat label="Final opinion" value={fmt(summary?.opinion_final)} />
          <Stat
            label="Total change"
            value={fmt(summary?.delta_total)}
            hint="final − initial"
          />
          <Stat
            label="Std. deviation"
            value={fmt(summary?.desviacion)}
            hint="spread across agents"
          />
          <Stat label="Mean polarization" value={fmt(summary?.polarizacion_media)} />
          <Stat label="Steps" value={String(summary?.pasos ?? '—')} />
          <Stat label="Dominant rule" value={String(summary?.regla_dominante ?? '—')} />
          <Stat label="Range" value={String(summary?.rango ?? '—')} />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-lg font-semibold">Mean opinion over time</h3>
        <div className="rounded-lg border p-3">
          <TrajectoryChart
            values={meanSeries}
            label="Mean opinion over time"
            domain={opinionDomain}
          />
        </div>
      </section>

      {polarizationSeries.length > 1 && (
        <section>
          <h3 className="mb-3 text-lg font-semibold">Polarization over time</h3>
          <div className="rounded-lg border p-3">
            <TrajectoryChart
              values={polarizationSeries}
              label="Polarization over time"
              domain={[0, 1]}
            />
          </div>
        </section>
      )}

      <section>
        <h3 className="mb-3 text-lg font-semibold">Final state</h3>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <Stat label="Mean" value={fmt(finalState?.mean_opinion)} />
          <Stat label="Std" value={fmt(finalState?.std_opinion)} />
          <Stat label="Agents" value={String(finalState?.opinions?.length ?? '—')} />
        </div>
      </section>

      <details className="rounded-lg border p-3">
        <summary className="cursor-pointer text-sm font-medium">
          Raw config used by the engine
        </summary>
        <pre className="mt-2 overflow-auto rounded bg-muted p-3 text-xs">
          {JSON.stringify(result.config_used ?? {}, null, 2)}
        </pre>
      </details>
    </div>
  );
}

export default ResultsPanel;
