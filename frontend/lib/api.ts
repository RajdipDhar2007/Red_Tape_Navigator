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

export function setTokens(access: string, refresh: string): void {
  store()?.setItem(ACCESS, access);
  store()?.setItem(REFRESH, refresh);
}
export function clearTokens(): void {
  store()?.removeItem(ACCESS);
  store()?.removeItem(REFRESH);
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
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
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
