"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api, post } from "@/lib/api";
import type { InterviewState, Session } from "@/lib/types";
import VoiceInput from "./VoiceInput";

type Msg = { role: "bot" | "user"; text: string };
type Submit = { saved: Record<string, string>; errors: Record<string, { message: string }>; next: InterviewState };

export default function InterviewChat({ session, onReview }: { session: Session; onReview: () => void }) {
  const t = useTranslations("interview");
  const sid = session.id;
  const [st, setSt] = useState<InterviewState | null>(null);
  const [log, setLog] = useState<Msg[]>([]);
  const [vals, setVals] = useState<Record<string, string>>({});
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const ask = useCallback((s: InterviewState) => {
    setSt(s);
    setLog((l) => [...l, ...s.questions.map((q) => ({ role: "bot" as const, text: q.question }))]);
  }, []);

  useEffect(() => {
    void api<InterviewState>(`/sessions/${sid}/interview`).then(ask);
  }, [sid, ask]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [log]);

  const send = async (override?: Record<string, string>) => {
    if (!st) return;
    const answers = override ?? Object.fromEntries(st.questions.map((q) => [q.key, (vals[q.key] ?? "").trim()]).filter(([, v]) => v));
    if (!Object.keys(answers).length) return;
    setBusy(true);
    try {
      const res = await post<Submit>(`/sessions/${sid}/interview`, { answers });
      setErrs(Object.fromEntries(Object.entries(res.errors).map(([k, v]) => [k, v.message])));
      const okKeys = Object.keys(res.saved);
      setLog((l) => [
        ...l,
        ...st.questions.filter((q) => okKeys.includes(q.key)).map((q) => ({ role: "user" as const, text: q.sensitive ? "••••••••" : answers[q.key] })),
      ]);
      setVals({});
      if (okKeys.length || res.next.complete) {
        const rest = res.next;
        // only append *new* questions (never re-ask failed ones: they stay in the form with an error)
        if (Object.keys(res.errors).length) setSt(rest);
        else ask(rest);
      }
    } finally {
      setBusy(false);
    }
  };

  const skip = async (key: string) => {
    const s = await post<InterviewState>(`/sessions/${sid}/interview/skip`, { key });
    setLog((l) => [...l, { role: "user", text: "—" }]);
    ask(s);
  };

  const resume = async () => ask(await api<InterviewState>(`/sessions/${sid}/interview?include_skipped=true`));

  if (!st) return <p aria-live="polite">…</p>;
  const skippedCount = st.progress.skipped.length;

  return (
    <section aria-labelledby="int-h">
      <h2 id="int-h" className="text-xl font-semibold">
        {t("heading")}
      </h2>
      <p className="mb-2">{t("intro")}</p>
      <div className="mb-3">
        <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={st.progress.percent} aria-label={t("progress", { answered: st.progress.answered, total: st.progress.total })} className="h-3 w-full overflow-hidden rounded bg-slate-300">
          <div className="h-full bg-brand-600" style={{ width: `${st.progress.percent}%` }} />
        </div>
        <p className="text-sm">{t("progress", { answered: st.progress.answered, total: st.progress.total })}</p>
      </div>

      <div className="card mb-3 max-h-80 space-y-2 overflow-y-auto" role="log" aria-live="polite" aria-relevant="additions">
        {log.map((m, i) => (
          <p key={i} className={m.role === "bot" ? "mr-10 rounded-lg bg-slate-100 p-2" : "ml-10 rounded-lg bg-brand-50 p-2 text-right"}>
            {m.text}
          </p>
        ))}
        <div ref={endRef} />
      </div>

      {st.questions.length > 0 && (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          {st.questions.map((q) => (
            <div key={q.key}>
              <label htmlFor={`q-${q.key}`} className="font-medium">
                {q.label}
              </label>
              {q.sensitive && <p className="text-sm text-slate-700">{t("sensitive")}</p>}
              {q.options.length > 0 ? (
                <div className="mt-1 flex flex-wrap gap-2" role="group" aria-label={t("options")}>
                  {q.options.map((o) => (
                    <button type="button" key={o} className="btn-secondary" disabled={busy} onClick={() => void send({ [q.key]: o })}>
                      {o}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="mt-1 flex gap-2">
                  <input
                    id={`q-${q.key}`}
                    className="input"
                    type={q.sensitive ? "password" : "text"}
                    autoComplete="off"
                    inputMode={["mobile", "premises_pincode", "residence_pincode", "annual_turnover", "num_employees", "premises_area_sqft", "investment_amount"].includes(q.key) ? "numeric" : undefined}
                    value={vals[q.key] ?? ""}
                    aria-invalid={!!errs[q.key]}
                    aria-describedby={errs[q.key] ? `e-${q.key}` : undefined}
                    onChange={(e) => setVals({ ...vals, [q.key]: e.target.value })}
                  />
                  <VoiceInput onText={(x) => setVals((v) => ({ ...v, [q.key]: x }))} />
                </div>
              )}
              {errs[q.key] && (
                <p id={`e-${q.key}`} role="alert" className="mt-1 text-red-800">
                  {errs[q.key]}
                </p>
              )}
              <button type="button" className="mt-1 text-sm text-brand-700 underline" onClick={() => void skip(q.key)}>
                {t("skip")}
              </button>
            </div>
          ))}
          <button className="btn" disabled={busy}>
            {t("send")}
          </button>
        </form>
      )}

      {skippedCount > 0 && st.questions.length === 0 && (
        <p className="mt-3">
          {t("skippedNote", { count: skippedCount })}{" "}
          <button className="text-brand-700 underline" onClick={() => void resume()}>
            {t("resume")}
          </button>
        </p>
      )}

      {st.ready_for_review && (
        <div className="mt-4">
          {st.complete && <p className="mb-2 font-medium">{t("complete")}</p>}
          <button className="btn" onClick={onReview}>
            {t("toReview")}
          </button>
        </div>
      )}
    </section>
  );
}
