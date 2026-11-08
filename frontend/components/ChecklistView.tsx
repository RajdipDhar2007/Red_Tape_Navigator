"use client";

import { useTranslations } from "next-intl";
import type { Claim, Session } from "@/lib/types";
import CitationLine from "./CitationLine";

function Line({ label, claim }: { label: string; claim?: Claim }) {
  if (!claim) return null;
  return (
    <div className="mt-2">
      <p>
        <strong>{label}:</strong> {claim.text.replace(/^[^:]+:\s*/, "")}
      </p>
      <CitationLine source_url={claim.source_url} fetched_at={claim.fetched_at} content_hash={claim.content_hash} confidence={claim.confidence} verify={claim.needs_verification ?? false} />
    </div>
  );
}

export default function ChecklistView({ session, mode, onStart }: { session: Session; mode?: string; onStart: () => void }) {
  const t = useTranslations("checklist");
  const steps = session.plan.steps ?? [];
  return (
    <section aria-labelledby="chk-h">
      <h2 id="chk-h" className="text-xl font-semibold">
        {t("heading")}
      </h2>
      <p className="mb-1">{t("intro")}</p>
      {session.parsed.activity === "general_business" && (
        <p role="note" className="mb-3 rounded bg-amber-100 p-2 text-amber-950">
          {t("generalNote", { label: session.parsed.activity_label ?? "" })}
        </p>
      )}
      {mode && (
        <p className="mb-3 text-sm text-slate-700">
          {t("mode")}: {t(`mode${mode.charAt(0).toUpperCase()}${mode.slice(1)}` as "modeKnowledge_base")}
        </p>
      )}
      <ol className="space-y-3">
        {steps.map((st) => (
          <li key={st.licence} className="card">
            <h3 className="text-lg font-semibold">
              {st.order}. {st.name}
              {st.conditional && <span className="badge ml-2 bg-slate-200">{t("conditional")}</span>}
            </h3>
            <p className="text-sm">{st.form ? t("form") : t("noForm")}</p>
            {st.municipal_data_missing && (
              <p role="note" className="mt-2 rounded bg-amber-100 p-2 text-amber-950">
                {t("municipalMissing")}
              </p>
            )}
            <Line label={t("authority")} claim={st.claims.authority} />
            <Line label={t("fee")} claim={st.claims.fee} />
            <Line label={t("timeline")} claim={st.claims.timeline} />
            <Line label={t("documents")} claim={st.claims.documents} />
          </li>
        ))}
      </ol>
      {session.plan.out_of_scope ? (
        <div role="note" className="card mt-3 border-amber-400 bg-amber-50">
          <h3 className="font-semibold">{t("outOfScopeHeading")}</h3>
          <p className="mt-1">{t("outOfScope")}</p>
          <p className="mt-2">
            <a className="underline" href="https://www.india.gov.in" target="_blank" rel="noopener noreferrer">
              india.gov.in
            </a>
          </p>
        </div>
      ) : (
        <button className="btn mt-4" onClick={onStart}>
          {t("start")}
        </button>
      )}
    </section>
  );
}
