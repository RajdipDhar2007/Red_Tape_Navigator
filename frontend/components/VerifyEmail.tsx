"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { post } from "@/lib/api";

export default function VerifyEmail() {
  const t = useTranslations("verify");
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<"working" | "done" | "failed">(token ? "working" : "failed");

  useEffect(() => {
    if (!token) return;
    post("/auth/verify-email", { token })
      .then(() => setState("done"))
      .catch(() => setState("failed"));
  }, [token]);

  return (
    <section className="card mx-auto max-w-md" aria-labelledby="verify-h">
      <h1 id="verify-h" className="mb-3 text-xl font-semibold">
        {t("title")}
      </h1>
      {state === "working" && <p role="status">{t("working")}</p>}
      {state === "done" && (
        <p role="status" className="mb-3 text-green-800">
          {t("done")}
        </p>
      )}
      {state === "failed" && (
        <p role="alert" className="mb-3 text-red-800">
          {t("failed")}
        </p>
      )}
      {state !== "working" && (
        <Link href="/" className="btn">
          {t("home")}
        </Link>
      )}
    </section>
  );
}
