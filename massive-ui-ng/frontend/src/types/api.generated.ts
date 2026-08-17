// ============================================================
// AUTO-GENERATED — do not edit manually.
// Source of truth: backend/app/models (Pydantic v2).
// Regenerate with:  python scripts/gen_ts_types.py
// ============================================================

export enum SimMode {
  live = "live",
  replay = "replay",
}

export enum SimEventKind {
  started = "started",
  stopped = "stopped",
  reset = "reset",
  error = "error",
}

export interface SimAgentLite {
  id: string;
  layer: string;
  x: number;
  y: number;
  z?: number;
  opinion: number;
  metadata?: Record<string, unknown> | null;
}

export interface SimAggregateMetrics {
  mean_opinion: number;
  std_opinion: number;
  polarization: number;
  dominant_rule: string;
  consensus_rate: number;
  fragmentation_index: number;
  active_agents: number;
  schema_version?: string | null;
}

export interface SimulationSnapshotPayload {
  tick: number;
  metrics: SimAggregateMetrics;
  agents?: SimAgentLite[] | null;
  mode?: SimMode;
  schema_version?: string | null;
}

export interface SimSnapshotMessage {
  type?: "snapshot";
  sim_id: string;
  timestamp: string;
  payload: SimulationSnapshotPayload;
  schema_version?: string | null;
}

export interface SimEventMessage {
  type?: "event";
  sim_id: string;
  event: SimEventKind;
  detail?: string | null;
  schema_version?: string | null;
}

export interface SnapshotRecord {
  snapshot_id: string;
  sim_id: string;
  tick: number;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface TimelineTick {
  tick: number;
  mean_opinion: number;
  polarization: number;
  dominant_rule: string;
  timestamp?: string | null;
}

export interface TimelineResponse {
  sim_id: string;
  ticks: TimelineTick[];
  total: number;
}

export interface ForecastPoint {
  tick: number;
  mean_opinion: number;
  polarization: number;
  confidence_lower: number;
  confidence_upper: number;
}

export interface Feasibility {
  score: number;
  label: string;
  rationale?: string | null;
}

export interface ForecastResponse {
  sim_id: string;
  horizon_ticks: number;
  points: ForecastPoint[];
  feasibility: Feasibility;
}

export interface InterventionRecord {
  intervention_id: string;
  sim_id: string;
  time_start: number;
  time_end: number;
  model_name: string;
  parameters: Record<string, unknown>;
  target_nodes?: string[] | null;
  rationale?: string | null;
}

export interface InterventionLogEntry {
  entry_id: string;
  intervention_id: string;
  tick: number;
  timestamp: string;
  effect_delta: number;
  notes?: string | null;
}

export interface ArchitectEventMessage {
  type?: "architect_event";
  sim_id: string;
  intervention: InterventionRecord;
  timestamp: string;
  schema_version?: string | null;
}

export interface AssumptionItem {
  parameter: string;
  value: string;
  reason: string;
  confidence: number;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ConversationRequest {
  messages: ChatMessage[];
  language?: "es" | "en";
}

export interface ConversationResponse {
  reply: string;
  action: "clarify" | "propose" | "ready";
  assumptions?: AssumptionItem[];
  questions?: string[];
  config_draft?: Record<string, unknown>;
  mode: "llm" | "heuristic";
}

export interface SimulateRequest {
  engine?: "scalar" | "energy" | "multilayer" | "massive";
  escenario?: string;
  pasos?: number;
  estado_inicial?: Record<string, unknown>;
  config?: Record<string, unknown>;
  seed?: number | null;
  scientific?: boolean;
  language?: "es" | "en";
  audience?: "general" | "tecnico";
  n_agents?: number | null;
  connectivity?: number;
  range_type?: "bipolar" | "unipolar";
  layer_weights?: number[] | null;
  quantize?: boolean;
  event_driven?: boolean;
}

export interface SimulateResponse {
  run_id: string;
  engine: string;
  mode: "llm" | "heuristic";
  language: string;
  summary?: Record<string, unknown>;
  scientific_report?: Record<string, unknown> | null;
  series?: Record<string, unknown>;
  narrative?: string;
  highlights?: Highlight[];
  meta?: Record<string, unknown>;
}

export interface Highlight {
  label: string;
  value: string;
  meaning: string;
}

export interface ExplainRequest {
  run_id: string;
  language?: "es" | "en";
  audience?: "general" | "tecnico";
}

export interface ExplainResponse {
  run_id: string;
  language: string;
  audience: string;
  narrative: string;
  highlights?: Highlight[];
  mode: "llm" | "template";
}

export interface RunListItem {
  run_id: string;
  engine: string;
  language: string;
  headline: string;
  final_opinion?: number | null;
  dominant_rule?: string | null;
  mode: string;
}

export interface LLMStatus {
  configured: boolean;
  provider: string;
  model: string;
}

export interface CFCStatus {
  regime_selector?: boolean;
  tau_matrix?: boolean;
  architect_policy?: boolean;
}

export interface StatusResponse {
  service: string;
  version: string;
  llm: LLMStatus;
  cfc: CFCStatus;
  rust_available: boolean;
  engines: string[];
  factbook_countries?: string[];
  languages?: string[];
}
