import { create } from "zustand";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const STORAGE_KEY = "jai_auth_session";

// Restore persisted session on load
function getPersistedSession() {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed?.user && parsed?.isAuthenticated) return parsed;
  } catch { /* ignore */ }
  return null;
}

const persisted = getPersistedSession();

const useAuthStore = create((set, get) => ({
  user: persisted?.user || null,
  isAuthenticated: persisted?.isAuthenticated || false,
  isLoading: false,
  error: null,
  rememberMe: persisted ? true : false,

  setRememberMe: (val) => set({ rememberMe: val }),

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Invalid email or password");
      }
      const data = await res.json();
      const displayName = data.display_name || email.split("@")[0].replace(/[._]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      const user = {
        id: data.user_id,
        email: data.email || email,
        username: data.username,
        displayName,
        avatar: displayName.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase(),
        roles: data.roles || ["viewer"],
        accessToken: data.access_token,
      };
      set({ user, isAuthenticated: true, isLoading: false });
      // Persist if Remember Me is checked
      if (get().rememberMe) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ user, isAuthenticated: true })); } catch {}
      }
    } catch (err) {
      const msg = err.message === "Failed to fetch" ? "Invalid username or password" : err.message;
      set({ isLoading: false, error: msg });
    }
  },

  loginWithSSO: async () => {
    set({ error: "Microsoft SSO integration is coming in a future release. Please sign in with email and password." });
  },

  logout: () => {
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
    set({ user: null, isAuthenticated: false, error: null, rememberMe: false });
  },
}));

export default useAuthStore;
