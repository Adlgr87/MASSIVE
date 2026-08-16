// ── WebSocket client for the live simulation endpoint (/ws/live) ─────────

import type { LiveSnapshot } from "./types";

export interface LiveParams {
  engine: "energy" | "massive";
  n_agents: number;
  connectivity: number;
  range_type: "bipolar" | "unipolar";
  seed: number;
  pasos: number;
  user_goal: string;
}

export interface LiveHandlers {
  onOpen: () => void;
  onSnapshot: (snap: LiveSnapshot) => void;
  onEvent: (event: string, detail?: string) => void;
  onClose: (code: number) => void;
  onError: (err: string) => void;
}

export interface LiveConnection {
  send: (obj: unknown) => void;
  close: () => void;
}

export function openLiveStream(
  params: LiveParams,
  handlers: LiveHandlers
): LiveConnection {
  const qs = new URLSearchParams({
    engine: params.engine,
    n_agents: String(params.n_agents),
    connectivity: String(params.connectivity),
    range_type: params.range_type,
    seed: String(params.seed),
    pasos: String(params.pasos),
    user_goal: params.user_goal,
  });
  // Browsers cannot set WS headers → key is not sent from here; in prod the
  // page is served same-origin behind the same auth as the API gateway.
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${scheme}://${window.location.host}/ws/live?${qs.toString()}`;

  const ws = new WebSocket(url);
  ws.onopen = () => handlers.onOpen();
  ws.onmessage = (ev) => {
    let data: any;
    try {
      data = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (data?.type === "snapshot") {
      const p = data.payload ?? {};
      handlers.onSnapshot({
        tick: p.tick ?? 0,
        metrics: p.metrics ?? null,
        agents: p.agents ?? null,
        sim_id: data.sim_id,
      });
    } else if (data?.type === "event") {
      handlers.onEvent(data.event ?? "event", data.detail);
    }
  };
  ws.onerror = () => handlers.onError("ws-error");
  ws.onclose = (ev) => handlers.onClose(ev.code);

  return {
    send: (obj: unknown) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
    },
    close: () => ws.close(1000, "client close"),
  };
}
