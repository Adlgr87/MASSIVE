// ── Thin API client (same-origin; Vite proxies /api to the FastAPI backend) ──

import { streamSSE } from "./stream";
import type {
  ChatMessage,
  ConversationResponse,
  ExplainResponse,
  Language,
  RunListItem,
  SimulateRequest,
  SimulateResponse,
  StatusResponse,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep generic detail */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const api = {
  status: () => request<StatusResponse>("/api/status"),

  conversation: (messages: ChatMessage[], language: Language) =>
    request<ConversationResponse>("/api/conversation", {
      method: "POST",
      body: JSON.stringify({ messages, language }),
    }),

  conversationStream: (
    messages: ChatMessage[],
    language: Language,
    onEvent: (event: string, data: any) => void,
    signal?: AbortSignal
  ) =>
    streamSSE("/api/conversation/stream", { messages, language }, { onEvent, signal }),

  simulate: (req: SimulateRequest) =>
    request<SimulateResponse>("/api/simulate", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  simulateStream: (
    req: SimulateRequest,
    onEvent: (event: string, data: any) => void,
    signal?: AbortSignal
  ) => streamSSE("/api/simulate/stream", req, { onEvent, signal }),

  explain: (runId: string, language: Language, audience: "general" | "tecnico") =>
    request<ExplainResponse>("/api/explain", {
      method: "POST",
      body: JSON.stringify({ run_id: runId, language, audience }),
    }),

  runs: () => request<RunListItem[]>("/api/runs"),

  run: (runId: string, language: Language, audience: "general" | "tecnico") =>
    request<SimulateResponse>(
      `/api/runs/${runId}?language=${language}&audience=${audience}`
    ),

  deleteRun: (runId: string) =>
    request<{ deleted: string }>(`/api/runs/${runId}`, { method: "DELETE" }),
};
