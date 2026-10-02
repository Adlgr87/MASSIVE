import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import type { ForecastResponse } from "../types/api.generated";

/**
 * API service bound to the MASSIVE v1 API contract.
 *
 * The base URL is "/v1"; every endpoint below is relative to it:
 *
 * v1 typed endpoints:
 *  - POST /v1/forecast         → ForecastResponse (with raw engine payload)
 *  - POST /v1/engine/architect → { strategy, narrative, attempts, history_summary, history_length }
 *  - POST /v1/engine/energy    → Langevin energy engine result dict
 *
 * v1 LLM + UIL endpoints:
 *  - POST /v1/simulate         → full UIL pipeline from a description (was /api/simulate-uil)
 *  - POST /v1/llm/extract      → upload a document and return an extracted config (was /api/extract)
 *  - POST /v1/llm/wizard       → generate a config from natural-language description (was /api/wizard)
 *
 * All endpoints require the `X-API-Key` header (injected in the constructor).
 * The deprecated /api/* aliases are no longer referenced by this client.
 */
/** Request body for POST /v1/engine/energy. */
export type EnergyRequest = {
  user_goal: string;
  n_agents?: number;
  steps?: number;
  connectivity?: number;
  range_type?: "bipolar" | "unipolar";
  seed?: number;
  config_overrides?: Record<string, unknown> | null;
};

/** Response body for POST /v1/engine/energy. */
export type EnergyResult = {
  history: Record<string, unknown>[];
  metrics_timeline: Record<string, number | string | null>[];
  final_state: {
    opinions: number[];
    mean_opinion: number;
    std_opinion: number;
  };
  summary: {
    opinion_inicial: number;
    opinion_final: number;
    delta_total: number;
    media: number;
    desviacion: number;
    polarizacion_media: number;
    pasos: number;
    regla_dominante: string;
    neutro: number;
    rango: string;
  };
  config_used: Record<string, unknown>;
  archetype_info: Record<string, unknown>;
};

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: "/v1",
      headers: {
        "Content-Type": "application/json",
      },
    });

    // API key is read from the Vite env at init time.
    //
    // No credential is hardcoded here. This used to fall back to the literal
    // "dev-secret-key" whenever MODE === "development", which baked a known
    // credential into client source and contradicted the project's
    // fail-closed invariant. It was also simply wrong: the backend only
    // honours that fallback when MASSIVE_DEV_FALLBACK is explicitly set, so
    // the client was silently sending a key the server would reject.
    //
    // To develop against a local backend, set VITE_MASSIVE_API_KEY in
    // frontend/.env.local (git-ignored) to whatever MASSIVE_API_KEY the
    // backend is running with.
    const apiKey = import.meta.env.VITE_MASSIVE_API_KEY;

    if (apiKey) {
      this.client.defaults.headers.common["X-API-Key"] = apiKey;
    } else {
      console.warn(
        "[MASSIVE] VITE_MASSIVE_API_KEY is not set — requests will be sent " +
          "without an X-API-Key header and the API will answer 401/503. " +
          "Set it in frontend/.env.local to match the backend's MASSIVE_API_KEY.",
      );
    }

    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error) => {
        if (error.response?.status === 401) {
          console.error("Unauthorized: invalid or missing API key");
        } else if (error.response?.status === 429) {
          console.error("Rate limit exceeded");
        }
        return Promise.reject(error);
      },
    );
  }

  /* ───────────── generic HTTP helpers ───────────── */

  async get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T = unknown, D = unknown>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T = unknown, D = unknown>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async patch<T = unknown, D = unknown>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  async delete<T = unknown>(
    url: string,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  getClient(): AxiosInstance {
    return this.client;
  }

  /* ───────────── v1 typed endpoints ───────────── */

  /** POST /v1/forecast — projected risk / opinion state over a horizon. */
  async forecast(payload: {
    simulation_state: Record<string, unknown>;
    sim_id?: string | null;
    temporal_config?: Record<string, unknown>;
    mode?: "analytical" | "monte_carlo";
    n_runs?: number;
  }): Promise<{ forecast: ForecastResponse; raw: Record<string, unknown> }> {
    return this.post("/forecast", payload);
  }

  /** POST /v1/engine/architect — inverse-search strategy for a user goal. */
  async architect(payload: {
    estado_inicial: Record<string, unknown>;
    objetivo_usuario: string;
    max_intentos?: number;
    config?: Record<string, unknown> | null;
    modo_simulacion?: "macro" | "corporativo";
    metricas_red?: string;
  }): Promise<{
    strategy: Record<string, unknown>;
    narrative: string;
    attempts: number;
    history_summary: unknown[];
    history_length: number;
  }> {
    return this.post("/engine/architect", payload);
  }

  /** POST /v1/engine/energy — Langevin energy landscape simulation. */
  async energy(payload: EnergyRequest): Promise<EnergyResult> {
    return this.post("/engine/energy", payload);
  }

  /* ───────────── v1 LLM + UIL endpoints ───────────── */

  /**
   * POST /v1/llm/simulate_uil — run the full UIL pipeline from a description.
   *
   * NOTE: this used to post `{ description }` to `/v1/simulate`, but that
   * route is backed by the `SimRequest` DTO (`extra="forbid"`, fields
   * `estado_inicial` / `escenario` / `pasos` / `config` / `verbose`), so every
   * call returned 422. The UIL pipeline lives under `/v1/llm/*`.
   */
  async simulateUil(description: string): Promise<{
    config: Record<string, unknown>;
    summary: Record<string, unknown>;
    n_steps: number;
  }> {
    return this.post("/llm/simulate_uil", { description });
  }

  /** POST /v1/simulate — run a scalar MASSIVE simulation (typed SimRequest). */
  async simulate(payload: {
    estado_inicial?: Record<string, unknown> | null;
    escenario?: string;
    pasos?: number;
    config?: Record<string, unknown> | null;
    verbose?: boolean;
  }): Promise<Record<string, unknown>> {
    return this.post("/simulate", payload);
  }

  /** POST /v1/llm/extract — upload a document and get an extracted config (was /api/extract). */
  async extractDocument(
    file: File,
  ): Promise<{ config: Record<string, unknown> }> {
    const form = new FormData();
    form.append("file", file);
    return this.post("/llm/extract", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  }

  /** POST /v1/llm/wizard — generate a config from a natural-language description (was /api/wizard). */
  async wizard(
    description: string,
  ): Promise<{ config: Record<string, unknown> }> {
    return this.post("/llm/wizard", { description });
  }
}

export const api = new ApiService();
export default api;
