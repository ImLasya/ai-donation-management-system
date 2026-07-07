// Centralized API client. Switches between mock and real backend via env.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
export const MOCK_MODE = (import.meta.env.VITE_ENABLE_MOCK_API ?? "true") === "true";
export const APP_NAME = import.meta.env.VITE_APP_NAME ?? "Donate";

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
