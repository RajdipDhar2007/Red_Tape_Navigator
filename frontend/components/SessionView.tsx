"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, post } from "@/lib/api";
import { Link } from "@/i18n/navigation";
import type { Session } from "@/lib/types";
import ProgressTracker from "./ProgressTracker";
import ChecklistView from "./ChecklistView";
import InterviewChat from "./InterviewChat";
import ReviewView from "./ReviewView";
import DoneView from "./DoneView";
import VoiceInput from "./VoiceInput";

type Phase = "clarify" | "research" | "checklist" | "interview" | "review" | "done";
const FROM_TRACKER: Record<string, Phase> = {
  goal: "clarify", research: "research", checklist: "checklist", interview: "interview", review: "interview", submit: "done",
};

export default function SessionView({ id }: { id: string }) {
  const t = useTranslations();
  const [s, setS] = useState<Session | null>(null);
  const [phase, setPhase] = useState<Phase>("research");
  const [mode, setMode] = useState<string | undefined>();
  const [err, setErr] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const answerId = useId();

  const load = useCallback(async () => {
    try {
      const x = await api<Session>(`/sessions/${id}`);
      setS(x);
      setPhase(FROM_TRACKER[x.tracker.current] ?? "research");
    } catch (e) {
      setErr(e instanceof ApiError && e.status === 404 ? "404" : t("app.error"));
    }
  }, [id, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const runResearch = useCallback(async () => {
    try {
      const r = await post<{ mode: string }>(`/sessions/${id}/research`, {});
      setMode(r.mode);
      await load();
      setPhase("checklist");
    } catch (e) {
      if (e instanceof ApiError && e.code === "goal_incomplete") {
        await load(); // the server needs one more detail: show the clarify form instead of an error
        return;
      }
      setErr(e instanceof ApiError ? e.message : t("app.error"));
    }
  }, [id, load, t]);

  useEffect(() => {
    if (phase === "research" && s) void runResearch();
  }, [phase, s, runResearch]);

  if (err) return <p role="alert">{err}</p>;
  if (!s) return <p aria-live="polite">{t("app.loading")}</p>;

  return (
    <div className="animate-fade-up">
      <Link href="/" className="btn-ghost mb-2">
        ← {t("nav.applications")}
      </Link>
      <ProgressTracker tracker={s.tracker} />
      <div aria-live="polite" className="mb-5 rounded-xl border-l-4 border-saffron-500 bg-white px-4 py-3 text-lg font-medium text-navy-900 shadow-card">
        <span className="sr-only">{t("tracker.label")}: </span>
        {s.goal}
      </div>

      {phase === "clarify" && (
        <form
          className="card space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void post(`/sessions/${id}/clarify`, { answer }).then(load);
          }}
        >
          <h2 className="text-xl font-semibold">{t("goal.clarify")}</h2>
          <label htmlFor={answerId}>{s.parsed.clarifying_question}</label>
          <input id={answerId} className="input" required minLength={2} value={answer} onChange={(e) => setAnswer(e.target.value)} />
          <div className="flex gap-2">
            <button className="btn">{t("goal.send")}</button>
            <VoiceInput onText={setAnswer} />
          </div>
        </form>
      )}

      {phase === "research" && <p aria-live="polite">{t("app.loading")}</p>}
      {phase === "checklist" && <ChecklistView session={s} mode={mode} onStart={() => setPhase("interview")} />}
      {phase === "interview" && <InterviewChat session={s} onReview={() => setPhase("review")} />}
      {phase === "review" && (
        <ReviewView
          session={s}
          onBack={() => setPhase("interview")}
          onConfirmed={async () => {
            await load();
            setPhase("done");
          }}
        />
      )}
      {phase === "done" && <DoneView session={s} />}
    </div>
  );
}
