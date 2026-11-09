"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, apiBlob, ApiError, post } from "@/lib/api";
import type { ChecklistItem, Session } from "@/lib/types";
import Confetti from "./fx/Confetti";
import KeyInSheet from "./KeyInSheet";

type Esign = { request_id: string; status: string; mock: boolean; label?: string; signing_url?: string | null };

export default function DoneView({ session }: { session: Session }) {
  const t = useTranslations("done");
  const ta = useTranslations("app");
  const sid = session.id;
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [esign, setEsign] = useState<Record<string, Esign>>({});
  const [needShare, setNeedShare] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string[]>([]);
  const [channel, setChannel] = useState("email");
  const [sched, setSched] = useState<{ title: string; due_at: string }[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const forms = [...new Set((session.plan.steps ?? []).map((s) => s.form).filter((f): f is string => !!f))];

  const [burst, setBurst] = useState(0);
  useEffect(() => setBurst(1), []);

  useEffect(() => {
    void api<{ items: ChecklistItem[] }>(`/sessions/${sid}/submission-checklist`).then((r) => setItems(r.items));
  }, [sid]);

  const download = async (fid: string) => {
    const blob = await apiBlob(`/sessions/${sid}/forms/${fid}/download`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${fid}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const sign = async (fid: string, consent = false) => {
    try {
      if (consent) await post("/consent", { purpose: "identity_providers", granted: true });
      const r = await post<Esign>(`/sessions/${sid}/esign`, { form_id: fid });
      setNeedShare(null);
      setMsg(null);
      setEsign((e) => ({ ...e, [fid]: r }));
    } catch (e) {
      if (e instanceof ApiError && e.code === "consent_required") setNeedShare(fid);
      else setMsg(ta("error"));
    }
  };

  // The webhook normally updates the status; polling covers a late or missed webhook.
  const pending = Object.entries(esign).filter(([, r]) => !r.mock && r.status === "pending");
  useEffect(() => {
    if (!pending.length) return;
    const timer = setInterval(() => {
      pending.forEach(([fid, r]) => {
        void api<Esign>(`/sessions/${sid}/esign/${r.request_id}`).then((n) => setEsign((e) => ({ ...e, [fid]: { ...e[fid], ...n } })));
      });
    }, 5000);
    return () => clearInterval(timer);
  }, [pending.map(([f, r]) => `${f}:${r.status}`).join(","), sid]); // eslint-disable-line react-hooks/exhaustive-deps

  const downloadSigned = async (fid: string, rid: string) => {
    const blob = await apiBlob(`/sessions/${sid}/esign/${rid}/signed.pdf`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${fid}-signed.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const remind = async () => {
    try {
      const r = await post<{ scheduled: { title: string; due_at: string }[] }>(`/sessions/${sid}/submitted`, { licences: chosen, channel });
      setSched(r.scheduled);
      setMsg(null);
    } catch (e) {
      setMsg(e instanceof ApiError && e.code === "consent_required" ? t("need") : ta("error"));
    }
  };

  return (
    <section aria-labelledby="done-h" className="space-y-4 animate-fade-up">
      <Confetti burst={burst} />
      <h2 id="done-h" className="text-xl font-semibold">
        {t("heading")}
      </h2>
      <p role="note" className="rounded border border-brand-600 bg-brand-50 p-3 font-medium">
        {t("important")}
      </p>

      <div className="card space-y-4">
        {forms.map((f) => (
          <div key={f} className="flex flex-wrap items-center gap-2 border-b border-slate-100 pb-4 last:border-0 last:pb-0">
            <button className="btn" onClick={() => void download(f)}>
              {t("download")}: {f}
            </button>
            <button className="btn-secondary" onClick={() => void sign(f)}>
              {t("esign")}
            </button>
            {esign[f]?.mock && (
              <span role="status" className="badge bg-amber-200 text-amber-950">
                {esign[f].label} — {t("esignResult")}
              </span>
            )}
            {esign[f] && !esign[f].mock && (
              <div role="status" className="flex flex-wrap items-center gap-2">
                {esign[f].status === "pending" && (
                  <>
                    {esign[f].signing_url && (
                      <a className="btn" href={esign[f].signing_url ?? undefined} target="_blank" rel="noopener noreferrer">
                        {t("esignOpen")}
                      </a>
                    )}
                    <span className="text-sm">{t("esignWaiting")} {t("esignMailed")}</span>
                  </>
                )}
                {esign[f].status === "completed" && (
                  <>
                    <span className="badge bg-green-200 text-green-950">{t("esignSigned")}</span>
                    <button className="btn" onClick={() => void downloadSigned(f, esign[f].request_id)}>
                      {t("esignDownload")}
                    </button>
                  </>
                )}
                {!["pending", "completed"].includes(esign[f].status) && <span className="badge bg-red-200 text-red-950">{t("esignFailed")}</span>}
              </div>
            )}
            {needShare === f && (
              <div role="alert" className="w-full rounded border border-brand-600 bg-brand-50 p-3 text-sm">
                <p>{t("esignShare")}</p>
                <button className="btn mt-2" onClick={() => void sign(f, true)}>
                  {t("esignShareBtn")}
                </button>
              </div>
            )}
            <KeyInSheet sid={sid} fid={f} />
          </div>
        ))}
      </div>

      <div className="card">
        <h3 className="mb-2 text-lg font-semibold">{t("checklist")}</h3>
        <ol className="space-y-4">
          {items.map((it) => (
            <li key={it.licence}>
              <p className="font-medium">
                {t("step")} {it.order}: {it.name}
              </p>
              {it.portal_url && (
                <a className="text-brand-700 underline" href={it.portal_url} target="_blank" rel="noopener noreferrer">
                  {t("portal")}
                </a>
              )}
              <ul className="ml-5 list-disc text-sm">
                {it.actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </div>

      <div className="card space-y-3">
        <h3 className="text-lg font-semibold">{t("submittedHeading")}</h3>
        <p>{t("submittedHelp")}</p>
        <fieldset className="space-y-1">
          {items.map((it) => (
            <label key={it.licence} className="flex items-center gap-2">
              <input type="checkbox" className="h-5 w-5" checked={chosen.includes(it.licence)} onChange={(e) => setChosen(e.target.checked ? [...chosen, it.licence] : chosen.filter((x) => x !== it.licence))} />
              {it.name}
            </label>
          ))}
        </fieldset>
        <label className="flex items-center gap-2">
          {t("channel")}
          <select className="rounded border border-slate-500 bg-white px-2" value={channel} onChange={(e) => setChannel(e.target.value)}>
            <option value="email">Email</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="sms">SMS</option>
          </select>
        </label>
        <button className="btn" disabled={!chosen.length} onClick={() => void remind()}>
          {t("remind")}
        </button>
        {msg && <p role="alert">{msg}</p>}
        {sched && (
          <div role="status">
            <p className="font-medium">{t("scheduled")}</p>
            <ul className="list-disc pl-5 text-sm">
              {sched.map((s) => (
                <li key={s.title}>
                  {s.title} — {new Date(s.due_at).toLocaleDateString()}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
