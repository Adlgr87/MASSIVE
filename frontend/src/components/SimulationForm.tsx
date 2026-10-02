import { useId } from 'react';
import { Button } from '@/components/ui/button';

export type EnergyParams = {
  user_goal: string;
  n_agents: number;
  steps: number;
  connectivity: number;
  range_type: 'bipolar' | 'unipolar';
  seed: number;
};

export const DEFAULT_PARAMS: EnergyParams = {
  user_goal: 'Shift public opinion toward supporting a carbon tax',
  n_agents: 200,
  steps: 100,
  connectivity: 0.1,
  range_type: 'bipolar',
  // Fixed seed by default: the engine is deterministic given a seed, and a
  // reproducible first impression is more useful than a random one.
  seed: 42,
};

type Props = {
  value: EnergyParams;
  onChange: (next: EnergyParams) => void;
  onSubmit: () => void;
  loading: boolean;
};

function NumberField({
  label,
  hint,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  hint?: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (n: number) => void;
}) {
  const id = useId();
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        type="number"
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        value={value}
        min={min}
        max={max}
        step={step ?? 1}
        onChange={(e) => {
          const parsed = Number(e.target.value);
          // Ignore unparseable input rather than propagating NaN into the
          // request payload, which the API would reject with a 422.
          if (Number.isFinite(parsed)) onChange(parsed);
        }}
      />
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function SimulationForm({ value, onChange, onSubmit, loading }: Props) {
  const goalId = useId();
  const rangeId = useId();

  const set = <K extends keyof EnergyParams>(key: K, v: EnergyParams[K]) =>
    onChange({ ...value, [key]: v });

  const goalInvalid = value.user_goal.trim().length === 0;

  return (
    <form
      className="space-y-4 rounded-lg border p-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (!goalInvalid && !loading) onSubmit();
      }}
    >
      <div className="space-y-1">
        <label htmlFor={goalId} className="text-sm font-medium">
          Goal
        </label>
        <textarea
          id={goalId}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          rows={3}
          value={value.user_goal}
          onChange={(e) => set('user_goal', e.target.value)}
          placeholder="Describe the social outcome to simulate"
        />
        {goalInvalid && <p className="text-xs text-destructive">A goal is required.</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <NumberField
          label="Agents"
          hint="Population size"
          value={value.n_agents}
          min={10}
          max={5000}
          step={10}
          onChange={(n) => set('n_agents', n)}
        />
        <NumberField
          label="Steps"
          hint="Integration steps"
          value={value.steps}
          min={1}
          max={2000}
          step={10}
          onChange={(n) => set('steps', n)}
        />
        <NumberField
          label="Connectivity"
          hint="Edge probability (0–1)"
          value={value.connectivity}
          min={0}
          max={1}
          step={0.01}
          onChange={(n) => set('connectivity', n)}
        />
        <NumberField
          label="Seed"
          hint="Same seed ⇒ same result"
          value={value.seed}
          min={0}
          max={2 ** 31 - 1}
          onChange={(n) => set('seed', n)}
        />
      </div>

      <div className="space-y-1">
        <label htmlFor={rangeId} className="text-sm font-medium">
          Opinion range
        </label>
        <select
          id={rangeId}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={value.range_type}
          onChange={(e) => set('range_type', e.target.value as EnergyParams['range_type'])}
        >
          <option value="bipolar">bipolar (−1 … 1)</option>
          <option value="unipolar">unipolar (0 … 1)</option>
        </select>
      </div>

      <Button type="submit" disabled={loading || goalInvalid} className="w-full">
        {loading ? 'Running simulation…' : 'Run simulation'}
      </Button>
    </form>
  );
}

export default SimulationForm;
