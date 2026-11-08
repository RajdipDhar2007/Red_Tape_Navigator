"use client";

import { useId, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { post } from "@/lib/api";

export default function ResetPassword() {
  const t = useTranslations("auth");
  const token = useSearchParams().get("token") ?? "";
  const id = useId();
  const [password, setPassword] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "done" | "failed">("idle");

  const submit = async () => {
    setState("busy");
    try {
      await post("/auth/reset", { token, password });
      setState("done");
    } catch {
      setState("failed");
    }
  };

  return (
    <section className="card mx-auto max-w-md" aria-labelledby="reset-h">
      <h1 id="reset-h" className="mb-3 text-xl font-semibold">
        {t("resetHeading")}
      </h1>
      {state === "done" ? (
        <>
          <p role="status" className="mb-3 text-green-800">
            {t("resetDone")}
          </p>
          <Link href="/" className="btn">
            {t("login")}
          </Link>
        </>
      ) : (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <div>
            <label htmlFor={id}>{t("newPassword")}</label>
            <input id={id} className="input" type="password" autoComplete="new-password" minLength={10} required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {(state === "failed" || !token) && (
            <p role="alert" className="text-red-800">
              {t("resetFailed")}
            </p>
          )}
          <button className="btn w-full" disabled={state === "busy" || !token}>
            {t("resetButton")}
          </button>
        </form>
      )}
    </section>
  );
}
