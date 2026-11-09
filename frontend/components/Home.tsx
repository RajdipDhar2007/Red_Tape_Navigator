"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { api, ApiError, hasToken, post, setTokens } from "@/lib/api";
import Icon, { type IconName } from "./Icon";
import { ChakraWheel } from "./LogoMark";
import CountUp from "./fx/CountUp";
import ProgressRing from "./fx/ProgressRing";
import Reveal from "./fx/Reveal";
import VoiceInput from "./VoiceInput";

type Consent = { purpose: string; granted: boolean }[];
type AppRow = { id: string; goal: string; created_at: string; reviewed: boolean; city: string | null; steps: number };

/** 0 = too weak to submit, 1 = weak, 2 = fair, 3 = strong. Length matters most; variety and obvious patterns adjust it. */
export function passwordStrength(p: string): 0 | 1 | 2 | 3 {
  if (p.length < 10) return 0;
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((r) => r.test(p)).length;
  const common = /^(password|12345678|qwerty|letmein|iloveyou|welcome)/i.test(p) || /^(.)\1+$/.test(p);
  if (common) return 1;
  if (p.length >= 16 || (p.length >= 12 && classes >= 3)) return 3;
  return classes >= 2 ? 2 : 1;
}

function AuthCard({ onDone }: { onDone: () => void }) {
  const t = useTranslations("auth");
  const locale = useLocale();
  const [mode, setMode] = useState<"login" | "register" | "forgot">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const ids = [useId(), useId()];
  const strength = passwordStrength(password);

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      if (mode === "forgot") {
        await post("/auth/forgot", { email });
        setSent(true);
        return;
      }
      const tok = await post<{ access_token: string; refresh_token: string }>(mode === "login" ? "/auth/login" : "/auth/register", {
        email,
        password,
        language: locale,
      });
      setTokens(tok.access_token, tok.refresh_token);
      onDone();
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) setErr(t("locked"));
      else if (e instanceof ApiError && e.status === 409) setErr(t("exists"));
      else setErr(mode === "forgot" ? t("failed") : t("failed"));
    } finally {
      setBusy(false);
    }
  };

  const heading = mode === "forgot" ? t("forgotHeading") : mode === "login" ? t("loginHeading") : t("heading");
  const meter = ["bg-slate-200", "bg-red-500", "bg-saffron-500", "bg-indgreen-600"];

  return (
    <section id="start" className="card relative w-full max-w-md scroll-mt-24 border-t-4 border-t-saffron-500 shadow-lift animate-fade-up" aria-labelledby="auth-h">
      <h2 id="auth-h" className="mb-1 text-xl font-bold">
        {heading}
      </h2>
      {mode === "register" && <p className="mb-3 text-sm text-slate-600">{t("registerHelp")}</p>}
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <div>
          <label htmlFor={ids[0]}>{t("email")}</label>
          <input id={ids[0]} className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        {mode !== "forgot" && (
          <div>
            <label htmlFor={ids[1]}>{t("password")}</label>
            <div className="relative">
              <input
                id={ids[1]}
                className="input pr-20"
                type={show ? "text" : "password"}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={10}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button type="button" className="btn-ghost absolute right-1.5 top-1.5 !min-h-0 text-sm" onClick={() => setShow(!show)} aria-pressed={show}>
                {show ? t("hide") : t("show")}
              </button>
            </div>
            {mode === "register" && password && (
              <div className="mt-2" aria-live="polite">
                <div className="flex gap-1" aria-hidden="true">
                  {[1, 2, 3].map((n) => (
                    <span key={n} className={`h-1.5 flex-1 rounded-full transition-colors ${strength >= n ? meter[strength] : "bg-slate-200"}`} />
                  ))}
                </div>
                <p className="mt-1 text-xs text-slate-600">{[t("tooShort"), t("weak"), t("fair"), t("strong")][strength]}</p>
              </div>
            )}
          </div>
        )}
        {err && (
          <p role="alert" className="flex items-start gap-2 rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
            <Icon name="alert" size={18} className="mt-0.5 shrink-0" />
            {err}
          </p>
        )}
        {sent && (
          <p role="status" className="rounded-lg bg-indgreen-50 p-2.5 text-sm text-indgreen-800">
            {t("linkSent")}
          </p>
        )}
        <button className="btn-accent w-full" disabled={busy || (mode === "register" && strength === 0)}>
          {busy ? "…" : mode === "forgot" ? t("sendLink") : mode === "login" ? t("login") : t("register")}
          <Icon name="arrow" size={18} />
        </button>
      </form>
      <div className="mt-4 flex flex-col items-start gap-1 text-sm">
        <button type="button" className="btn-ghost" onClick={() => { setErr(null); setSent(false); setMode(mode === "register" ? "login" : "register"); }}>
          {mode === "register" ? t("toLogin") : mode === "login" ? t("toRegister") : t("backToLogin")}
        </button>
        {mode === "login" && (
          <button type="button" className="btn-ghost" onClick={() => { setErr(null); setMode("forgot"); }}>
            {t("forgot")}
          </button>
        )}
      </div>
    </section>
  );
}

function Landing({ onDone }: { onDone: () => void }) {
  const t = useTranslations("landing");
  const ta = useTranslations("app");
  const how: [IconName, string][] = [["goal", "s1"], ["search", "s2"], ["chat", "s3"], ["shield", "s4"]];
  const services: [IconName, string][] = [["food", "food"], ["store", "retail"], ["scissors", "salon"], ["factory", "factory"], ["dumbbell", "fitness"], ["laptop", "online"], ["plant", "grants"], ["home", "permits"]];
  const trust: [IconName, string][] = [["shield", "t1"], ["file", "t2"], ["lock", "t3"], ["globe", "t4"]];

  return (
    <div className="space-y-16">
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-navy-900 via-navy-800 to-navy-700 px-6 py-12 text-white shadow-lift sm:px-10 lg:py-16">
        <ChakraWheel size={460} className="pointer-events-none absolute -right-24 -top-24 animate-spin-slow text-white/[0.06]" />
        <div className="pointer-events-none absolute -bottom-24 -left-16 h-72 w-72 animate-orb rounded-full bg-saffron-500/20 blur-3xl" aria-hidden="true" />
        <div className="pointer-events-none absolute -bottom-10 right-1/3 h-56 w-56 animate-orb rounded-full bg-indgreen-500/20 blur-3xl [animation-delay:-6s]" aria-hidden="true" />
        <div className="relative grid items-center gap-10 lg:grid-cols-[1.25fr_1fr]">
          <div className="animate-fade-up">
            <span className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-medium text-saffron-200 ring-1 ring-white/20">
              <span className="h-2 w-2 rounded-full bg-indgreen-500" aria-hidden="true" /> {t("badge")}
            </span>
            <h1 className="text-4xl font-bold leading-tight !text-white sm:text-5xl">
              {t("heroTitle1")} <span className="bg-gradient-to-r from-saffron-400 to-saffron-200 bg-clip-text text-transparent">{t("heroTitle2")}</span>
            </h1>
            <p className="mt-4 max-w-xl text-lg text-navy-100">{ta("tagline")}</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <a href="#start" className="btn-accent">
                {t("cta")} <Icon name="arrow" size={18} />
              </a>
              <a href="#how" className="inline-flex items-center rounded-xl border border-white/30 px-5 py-3 font-semibold text-white transition hover:bg-white/10">
                {t("ctaHow")}
              </a>
            </div>
            <dl className="mt-8 grid max-w-md grid-cols-3 gap-4 text-center">
              {[[3, t("langs")], [8, t("cities")], [0, t("autoSubmits")]].map(([n, l]) => (
                <div key={l} className="rounded-xl bg-white/10 p-3 ring-1 ring-white/15 transition hover:-translate-y-1 hover:bg-white/15">
                  <dt className="font-head text-2xl font-bold text-saffron-300">
                    <CountUp to={Number(n)} />
                  </dt>
                  <dd className="text-xs text-navy-100">{l}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="flex justify-center lg:justify-end">
            <AuthCard onDone={onDone} />
          </div>
        </div>
      </section>

      <Reveal>
      <section id="how" className="scroll-mt-24">
        <h2 className="section-title text-center">{t("howTitle")}</h2>
        <ol className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {how.map(([icon, k], i) => (
            <li key={k} className="card card-tilt relative animate-fade-up" style={{ animationDelay: `${i * 90}ms` }}>
              <span className="absolute -top-3 left-5 rounded-full bg-saffron-500 px-2.5 py-0.5 text-xs font-bold text-navy-900">{i + 1}</span>
              <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-navy-50 text-navy-700">
                <Icon name={icon} />
              </span>
              <h3 className="text-lg font-semibold">{t(`${k}t`)}</h3>
              <p className="mt-1 text-sm text-slate-700">{t(`${k}d`)}</p>
            </li>
          ))}
        </ol>
      </section>
      </Reveal>

      <Reveal>
      <section>
        <h2 className="section-title text-center">{t("servicesTitle")}</h2>
        <p className="mx-auto mt-2 max-w-2xl text-center text-slate-700">{t("servicesSub")}</p>
        <ul className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {services.map(([icon, k], i) => (
            <li key={k} className="card card-tilt flex cursor-default flex-col items-center gap-2 text-center animate-fade-up" style={{ animationDelay: `${i * 60}ms` }}>
              <span className={`flex h-12 w-12 items-center justify-center rounded-full ${i % 3 === 0 ? "bg-saffron-100 text-saffron-700" : i % 3 === 1 ? "bg-navy-100 text-navy-700" : "bg-indgreen-100 text-indgreen-700"}`}>
                <Icon name={icon} size={26} />
              </span>
              <span className="font-semibold text-navy-900">{t(`sv_${k}`)}</span>
            </li>
          ))}
        </ul>
      </section>
      </Reveal>

      <Reveal>
      <section className="rounded-3xl bg-white p-6 shadow-card ring-1 ring-slate-200 sm:p-10">
        <h2 className="section-title text-center">{t("trustTitle")}</h2>
        <ul className="mt-8 grid gap-6 sm:grid-cols-2">
          {trust.map(([icon, k]) => (
            <li key={k} className="flex gap-4">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indgreen-50 text-indgreen-700">
                <Icon name={icon} />
              </span>
              <div>
                <h3 className="font-semibold">{t(`${k}t`)}</h3>
                <p className="text-sm text-slate-700">{t(`${k}d`)}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>
      </Reveal>
    </div>
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
    <section className="card mx-auto max-w-2xl border-t-4 border-t-indgreen-600 animate-fade-up" aria-labelledby="consent-h">
      <h2 id="consent-h" className="mb-2 flex items-center gap-2 text-xl font-bold">
        <Icon name="lock" className="text-indgreen-700" /> {t("heading")}
      </h2>
      <p className="mb-3 text-slate-700">{t("intro")}</p>
      <ul className="mb-4 space-y-2">
        {[t("service"), t("data"), t("retention", { days })].map((x) => (
          <li key={x} className="flex gap-2">
            <Icon name="check" size={20} className="mt-0.5 shrink-0 text-indgreen-600" />
            <span>{x}</span>
          </li>
        ))}
      </ul>
      <label className="mb-4 flex items-start gap-3 rounded-xl bg-slate-50 p-3 ring-1 ring-slate-200">
        <input type="checkbox" className="mt-1 h-5 w-5 accent-navy-700" checked={reminders} onChange={(e) => setReminders(e.target.checked)} />
        <span className="font-normal">
          {t("acceptReminders")} — {t("reminders")}
        </span>
      </label>
      {err && (
        <p role="alert" className="mb-2 text-red-800">
          !
        </p>
      )}
      <button className="btn-accent" disabled={busy} onClick={() => void accept()}>
        {t("accept")} <Icon name="arrow" size={18} />
      </button>
    </section>
  );
}

/** Progress and badges, derived from the citizen's own plans (nothing extra is stored). */
function Momentum({ apps }: { apps: AppRow[] }) {
  const t = useTranslations("dash");
  const started = apps.length;
  const reviewed = apps.filter((a) => a.reviewed).length;
  const badges = [
    { id: "first", ok: started >= 1, label: t("badgeFirst"), icon: "goal" as IconName },
    { id: "reviewed", ok: reviewed >= 1, label: t("badgeReviewed"), icon: "file" as IconName },
    { id: "three", ok: started >= 3, label: t("badgeThree"), icon: "shield" as IconName },
  ];
  const next = badges.find((b) => !b.ok);
  return (
    <section aria-labelledby="mom-h" className="card flex flex-wrap items-center gap-5 animate-fade-up">
      <ProgressRing percent={(reviewed / started) * 100} size={76} label={t("formsReviewed", { n: reviewed })} />
      <div className="min-w-48 flex-1">
        <h2 id="mom-h" className="text-lg font-bold">
          {t("momentum")}
        </h2>
        <p className="text-sm text-slate-700">
          {t("plansStarted", { n: started })} · {t("formsReviewed", { n: reviewed })}
        </p>
      </div>
      <ul className="flex flex-wrap gap-2">
        {badges.map((b, i) => (
          <li key={b.id} className={`badge !px-3 !py-1.5 text-sm ${b.ok ? "bg-indgreen-100 text-indgreen-800 animate-pop" : "bg-slate-100 text-slate-500"}`} style={{ animationDelay: `${i * 120}ms` }}>
            <Icon name={b.icon} size={16} /> {b.label}
            {next?.id === b.id && <span className="sr-only"> ({t("nextBadge")})</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Dashboard() {
  const t = useTranslations("dash");
  const tg = useTranslations("goal");
  const locale = useLocale();
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [apps, setApps] = useState<AppRow[] | null>(null);
  const id = useId();
  const [ph, setPh] = useState(0);

  // the empty box cycles through the example goals so a first-time visitor sees what to type
  useEffect(() => {
    const timer = window.setInterval(() => setPh((n) => (n + 1) % 3), 3200);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    api<AppRow[]>("/sessions")
      .then(setApps)
      .catch(() => setApps([]));
  }, []);

  const start = async (text: string) => {
    setBusy(true);
    setErr(null);
    try {
      const s = await post<{ id: string }>("/sessions", { goal: text, language: locale });
      router.push(`/session/${s.id}`);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : t("error"));
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="card relative overflow-hidden border-t-4 border-t-saffron-500 animate-fade-up" aria-labelledby="goal-h">
        <ChakraWheel size={220} className="pointer-events-none absolute -right-16 -top-16 text-navy-900/[0.04]" />
        <h1 id="goal-h" className="text-2xl font-bold sm:text-3xl">
          {t("newTitle")}
        </h1>
        <p className="mt-1 text-slate-700">{t("newHelp")}</p>
        <form
          className="relative mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void start(goal);
          }}
        >
          <label htmlFor={id}>{tg("label")}</label>
          <textarea id={id} className="input min-h-28 text-base" minLength={5} maxLength={1000} required value={goal} placeholder={goal ? undefined : t(["ex1", "ex2", "ex3"][ph])} onChange={(e) => setGoal(e.target.value)} />
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-slate-600">{t("tryExamples")}</span>
            {["ex1", "ex2", "ex3"].map((k) => (
              <button key={k} type="button" className="chip" onClick={() => setGoal(t(k))}>
                {t(k)}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-3">
            <button className="btn-accent" disabled={busy}>
              {busy ? "…" : tg("start")} <Icon name="arrow" size={18} />
            </button>
            <VoiceInput onText={(x) => setGoal((g) => (g ? `${g} ${x}` : x))} />
          </div>
          {err && (
            <p role="alert" className="rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
              {err}
            </p>
          )}
        </form>
      </section>

      {apps && apps.length > 0 && <Momentum apps={apps} />}

      <section aria-labelledby="mine-h">
        <h2 id="mine-h" className="mb-3 text-xl font-bold">
          {t("mineTitle")}
        </h2>
        {apps === null ? (
          <p aria-live="polite">{t("loading")}</p>
        ) : apps.length === 0 ? (
          <p className="card text-slate-700">{t("empty")}</p>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {apps.map((a, i) => (
              <li key={a.id} className="card card-hover flex flex-col justify-between gap-3 animate-fade-up" style={{ animationDelay: `${i * 50}ms` }}>
                <div>
                  <span className={`badge ${a.reviewed ? "bg-indgreen-100 text-indgreen-800" : "bg-saffron-100 text-saffron-700"}`}>
                    {a.reviewed ? t("statusDone") : t("statusProgress")}
                  </span>
                  <p className="mt-2 line-clamp-2 font-semibold text-navy-900">{a.goal}</p>
                  <p className="mt-1 text-sm text-slate-600">
                    {new Date(a.created_at).toLocaleDateString()}
                    {a.city ? ` · ${a.city}` : ""}
                    {a.steps ? ` · ${t("steps", { n: a.steps })}` : ""}
                  </p>
                </div>
                <Link href={`/session/${a.id}`} className="btn-secondary self-start">
                  {a.reviewed ? t("open") : t("continue")} <Icon name="arrow" size={16} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default function Home() {
  const t = useTranslations("app");
  const [stage, setStage] = useState<"loading" | "auth" | "consent" | "app">("loading");

  const check = useCallback(async () => {
    if (!hasToken()) return setStage("auth");
    try {
      const log = await api<Consent>("/consent");
      setStage(log.some((c) => c.purpose === "service" && c.granted) ? "app" : "consent");
    } catch {
      setStage("auth");
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  if (stage === "loading") return <p aria-live="polite">{t("loading")}</p>;
  if (stage === "auth") return <Landing onDone={() => void check()} />;
  if (stage === "consent") return <ConsentGate onDone={() => setStage("app")} />;
  return <Dashboard />;
}
