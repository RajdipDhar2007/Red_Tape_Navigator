"use client";

import { useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { api, hasToken, post, setTokens } from "@/lib/api";
import { passwordStrength } from "./Home";

export default function AccountView() {
  const t = useTranslations("account");
  const ta = useTranslations("auth");
  const ids = [useId(), useId()];
  const [email, setEmail] = useState<string | null>(null);
  const [verified, setVerified] = useState<boolean | null>(null);
  const [resent, setResent] = useState(false);
  const [tf, setTf] = useState<boolean | null>(null);
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [tfPw, setTfPw] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [tfErr, setTfErr] = useState<string | null>(null);
  const tfIds = [useId(), useId(), useId()];
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "done" | "failed">("idle");
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!hasToken()) {
      setDenied(true);
      return;
    }
    api<{ email: string; email_verified: boolean; two_factor: boolean }>("/auth/me")
      .then((m) => {
        setEmail(m.email);
        setVerified(m.email_verified);
        setTf(m.two_factor);
      })
      .catch(() => setEmail(null));
  }, []);

  if (denied) return <p role="alert">{t("signin")}</p>;

  const submit = async () => {
    setState("busy");
    try {
      const tok = await post<{ access_token: string; refresh_token: string }>("/auth/change-password", { current_password: current, new_password: next });
      setTokens(tok.access_token, tok.refresh_token);
      setCurrent("");
      setNext("");
      setState("done");
    } catch {
      setState("failed");
    }
  };

  const startTf = async () => {
    setTfErr(null);
    setSetup(await post<{ secret: string; otpauth_uri: string }>("/auth/2fa/setup"));
  };
  const confirmTf = async () => {
    setTfErr(null);
    try {
      const r = await post<{ recovery_codes: string[] }>("/auth/2fa/enable", { code });
      setCodes(r.recovery_codes);
      setSetup(null);
      setCode("");
      setTf(true);
    } catch {
      setTfErr(t("tfBad"));
    }
  };
  const disableTf = async () => {
    setTfErr(null);
    try {
      await post("/auth/2fa/disable", { password: tfPw, code });
      setTf(false);
      setCodes(null);
      setCode("");
      setTfPw("");
    } catch {
      setTfErr(t("tfDisableFail"));
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-2xl font-bold sm:text-3xl">{t("title")}</h1>
      <section className="card">
        <p className="text-sm text-slate-600">{t("email")}</p>
        <p className="font-semibold">{email ?? "…"}</p>
        {verified !== null && (
          <p className="mt-1 text-sm" role="status">
            {verified ? t("verifiedYes") : t("verifiedNo")}
          </p>
        )}
        {verified === false && (
          <>
            <button
              className="btn-ghost mt-1"
              onClick={() => {
                void post("/auth/verify-email/send").then(() => setResent(true));
              }}
            >
              {t("resend")}
            </button>
            {resent && (
              <p role="status" className="text-sm text-indgreen-800">
                {t("resent")}
              </p>
            )}
          </>
        )}
        <Link href="/teams" className="btn-ghost mt-1">
          {t("teamsLink")}
        </Link>
      </section>
      <section className="card" aria-labelledby="tf-h">
        <h2 id="tf-h" className="mb-2 text-lg font-bold">
          {t("tfHeading")}
        </h2>
        {tf !== null && <p className="mb-3 text-sm">{tf ? t("tfOn") : t("tfOff")}</p>}
        {tfErr && (
          <p role="alert" className="mb-2 rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
            {tfErr}
          </p>
        )}
        {codes && (
          <div role="status" className="mb-3 rounded-lg bg-indgreen-50 p-3">
            <p className="font-semibold">{t("tfRecoveryTitle")}</p>
            <p className="mb-2 text-sm">{t("tfRecoveryHelp")}</p>
            <ul className="grid grid-cols-2 gap-1 font-mono text-sm">
              {codes.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        )}
        {tf === false && !setup && (
          <button className="btn" onClick={() => void startTf()}>
            {t("tfStart")}
          </button>
        )}
        {setup && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              void confirmTf();
            }}
          >
            <p className="text-sm">{t("tfScan")}</p>
            <div>
              <label htmlFor={tfIds[0]}>{t("tfSecret")}</label>
              <input id={tfIds[0]} readOnly className="input font-mono" value={setup.secret} onFocus={(e) => e.currentTarget.select()} />
            </div>
            <div>
              <label htmlFor={tfIds[1]}>{t("tfCode")}</label>
              <input id={tfIds[1]} className="input" inputMode="numeric" autoComplete="one-time-code" required value={code} onChange={(e) => setCode(e.target.value)} />
            </div>
            <button className="btn">{t("tfConfirm")}</button>
          </form>
        )}
        {tf === true && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              void disableTf();
            }}
          >
            <div>
              <label htmlFor={tfIds[2]}>{t("current")}</label>
              <input id={tfIds[2]} className="input" type="password" autoComplete="current-password" required value={tfPw} onChange={(e) => setTfPw(e.target.value)} />
            </div>
            <div>
              <label htmlFor={tfIds[1]}>{t("tfCode")}</label>
              <input id={tfIds[1]} className="input" required value={code} onChange={(e) => setCode(e.target.value)} />
            </div>
            <button className="btn-ghost text-red-800">{t("tfDisable")}</button>
          </form>
        )}
      </section>
      <section className="card border-t-4 border-t-navy-700" aria-labelledby="pw-h">
        <h2 id="pw-h" className="mb-3 text-lg font-bold">
          {t("changeHeading")}
        </h2>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <div>
            <label htmlFor={ids[0]}>{t("current")}</label>
            <input id={ids[0]} className="input" type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} />
          </div>
          <div>
            <label htmlFor={ids[1]}>{ta("newPassword")}</label>
            <input id={ids[1]} className="input" type="password" autoComplete="new-password" minLength={10} required value={next} onChange={(e) => setNext(e.target.value)} />
          </div>
          {state === "failed" && (
            <p role="alert" className="rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
              {t("failed")}
            </p>
          )}
          {state === "done" && (
            <p role="status" className="rounded-lg bg-indgreen-50 p-2.5 text-sm text-indgreen-800">
              {t("saved")}
            </p>
          )}
          <button className="btn" disabled={state === "busy" || passwordStrength(next) === 0 || !current}>
            {t("save")}
          </button>
        </form>
      </section>
    </div>
  );
}
