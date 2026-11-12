"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { api, apiBlob, clearTokens, del, hasToken, post, setTokens } from "@/lib/api";
import { passwordStrength } from "./Home";

type ConsentPurpose = "service" | "reminders" | "identity_providers";
type ConsentEntry = { purpose: string; granted: boolean; policy_version: string; at: string };
type SessionItem = { id: string; goal: string; created_at: string; reviewed: boolean; city: string | null; steps: number };

const PURPOSES: ConsentPurpose[] = ["service", "reminders", "identity_providers"];

export default function AccountView() {
  const t = useTranslations("account");
  const ta = useTranslations("auth");
  const tp = useTranslations("privacy");
  const router = useRouter();
  const ids = [useId(), useId()];
  const deleteInputId = useId();
  const [email, setEmail] = useState<string | null>(null);
  const [verified, setVerified] = useState<boolean | null>(null);
  const [resent, setResent] = useState(false);
  const [tf, setTf] = useState<boolean | null>(null);
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [tfPw, setTfPw] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [tfErr, setTfErr] = useState<string | null>(null);
  const tfIds = [useId(), useId(), useId()];
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "done" | "failed">("idle");
  const [denied, setDenied] = useState(false);

  // Privacy & DPDP state
  const [exportState, setExportState] = useState<"idle" | "busy" | "done" | "failed">("idle");
  const [consents, setConsents] = useState<Record<ConsentPurpose, boolean>>({
    service: false,
    reminders: false,
    identity_providers: false,
  });
  const [consentBusy, setConsentBusy] = useState<ConsentPurpose | null>(null);
  const [confirmWithdrawService, setConfirmWithdrawService] = useState(false);
  const [consentNotice, setConsentNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [confirmSessionId, setConfirmSessionId] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [sessionNotice, setSessionNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const [showDeleteAccount, setShowDeleteAccount] = useState(false);
  const [deletePhrase, setDeletePhrase] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteErr, setDeleteErr] = useState<string | null>(null);

  const loadPrivacyData = useCallback(async () => {
    try {
      const [cLog, sList] = await Promise.all([
        api<ConsentEntry[]>("/consent"),
        api<SessionItem[]>("/sessions"),
      ]);
      const nextConsents: Record<ConsentPurpose, boolean> = {
        service: false,
        reminders: false,
        identity_providers: false,
      };
      for (const entry of cLog) {
        if (entry.purpose in nextConsents) {
          nextConsents[entry.purpose as ConsentPurpose] = entry.granted;
        }
      }
      setConsents(nextConsents);
      setSessions(sList);
    } catch {
      /* non-fatal if secondary fetch fails */
    }
  }, []);

  useEffect(() => {
    if (!hasToken()) {
      setDenied(true);
      return;
    }
    api<{ email: string; email_verified: boolean; two_factor: boolean }>("/auth/me")
      .then((m) => {
        setEmail(m.email);
        setVerified(m.email_verified);
        setTf(m.two_factor);
      })
      .catch(() => setEmail(null));
    void loadPrivacyData();
  }, [loadPrivacyData]);

  if (denied) return <p role="alert">{t("signin")}</p>;

  const submit = async () => {
    setState("busy");
    try {
      const tok = await post<{ access_token: string; refresh_token: string }>("/auth/change-password", { current_password: current, new_password: next });
      setTokens(tok.access_token, tok.refresh_token);
      setCurrent("");
      setNext("");
      setState("done");
    } catch {
      setState("failed");
    }
  };

  const startTf = async () => {
    setTfErr(null);
    setSetup(await post<{ secret: string; otpauth_uri: string }>("/auth/2fa/setup"));
  };
  const confirmTf = async () => {
    setTfErr(null);
    try {
      const r = await post<{ recovery_codes: string[] }>("/auth/2fa/enable", { code });
      setCodes(r.recovery_codes);
      setSetup(null);
      setCode("");
      setTf(true);
    } catch {
      setTfErr(t("tfBad"));
    }
  };
  const disableTf = async () => {
    setTfErr(null);
    try {
      await post("/auth/2fa/disable", { password: tfPw, code });
      setTf(false);
      setCodes(null);
      setCode("");
      setTfPw("");
    } catch {
      setTfErr(t("tfDisableFail"));
    }
  };

  const exportMyData = async () => {
    setExportState("busy");
    try {
      const blob = await apiBlob("/privacy/export");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "my-data.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setExportState("done");
    } catch {
      setExportState("failed");
    }
  };

  const updateConsent = async (purpose: ConsentPurpose, granted: boolean) => {
    setConsentBusy(purpose);
    setConsentNotice(null);
    try {
      await post("/consent", { purpose, granted });
      setConsents((prev) => ({ ...prev, [purpose]: granted }));
      setConfirmWithdrawService(false);
      setConsentNotice({ kind: "ok", text: tp("consentUpdated") });
    } catch {
      setConsentNotice({ kind: "err", text: tp("consentError") });
    } finally {
      setConsentBusy(null);
    }
  };

  const handleDeleteSession = async (sid: string) => {
    setDeletingSessionId(sid);
    setSessionNotice(null);
    try {
      await del(`/privacy/sessions/${sid}`);
      setSessions((prev) => prev.filter((s) => s.id !== sid));
      setConfirmSessionId(null);
      setSessionNotice({ kind: "ok", text: tp("sessionDeleted") });
    } catch {
      setSessionNotice({ kind: "err", text: tp("sessionDeleteError") });
    } finally {
      setDeletingSessionId(null);
    }
  };

  const handleDeleteAccount = async () => {
    if (deletePhrase.trim() !== "DELETE" || deleteBusy) return;
    setDeleteBusy(true);
    setDeleteErr(null);
    try {
      await del("/privacy/me");
      clearTokens();
      router.push("/");
      router.refresh();
    } catch {
      setDeleteErr(tp("deleteError"));
      setDeleteBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-2xl font-bold sm:text-3xl">{t("title")}</h1>
      <section className="card">
        <p className="text-sm text-slate-600">{t("email")}</p>
        <p className="font-semibold">{email ?? "…"}</p>
        {verified !== null && (
          <p className="mt-1 text-sm" role="status">
            {verified ? t("verifiedYes") : t("verifiedNo")}
          </p>
        )}
        {verified === false && (
          <>
            <button
              className="btn-ghost mt-1"
              onClick={() => {
                void post("/auth/verify-email/send").then(() => setResent(true));
              }}
            >
              {t("resend")}
            </button>
            {resent && (
              <p role="status" className="text-sm text-indgreen-800">
                {t("resent")}
              </p>
            )}
          </>
        )}
        <Link href="/teams" className="btn-ghost mt-1">
          {t("teamsLink")}
        </Link>
      </section>
      <section className="card" aria-labelledby="tf-h">
        <h2 id="tf-h" className="mb-2 text-lg font-bold">
          {t("tfHeading")}
        </h2>
        {tf !== null && <p className="mb-3 text-sm">{tf ? t("tfOn") : t("tfOff")}</p>}
        {tfErr && (
          <p role="alert" className="mb-2 rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
            {tfErr}
          </p>
        )}
        {codes && (
          <div role="status" className="mb-3 rounded-lg bg-indgreen-50 p-3">
            <p className="font-semibold">{t("tfRecoveryTitle")}</p>
            <p className="mb-2 text-sm">{t("tfRecoveryHelp")}</p>
            <ul className="grid grid-cols-2 gap-1 font-mono text-sm">
              {codes.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        )}
        {tf === false && !setup && (
          <button className="btn" onClick={() => void startTf()}>
            {t("tfStart")}
          </button>
        )}
        {setup && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              void confirmTf();
            }}
          >
            <p className="text-sm">{t("tfScan")}</p>
            <div>
              <label htmlFor={tfIds[0]}>{t("tfSecret")}</label>
              <input id={tfIds[0]} readOnly className="input font-mono" value={setup.secret} onFocus={(e) => e.currentTarget.select()} />
            </div>
            <div>
              <label htmlFor={tfIds[1]}>{t("tfCode")}</label>
              <input id={tfIds[1]} className="input" inputMode="numeric" autoComplete="one-time-code" required value={code} onChange={(e) => setCode(e.target.value)} />
            </div>
            <button className="btn">{t("tfConfirm")}</button>
          </form>
        )}
        {tf === true && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              void disableTf();
            }}
          >
            <div>
              <label htmlFor={tfIds[2]}>{t("current")}</label>
              <input id={tfIds[2]} className="input" type="password" autoComplete="current-password" required value={tfPw} onChange={(e) => setTfPw(e.target.value)} />
            </div>
            <div>
              <label htmlFor={tfIds[1]}>{t("tfCode")}</label>
              <input id={tfIds[1]} className="input" required value={code} onChange={(e) => setCode(e.target.value)} />
            </div>
            <button className="btn-ghost text-red-800">{t("tfDisable")}</button>
          </form>
        )}
      </section>
      <section className="card border-t-4 border-t-navy-700" aria-labelledby="pw-h">
        <h2 id="pw-h" className="mb-3 text-lg font-bold">
          {t("changeHeading")}
        </h2>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <div>
            <label htmlFor={ids[0]}>{t("current")}</label>
            <input id={ids[0]} className="input" type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} />
          </div>
          <div>
            <label htmlFor={ids[1]}>{ta("newPassword")}</label>
            <input id={ids[1]} className="input" type="password" autoComplete="new-password" minLength={10} required value={next} onChange={(e) => setNext(e.target.value)} />
          </div>
          {state === "failed" && (
            <p role="alert" className="rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
              {t("failed")}
            </p>
          )}
          {state === "done" && (
            <p role="status" className="rounded-lg bg-indgreen-50 p-2.5 text-sm text-indgreen-800">
              {t("saved")}
            </p>
          )}
          <button className="btn" disabled={state === "busy" || passwordStrength(next) === 0 || !current}>
            {t("save")}
          </button>
        </form>
      </section>

      {/* Privacy & Data (DPDP Act 2023 Self-Service Controls) */}
      <section className="card border-t-4 border-t-indgreen-600 space-y-6" aria-labelledby="priv-h">
        <div>
          <h2 id="priv-h" className="text-lg font-bold">
            {tp("heading")}
          </h2>
          <p className="mt-1 text-sm text-slate-700">{tp("exportHelp")}</p>
          <div className="mt-3">
            <button
              type="button"
              className="btn-secondary"
              disabled={exportState === "busy"}
              onClick={() => void exportMyData()}
            >
              {exportState === "busy" ? tp("exporting") : tp("export")}
            </button>
          </div>
          {exportState === "done" && (
            <p role="status" className="mt-2 rounded-lg bg-indgreen-50 p-2.5 text-sm text-indgreen-800">
              {tp("exportSuccess")}
            </p>
          )}
          {exportState === "failed" && (
            <p role="alert" className="mt-2 rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
              {tp("exportError")}
            </p>
          )}
        </div>

        {/* Consent Management */}
        <div className="border-t border-slate-200 pt-4">
          <h3 className="text-base font-bold">{tp("consentsHeading")}</h3>
          <p className="mt-1 text-sm text-slate-700">{tp("consentsHelp")}</p>
          {consentNotice && (
            <p
              role={consentNotice.kind === "err" ? "alert" : "status"}
              className={`mt-2 rounded-lg p-2.5 text-sm ${consentNotice.kind === "err" ? "bg-red-50 text-red-900" : "bg-indgreen-50 text-indgreen-800"}`}
            >
              {consentNotice.text}
            </p>
          )}
          <ul className="mt-3 space-y-3">
            {PURPOSES.map((p) => {
              const active = consents[p];
              const isBusy = consentBusy === p;
              return (
                <li key={p} className="rounded-xl bg-slate-50 p-3 ring-1 ring-slate-200">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-navy-900">{tp(`purpose_${p}`)}</span>
                    <span className={`badge ${active ? "bg-indgreen-100 text-indgreen-800" : "bg-slate-200 text-slate-700"}`}>
                      {active ? tp("statusGranted") : tp("statusWithdrawn")}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-700">{tp(`purpose_${p}_desc`)}</p>
                  {p === "service" && active && confirmWithdrawService ? (
                    <div className="mt-3 rounded-lg bg-amber-50 p-2.5 text-sm text-amber-950 ring-1 ring-amber-300">
                      <p className="mb-2">{tp("withdrawServiceWarn")}</p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="btn-ghost text-red-800"
                          disabled={isBusy}
                          onClick={() => void updateConsent("service", false)}
                        >
                          {tp("confirmWithdraw")}
                        </button>
                        <button
                          type="button"
                          className="btn-ghost"
                          disabled={isBusy}
                          onClick={() => setConfirmWithdrawService(false)}
                        >
                          {tp("cancel")}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-2">
                      <button
                        type="button"
                        className={active ? "btn-ghost text-red-800 !min-h-0 py-1 text-sm" : "btn-secondary !min-h-0 py-1.5 text-sm"}
                        disabled={isBusy}
                        onClick={() => {
                          if (p === "service" && active) {
                            setConfirmWithdrawService(true);
                          } else {
                            void updateConsent(p, !active);
                          }
                        }}
                      >
                        {active ? tp("withdrawBtn") : tp("grantBtn")}
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </div>

        {/* Saved Sessions Deletion */}
        <div className="border-t border-slate-200 pt-4">
          <h3 className="text-base font-bold">{tp("sessionsHeading")}</h3>
          <p className="mt-1 text-sm text-slate-700">{tp("sessionsHelp")}</p>
          {sessionNotice && (
            <p
              role={sessionNotice.kind === "err" ? "alert" : "status"}
              className={`mt-2 rounded-lg p-2.5 text-sm ${sessionNotice.kind === "err" ? "bg-red-50 text-red-900" : "bg-indgreen-50 text-indgreen-800"}`}
            >
              {sessionNotice.text}
            </p>
          )}
          {sessions.length === 0 ? (
            <p className="mt-2 text-sm text-slate-600">{tp("sessionsEmpty")}</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {sessions.map((s) => (
                <li key={s.id} className="rounded-xl bg-slate-50 p-3 ring-1 ring-slate-200">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium text-navy-900">{s.goal}</p>
                      <p className="text-xs text-slate-600">
                        {new Date(s.created_at).toLocaleDateString()}
                        {s.city ? ` · ${s.city}` : ""}
                      </p>
                    </div>
                    {confirmSessionId !== s.id && (
                      <button
                        type="button"
                        className="btn-ghost text-red-800 !min-h-0 py-1 text-sm"
                        onClick={() => setConfirmSessionId(s.id)}
                      >
                        {tp("deleteSessionBtn")}
                      </button>
                    )}
                  </div>
                  {confirmSessionId === s.id && (
                    <div className="mt-2 rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
                      <p className="mb-2">{tp("deleteSessionWarn")}</p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="btn bg-red-700 hover:bg-red-800 text-white !min-h-0 py-1.5 text-sm"
                          disabled={deletingSessionId === s.id}
                          onClick={() => void handleDeleteSession(s.id)}
                        >
                          {tp("deleteSessionConfirm")}
                        </button>
                        <button
                          type="button"
                          className="btn-ghost !min-h-0 py-1.5 text-sm"
                          disabled={deletingSessionId === s.id}
                          onClick={() => setConfirmSessionId(null)}
                        >
                          {tp("cancel")}
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* Dangerous Action: Delete My Account */}
      <section className="card border-t-4 border-t-red-700" aria-labelledby="del-acct-h">
        <h2 id="del-acct-h" className="text-lg font-bold text-red-900">
          {tp("dangerHeading")}
        </h2>
        <p className="mt-1 text-sm text-slate-700">{tp("dangerWarn")}</p>
        {!showDeleteAccount ? (
          <button
            type="button"
            className="btn-ghost mt-3 border border-red-300 text-red-800 hover:bg-red-50"
            onClick={() => {
              setDeleteErr(null);
              setDeletePhrase("");
              setShowDeleteAccount(true);
            }}
          >
            {tp("delete")}
          </button>
        ) : (
          <form
            className="mt-4 space-y-3 rounded-xl bg-red-50 p-4 ring-1 ring-red-200"
            onSubmit={(e) => {
              e.preventDefault();
              void handleDeleteAccount();
            }}
          >
            <p className="text-sm font-semibold text-red-900">{tp("confirm")}</p>
            <div>
              <label htmlFor={deleteInputId} className="text-sm text-red-900">
                {tp("deleteTypeLabel")}
              </label>
              <input
                id={deleteInputId}
                className="input mt-1 font-mono"
                required
                value={deletePhrase}
                onChange={(e) => setDeletePhrase(e.target.value)}
                placeholder="DELETE"
                autoComplete="off"
              />
            </div>
            {deleteErr && (
              <p role="alert" className="text-sm font-medium text-red-900">
                {deleteErr}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                className="btn bg-red-700 hover:bg-red-800 text-white"
                disabled={deleteBusy || deletePhrase.trim() !== "DELETE"}
              >
                {tp("deleteConfirmBtn")}
              </button>
              <button
                type="button"
                className="btn-ghost"
                disabled={deleteBusy}
                onClick={() => {
                  setShowDeleteAccount(false);
                  setDeletePhrase("");
                  setDeleteErr(null);
                }}
              >
                {tp("cancel")}
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}
