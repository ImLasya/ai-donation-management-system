// Centralized API client. Switches between mock and real backend via env.
const rawBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
const BASE_URL = rawBase.endsWith("/api") ? rawBase : `${rawBase}/api`;
export const MOCK_MODE = (import.meta.env.VITE_ENABLE_MOCK_API ?? "true") === "true";
export const APP_NAME = import.meta.env.VITE_APP_NAME ?? "Donate";

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("da_token") : null;
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  // Destructure headers out of options so the spread below doesn't overwrite the merged headers
  const { headers: callerHeaders, ...restOptions } = options;

  const res = await fetch(`${BASE_URL}${path}`, {
    ...restOptions,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...(callerHeaders as Record<string, string> ?? {}),
    },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
