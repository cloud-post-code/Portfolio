/**
 * Client-side helpers for the single-secret auth flow.
 * The signed-in password (AUTH_SECRET) lives in sessionStorage and rides along
 * on every API request as `Authorization: Bearer <secret>`.
 */

const KEY = "yap_auth";

export function getStoredSecret(): string | null {
  if (typeof window === "undefined") return null;
  const v = window.sessionStorage.getItem(KEY);
  return v && v.trim() ? v : null;
}

export function setStoredSecret(secret: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(KEY, secret);
}

export function clearStoredSecret(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(KEY);
}

/** fetch wrapper that adds the bearer header when a secret is in sessionStorage. */
export async function authedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const secret = getStoredSecret();
  const headers = new Headers(init.headers ?? {});
  if (secret) headers.set("Authorization", `Bearer ${secret}`);
  return fetch(input, { ...init, headers });
}
