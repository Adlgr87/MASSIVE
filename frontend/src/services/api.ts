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
class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: "/v1",
      headers: {
        "Content-Type": "application/json",
      },
    });

    // API key is read from the Vite env at init time. In dev mode the backend
    // accepts the dev fallback "dev-secret-key", so a missing key simply
    // disables auth rather than breaking the client build.
    const apiKey =
      import.meta.env.VITE_MASSIVE_API_KEY ||
      (import.meta.env.MODE === "development" ? "dev-secret-key" : undefined);

    if (apiKey) {
      this.client.defaults.headers.common["X-API-Key"] = apiKey;
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
  async energy(payload: {
    user_goal: string;
    n_agents?: number;
    steps?: number;
    connectivity?: number;
    range_type?: "bipolar" | "unipolar";
    seed?: number;
    config_overrides?: Record<string, unknown> | null;
  }): Promise<{
    history: Record<string, unknown>[];
    metrics_timeline: Record<string, unknown>[];
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
  }> {
    return this.post("/engine/energy", payload);
  }

  /* ───────────── v1 LLM + UIL endpoints ───────────── */

  /** POST /v1/simulate — run the full UIL pipeline from a description (was /api/simulate-uil). */
  async simulateUil(description: string): Promise<{
    config: Record<string, unknown>;
    summary: Record<string, unknown>;
    n_steps: number;
  }> {
    return this.post("/simulate", { description });
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
