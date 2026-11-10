"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { api, hasToken, post } from "@/lib/api";

type Ws = { id: string; name: string; role: "owner" | "admin" | "member" };
type Detail = { id: string; name: string; your_role: Ws["role"]; members: { user_id: string; email: string; role: Ws["role"] }[] };
type Invite = { id: string; email: string; role: string; expired: boolean };
type Shared = { id: string; goal: string; owner: string };
type Mine = { id: string; goal: string };

function Team({ ws }: { ws: Ws }) {
  const t = useTranslations("teams");
  const [d, setD] = useState<Detail | null>(null);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [shared, setShared] = useState<Shared[]>([]);
  const [mine, setMine] = useState<Mine[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [link, setLink] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [gone, setGone] = useState(false);
  const ids = [useId(), useId()];
  const manager = ws.role !== "member";

  const load = useCallback(async () => {
    try {
      setD(await api<Detail>(`/workspaces/${ws.id}`));
      setShared(await api<Shared[]>(`/workspaces/${ws.id}/sessions`));
      setMine(await api<Mine[]>("/sessions"));
      if (manager) setInvites(await api<Invite[]>(`/workspaces/${ws.id}/invites`));
    } catch {
      setErr(t("failed"));
    }
  }, [ws.id, manager, t]);
  useEffect(() => {
    void load();
  }, [load]);

  const run = async (fn: () => Promise<unknown>) => {
    setErr(null);
    try {
      await fn();
      await load();
    } catch (e) {
      const code = (e as { code?: string }).code;
      setErr(code === "email_not_verified" ? t("needVerify") : t("failed"));
    }
  };

  if (gone) return null;
  const sharedIds = new Set(shared.map((s) => s.id));
  return (
    <section className="card space-y-4" aria-labelledby={`ws-${ws.id}`}>
      <h2 id={`ws-${ws.id}`} className="text-lg font-bold">
        {ws.name} <span className="text-sm font-normal text-slate-600">({t(`role_${ws.role}`)})</span>
      </h2>
      {err && (
        <p role="alert" className="rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
          {err}
        </p>
      )}
      <div>
        <h3 className="font-semibold">{t("members")}</h3>
        <ul className="divide-y">
          {d?.members.map((m) => (
            <li key={m.user_id} className="flex items-center justify-between gap-2 py-1.5 text-sm">
              <span>
                {m.email} <span className="text-slate-600">({t(`role_${m.role}`)})</span>
              </span>
              {m.role !== "owner" && (ws.role === "owner" || (ws.role === "admin" && m.role === "member")) && (
                <button className="btn-ghost !min-h-0 text-sm" onClick={() => run(() => api(`/workspaces/${ws.id}/members/${m.user_id}`, { method: "DELETE" }))}>
                  {t("remove")}
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
      {manager && (
        <div>
          <h3 className="font-semibold">{t("invite")}</h3>
          <form
            className="grid gap-2 sm:grid-cols-[1fr_auto_auto] sm:items-end"
            onSubmit={(e) => {
              e.preventDefault();
              void run(async () => {
                const r = await post<{ token: string }>(`/workspaces/${ws.id}/invites`, { email, role });
                setLink(`${window.location.origin}/${document.documentElement.lang || "en"}/invite?token=${r.token}`);
                setEmail("");
              });
            }}
          >
            <div>
              <label htmlFor={ids[0]}>{t("inviteEmail")}</label>
              <input id={ids[0]} className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label htmlFor={ids[1]}>{t("inviteRole")}</label>
              <select id={ids[1]} className="input" value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="member">{t("role_member")}</option>
                <option value="admin">{t("role_admin")}</option>
              </select>
            </div>
            <button className="btn">{t("inviteButton")}</button>
          </form>
          {link && (
            <div role="status" className="mt-2 rounded-lg bg-indgreen-50 p-2.5 text-sm">
              <p className="font-semibold">{t("linkTitle")}</p>
              <input readOnly className="input mt-1" value={link} onFocus={(e) => e.currentTarget.select()} aria-label={t("linkTitle")} />
              <p className="mt-1 text-slate-700">{t("linkHelp")}</p>
            </div>
          )}
          {invites.length > 0 && (
            <>
              <h4 className="mt-3 text-sm font-semibold">{t("pending")}</h4>
              <ul className="text-sm">
                {invites.map((i) => (
                  <li key={i.id} className="flex items-center justify-between py-1">
                    <span>
                      {i.email} ({t(`role_${i.role as "admin" | "member"}`)}){i.expired ? ` · ${t("expired")}` : ""}
                    </span>
                    <button className="btn-ghost !min-h-0 text-sm" onClick={() => run(() => api(`/workspaces/${ws.id}/invites/${i.id}`, { method: "DELETE" }))}>
                      {t("revoke")}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
      <div>
        <h3 className="font-semibold">{t("shared")}</h3>
        {shared.length === 0 ? (
          <p className="text-sm text-slate-600">{t("noShared")}</p>
        ) : (
          <ul className="text-sm">
            {shared.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-2 py-1">
                <span>
                  {s.goal.slice(0, 80)} <span className="text-slate-600">· {s.owner}</span>
                </span>
                <button className="btn-ghost !min-h-0 text-sm" onClick={() => run(() => api(`/workspaces/${ws.id}/sessions/${s.id}`, { method: "DELETE" }))}>
                  {t("unshare")}
                </button>
              </li>
            ))}
          </ul>
        )}
        {mine.some((m) => !sharedIds.has(m.id)) && (
          <>
            <h4 className="mt-3 text-sm font-semibold">{t("yourApps")}</h4>
            <ul className="text-sm">
              {mine
                .filter((m) => !sharedIds.has(m.id))
                .map((m) => (
                  <li key={m.id} className="flex items-center justify-between gap-2 py-1">
                    <span>{m.goal.slice(0, 80)}</span>
                    <button className="btn-ghost !min-h-0 text-sm" onClick={() => run(() => post(`/workspaces/${ws.id}/sessions`, { session_id: m.id }))}>
                      {t("share")}
                    </button>
                  </li>
                ))}
            </ul>
          </>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-3 border-t pt-3">
        {ws.role === "owner" ? (
          <>
            <button
              className="btn-ghost text-red-800"
              onClick={() =>
                run(async () => {
                  await api(`/workspaces/${ws.id}`, { method: "DELETE" });
                  setGone(true);
                })
              }
            >
              {t("delete")}
            </button>
            <span className="text-sm text-slate-600">{t("deleteNote")}</span>
          </>
        ) : (
          <button
            className="btn-ghost"
            onClick={() =>
              run(async () => {
                const me = await api<{ id: string }>("/auth/me");
                await api(`/workspaces/${ws.id}/members/${me.id}`, { method: "DELETE" });
                setGone(true);
              })
            }
          >
            {t("leave")}
          </button>
        )}
      </div>
    </section>
  );
}

export default function TeamsView() {
  const t = useTranslations("teams");
  const id = useId();
  const [list, setList] = useState<Ws[] | null>(null);
  const [name, setName] = useState("");
  const [denied, setDenied] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setList(await api<Ws[]>("/workspaces"));
    } catch {
      setErr(t("failed"));
    }
  }, [t]);
  useEffect(() => {
    if (!hasToken()) {
      setDenied(true);
      return;
    }
    void load();
  }, [load]);

  if (denied) return <p role="alert">{t("signin")}</p>;
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold sm:text-3xl">{t("title")}</h1>
      <p className="text-slate-700">{t("intro")}</p>
      {err && (
        <p role="alert" className="rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
          {err}
        </p>
      )}
      <form
        className="card flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          post("/workspaces", { name })
            .then(() => {
              setName("");
              return load();
            })
            .catch(() => setErr(t("failed")));
        }}
      >
        <div className="min-w-[12rem] flex-1">
          <label htmlFor={id}>{t("newName")}</label>
          <input id={id} className="input" required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <button className="btn">{t("create")}</button>
      </form>
      {list && list.length === 0 && <p className="text-slate-600">{t("none")}</p>}
      {list?.map((w) => <Team key={w.id} ws={w} />)}
    </div>
  );
}
