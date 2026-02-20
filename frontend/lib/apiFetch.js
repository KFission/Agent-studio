/**
 * Authenticated fetch wrapper.
 * Automatically injects the Bearer token from the auth store into every request.
 * Falls back to standard fetch if no token is available (public endpoints).
 *
 * Usage:  import apiFetch from "@/lib/apiFetch";
 *         apiFetch(`${API}/models`).then(r => r.json())...
 */

const STORAGE_KEY = "jai_auth_session";

function getSession() {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export default function apiFetch(url, options = {}) {
  const session = getSession();
  const token = session?.user?.accessToken || null;
  const displayName = session?.user?.displayName || null;
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (displayName) {
    headers["X-User-Display-Name"] = displayName;
  }
  return fetch(url, { ...options, headers });
}
