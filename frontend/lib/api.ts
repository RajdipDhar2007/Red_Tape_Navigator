/**
 * Minimal API client. Tokens live in sessionStorage (cleared when the tab closes).
 * Production hardening: move tokens to httpOnly cookies behind a BFF (see docs/ARCHITECTURE.md, Security).
 */
export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ACCESS = "rtn.access";
const REFRESH = "rtn.refresh";

function store(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

export const AUTH_EVENT = "rtn:auth";

function announce(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(AUTH_EVENT));
}

export function setTokens(access: string, refresh: string): void {
  const had = hasToken();
  store()?.setItem(ACCESS, access);
  store()?.setItem(REFRESH, refresh);
  if (!had) announce(); // signed in: let the header load the user without waiting for a page change
}
export function clearTokens(): void {
  const had = hasToken();
  store()?.removeItem(ACCESS);
  store()?.removeItem(REFRESH);
  if (had) announce();
}
export function hasToken(): boolean {
  return !!store()?.getItem(ACCESS);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    const msg = (detail as { message?: unknown } | null | undefined)?.message;
    super(typeof detail === "string" ? detail : typeof msg === "string" ? msg : JSON.stringify(detail));
  }
  get code(): string | undefined {
    const d = this.detail as { code?: string } | undefined;
    return typeof d === "object" && d ? d.code : undefined;
  }
}

async function refresh(): Promise<boolean> {
  const rt = store()?.getItem(REFRESH);
  if (!rt) return false;
  const r = await fetch(`${API}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: rt }),
  });
  if (!r.ok) {
    clearTokens();
    return false;
  }
  const t = await r.json();
  setTokens(t.access_token, t.refresh_token);
  return true;
}

async function raw(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers);
  const at = store()?.getItem(ACCESS);
  if (at) headers.set("Authorization", `Bearer ${at}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  // The server translates plans, rules and checklists into the interface language (Hindi / Bengali).
  if (typeof document !== "undefined" && !headers.has("Accept-Language")) headers.set("Accept-Language", document.documentElement.lang || "en");
  const r = await fetch(`${API}${path}`, { ...init, headers });
  if (r.status === 401 && retry && (await refresh())) return raw(path, init, false);
  return r;
}

export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await raw(path, init);
  if (!r.ok) {
    let detail: unknown = r.statusText;
    try {
      detail = (await r.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(r.status, detail);
  }
  return (r.status === 204 ? undefined : await r.json()) as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  const r = await raw(path);
  if (!r.ok) throw new ApiError(r.status, r.statusText);
  return r.blob();
}

export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = <T = void>(path: string) => api<T>(path, { method: "DELETE" });

export const VAULT_ALLOWED_TYPES = ["application/pdf", "image/png", "image/jpeg"] as const;
export const VAULT_DEFAULT_MAX_BYTES = 5 * 1024 * 1024;

export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function validateVaultFile(
  file: { name: string; type: string; size: number },
  maxBytes: number = VAULT_DEFAULT_MAX_BYTES,
): { ok: true } | { ok: false; code: "empty" | "too_large" | "unsupported" } {
  if (file.size <= 0) return { ok: false, code: "empty" };
  if (file.size > maxBytes) return { ok: false, code: "too_large" };
  const normType = file.type === "image/jpg" ? "image/jpeg" : file.type.toLowerCase();
  const ext = file.name.includes(".") ? `.${file.name.split(".").pop()?.toLowerCase() ?? ""}` : "";
  const validByMime =
    (normType === "application/pdf" && (ext === ".pdf" || ext === "")) ||
    (normType === "image/png" && (ext === ".png" || ext === "")) ||
    (normType === "image/jpeg" && (ext === ".jpg" || ext === ".jpeg" || ext === ""));
  if (!validByMime) return { ok: false, code: "unsupported" };
  return { ok: true };
}

export async function uploadForm<T = unknown>(
  path: string,
  formData: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  if (typeof XMLHttpRequest === "undefined" || !onProgress) {
    return api<T>(path, { method: "POST", body: formData });
  }
  const sendOnce = (token: string | null) =>
    new Promise<{ status: number; body: unknown }>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API}${path}`);
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      if (typeof document !== "undefined") {
        xhr.setRequestHeader("Accept-Language", document.documentElement.lang || "en");
      }
      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable && evt.total > 0) {
          onProgress(Math.min(100, Math.round((evt.loaded / evt.total) * 100)));
        }
      };
      xhr.onload = () => {
        let parsed: unknown = xhr.statusText;
        try {
          parsed = xhr.responseText ? JSON.parse(xhr.responseText) : undefined;
        } catch {
          /* non-JSON body */
        }
        resolve({ status: xhr.status, body: parsed });
      };
      xhr.onerror = () => reject(new ApiError(0, "Network error"));
      xhr.send(formData);
    });

  let res = await sendOnce(store()?.getItem(ACCESS) ?? null);
  if (res.status === 401 && (await refresh())) {
    res = await sendOnce(store()?.getItem(ACCESS) ?? null);
  }
  if (res.status < 200 || res.status >= 300) {
    const detail = (res.body as { detail?: unknown } | undefined)?.detail ?? res.body;
    throw new ApiError(res.status, detail);
  }
  onProgress(100);
  return res.body as T;
}
