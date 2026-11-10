"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { ApiError, hasToken, post } from "@/lib/api";

type State = "working" | "done" | "failed" | "verify" | "signin";

export default function AcceptInvite() {
  const t = useTranslations("teams");
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<State>("working");

  useEffect(() => {
    if (!token) {
      setState("failed");
      return;
    }
    if (!hasToken()) {
      setState("signin");
      return;
    }
    post("/workspaces/invites/accept", { token })
      .then(() => setState("done"))
      .catch((e) => setState(e instanceof ApiError && e.code === "email_not_verified" ? "verify" : "failed"));
  }, [token]);

  const msg: Record<State, string> = {
    working: t("accepting"),
    done: t("accepted"),
    failed: t("acceptFailed"),
    verify: t("acceptVerify"),
    signin: t("acceptSignin"),
  };
  return (
    <section className="card mx-auto max-w-md" aria-labelledby="inv-h">
      <h1 id="inv-h" className="mb-3 text-xl font-semibold">
        {t("acceptTitle")}
      </h1>
      <p role={state === "done" || state === "working" ? "status" : "alert"} className="mb-3">
        {msg[state]}
      </p>
      {state === "done" && (
        <Link href="/teams" className="btn">
          {t("open")}
        </Link>
      )}
      {(state === "verify" || state === "signin") && (
        <Link href={state === "verify" ? "/account" : "/"} className="btn">
          {state === "verify" ? t("open") : t("acceptTitle")}
        </Link>
      )}
    </section>
  );
}
