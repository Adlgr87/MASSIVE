// ── Typed contract with the UI-NG backend ────────────────────────────────
// The canonical interfaces live in ./types/api.generated.ts (generated from
// backend/app/models Pydantic DTOs by `python scripts/gen_ts_types.py`).
// This module re-exports them and adds ergonomic aliases for the fields the
// backend types as free-form dicts (summary/series/meta payloads).

import type { Highlight, SimulateResponse as SimulateResponseGen } from "./types/api.generated";

export type {
  AssumptionItem,
  ChatMessage,
  ConversationResponse,
  ExplainResponse,
  Highlight,
  LLMStatus,
  CFCStatus,
  RunListItem,
  StatusResponse,
  SimulateRequest as SimulateRequestGen,
  SimulateResponse as SimulateResponseGen,
  SimAgentLite,
  SimAggregateMetrics,
  SimulationSnapshotPayload,
  SimSnapshotMessage,
  SimEventMessage,
  SimEventKind,
  SimMode,
} from "./types/api.generated";

// ── Live (WebSocket) state ────────────────────────────────────────────────

export interface LiveMetrics {
  mean_opinion: number;
  std_opinion: number;
  polarization: number;
  dominant_rule: string;
  consensus_rate: number;
  fragmentation_index: number;
  active_agents: number;
}

export interface LiveAgent {
  id: string;
  layer: string;
  x: number;
  y: number;
  opinion: number;
}

export interface LiveSnapshot {
  tick: number;
  metrics: LiveMetrics;
  agents: LiveAgent[] | null;
  sim_id?: string;
}

export type LiveStatus = "idle" | "connecting" | "running" | "stopped" | "error";

export interface LiveState {
  status: LiveStatus;
  engine: "energy" | "massive";
  range_type?: "bipolar" | "unipolar";
  snapshot: LiveSnapshot | null;
  error: string | null;
}

// ── Local aliases ─────────────────────────────────────────────────────────

export type Language = "es" | "en";
export type Audience = "general" | "tecnico";
export type Engine = "scalar" | "energy" | "multilayer" | "massive";

/** Free-form config draft produced by the translator (validated server-side). */
export interface ConfigDraft {
  estado_inicial?: Record<string, number>;
  escenario?: string;
  pasos?: number;
  config?: Record<string, unknown>;
}

/** Typed view of the engine summary payload. */
export interface RunSummary {
  opinion_inicial?: number | null;
  opinion_final?: number | null;
  delta_total?: number | null;
  polarizacion_media?: number | null;
  media?: number | null;
  desviacion?: number | null;
  pasos?: number | null;
  regla_dominante?: string | null;
  neutro?: number | null;
  rango?: string | null;
  [key: string]: unknown;
}

/** Typed view of the chart series payload. */
export interface RunSeries {
  t?: number[];
  opinion?: number[];
  propaganda?: number[];
  confianza?: number[];
  std_opinion?: number[];
  polarization?: number[];
  active_fraction?: number[];
  cooperation?: number[];
  regla?: (number | null)[];
  regla_nombre?: (string | null)[];
  razon?: (string | null)[];
  [key: string]: unknown;
}

/** Typed view of the engine metadata payload. */
export interface RunMeta {
  n_agents?: number | null;
  n_clusters?: number | null;
  memory_savings_pct?: number | null;
  steps_per_second?: number | null;
  elapsed_seconds?: number | null;
  active_history?: number[];
  neutro?: number | null;
  rango?: string | null;
  [key: string]: unknown;
}

/** Client-side simulation request (stricter field types than the generated DTO). */
export interface SimulateRequest {
  engine: Engine;
  escenario: string;
  pasos: number;
  estado_inicial: Record<string, number>;
  config: Record<string, unknown>;
  seed?: number | null;
  scientific: boolean;
  language: Language;
  audience: Audience;
  n_agents?: number | null;
  connectivity?: number;
  range_type?: "bipolar" | "unipolar";
  layer_weights?: number[];
  quantize?: boolean;
  event_driven?: boolean;
}

/** Server response with typed payload views. */
export interface SimulateResponse
  extends Omit<SimulateResponseGen, "summary" | "series" | "meta" | "scientific_report" | "narrative" | "highlights"> {
  summary: RunSummary;
  scientific_report: Record<string, any> | null;
  series: RunSeries;
  meta: RunMeta;
  narrative: string;
  highlights: Highlight[];
}
