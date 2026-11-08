"use client";

import { useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { api, hasToken, post, setTokens } from "@/lib/api";
import { passwordStrength } from "./Home";

export default function AccountView() {
  const t = useTranslations("account");
  const ta = useTranslations("auth");
  const ids = [useId(), useId()];
  const [email, setEmail] = useState<string | null>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "done" | "failed">("idle");
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!hasToken()) {
      setDenied(true);
      return;
    }
    api<{ email: string }>("/auth/me")
      .then((m) => setEmail(m.email))
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

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-2xl font-bold sm:text-3xl">{t("title")}</h1>
      <section className="card">
        <p className="text-sm text-slate-600">{t("email")}</p>
        <p className="font-semibold">{email ?? "…"}</p>
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
