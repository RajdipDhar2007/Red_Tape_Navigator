"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, apiBlob, ApiError, post, put } from "@/lib/api";
import type { ReportRow, Review, Session } from "@/lib/types";
import CitationLine from "./CitationLine";

const BADGE: Record<ReportRow["status"], string> = {
  filled: "bg-green-100 text-green-950",
  missing: "bg-red-100 text-red-950",
  doubtful: "bg-amber-200 text-amber-950",
  unmapped: "bg-slate-200 text-slate-900",
};

function saveData(): boolean {
  const c = (navigator as unknown as { connection?: { saveData?: boolean } }).connection;
  return !!c?.saveData;
}

export default function ReviewView({ session, onBack, onConfirmed }: { session: Session; onBack: () => void; onConfirmed: () => Promise<void> }) {
  const t = useTranslations("review");
  const tc = useTranslations("checklist");
  const ta = useTranslations("app");
  const sid = session.id;
  const [rv, setRv] = useState<Review | null>(null);
  const [active, setActive] = useState(0);
  const [img, setImg] = useState<string | null>(null);
  const [lowData, setLowData] = useState(false);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<Record<string, string>>({});
  const [consent, setConsent] = useState(false);
  const [ack, setAck] = useState(false);
  const [needAck, setNeedAck] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => setRv(await api<Review>(`/sessions/${sid}/review`)), [sid]);

  useEffect(() => {
    setLowData(saveData());
    void reload();
  }, [reload]);

  const form = rv?.forms[active];
  const formId = form?.form_id;
  const version = rv ? JSON.stringify(rv.forms.map((f) => f.fields.map((x) => [x.value, x.status]))) : "";

  useEffect(() => {
    if (!formId || lowData) return;
    let url: string | null = null;
    let cancelled = false;
    void apiBlob(`/sessions/${sid}/forms/${formId}/preview.png`).then((b) => {
      if (cancelled) return;
      url = URL.createObjectURL(b);
      setImg(url);
    });
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [sid, formId, lowData, version]);

  const save = async (row: ReportRow) => {
    if (!row.answer_key || !edits[row.answer_key]?.trim()) return;
    try {
      await put(`/sessions/${sid}/answers/${row.answer_key}`, { value: edits[row.answer_key] });
      setMsg((m) => ({ ...m, [row.pdf_field]: t("saved") }));
      setEdits((e) => ({ ...e, [row.answer_key as string]: "" }));
      await reload();
    } catch (e) {
      const d = e instanceof ApiError ? (e.detail as { message?: string }) : undefined;
      setMsg((m) => ({ ...m, [row.pdf_field]: d?.message ?? ta("error") }));
    }
  };

  const confirm = async () => {
    setErr(null);
    try {
      await post(`/sessions/${sid}/review`, { confirm: true, acknowledge_incomplete: ack });
      await onConfirmed();
    } catch (e) {
      if (e instanceof ApiError && e.code === "incomplete") setNeedAck(true);
      else setErr(ta("error"));
    }
  };

  if (!rv || !form) return <p aria-live="polite">{ta("loading")}</p>;

  return (
    <section aria-labelledby="rv-h">
      <h2 id="rv-h" className="mb-3 text-xl font-semibold">
        {t("heading")}
      </h2>

      <div role="tablist" className="mb-3 flex flex-wrap gap-2">
        {rv.forms.map((f, i) => (
          <button key={f.form_id} role="tab" aria-selected={i === active} className={i === active ? "btn" : "btn-secondary"} onClick={() => setActive(i)}>
            {f.title.replace(/\s*\(PLACEHOLDER\)/, "")}
          </button>
        ))}
      </div>

      {form.placeholder && (
        <p role="note" className="mb-3 rounded border border-red-400 bg-red-50 p-2 text-red-950">
          {t("placeholder")}
        </p>
      )}
      {form.official_source && (
        <p role="note" className="mb-3 rounded border border-green-500 bg-green-50 p-2 text-green-950">
          {t("officialSource", {
            host: new URL(form.official_source.url).hostname,
            date: new Date(form.official_source.fetched_at).toLocaleDateString(),
            hash: form.official_source.sha256.slice(0, 10),
          })}
        </p>
      )}
      {form.warnings.length > 0 && (
        <div role="alert" className="mb-3 rounded border border-amber-500 bg-amber-100 p-2 text-amber-950">
          <strong>{t("warnings")}:</strong>
          <ul className="list-disc pl-5">
            {form.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <h3 className="mb-2 font-semibold">{t("preview")}</h3>
          {lowData ? (
            <button className="btn-secondary" onClick={() => setLowData(false)}>
              {t("showPreview")}
            </button>
          ) : img ? (
            // eslint-disable-next-line @next/next/no-img-element -- blob URL from an authenticated fetch
            <img src={img} alt={form.title} className="w-full rounded border border-slate-300" />
          ) : (
            <p aria-live="polite">{ta("loading")}</p>
          )}
        </div>

        <div className="card">
          <h3 className="mb-2 font-semibold">{t("fields")}</h3>
          <ul className="space-y-3">
            {form.fields.map((row) => (
              <li key={row.pdf_field} className="border-b border-slate-200 pb-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{row.label}</span>
                  <span className={`badge ${BADGE[row.status]}`}>{t(`status.${row.status}`)}</span>
                </div>
                {row.value && <p className="text-sm">{row.value}</p>}
                {row.source && (
                  <p className="text-xs text-slate-700">
                    {t("from")}: {row.source}
                  </p>
                )}
                {row.note && <p className="text-xs text-slate-800">{row.note}</p>}
                {row.editable && row.answer_key && (
                  <div className="mt-1 flex gap-2">
                    <input
                      aria-label={row.label}
                      className="input"
                      placeholder={row.answer_value ?? ""}
                      value={edits[row.answer_key] ?? ""}
                      onChange={(e) => setEdits({ ...edits, [row.answer_key as string]: e.target.value })}
                    />
                    <button className="btn-secondary" onClick={() => void save(row)}>
                      {t("save")}
                    </button>
                  </div>
                )}
                {msg[row.pdf_field] && (
                  <p role="status" className="text-sm">
                    {msg[row.pdf_field]}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card mt-4">
        <h3 className="mb-2 font-semibold">{t("summary")}</h3>
        <ol className="space-y-3">
          {rv.summary.steps.map((s) => (
            <li key={s.order}>
              <p className="font-medium">
                {s.order}. {s.name}
              </p>
              {s.municipal_data_missing && <p className="text-amber-950">{tc("municipalMissing")}</p>}
              {s.lines
                .filter((l) => l.text)
                .map((l) => (
                  <div key={l.label} className="ml-3 mt-1">
                    <p>
                      <strong>{l.label}:</strong> {l.text?.replace(/^[^:]+:\s*/, "")}
                    </p>
                    {l.citation && (
                      <CitationLine source_url={l.citation.source_url} fetched_at={l.citation.fetched_at} content_hash={l.citation.content_hash} confidence={l.citation.confidence} verify={l.citation.verify_with_authority} />
                    )}
                  </div>
                ))}
            </li>
          ))}
        </ol>
      </div>

      <div className="card mt-4 space-y-3">
        <label className="flex items-start gap-2">
          <input type="checkbox" className="mt-1 h-5 w-5" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span>{t("consent")}</span>
        </label>
        {needAck && (
          <label className="flex items-start gap-2 text-red-950">
            <input type="checkbox" className="mt-1 h-5 w-5" checked={ack} onChange={(e) => setAck(e.target.checked)} />
            <span>
              {t("incomplete")} {t("acknowledge")}
            </span>
          </label>
        )}
        {err && <p role="alert">{err}</p>}
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={onBack}>
            {ta("back")}
          </button>
          <button className="btn" disabled={!consent || (needAck && !ack)} onClick={() => void confirm()}>
            {t("confirm")}
          </button>
        </div>
      </div>
    </section>
  );
}
