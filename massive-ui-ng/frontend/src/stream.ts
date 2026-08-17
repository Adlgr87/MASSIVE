// ── Minimal SSE-over-fetch client (POST streaming endpoints) ─────────────

export interface SSEHandlers {
  onEvent: (event: string, data: any) => void;
  onError?: (err: Error) => void;
  signal?: AbortSignal;
}

async function errorDetail(res: Response): Promise<string> {
  let detail = `${res.status} ${res.statusText}`;
  try {
    const body = await res.json();
    if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    /* keep generic detail */
  }
  return detail;
}

export async function streamSSE(
  url: string,
  body: unknown,
  handlers: SSEHandlers
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: handlers.signal,
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let event = "message";
      const dataLines: string[] = [];
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) continue;
      try {
        handlers.onEvent(event, JSON.parse(dataLines.join("\n")));
      } catch (e) {
        handlers.onError?.(e as Error);
      }
    }
  }
}
