import { create } from "zustand";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

function apiFetch(url, opts = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("jai_token") : null;
  return fetch(url, { ...opts, headers: { ...opts.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}), "Content-Type": "application/json" } });
}

// ═══════════════════════════════════════════════════════════════════
// Environment definitions (visual config — backend is source of truth)
// ═══════════════════════════════════════════════════════════════════

export const ENVIRONMENTS = [
  { id: "dev", label: "Dev", color: "#64748b", bg: "bg-slate-100", text: "text-slate-700", border: "border-slate-300", dot: "bg-slate-400", description: "Development — build & iterate freely" },
  { id: "qa", label: "QA", color: "#f59e0b", bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-300", dot: "bg-amber-400", description: "Quality Assurance — automated tests & review" },
  { id: "uat", label: "UAT", color: "#3b82f6", bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-300", dot: "bg-blue-400", description: "User Acceptance Testing — stakeholder validation" },
  { id: "prod", label: "Prod", color: "#10b981", bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-300", dot: "bg-emerald-500", description: "Production — live deployment" },
];

export const ENV_MAP = Object.fromEntries(ENVIRONMENTS.map((e) => [e.id, e]));

// ═══════════════════════════════════════════════════════════════════
// Per-environment permissions (gated by user role)
// In production this would come from the backend / Keycloak
// ═══════════════════════════════════════════════════════════════════

const DEFAULT_PERMISSIONS = {
  dev:  { canView: true, canEdit: true },
  qa:   { canView: true, canEdit: true },
  uat:  { canView: true, canEdit: true },
  prod: { canView: true, canEdit: false },
};

// ═══════════════════════════════════════════════════════════════════
// Zustand store — backend-enforced environments
// ═══════════════════════════════════════════════════════════════════

const useEnvStore = create((set, get) => ({
  // Current environment
  currentEnv: "dev",
  
  // Permission map per environment
  permissions: { ...DEFAULT_PERMISSIONS },
  
  // Dirty state tracking (unsaved changes)
  isDirty: false,
  dirtyAssetId: null,
  
  // Pending switch (when dirty, we store where user wants to go)
  pendingEnvSwitch: null,
  
  // Prod edit confirmation
  showProdConfirm: false,
  prodConfirmCallback: null,

  // Backend-synced state
  backendEnvs: [],             // environment configs from backend
  promotions: [],              // promotion records
  pendingApprovals: [],        // promotions awaiting approval
  deployedAssets: {},          // { envId: [assets] }
  envVariables: {},            // { envId: { key: varObj } }
  envStats: null,              // aggregate stats
  envLoading: false,
  promotionLoading: false,

  // ── Getters ──────────────────────────────────────────────────────

  getEnvMeta: () => ENV_MAP[get().currentEnv] || ENV_MAP.dev,
  
  getPermissions: (envId) => {
    const env = envId || get().currentEnv;
    return get().permissions[env] || { canView: false, canEdit: false };
  },

  canEdit: (envId) => {
    const env = envId || get().currentEnv;
    // Also check backend lock status
    const beCfg = get().backendEnvs.find(e => e.env_id === env);
    if (beCfg?.is_locked) return false;
    return get().permissions[env]?.canEdit ?? false;
  },

  canView: (envId) => {
    const env = envId || get().currentEnv;
    return get().permissions[env]?.canView ?? false;
  },

  isProd: () => get().currentEnv === "prod",
  isProtectedEnv: () => ["prod", "uat"].includes(get().currentEnv),

  getAssetEnvMeta: (assetId) => {
    // Return real deployed asset info if available, else fallback
    const { currentEnv, deployedAssets } = get();
    const assets = deployedAssets[currentEnv] || [];
    const found = assets.find(a => a.asset_id === assetId);
    if (found) {
      return { version: found.version, lastUpdated: found.deployed_at || new Date().toISOString(), updatedBy: found.deployed_by || "system", available: true };
    }
    // Not deployed in this env
    return { version: 0, lastUpdated: null, updatedBy: "", available: false };
  },

  // ── Local Actions ──────────────────────────────────────────────

  switchEnv: (envId) => {
    const { isDirty, permissions } = get();
    const perm = permissions[envId];
    if (!perm?.canView) return;

    if (isDirty) {
      set({ pendingEnvSwitch: envId });
      return;
    }

    set({ currentEnv: envId, pendingEnvSwitch: null });
  },

  confirmEnvSwitch: () => {
    const { pendingEnvSwitch } = get();
    if (pendingEnvSwitch) {
      set({ currentEnv: pendingEnvSwitch, pendingEnvSwitch: null, isDirty: false, dirtyAssetId: null });
    }
  },

  cancelEnvSwitch: () => {
    set({ pendingEnvSwitch: null });
  },

  setDirty: (assetId) => {
    set({ isDirty: true, dirtyAssetId: assetId || "unknown" });
  },

  clearDirty: () => {
    set({ isDirty: false, dirtyAssetId: null });
  },

  // Prod edit guard
  requestProdEdit: (callback) => {
    if (get().currentEnv === "prod") {
      set({ showProdConfirm: true, prodConfirmCallback: callback });
    } else if (callback) {
      callback();
    }
  },

  confirmProdEdit: () => {
    const cb = get().prodConfirmCallback;
    set({ showProdConfirm: false, prodConfirmCallback: null });
    if (cb) cb();
  },

  cancelProdEdit: () => {
    set({ showProdConfirm: false, prodConfirmCallback: null });
  },

  setPermissions: (perms) => {
    set({ permissions: { ...DEFAULT_PERMISSIONS, ...perms } });
  },

  // ── Backend API Actions ────────────────────────────────────────

  fetchEnvironments: async () => {
    set({ envLoading: true });
    try {
      const r = await apiFetch(`${API}/environments`);
      const data = await r.json();
      set({ backendEnvs: data.environments || [], envLoading: false });
    } catch { set({ envLoading: false }); }
  },

  fetchEnvVariables: async (envId) => {
    try {
      const r = await apiFetch(`${API}/environments/${envId}/variables`);
      const data = await r.json();
      set(s => ({ envVariables: { ...s.envVariables, [envId]: data } }));
    } catch {}
  },

  fetchDeployedAssets: async (envId) => {
    try {
      const r = await apiFetch(`${API}/environments/${envId}/assets`);
      const data = await r.json();
      set(s => ({ deployedAssets: { ...s.deployedAssets, [envId]: Array.isArray(data) ? data : (data.assets || []) } }));
    } catch {}
  },

  fetchPromotions: async (envId, status) => {
    set({ promotionLoading: true });
    try {
      let url = `${API}/environments/promotions?`;
      if (envId) url += `env_id=${envId}&`;
      if (status) url += `status=${status}&`;
      const r = await apiFetch(url);
      const data = await r.json();
      const promos = data.promotions || [];
      set({ promotions: promos, promotionLoading: false });
      if (!status) {
        set({ pendingApprovals: promos.filter(p => p.status === "pending") });
      }
    } catch { set({ promotionLoading: false }); }
  },

  fetchEnvStats: async () => {
    try {
      const r = await apiFetch(`${API}/environments/stats`);
      const data = await r.json();
      set({ envStats: data });
    } catch {}
  },

  requestPromotion: async ({ assetType, assetId, assetName, fromEnv, toEnv, configJson, fromVersion }) => {
    try {
      const r = await apiFetch(`${API}/environments/promotions`, {
        method: "POST",
        body: JSON.stringify({
          asset_type: assetType, asset_id: assetId, asset_name: assetName,
          from_env: fromEnv, to_env: toEnv, config_json: configJson || {},
          from_version: fromVersion || 0, requested_by: "admin",
        }),
      });
      if (!r.ok) { const err = await r.json(); throw new Error(err.detail || "Promotion failed"); }
      const data = await r.json();
      // Refresh promotions
      get().fetchPromotions();
      return data;
    } catch (e) { throw e; }
  },

  approvePromotion: async (promotionId) => {
    try {
      const r = await apiFetch(`${API}/environments/promotions/${promotionId}/approve?approved_by=admin`, { method: "POST" });
      if (!r.ok) throw new Error("Approve failed");
      const data = await r.json();
      get().fetchPromotions();
      return data;
    } catch (e) { throw e; }
  },

  rejectPromotion: async (promotionId, reason) => {
    try {
      const r = await apiFetch(`${API}/environments/promotions/${promotionId}/reject?rejected_by=admin&reason=${encodeURIComponent(reason || "")}`, { method: "POST" });
      if (!r.ok) throw new Error("Reject failed");
      const data = await r.json();
      get().fetchPromotions();
      return data;
    } catch (e) { throw e; }
  },

  rollbackPromotion: async (promotionId) => {
    try {
      const r = await apiFetch(`${API}/environments/promotions/${promotionId}/rollback?rolled_back_by=admin`, { method: "POST" });
      if (!r.ok) throw new Error("Rollback failed");
      const data = await r.json();
      get().fetchPromotions();
      return data;
    } catch (e) { throw e; }
  },

  lockEnvironment: async (envId) => {
    try {
      await apiFetch(`${API}/environments/${envId}/lock?locked_by=admin`, { method: "POST" });
      get().fetchEnvironments();
    } catch {}
  },

  unlockEnvironment: async (envId) => {
    try {
      await apiFetch(`${API}/environments/${envId}/unlock`, { method: "POST" });
      get().fetchEnvironments();
    } catch {}
  },

  diffEnvironments: async (envA, envB, assetType) => {
    try {
      let url = `${API}/environments/diff/${envA}/${envB}?`;
      if (assetType) url += `asset_type=${assetType}&`;
      const r = await apiFetch(url);
      return await r.json();
    } catch { return null; }
  },
}));

export default useEnvStore;
