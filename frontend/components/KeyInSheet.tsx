"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import Icon from "./Icon";

type Row = { label: string; value: string; status: string; note: string | null; required: boolean };
type Sheet = { title: string; authority: string; portal_url: string | null; rows: Row[]; important: string };

function CopyButton({ value, label }: { value: string; label: string }) {
  const t = useTranslations("done");
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="btn-secondary !min-h-0 !px-2.5 !py-1 text-sm"
      disabled={!value}
      aria-label={`${t("copy")}: ${label}`}
      onClick={() => {
        void navigator.clipboard
          .writeText(value)
          .then(() => {
            setDone(true);
            setTimeout(() => setDone(false), 1500);
          })
          .catch(() => setDone(false));
      }}
    >
      <Icon name={done ? "check" : "copy"} size={16} className={done ? "text-indgreen-600" : ""} />
      {done ? t("copied") : t("copy")}
    </button>
  );
}

/** For portals that are filled online (FoSCoS, Udyam, GST): every value in form order, one click to copy. */
export default function KeyInSheet({ sid, fid }: { sid: string; fid: string }) {
  const t = useTranslations("done");
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState(false);

  const toggle = async () => {
    setOpen(!open);
    if (!sheet && !open) {
      try {
        setSheet(await api<Sheet>(`/sessions/${sid}/forms/${fid}/keyin`));
      } catch {
        setErr(true);
      }
    }
  };

  return (
    <div className="w-full">
      <button type="button" className="btn-ghost" aria-expanded={open} onClick={() => void toggle()}>
        <Icon name="file" size={18} /> {open ? t("keyinHide") : t("keyinShow")}
      </button>
      {open && (
        <div className="mt-2 rounded-xl border border-navy-100 bg-navy-50/60 p-4">
          {err && <p role="alert">{t("keyinError")}</p>}
          {sheet && (
            <>
              <p className="mb-3 text-sm text-navy-900">{t("keyinHelp")}</p>
              {sheet.portal_url && (
                <a className="btn mb-3" href={sheet.portal_url} target="_blank" rel="noopener noreferrer">
                  {t("openPortal")} <Icon name="external" size={16} />
                </a>
              )}
              <ul className="divide-y divide-navy-100 rounded-lg bg-white ring-1 ring-navy-100">
                {sheet.rows.map((r) => (
                  <li key={r.label} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">{r.label}</p>
                      <p className={`break-words font-medium ${r.value ? "text-navy-900" : "text-red-800"}`}>{r.value || t("keyinMissing")}</p>
                      {r.note && <p className="text-xs text-saffron-700">{r.note}</p>}
                    </div>
                    <CopyButton value={r.value} label={r.label} />
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-sm font-medium text-saffron-700">{sheet.important}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
