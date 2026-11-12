"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { formatDate } from "@/lib/format";
import {
  api,
  apiBlob,
  ApiError,
  del,
  formatFileSize,
  hasToken,
  uploadForm,
  validateVaultFile,
  VAULT_DEFAULT_MAX_BYTES,
} from "@/lib/api";
import Icon from "./Icon";

type DocumentItem = {
  id: string;
  user_id: string;
  workspace_id: string | null;
  session_id: string | null;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  checksum: string;
  category: string;
  scan_status: string;
  created_at: string;
  updated_at: string;
};

type DocumentListResponse = {
  items: DocumentItem[];
  total: number;
  limit: number;
  offset: number;
  max_upload_bytes: number;
  allowed_content_types: string[];
  scan_mode: string;
};

const CATEGORIES = ["general", "identity", "premises", "business", "licence"] as const;

export default function DocumentsView() {
  const t = useTranslations("documents");
  const locale = useLocale();
  const categorySelectId = useId();
  const fileInputId = useId();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [docs, setDocs] = useState<DocumentItem[] | null>(null);
  const [maxBytes, setMaxBytes] = useState<number>(VAULT_DEFAULT_MAX_BYTES);
  const [scanMode, setScanMode] = useState<string>("disabled");
  const [category, setCategory] = useState<string>("general");
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    if (!hasToken()) {
      setSignedIn(false);
      setDocs([]);
      return;
    }
    setSignedIn(true);
    try {
      const res = await api<DocumentListResponse>("/documents?limit=50&offset=0");
      setDocs(res.items);
      if (res.max_upload_bytes) setMaxBytes(res.max_upload_bytes);
      if (res.scan_mode) setScanMode(res.scan_mode);
    } catch {
      setError(t("loadError"));
      setDocs([]);
    }
  }, [t]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const handleUploadFile = async (file: File) => {
    setError(null);
    setSuccessMsg(null);
    const check = validateVaultFile(file, maxBytes);
    if (!check.ok) {
      if (check.code === "empty") setError(t("errEmpty"));
      else if (check.code === "too_large") {
        setError(t("errTooLarge", { max: formatFileSize(maxBytes) }));
      } else {
        setError(t("errUnsupported"));
      }
      return;
    }

    setUploading(true);
    setProgress(0);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("category", category);
      const created = await uploadForm<DocumentItem>("/documents", formData, (pct) => {
        setProgress(pct);
      });
      setDocs((prev) => [created, ...(prev ?? [])]);
      setSuccessMsg(t("uploadSuccess", { name: created.original_filename }));
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.code === "file_too_large" || e.status === 413) {
          setError(t("errTooLarge", { max: formatFileSize(maxBytes) }));
        } else if (
          e.code === "unsupported_content_type" ||
          e.code === "invalid_file_extension" ||
          e.code === "file_signature_mismatch"
        ) {
          setError(t("errUnsupported"));
        } else if (e.code === "empty_file") {
          setError(t("errEmpty"));
        } else if (e.code === "malware_detected") {
          setError(t("errMalware"));
        } else {
          setError(t("uploadError"));
        }
      } else {
        setError(t("uploadError"));
      }
    } finally {
      setUploading(false);
      setProgress(null);
    }
  };

  const handleDownload = async (doc: DocumentItem) => {
    setError(null);
    setDownloadingId(doc.id);
    try {
      const blob = await apiBlob(`/documents/${doc.id}/download`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.original_filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError(t("downloadError"));
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDelete = async (docId: string) => {
    setError(null);
    setSuccessMsg(null);
    setDeletingId(docId);
    try {
      await del(`/documents/${docId}`);
      setDocs((prev) => (prev ? prev.filter((d) => d.id !== docId) : []));
      setConfirmDeleteId(null);
      setSuccessMsg(t("deleteSuccess"));
    } catch {
      setError(t("deleteError"));
    } finally {
      setDeletingId(null);
    }
  };

  const formatTypeBadge = (contentType: string) => {
    if (contentType === "application/pdf") return "PDF";
    if (contentType === "image/png") return "PNG";
    if (contentType === "image/jpeg") return "JPEG";
    return contentType;
  };

  if (signedIn === false) {
    return (
      <section className="card mx-auto max-w-xl">
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        <p className="mt-2 text-slate-700">{t("signin")}</p>
      </section>
    );
  }

  return (
    <div className="space-y-8">
      <section className="card border-t-4 border-t-saffron-500 space-y-4 animate-fade-up" aria-labelledby="vault-h">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 id="vault-h" className=" flex items-center gap-2 text-2xl font-bold sm:text-3xl">
              <Icon name="lock" className="text-navy-700" /> {t("title")}
            </h1>
            <p className="mt-1 text-slate-700">{t("intro")}</p>
          </div>
          <span className="badge bg-indgreen-100 text-indgreen-800">
            <Icon name="shield" size={16} /> {t("privateBadge")}
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-[220px_1fr] sm:items-end">
          <div>
            <label htmlFor={categorySelectId} className="block text-sm font-semibold text-navy-900">
              {t("categoryLabel")}
            </label>
            <select
              id={categorySelectId}
              className="input mt-1"
              value={category}
              disabled={uploading}
              onChange={(e) => setCategory(e.target.value)}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {t(`cat_${c}`)}
                </option>
              ))}
            </select>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (!uploading) setDragActive(true);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setDragActive(false);
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setDragActive(false);
              if (uploading) return;
              const f = e.dataTransfer.files?.[0];
              if (f) void handleUploadFile(f);
            }}
            className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-5 text-center transition ${
              dragActive
                ? "border-navy-700 bg-navy-50"
                : "border-slate-300 bg-slate-50/70 hover:border-navy-400"
            }`}
          >
            <input
              ref={fileInputRef}
              id={fileInputId}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
              className="sr-only"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void handleUploadFile(f);
              }}
            />
            <Icon name="file" size={28} className="mb-2 text-navy-700" />
            <p className="text-sm font-medium text-navy-900">{t("dropHint")}</p>
            <p className="mt-1 text-xs text-slate-600">
              {t("guidance", { max: formatFileSize(maxBytes) })}
            </p>
            <label
              htmlFor={fileInputId}
              className={`btn-accent mt-3 cursor-pointer !py-2 text-sm ${uploading ? "pointer-events-none opacity-60" : ""}`}
            >
              {uploading ? t("uploading") : t("uploadBtn")}
            </label>
          </div>
        </div>

        {progress !== null && (
          <div className="space-y-1" aria-live="polite">
            <div className="flex justify-between text-xs font-semibold text-navy-800">
              <span>{t("uploading")}</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full bg-indgreen-600 transition-all duration-150"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {scanMode === "disabled" && (
          <p className="text-xs text-slate-600">
            {t("scanNoticeDisabled")}
          </p>
        )}

        {error && (
          <p role="alert" className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-900">
            <Icon name="alert" size={18} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </p>
        )}

        {successMsg && (
          <p role="status" className="flex items-center gap-2 rounded-lg bg-indgreen-50 p-3 text-sm text-indgreen-900">
            <Icon name="check" size={18} className="shrink-0" />
            <span>{successMsg}</span>
          </p>
        )}
      </section>

      <section aria-labelledby="vault-list-h" className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 id="vault-list-h" className="text-xl font-bold">
            {t("listHeading")}
          </h2>
          {docs && docs.length > 0 && (
            <span className="text-sm font-medium text-slate-600">
              {t("countLabel", { count: docs.length })}
            </span>
          )}
        </div>

        {docs === null ? (
          <p aria-live="polite" className="card text-slate-700">
            {t("loading")}
          </p>
        ) : docs.length === 0 ? (
          <div className="card text-center py-8 space-y-2">
            <p className="font-semibold text-navy-900">{t("emptyTitle")}</p>
            <p className="text-sm text-slate-600">{t("emptyHelp")}</p>
          </div>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {docs.map((doc) => (
              <li key={doc.id} className="card flex flex-col justify-between gap-3">
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="badge bg-navy-100 text-navy-800">
                      {formatTypeBadge(doc.content_type)}
                    </span>
                    <span className="badge bg-slate-100 text-slate-700">
                      {t(
                        CATEGORIES.includes(doc.category as (typeof CATEGORIES)[number])
                          ? `cat_${doc.category as (typeof CATEGORIES)[number]}`
                          : "cat_general",
                      )}
                    </span>
                  </div>
                  <p className="break-all font-semibold text-navy-900">{doc.original_filename}</p>
                  <p className="text-xs text-slate-600">
                    {formatFileSize(doc.size_bytes)} · {formatDate(doc.created_at, locale)} · SHA-256{" "}
                    <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px]">
                      {doc.checksum.slice(0, 12)}…
                    </code>
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                  <button
                    type="button"
                    className="btn-secondary !min-h-0 py-1.5 px-3 text-sm"
                    disabled={downloadingId === doc.id}
                    onClick={() => void handleDownload(doc)}
                  >
                    <Icon name="file" size={16} />{" "}
                    {downloadingId === doc.id ? t("downloading") : t("downloadBtn")}
                  </button>

                  {confirmDeleteId !== doc.id && (
                    <button
                      type="button"
                      className="btn-ghost text-red-800 !min-h-0 py-1.5 text-sm"
                      onClick={() => setConfirmDeleteId(doc.id)}
                    >
                      {t("deleteBtn")}
                    </button>
                  )}
                </div>

                {confirmDeleteId === doc.id && (
                  <div className="rounded-lg bg-red-50 p-2.5 text-sm text-red-900">
                    <p className="mb-2">{t("deleteWarn", { name: doc.original_filename })}</p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="btn bg-red-700 hover:bg-red-800 text-white !min-h-0 py-1 text-xs"
                        disabled={deletingId === doc.id}
                        onClick={() => void handleDelete(doc.id)}
                      >
                        {deletingId === doc.id ? t("deleting") : t("deleteConfirmBtn")}
                      </button>
                      <button
                        type="button"
                        className="btn-ghost !min-h-0 py-1 text-xs"
                        disabled={deletingId === doc.id}
                        onClick={() => setConfirmDeleteId(null)}
                      >
                        {t("cancelBtn")}
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

