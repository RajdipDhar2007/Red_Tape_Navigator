"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, hasToken, post } from "@/lib/api";

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
type Item = {
  id: string;
  reason: string;
  claim: { key: string; text: string; source_url: string; confidence: number; fetched_at: string } | null;
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
  const [state, setState] = useState<"loading" | "denied" | "ready" | "error">("loading");
  const [stats, setStats] = useState<Stats | null>(null);
  const [queue, setQueue] = useState<Item[]>([]);
  const [chain, setChain] = useState<boolean | null>(null);

  const load = useCallback(async () => {
    if (!hasToken()) return setState("denied");
    try {
      const me = await api<{ role: string }>("/auth/me");
      if (me.role === "citizen") return setState("denied");
      const [s, q, a] = await Promise.all([
        api<Stats>("/admin/stats"),
        api<Item[]>("/admin/review-queue"),
        api<{ chain_valid: boolean }>("/admin/audit/verify"),
      ]);
      setStats(s);
      setQueue(q);
      setChain(a.chain_valid);
      setState("ready");
    } catch (e) {
      setState(e instanceof ApiError && (e.status === 401 || e.status === 403) ? "denied" : "error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (state === "loading") return <p role="status">{t("loading")}</p>;
  if (state === "denied") return <p role="alert">{t("denied")}</p>;
  if (state === "error" || !stats) return <p role="alert">{t("error")}</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
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
      <div className="grid gap-3 md:grid-cols-2">
        <Breakdown title={t("byActivity")} data={stats.sessions.by_activity} />
        <Breakdown title={t("byState")} data={stats.sessions.by_state} />
      </div>
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
