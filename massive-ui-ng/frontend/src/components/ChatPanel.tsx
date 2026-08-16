import { useEffect, useRef, useState } from "react";
import type { ChatMessage, ConversationResponse } from "../types";
import { t, type Language } from "../i18n";
import { AssumptionsPanel, QuestionsPanel } from "./DraftEditor";

export default function ChatPanel({
  messages,
  thinking,
  streamingText,
  turn,
  lang,
  onSend,
  onAsk,
}: {
  messages: ChatMessage[];
  thinking: boolean;
  streamingText: string | null;
  turn: ConversationResponse | null;
  lang: Language;
  onSend: (text: string) => void;
  onAsk: (q: string) => void;
}) {
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);
  const typingTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    const scrollToBottom = () => {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    };
    if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = window.setTimeout(scrollToBottom, 50);
    return () => {
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    };
  }, [messages, thinking, turn, streamingText]);

  const submit = () => {
    const text = input.trim();
    if (!text || thinking) return;
    setInput("");
    onSend(text);
  };

  return (
    <div className="chat-container">
      <div className="chat-area">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className={`avatar ${m.role === "user" ? "avatar-user" : "avatar-assistant"}`}>
              {m.role === "user" ? "U" : "🌊"}
            </div>
            <div className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-assistant"}`}>
              {m.content.split("\n").map((line, j) => (
                <p key={j} style={{ margin: j > 0 ? "6px 0 0" : 0 }}>{line || "\u00A0"}</p>
              ))}
            </div>
          </div>
        ))}

        {turn && <AssumptionsPanel assumptions={turn.assumptions ?? []} lang={lang} />}
        {turn && <QuestionsPanel questions={turn.questions ?? []} onAsk={onAsk} lang={lang} />}

        {(thinking || streamingText !== null) && (
          <div className="msg assistant">
            <div className="avatar avatar-assistant">🌊</div>
            <div className="bubble bubble-assistant">
              {streamingText ? (
                <TypingIndicator text={streamingText} />
              ) : (
                <>
                  <span className="typing-dots">
                    <span>.</span><span>.</span><span>.</span>
                  </span>
                  {t("thinking", lang)}
                </>
              )}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="chat-input-row">
        <input
          className="chat-input"
          placeholder={t("placeholder", lang)}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          aria-label={t("placeholder", lang)}
        />
        <button
          className="btn primary send-btn"
          onClick={submit}
          disabled={thinking || !input.trim()}
          title={t("send", lang)}
        >
          <span className="send-icon">➤</span>
        </button>
      </div>
    </div>
  );
}

// Componente de indicador de escritura con animación de cursor parpadeante
function TypingIndicator({ text }: { text: string }) {
  const [visibleChars, setVisibleChars] = useState(0);
  const charIndexRef = useRef(0);

  useEffect(() => {
    charIndexRef.current = 0;
    setVisibleChars(0);

    const interval = setInterval(() => {
      charIndexRef.current += 1;
      setVisibleChars(charIndexRef.current);
    }, 15);

    return () => clearInterval(interval);
  }, [text]);

  return (
    <>
      <span className="streaming-text">{text.slice(0, visibleChars)}</span>
      <span className="cursor-blink">|</span>
    </>
  );
}
