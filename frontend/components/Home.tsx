"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { api, ApiError, hasToken, post, randomDemoCredentials, setTokens } from "@/lib/api";
import type { Session } from "@/lib/types";
import VoiceInput from "./VoiceInput";

const DEMO = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";
type Consent = { purpose: string; granted: boolean }[];
const DEMO_GOAL: Record<string, string> = {
  en: "I want to open a small bakery in Kolkata",
  bn: "আমি কলকাতায় একটি ছোট বেকারি খুলতে চাই",
  hi: "मैं कोलकाता में एक छोटी बेकरी खोलना चाहता हूँ",
};

function AuthForm({ onDone }: { onDone: () => void }) {
  const t = useTranslations("auth");
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const locale = useLocale();
  const ids = [useId(), useId()];

  const go = async (path: string, body: object) => {
    setBusy(true);
    setErr(null);
    try {
      const tok = await post<{ access_token: string; refresh_token: string }>(path, body);
      setTokens(tok.access_token, tok.refresh_token);
      onDone();
    } catch {
      setErr(t("failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card mx-auto max-w-md" aria-labelledby="auth-h">
      <h2 id="auth-h" className="mb-3 text-xl font-semibold">
        {t("heading")}
      </h2>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          void go(mode === "login" ? "/auth/login" : "/auth/register", { email, password, language: locale });
        }}
      >
        <div>
          <label htmlFor={ids[0]}>{t("email")}</label>
          <input id={ids[0]} className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label htmlFor={ids[1]}>{t("password")}</label>
          <input id={ids[1]} className="input" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={10} required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {err && (
          <p role="alert" className="text-red-800">
            {err}
          </p>
        )}
        <button className="btn w-full" disabled={busy}>
          {mode === "login" ? t("login") : t("register")}
        </button>
      </form>
      <div className="mt-3 flex flex-col gap-2">
        <button type="button" className="text-left text-brand-700 underline" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? t("toRegister") : t("toLogin")}
        </button>
        {DEMO && (
          <button type="button" className="btn-secondary" disabled={busy} onClick={() => void go("/auth/register", { ...randomDemoCredentials(), language: locale })}>
            {t("demo")}
          </button>
        )}
      </div>
    </section>
  );
}

function ConsentGate({ onDone }: { onDone: () => void }) {
  const t = useTranslations("consent");
  const [reminders, setReminders] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);
  const days = 90;

  const accept = async () => {
    setBusy(true);
    try {
      await post("/consent", { purpose: "service", granted: true });
      if (reminders) await post("/consent", { purpose: "reminders", granted: true });
      onDone();
    } catch {
      setErr(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card mx-auto max-w-2xl" aria-labelledby="consent-h">
      <h2 id="consent-h" className="mb-2 text-xl font-semibold">
        {t("heading")}
      </h2>
      <p className="mb-3">{t("intro")}</p>
      <ul className="mb-3 list-disc space-y-1 pl-5">
        <li>{t("service")}</li>
        <li>{t("data")}</li>
        <li>{t("retention", { days })}</li>
      </ul>
      <label className="mb-3 flex items-start gap-2">
        <input type="checkbox" className="mt-1 h-5 w-5" checked={reminders} onChange={(e) => setReminders(e.target.checked)} />
        <span>
          {t("acceptReminders")} — {t("reminders")}
        </span>
      </label>
      {err && (
        <p role="alert" className="mb-2 text-red-800">
          !
        </p>
      )}
      <button className="btn" disabled={busy} onClick={() => void accept()}>
        {t("accept")}
      </button>
    </section>
  );
}

function GoalForm() {
  const t = useTranslations("goal");
  const locale = useLocale();
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const id = useId();

  const start = async (text: string) => {
    setBusy(true);
    setErr(null);
    try {
      const s = await post<Session>("/sessions", { goal: text, language: locale });
      router.push(`/session/${s.id}`);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "error");
      setBusy(false);
    }
  };

  return (
    <section className="card mx-auto max-w-2xl" aria-labelledby="goal-h">
      <h2 id="goal-h" className="mb-3 text-xl font-semibold">
        {t("heading")}
      </h2>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          void start(goal);
        }}
      >
        <label htmlFor={id}>{t("label")}</label>
        <textarea id={id} className="input min-h-24" minLength={5} maxLength={1000} required value={goal} placeholder={t("placeholder")} onChange={(e) => setGoal(e.target.value)} />
        <div className="flex flex-wrap gap-2">
          <button className="btn" disabled={busy}>
            {t("start")}
          </button>
          <VoiceInput onText={(x) => setGoal((g) => (g ? `${g} ${x}` : x))} />
          {DEMO && (
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => void start(DEMO_GOAL[locale] ?? DEMO_GOAL.en)}>
              {t("demo")}
            </button>
          )}
        </div>
        {err && (
          <p role="alert" className="text-red-800">
            {err}
          </p>
        )}
      </form>
    </section>
  );
}

export default function Home() {
  const t = useTranslations("app");
  const [stage, setStage] = useState<"loading" | "auth" | "consent" | "goal">("loading");

  const check = useCallback(async () => {
    if (!hasToken()) return setStage("auth");
    try {
      const log = await api<Consent>("/consent");
      setStage(log.some((c) => c.purpose === "service" && c.granted) ? "goal" : "consent");
    } catch {
      setStage("auth");
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-brand-900">{t("tagline")}</h1>
      {stage === "loading" && <p aria-live="polite">{t("loading")}</p>}
      {stage === "auth" && <AuthForm onDone={() => void check()} />}
      {stage === "consent" && <ConsentGate onDone={() => setStage("goal")} />}
      {stage === "goal" && <GoalForm />}
    </div>
  );
}
