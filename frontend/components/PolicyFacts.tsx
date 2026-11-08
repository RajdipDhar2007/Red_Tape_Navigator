"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { API } from "@/lib/api";

type Policy = { retention_days: number; data_region: string; grievance_contact: string };

/** Live facts from the backend so the policy can never disagree with the real configuration. */
export default function PolicyFacts() {
  const t = useTranslations("legal");
  const [p, setP] = useState<Policy | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch(`${API}/privacy/policy`)
      .then((r) => (r.ok ? (r.json() as Promise<Policy>) : Promise.reject(new Error("bad status"))))
      .then(setP)
      .catch(() => setFailed(true));
  }, []);

  return (
    <section aria-labelledby="facts-h" className="card space-y-1 text-sm">
      <h2 id="facts-h" className="text-base font-semibold">
        {t("factsHeading")}
      </h2>
      {p && (
        <ul className="list-disc space-y-1 pl-5">
          <li>{t("factRetention", { days: p.retention_days })}</li>
          <li>{t("factRegion", { region: p.data_region })}</li>
          <li>{t("factGrievance", { contact: p.grievance_contact })}</li>
        </ul>
      )}
      {failed && <p role="alert">{t("factLoadError")}</p>}
    </section>
  );
}
