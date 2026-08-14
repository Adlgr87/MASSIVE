import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import type { ForecastResponse } from "../types/api.generated";

/**
 * API service bound to the MASSIVE backend contract (api.py).
 *
 * Endpoints (all require `X-API-Key` header, see constructor):
 *  - POST /api/v1/forecast  → ForecastResponse (with raw engine payload)
 *  - POST /api/v1/architect → { strategy, narrative, attempts, history_summary, history_length }
 *  - POST /api/v1/energy    → Langevin energy engine result dict
 *
 * Legacy endpoints retained for the UIL demo flow:
 *  - POST /api/extract
 *  - POST /api/wizard
 *  - POST /api/simulate-uil
 *
 * The base URL is '/api'; v1 endpoints prepend '/v1'.
 */
class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: "/api",
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

  /** POST /api/v1/forecast — projected risk / opinion state over a horizon. */
  async forecast(payload: {
    simulation_state: Record<string, unknown>;
    sim_id?: string | null;
    temporal_config?: Record<string, unknown>;
    mode?: "analytical" | "monte_carlo";
    n_runs?: number;
  }): Promise<{ forecast: ForecastResponse; raw: Record<string, unknown> }> {
    return this.post("/api/v1/forecast", payload);
  }

  /** POST /api/v1/architect — inverse-search strategy for a user goal. */
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
    return this.post("/api/v1/architect", payload);
  }

  /** POST /api/v1/energy — Langevin energy landscape simulation. */
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
    return this.post("/api/v1/energy", payload);
  }

  /* ───────────── legacy UIL demo endpoints ───────────── */

  /** POST /api/extract — upload a document and get an extracted config. */
  async extractDocument(
    file: File,
  ): Promise<{ config: Record<string, unknown> }> {
    const form = new FormData();
    form.append("file", file);
    return this.post("/api/extract", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  }

  /** POST /api/wizard — generate a config from a natural-language description. */
  async wizard(
    description: string,
  ): Promise<{ config: Record<string, unknown> }> {
    return this.post("/api/wizard", { description });
  }

  /** POST /api/simulate-uil — run the full UIL pipeline from a description. */
  async simulateUil(description: string): Promise<{
    config: Record<string, unknown>;
    summary: Record<string, unknown>;
    n_steps: number;
  }> {
    return this.post("/api/simulate-uil", { description });
  }
}

export const api = new ApiService();
export default api;
