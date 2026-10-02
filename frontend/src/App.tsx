import { useCallback, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import axios from 'axios';

import SimulationForm, { DEFAULT_PARAMS, type EnergyParams } from '@/components/SimulationForm';
import ResultsPanel from '@/components/ResultsPanel';
import api, { type EnergyResult } from '@/services/api';

/**
 * Translate an axios failure into something a human can act on.
 *
 * The API answers 401/403 when the key is missing or wrong, 503 when a
 * required optional component is absent (fail-closed, never degraded), 422
 * on DTO validation errors and 429 on rate limiting. Surfacing the raw
 * "Request failed with status code 503" string would leave the user with no
 * idea which of those happened.
 */
function describeError(err: unknown): string {
  if (!axios.isAxiosError(err)) {
    return err instanceof Error ? err.message : 'Unexpected error.';
  }
  if (!err.response) {
    return 'Could not reach the API. Is the backend running on port 8000?';
  }
  const { status, data } = err.response;
  const detail =
    typeof data === 'object' && data !== null && 'detail' in data
      ? JSON.stringify((data as { detail: unknown }).detail)
      : null;

  switch (status) {
    case 401:
    case 403:
      return 'Unauthorized. Set VITE_MASSIVE_API_KEY in frontend/.env.local to match the backend MASSIVE_API_KEY.';
    case 422:
      return `The API rejected these parameters: ${detail ?? 'validation error'}`;
    case 429:
      return 'Rate limit exceeded (60 requests/min per IP). Wait a moment and retry.';
    case 503:
      return `The engine is unavailable: ${detail ?? 'a required component is not configured'}.`;
    default:
      return `API error ${status}: ${detail ?? 'unknown error'}`;
  }
}

function SimulatePage() {
  const [params, setParams] = useState<EnergyParams>(DEFAULT_PARAMS);
  const [result, setResult] = useState<EnergyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.energy(params);
      setResult(data);
    } catch (err) {
      setError(describeError(err));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [params]);

  return (
    <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Energy engine</h2>
          <p className="text-sm text-muted-foreground">
            Langevin dynamics over a social energy landscape. Deterministic for a
            given seed — no LLM, GPU or Rust extension required.
          </p>
        </div>
        <SimulationForm
          value={params}
          onChange={setParams}
          onSubmit={run}
          loading={loading}
        />
      </div>

      <div className="min-w-0">
        {error && (
          <div
            role="alert"
            className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm"
          >
            <strong className="font-semibold">Simulation failed. </strong>
            {error}
          </div>
        )}

        {!error && !result && !loading && (
          <div className="flex h-64 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
            Configure the parameters and run a simulation to see results.
          </div>
        )}

        {loading && (
          <div className="flex h-64 items-center justify-center rounded-lg border text-sm text-muted-foreground">
            Running {params.steps} steps over {params.n_agents} agents…
          </div>
        )}

        {!loading && result && <ResultsPanel result={result} />}
      </div>
    </div>
  );
}

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container mx-auto flex items-baseline gap-3 px-4 py-4">
          <h1 className="text-2xl font-bold">MASSIVE UIL</h1>
          <span className="text-sm text-muted-foreground">
            Mathematical Architecture for Scalable Social Interaction and Virtual Engine
          </span>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<SimulatePage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
