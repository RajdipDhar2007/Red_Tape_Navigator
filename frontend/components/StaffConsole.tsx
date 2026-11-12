"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { formatDate } from "@/lib/format";
import { api, apiBlob, ApiError, hasToken, post } from "@/lib/api";

type Stats = {
  users: { total: number; by_role: Record<string, number> };
  sessions: {
    total: number;
    reviewed: number;
    completion_rate: number;
    by_stage: Record<string, number>;
    by_activity: Record<string, number>;
    by_state: Record<string, number>;
  };
  knowledge_base: { claims: number; needs_verification: number; seed_only: number };
  review_queue: Record<string, number>;
  consents: { granted: number; withdrawn: number };
};
type Source = {
  id: string;
  url: string;
  sha256: string;
  status: string;
  fetched_at: string;
  compatible: boolean;
  compat: { reason?: string; missing_required?: string[]; matched?: number; pdf_fields?: number };
};
type FormRow = {
  form_id: string;
  title: string;
  authority: string;
  official_url: string | null;
  serving: "official" | "placeholder";
  active: Source | null;
  candidates: Source[];
};
type Item = {
  id: string;
  reason: string;
  claim: { key: string; text: string; source_url: string; confidence: number; fetched_at: string } | null;
};
type ReadinessProvider = {
  configured?: boolean;
  ok?: boolean;
  mode: string;
};
type ReadinessData = {
  environment: string;
  demo_mode: boolean;
  providers: Record<string, ReadinessProvider>;
};

function Tile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <p className="text-sm text-slate-700">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const rows = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...rows.map(([, n]) => n));
  return (
    <section className="card" aria-label={title}>
      <h3 className="mb-2 font-semibold">{title}</h3>
      <ul className="space-y-1">
        {rows.map(([k, n]) => (
          <li key={k} className="flex items-center gap-2 text-sm">
            <span className="w-40 truncate">{k.replace(/_/g, " ")}</span>
            <span className="h-3 rounded bg-brand-600" style={{ width: `${(n / max) * 50}%` }} aria-hidden="true" />
            <span>{n}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function FormRowView({ f, onDone }: { f: FormRow; onDone: () => void }) {
  const t = useTranslations("staff");
  const locale = useLocale();
  const id = useId();
  const [url, setUrl] = useState(f.official_url ?? "");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      onDone();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : t("error"));
    } finally {
      setBusy(false);
    }
  };
  const view = async (sid: string) => {
    const blob = await apiBlob(`/admin/forms/sources/${sid}/pdf`);
    window.open(URL.createObjectURL(blob), "_blank", "noopener,noreferrer");
  };

  return (
    <li className="card space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{f.title.replace(/\s*\(PLACEHOLDER\)/, "")}</h3>
        <span className={f.serving === "official" ? "badge bg-green-200" : "badge bg-amber-200"}>
          {f.serving === "official" ? t("servingOfficial") : t("servingPlaceholder")}
        </span>
      </div>
      <p className="text-sm text-slate-700">{f.authority}</p>
      {f.active && <p className="text-sm">{t("activeCopy", { hash: f.active.sha256.slice(0, 10), date: formatDate(f.active.fetched_at, locale) })}</p>}
      <label htmlFor={id}>{t("officialUrl")}</label>
      <div className="flex flex-wrap gap-2">
        <input id={id} className="input flex-1" type="url" placeholder="https://" value={url} onChange={(e) => setUrl(e.target.value)} />
        <button type="button" className="btn" disabled={busy || !url} onClick={() => void run(() => post(`/admin/forms/${f.form_id}/fetch`, { url }))}>
          {t("fetchForm")}
        </button>
      </div>
      {msg && (
        <p role="alert" className="text-red-800">
          {msg}
        </p>
      )}
      {f.candidates.map((c) => (
        <div key={c.id} className="rounded border border-slate-300 p-2">
          <p className="text-sm">
            {c.url} · {c.sha256.slice(0, 10)}
          </p>
          <p className={c.compatible ? "text-sm text-green-800" : "text-sm text-red-800"}>
            {c.compatible ? t("compatible") : t("incompatible")}: {c.compat.reason}
          </p>
          <div className="mt-1 flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => void view(c.id)}>
              {t("viewPdf")}
            </button>
            <button type="button" className="btn" disabled={busy || !c.compatible} onClick={() => void run(() => post(`/admin/forms/sources/${c.id}/activate`))}>
              {t("activate")}
            </button>
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => void run(() => post(`/admin/forms/sources/${c.id}/reject`))}>
              {t("rejected")}
            </button>
          </div>
        </div>
      ))}
    </li>
  );
}

function QueueRow({ item, onDone }: { item: Item; onDone: () => void }) {
  const t = useTranslations("staff");
  const id = useId();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);
  const resolve = async (status: "verified" | "corrected" | "rejected") => {
    setBusy(true);
    setErr(false);
    try {
      await post(`/admin/review-queue/${item.id}/resolve`, { status, resolution: note });
      onDone();
    } catch {
      setErr(true);
    } finally {
      setBusy(false);
    }
  };
  return (
    <li className="card space-y-2">
      <p className="font-medium">{item.reason}</p>
      {item.claim && (
        <>
          <p>{item.claim.text}</p>
          <p className="text-sm text-slate-700">
            {t("confidence")}: {Math.round(item.claim.confidence * 100)}% ·{" "}
            <a className="underline" href={item.claim.source_url} target="_blank" rel="noopener noreferrer">
              {t("source")}
            </a>
          </p>
        </>
      )}
      <label htmlFor={id}>{t("note")}</label>
      <input id={id} className="input" value={note} maxLength={1000} onChange={(e) => setNote(e.target.value)} />
      {err && (
        <p role="alert" className="text-red-800">
          {t("resolveFailed")}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {(["verified", "corrected", "rejected"] as const).map((s) => (
          <button
            key={s}
            type="button"
            className={s === "verified" ? "btn" : "btn-secondary"}
            disabled={busy || note.trim().length < 3}
            onClick={() => void resolve(s)}
          >
            {t(s)}
          </button>
        ))}
      </div>
    </li>
  );
}

export default function StaffConsole() {
  const t = useTranslations("staff");
  const tp = useTranslations("privacy");
  const [state, setState] = useState<"loading" | "denied" | "ready" | "error">("loading");
  const [role, setRole] = useState<string>("reviewer");
  const [stats, setStats] = useState<Stats | null>(null);
  const [queue, setQueue] = useState<Item[]>([]);
  const [chain, setChain] = useState<boolean | null>(null);
  const [forms, setForms] = useState<FormRow[]>([]);
  const [readiness, setReadiness] = useState<ReadinessData | null>(null);
  const [confirmPurge, setConfirmPurge] = useState(false);
  const [purging, setPurging] = useState(false);
  const [purgeMsg, setPurgeMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!hasToken()) return setState("denied");
    try {
      const me = await api<{ role: string }>("/auth/me");
      if (me.role === "citizen") return setState("denied");
      setRole(me.role);
      const [s, q, a, fm, rd] = await Promise.all([
        api<Stats>("/admin/stats"),
        api<Item[]>("/admin/review-queue"),
        api<{ chain_valid: boolean }>("/admin/audit/verify"),
        api<FormRow[]>("/admin/forms"),
        api<ReadinessData>("/admin/readiness").catch(() => null),
      ]);
      setForms(fm);
      setStats(s);
      setQueue(q);
      setChain(a.chain_valid);
      if (rd && rd.providers) setReadiness(rd);
      setState("ready");
    } catch (e) {
      setState(e instanceof ApiError && (e.status === 401 || e.status === 403) ? "denied" : "error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runPurge = async () => {
    setPurging(true);
    setPurgeMsg(null);
    try {
      const res = await post<{ purged_sessions: number }>("/admin/purge");
      setPurgeMsg(t("purgeDone", { count: res.purged_sessions }));
      setConfirmPurge(false);
      await load();
    } catch {
      setPurgeMsg(t("error"));
    } finally {
      setPurging(false);
    }
  };

  if (state === "loading") return <p role="status">{t("loading")}</p>;
  if (state === "denied") return <p role="alert">{t("denied")}</p>;
  if (state === "error" || !stats) return <p role="alert">{t("error")}</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        {role === "admin" && !confirmPurge && (
          <button type="button" className="btn-secondary text-sm" onClick={() => setConfirmPurge(true)}>
            {t("purgeBtn")}
          </button>
        )}
      </div>

      {confirmPurge && (
        <div role="alert" className="card flex flex-wrap items-center justify-between gap-3 border-l-4 border-l-amber-500">
          <p className="font-medium text-navy-900">{t("purgeConfirm")}</p>
          <div className="flex gap-2">
            <button type="button" className="btn text-sm" disabled={purging} onClick={() => void runPurge()}>
              {t("purgeConfirmBtn")}
            </button>
            <button type="button" className="btn-ghost text-sm" disabled={purging} onClick={() => setConfirmPurge(false)}>
              {tp("cancel")}
            </button>
          </div>
        </div>
      )}

      {purgeMsg && (
        <p role="status" className="rounded-lg bg-indgreen-50 p-3 text-sm font-medium text-indgreen-900">
          {purgeMsg}
        </p>
      )}

      <section aria-label={t("overview")} className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Tile label={t("citizens")} value={stats.users.by_role.citizen ?? 0} />
        <Tile label={t("sessions")} value={stats.sessions.total} />
        <Tile label={t("completion")} value={`${Math.round(stats.sessions.completion_rate * 100)}%`} />
        <Tile label={t("openReviews")} value={stats.review_queue.open ?? 0} />
        <Tile label={t("rules")} value={stats.knowledge_base.claims} />
        <Tile label={t("needsVerification")} value={stats.knowledge_base.needs_verification} />
        <Tile label={t("consentsGranted")} value={stats.consents.granted} />
        <Tile label={t("auditChain")} value={chain ? t("intact") : t("broken")} />
      </section>

      {readiness && (
        <section aria-labelledby="readiness-h" className="card space-y-3">
          <div>
            <h2 id="readiness-h" className="text-xl font-semibold">
              {t("readinessHeading")}
            </h2>
            <p className="text-sm text-slate-700">{t("readinessIntro")}</p>
          </div>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(readiness.providers).map(([name, info]) => {
              const isLive = info.ok === true || info.configured === true;
              const isFallback = !isLive && (info.mode.includes("mock") || info.mode.includes("fallback") || info.mode.includes("memory") || info.mode.includes("local"));
              return (
                <li key={name} className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                  <div>
                    <p className="font-semibold text-navy-900">{name.replace(/_/g, " ")}</p>
                    <p className="text-xs text-slate-600">{info.mode}</p>
                  </div>
                  <span className={`badge ${isLive ? "bg-green-200 text-green-950" : isFallback ? "bg-amber-200 text-amber-950" : "bg-slate-200 text-slate-800"}`}>
                    {isLive ? t("statusLive") : isFallback ? t("statusMock") : t("statusDisabled")}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        <Breakdown title={t("byActivity")} data={stats.sessions.by_activity} />
        <Breakdown title={t("byState")} data={stats.sessions.by_state} />
      </div>
      <section aria-labelledby="forms-h" className="space-y-3">
        <h2 id="forms-h" className="text-xl font-semibold">
          {t("forms")}
        </h2>
        <p>{t("formsIntro")}</p>
        <ul className="space-y-3">
          {forms.map((f) => (
            <FormRowView key={f.form_id} f={f} onDone={() => void load()} />
          ))}
        </ul>
      </section>
      <section aria-labelledby="queue-h" className="space-y-3">
        <h2 id="queue-h" className="text-xl font-semibold">
          {t("queue")}
        </h2>
        {queue.length === 0 ? (
          <p>{t("queueEmpty")}</p>
        ) : (
          <ul className="space-y-3">
            {queue.map((i) => (
              <QueueRow key={i.id} item={i} onDone={() => void load()} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
