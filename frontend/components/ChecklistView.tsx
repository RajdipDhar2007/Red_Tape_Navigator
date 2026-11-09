"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import type { Claim, Session } from "@/lib/types";
import CitationLine from "./CitationLine";
import Confetti from "./fx/Confetti";
import ProgressRing from "./fx/ProgressRing";
import Icon from "./Icon";

/** Which steps the citizen has ticked off is a personal reminder kept only in this browser; it is never sent anywhere. */
function useDoneSteps(sessionId: string) {
  const key = `rtn-steps-${sessionId}`;
  const [done, setDone] = useState<string[]>([]);
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(key);
      if (raw) setDone(JSON.parse(raw) as string[]);
    } catch {
      /* storage blocked: the ticks still work for this visit */
    }
  }, [key]);
  const toggle = (licence: string) =>
    setDone((cur) => {
      const next = cur.includes(licence) ? cur.filter((x) => x !== licence) : [...cur, licence];
      try {
        window.localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  return [done, toggle] as const;
}

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
  const [doneSteps, toggle] = useDoneSteps(session.id);
  const doneCount = steps.filter((st) => doneSteps.includes(st.licence)).length;
  const percent = steps.length ? (doneCount / steps.length) * 100 : 0;
  const allDone = steps.length > 0 && doneCount === steps.length;
  const [burst, setBurst] = useState(0);
  const wasAllDone = useRef(false);
  useEffect(() => {
    if (allDone && !wasAllDone.current) setBurst((b) => b + 1);
    wasAllDone.current = allDone;
  }, [allDone]);
  // Only licence names go out (never the citizen's answers or identifiers), and only when they press a button.
  const planText = [t("shareIntro"), ...steps.map((st) => `${st.order}. ${st.name}`)].join("\n");
  const [copied, setCopied] = useState(false);
  const copyPlan = async () => {
    try {
      await navigator.clipboard.writeText(planText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard blocked: the share link still works */
    }
  };
  const nextId = steps.find((st) => !doneSteps.includes(st.licence))?.licence;
  return (
    <section aria-labelledby="chk-h">
      <Confetti burst={burst} />
      <div className="mb-2 flex items-center justify-between gap-4">
        <div>
          <h2 id="chk-h" className="text-xl font-semibold">
            {t("heading")}
          </h2>
          <p className="mb-1">{t("intro")}</p>
        </div>
        {steps.length > 0 && <ProgressRing percent={percent} label={t("progressLabel", { done: doneCount, total: steps.length })} />}
      </div>
      {steps.length > 0 && !session.plan.out_of_scope && (
        <div className="no-print mb-3 flex flex-wrap gap-2">
          <button type="button" className="btn-secondary" onClick={() => window.print()}>
            {t("print")}
          </button>
          <button type="button" className="btn-secondary" onClick={() => void copyPlan()}>
            {copied ? t("copied") : t("copy")}
          </button>
          <a className="btn-secondary" href={`https://wa.me/?text=${encodeURIComponent(planText)}`} target="_blank" rel="noopener noreferrer">
            {t("share")}
          </a>
        </div>
      )}
      {allDone && (
        <p role="status" className="mb-3 flex items-center gap-2 rounded-xl bg-indgreen-50 p-3 font-semibold text-indgreen-800 animate-pop">
          <Icon name="check" size={20} /> {t("allDone")}
        </p>
      )}
      {session.parsed.activity === "general_business" && session.parsed.regulated && (
        <p role="note" className="mb-3 rounded border border-amber-500 bg-amber-100 p-3 text-amber-950">
          {t(session.parsed.regulated.mode === "operated" ? "operatedNote" : session.parsed.regulated.mode === "authorised" ? "authorisedNote" : "regulatedNote", { label: session.parsed.activity_label ?? "", regulator: session.parsed.regulated.regulator })}
          {session.parsed.regulated.url && (
            <>
              {" "}
              <a className="underline" href={session.parsed.regulated.url} target="_blank" rel="noopener noreferrer">
                {t("regulatorSite")}
              </a>
            </>
          )}
        </p>
      )}
      {session.plan.restricted && (
        <div role="note" className="mb-3 rounded border border-amber-500 bg-amber-100 p-3 text-amber-950">
          <p className="font-semibold">
            {t("restrictedLead")} {session.plan.restricted.name}
          </p>
          <p className="mt-1 text-sm">{session.plan.restricted.text}</p>
        </div>
      )}
      {session.plan.coverage === "specific" && (
        <p role="note" className="mb-3 rounded bg-amber-100 p-2 text-amber-950">
          {t("coverageNote")}
        </p>
      )}
      {session.parsed.activity === "hotel" && (
        <p role="note" className="mb-3 rounded bg-amber-100 p-2 text-amber-950">
          {t("hotelNote")}
        </p>
      )}
      {session.parsed.activity === "general_business" && !session.parsed.regulated && (
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
        {steps.map((st, i) => {
          const isDone = doneSteps.includes(st.licence);
          return (
          <li key={st.licence} className={`card card-tilt animate-fade-up ${isDone ? "step-done border-indgreen-500" : st.licence === nextId ? "ring-2 ring-saffron-300" : ""}`} style={{ animationDelay: `${Math.min(i, 8) * 70}ms` }}>
            <div className="flex items-start justify-between gap-3">
            <h3 className="text-lg font-semibold">
              {st.order}. {st.name}
              {st.conditional && <span className="badge ml-2 bg-slate-200">{t("conditional")}</span>}
              {!isDone && st.licence === nextId && <span className="badge ml-2 bg-saffron-100 text-saffron-700 animate-ring-pulse">{t("nextUp")}</span>}
            </h3>
            <button type="button" aria-pressed={isDone} aria-label={`${t("markDone")}: ${st.name}`} onClick={() => toggle(st.licence)} className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 transition ${isDone ? "border-indgreen-600 bg-indgreen-600 text-white" : "border-slate-300 bg-white text-transparent hover:border-indgreen-500 hover:text-indgreen-500"}`}>
              <Icon name="check" size={18} className={isDone ? "animate-tick" : ""} />
            </button>
            </div>
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
          );
        })}
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
