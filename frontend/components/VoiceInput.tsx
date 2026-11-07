"use client";

import { useEffect, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

type Rec = {
  lang: string;
  interimResults: boolean;
  onresult: ((e: { results: { 0: { transcript: string } }[] }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type RecCtor = new () => Rec;

const LANG: Record<string, string> = { en: "en-IN", bn: "bn-IN", hi: "hi-IN" };

function getCtor(): RecCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: RecCtor; webkitSpeechRecognition?: RecCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Voice input via the Web Speech API. Renders nothing useful when unsupported (progressive enhancement). */
export default function VoiceInput({ onText }: { onText: (text: string) => void }) {
  const t = useTranslations("goal");
  const locale = useLocale();
  const [supported, setSupported] = useState<boolean | null>(null);
  const [listening, setListening] = useState(false);
  const rec = useRef<Rec | null>(null);

  useEffect(() => {
    setSupported(getCtor() !== null);
    return () => rec.current?.stop();
  }, []);

  if (supported === null) return null;
  if (!supported) return <p className="text-sm text-slate-700">{t("voiceUnsupported")}</p>;

  const toggle = () => {
    if (listening) {
      rec.current?.stop();
      return;
    }
    const Ctor = getCtor();
    if (!Ctor) return;
    const r = new Ctor();
    r.lang = LANG[locale] ?? "en-IN";
    r.interimResults = false;
    r.onresult = (e) => onText(e.results[0][0].transcript);
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    rec.current = r;
    setListening(true);
    r.start();
  };

  return (
    <button type="button" className="btn-secondary" onClick={toggle} aria-pressed={listening}>
      <span aria-hidden="true">🎤 </span>
      {listening ? t("voiceStop") : t("voice")}
      {listening && <span className="sr-only"> — {t("listening")}</span>}
    </button>
  );
}
