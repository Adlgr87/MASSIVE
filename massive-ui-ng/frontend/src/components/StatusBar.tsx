import type { StatusResponse } from "../types";
import { t, type Language } from "../i18n";

function Pill({ on, warn, info, children }: { on?: boolean; warn?: boolean; info?: boolean; children: React.ReactNode }) {
  const cls = ["pill", on ? "on" : warn ? "warn" : info ? "info" : ""].join(" ");
  return (
    <span className={cls}>
      <span className="dot" />
      {children}
    </span>
  );
}

export default function StatusBar({ status, lang }: { status: StatusResponse | null; lang: Language }) {
  return (
    <div className="header-right">
      {status && (
        <>
          {status.llm.configured ? (
            <Pill on>{`${t("llmConfigured", lang)}: ${status.llm.provider}`}</Pill>
          ) : (
            <Pill warn>{t("llmNotConfigured", lang)}</Pill>
          )}
          {status.cfc?.regime_selector && <Pill on>{t("cfcOn", lang)}</Pill>}
          {status.rust_available && <Pill info>{t("rustOn", lang)}</Pill>}
          <Pill info>v{status.version}</Pill>
        </>
      )}
    </div>
  );
}
