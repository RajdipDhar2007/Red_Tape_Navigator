"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, patch, post } from "@/lib/api";
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
  goal: "clarify",
  research: "research",
  checklist: "checklist",
  interview: "interview",
  review: "review",
  submit: "done",
};

export default function SessionView({ id }: { id: string }) {
  const t = useTranslations();
  const [s, setS] = useState<Session | null>(null);
  const [phase, setPhase] = useState<Phase>("research");
  const [mode, setMode] = useState<string | undefined>();
  const [err, setErr] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [clarifyBusy, setClarifyBusy] = useState(false);
  const [clarifyErr, setClarifyErr] = useState<string | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [titleInput, setTitleInput] = useState("");
  const [renameBusy, setRenameBusy] = useState(false);
  const answerId = useId();
  const titleId = useId();

  const load = useCallback(
    async (keepPhase = false) => {
      try {
        const x = await api<Session>(`/sessions/${id}`);
        setS(x);
        setTitleInput(x.goal);
        if (!keepPhase) {
          setPhase(FROM_TRACKER[x.tracker.current] ?? "research");
        }
      } catch (e) {
        setErr(e instanceof ApiError && e.status === 404 ? "404" : t("app.error"));
      }
    },
    [id, t],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const runResearch = useCallback(async () => {
    try {
      const r = await post<{ mode: string }>(`/sessions/${id}/research`, {});
      setMode(r.mode);
      await load(true);
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

  const saveTitle = async () => {
    const cleaned = titleInput.trim();
    if (cleaned.length < 5 || renameBusy) return;
    setRenameBusy(true);
    try {
      const updated = await patch<Session>(`/sessions/${id}`, { goal: cleaned });
      setS(updated);
      setRenaming(false);
    } catch {
      setErr(t("app.error"));
    } finally {
      setRenameBusy(false);
    }
  };

  if (err === "404") {
    return (
      <section role="alert" className="card mx-auto max-w-lg space-y-3 border-l-4 border-l-red-600 animate-fade-up">
        <h1 className="text-xl font-bold text-navy-900">{t("dash.notFoundTitle")}</h1>
        <p className="text-slate-700">{t("dash.notFoundHelp")}</p>
        <Link href="/" className="btn-secondary inline-flex">
          ← {t("nav.applications")}
        </Link>
      </section>
    );
  }

  if (err) {
    return (
      <section role="alert" className="card mx-auto max-w-lg space-y-3 border-l-4 border-l-red-600 animate-fade-up">
        <p className="font-medium text-red-900">{err}</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn"
            onClick={() => {
              setErr(null);
              void load();
            }}
          >
            {t("dash.retryBtn")}
          </button>
          <Link href="/" className="btn-secondary">
            ← {t("nav.applications")}
          </Link>
        </div>
      </section>
    );
  }

  if (!s) return <p aria-live="polite">{t("app.loading")}</p>;

  const hasPlan = (s.plan?.steps?.length ?? 0) > 0;

  return (
    <div className="animate-fade-up">
      <Link href="/" className="btn-ghost mb-2">
        ← {t("nav.applications")}
      </Link>
      <ProgressTracker tracker={s.tracker} />

      <div aria-live="polite" className="mb-4 rounded-xl border-l-4 border-saffron-500 bg-white px-4 py-3 text-lg font-medium text-navy-900 shadow-card">
        {!renaming ? (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="sr-only">{t("tracker.label")}: </span>
              {s.goal}
            </div>
            <button
              type="button"
              className="btn-ghost !min-h-0 px-2 py-1 text-xs font-semibold text-navy-700"
              onClick={() => {
                setTitleInput(s.goal);
                setRenaming(true);
              }}
            >
              {t("dash.renameBtn")}
            </button>
          </div>
        ) : (
          <form
            className="flex flex-wrap items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void saveTitle();
            }}
          >
            <label htmlFor={titleId} className="sr-only">
              {t("dash.renameBtn")}
            </label>
            <input
              id={titleId}
              className="input flex-1 text-base"
              minLength={5}
              maxLength={200}
              required
              disabled={renameBusy}
              value={titleInput}
              onChange={(e) => setTitleInput(e.target.value)}
            />
            <button type="submit" className="btn !py-1.5 text-sm" disabled={renameBusy || titleInput.trim().length < 5}>
              {t("dash.renameSave")}
            </button>
            <button type="button" className="btn-ghost !py-1.5 text-sm" disabled={renameBusy} onClick={() => setRenaming(false)}>
              {t("dash.renameCancel")}
            </button>
          </form>
        )}
      </div>

      {hasPlan && phase !== "clarify" && phase !== "research" && (
        <nav aria-label={t("tracker.label")} className="mb-5 flex flex-wrap gap-2">
          <button
            type="button"
            className={phase === "checklist" ? "btn !py-1.5 text-sm" : "btn-secondary !py-1.5 text-sm"}
            onClick={() => setPhase("checklist")}
          >
            1. {t("tracker.checklist")}
          </button>
          <button
            type="button"
            className={phase === "interview" ? "btn !py-1.5 text-sm" : "btn-secondary !py-1.5 text-sm"}
            onClick={() => setPhase("interview")}
          >
            2. {t("tracker.interview")}
          </button>
          <button
            type="button"
            className={phase === "review" ? "btn !py-1.5 text-sm" : "btn-secondary !py-1.5 text-sm"}
            onClick={() => setPhase("review")}
          >
            3. {t("tracker.review")}
          </button>
          {s.reviewed && (
            <button
              type="button"
              className={phase === "done" ? "btn !py-1.5 text-sm" : "btn-secondary !py-1.5 text-sm"}
              onClick={() => setPhase("done")}
            >
              4. {t("tracker.submit")}
            </button>
          )}
        </nav>
      )}

      {phase === "clarify" && (
        <form
          className="card space-y-3"
          aria-busy={clarifyBusy}
          onSubmit={(e) => {
            e.preventDefault();
            if (clarifyBusy || answer.trim().length < 2) return;
            setClarifyBusy(true);
            setClarifyErr(null);
            void post(`/sessions/${id}/clarify`, { answer: answer.trim() })
              .then(async () => {
                setAnswer("");
                await load();
              })
              .catch((errObj) => {
                setClarifyErr(errObj instanceof ApiError ? errObj.message : t("app.error"));
              })
              .finally(() => {
                setClarifyBusy(false);
              });
          }}
        >
          <h2 className="text-xl font-semibold">{t("goal.clarify")}</h2>
          <label htmlFor={answerId}>{s.parsed.clarifying_question}</label>
          <input
            id={answerId}
            className="input"
            required
            minLength={2}
            disabled={clarifyBusy}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          {clarifyErr && (
            <p role="alert" className="rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
              {clarifyErr}
            </p>
          )}
          <div className="flex gap-2">
            <button className="btn" disabled={clarifyBusy || answer.trim().length < 2}>
              {clarifyBusy ? t("app.loading") : t("goal.send")}
            </button>
            <VoiceInput onText={setAnswer} />
          </div>
        </form>
      )}

      {phase === "research" && <p aria-live="polite">{t("app.loading")}</p>}
      {phase === "checklist" && <ChecklistView session={s} mode={mode} onStart={() => setPhase("interview")} />}
      {phase === "interview" && (
        <InterviewChat
          session={s}
          onBack={() => setPhase("checklist")}
          onReview={() => setPhase("review")}
        />
      )}
      {phase === "review" && (
        <ReviewView
          session={s}
          onBack={() => setPhase("interview")}
          onConfirmed={async () => {
            await load(true);
            setPhase("done");
          }}
        />
      )}
      {phase === "done" && <DoneView session={s} onBackToReview={() => setPhase("review")} />}
    </div>
  );
}
