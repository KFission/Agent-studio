"use client";
import { useState, useRef, useEffect } from "react";
import { cn } from "../lib/cn";
import useEnvStore, { ENVIRONMENTS, ENV_MAP } from "../stores/envStore";
import {
  ChevronDown, Lock, AlertTriangle, X, Shield, ArrowRight,
  Clock, User, Tag, Info, CheckCircle2, XCircle, RotateCcw,
  Loader2, GitCompare, History, Unlock,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════
// EnvBadge — small inline badge showing environment name + color
// ═══════════════════════════════════════════════════════════════════

export function EnvBadge({ envId, size = "sm", className }) {
  const meta = ENV_MAP[envId];
  if (!meta) return null;
  const sizes = {
    xs: "text-[11px] px-1.5 py-0",
    sm: "text-[11px] px-2 py-0.5",
    md: "text-xs px-2.5 py-1",
  };
  return (
    <span className={cn(
      "inline-flex items-center gap-1 font-semibold rounded-full border uppercase tracking-wider",
      meta.bg, meta.text, meta.border, sizes[size] || sizes.sm, className
    )}>
      <span className={cn("w-1.5 h-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════
// EnvVersionMeta — shows version/timestamp/author for current env
// ═══════════════════════════════════════════════════════════════════

export function EnvVersionMeta({ assetId, className }) {
  const { currentEnv, getAssetEnvMeta } = useEnvStore();
  const meta = getAssetEnvMeta(assetId);
  if (!meta || !meta.available) return null;
  const envDef = ENV_MAP[currentEnv];

  return (
    <div className={cn("flex items-center gap-3 text-[11px] text-slate-400 flex-wrap", className)}>
      <span className="flex items-center gap-1">
        <Tag size={10} />
        v{meta.version}
      </span>
      <span className="flex items-center gap-1">
        <Clock size={10} />
        {new Date(meta.lastUpdated).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
      </span>
      <span className="flex items-center gap-1">
        <User size={10} />
        {meta.updatedBy}
      </span>
      <EnvBadge envId={currentEnv} size="xs" />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// NotAvailableInEnv — shown when asset doesn't exist in target env
// ═══════════════════════════════════════════════════════════════════

export function NotAvailableInEnv({ assetType = "asset", onPromote }) {
  const { currentEnv } = useEnvStore();
  const meta = ENV_MAP[currentEnv];
  const prevEnv = ENVIRONMENTS[ENVIRONMENTS.findIndex(e => e.id === currentEnv) - 1];

  return (
    <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-xl py-12 px-6 text-center">
      <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-4">
        <Info size={24} />
      </div>
      <div className="text-base font-semibold text-slate-900">
        Not available in {meta?.label}
      </div>
      <div className="text-sm text-slate-500 mt-2 max-w-[440px]">
        This {assetType} has not been promoted to the <strong>{meta?.label}</strong> environment yet.
        {prevEnv && (
          <> It exists in <strong>{prevEnv.label}</strong> — promote it to make it available here.</>
        )}
      </div>
      {prevEnv && onPromote && (
        <button
          onClick={onPromote}
          className="mt-5 flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"
        >
          <ArrowRight size={14} /> Promote from {prevEnv.label}
        </button>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// ProdWarningBanner — persistent banner when in Prod
// ═══════════════════════════════════════════════════════════════════

export function ProdWarningBanner() {
  const { currentEnv, canEdit } = useEnvStore();
  if (currentEnv !== "prod") return null;

  return (
    <div className="bg-red-50 border-b border-red-200 px-4 py-2 flex items-center gap-2 shrink-0">
      <AlertTriangle size={14} className="text-red-500 shrink-0" />
      <span className="text-xs font-medium text-red-700">
        Production Environment
      </span>
      <span className="text-xs text-red-500">
        {canEdit("prod")
          ? "— Changes here affect live systems. Proceed with caution."
          : "— View-only mode. You do not have edit permissions for Production."}
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// UatWarningBanner — subtle banner when in UAT
// ═══════════════════════════════════════════════════════════════════

export function UatWarningBanner() {
  const { currentEnv } = useEnvStore();
  if (currentEnv !== "uat") return null;

  return (
    <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 flex items-center gap-2 shrink-0">
      <Shield size={14} className="text-blue-500 shrink-0" />
      <span className="text-xs font-medium text-blue-700">
        UAT Environment
      </span>
      <span className="text-xs text-blue-500">
        — Changes require stakeholder sign-off before promotion to Production.
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// UnsavedChangesDialog — modal when switching env with dirty state
// ═══════════════════════════════════════════════════════════════════

export function UnsavedChangesDialog() {
  const { pendingEnvSwitch, confirmEnvSwitch, cancelEnvSwitch } = useEnvStore();
  if (!pendingEnvSwitch) return null;
  const target = ENV_MAP[pendingEnvSwitch];

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center gap-3">
          <AlertTriangle size={18} className="text-amber-500" />
          <h3 className="text-base font-semibold text-slate-900">Unsaved Changes</h3>
        </div>
        <div className="px-6 py-5">
          <p className="text-sm text-slate-600">
            You have unsaved changes. Switching to <strong>{target?.label}</strong> will discard them.
          </p>
          <p className="text-sm text-slate-500 mt-2">Do you want to continue?</p>
        </div>
        <div className="px-6 py-3 border-t border-slate-100 flex justify-end gap-2">
          <button
            onClick={cancelEnvSwitch}
            className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 cursor-pointer hover:bg-slate-50 transition"
          >
            Stay & Keep Editing
          </button>
          <button
            onClick={confirmEnvSwitch}
            className="px-4 py-2 bg-jai-primary text-white rounded-lg text-sm font-medium cursor-pointer hover:bg-jai-primary-hover transition"
          >
            Discard & Switch
          </button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// ProdEditConfirmDialog — confirmation before editing in Prod
// ═══════════════════════════════════════════════════════════════════

export function ProdEditConfirmDialog() {
  const { showProdConfirm, confirmProdEdit, cancelProdEdit } = useEnvStore();
  if (!showProdConfirm) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="px-6 py-4 border-b border-red-100 bg-red-50 flex items-center gap-3">
          <AlertTriangle size={18} className="text-red-500" />
          <h3 className="text-base font-semibold text-red-900">Edit Production Asset</h3>
        </div>
        <div className="px-6 py-5">
          <p className="text-sm text-slate-600">
            You are about to edit a <strong>Production</strong> asset. Changes will affect live systems immediately.
          </p>
          <p className="text-sm text-slate-500 mt-2">
            Are you sure you want to proceed?
          </p>
        </div>
        <div className="px-6 py-3 border-t border-slate-100 flex justify-end gap-2">
          <button
            onClick={cancelProdEdit}
            className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 cursor-pointer hover:bg-slate-50 transition"
          >
            Cancel
          </button>
          <button
            onClick={confirmProdEdit}
            className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium cursor-pointer hover:bg-red-700 transition"
          >
            Yes, Edit Production
          </button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// PromotionPanel — approval queue, history, env diff, lock controls
// ═══════════════════════════════════════════════════════════════════

export function PromotionPanel() {
  const {
    currentEnv, backendEnvs, promotions, pendingApprovals, promotionLoading,
    fetchEnvironments, fetchPromotions, approvePromotion, rejectPromotion,
    rollbackPromotion, lockEnvironment, unlockEnvironment, diffEnvironments,
  } = useEnvStore();

  const [tab, setTab] = useState("pending");
  const [actionLoading, setActionLoading] = useState(null);
  const [rejectId, setRejectId] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [diffResult, setDiffResult] = useState(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffEnvA, setDiffEnvA] = useState("dev");
  const [diffEnvB, setDiffEnvB] = useState("qa");

  useEffect(() => { fetchEnvironments(); fetchPromotions(); }, []);

  const handleApprove = async (id) => {
    setActionLoading(id);
    try { await approvePromotion(id); } catch {}
    setActionLoading(null);
  };
  const handleReject = async (id) => {
    setActionLoading(id);
    try { await rejectPromotion(id, rejectReason); setRejectId(null); setRejectReason(""); } catch {}
    setActionLoading(null);
  };
  const handleRollback = async (id) => {
    setActionLoading(id);
    try { await rollbackPromotion(id); } catch {}
    setActionLoading(null);
  };
  const handleDiff = async () => {
    setDiffLoading(true);
    const result = await diffEnvironments(diffEnvA, diffEnvB);
    setDiffResult(result);
    setDiffLoading(false);
  };

  const statusColors = {
    pending: "bg-amber-50 text-amber-700 border-amber-200",
    approved: "bg-blue-50 text-blue-700 border-blue-200",
    deployed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    rejected: "bg-red-50 text-red-700 border-red-200",
    rolled_back: "bg-slate-100 text-slate-600 border-slate-200",
  };

  const tabs = [
    { id: "pending", label: "Pending", count: pendingApprovals.length },
    { id: "history", label: "History" },
    { id: "diff", label: "Env Diff" },
    { id: "locks", label: "Locks" },
  ];

  const displayPromos = tab === "pending"
    ? promotions.filter(p => p.status === "pending")
    : promotions;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={cn("px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition border",
              tab === t.id ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50")}>
            {t.label}{t.count > 0 ? ` (${t.count})` : ""}
          </button>
        ))}
        <div className="flex-1" />
        <button onClick={() => fetchPromotions()} className="text-xs text-slate-400 hover:text-slate-700 cursor-pointer flex items-center gap-1">
          <RotateCcw size={11} /> Refresh
        </button>
      </div>

      {/* Pending / History tab */}
      {(tab === "pending" || tab === "history") && (
        <>
          {promotionLoading ? (
            <div className="text-sm text-slate-400 py-6 text-center"><Loader2 size={14} className="inline animate-spin mr-1" /> Loading...</div>
          ) : displayPromos.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
              <CheckCircle2 size={28} className="mx-auto text-slate-300 mb-2" />
              <div className="text-sm text-slate-500 font-medium">{tab === "pending" ? "No pending approvals" : "No promotion history"}</div>
            </div>
          ) : (
            <div className="space-y-2">
              {displayPromos.map(p => (
                <div key={p.promotion_id} className="bg-white border border-slate-200 rounded-xl p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-slate-900">{p.asset_name || p.asset_id}</span>
                        <span className={cn("text-[11px] px-1.5 py-0.5 rounded-full border font-medium", statusColors[p.status] || statusColors.pending)}>{p.status}</span>
                        <span className="text-[11px] text-slate-400">{p.asset_type}</span>
                      </div>
                      <div className="text-xs text-slate-500 mt-1 flex items-center gap-2">
                        <EnvBadge envId={p.from_env} size="xs" />
                        <ArrowRight size={10} className="text-slate-400" />
                        <EnvBadge envId={p.to_env} size="xs" />
                        <span className="text-slate-300">·</span>
                        <span>by {p.requested_by}</span>
                        {p.created_at && <span className="text-slate-300">· {new Date(p.created_at).toLocaleDateString()}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {p.status === "pending" && (
                        <>
                          <button onClick={() => handleApprove(p.promotion_id)}
                            disabled={actionLoading === p.promotion_id}
                            className="flex items-center gap-1 text-xs text-emerald-600 border border-emerald-200 rounded-lg px-2.5 py-1.5 cursor-pointer hover:bg-emerald-50 transition">
                            {actionLoading === p.promotion_id ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />} Approve
                          </button>
                          <button onClick={() => setRejectId(rejectId === p.promotion_id ? null : p.promotion_id)}
                            className="flex items-center gap-1 text-xs text-red-500 border border-red-200 rounded-lg px-2.5 py-1.5 cursor-pointer hover:bg-red-50 transition">
                            <XCircle size={11} /> Reject
                          </button>
                        </>
                      )}
                      {p.status === "deployed" && (
                        <button onClick={() => handleRollback(p.promotion_id)}
                          disabled={actionLoading === p.promotion_id}
                          className="flex items-center gap-1 text-xs text-amber-600 border border-amber-200 rounded-lg px-2.5 py-1.5 cursor-pointer hover:bg-amber-50 transition">
                          {actionLoading === p.promotion_id ? <Loader2 size={11} className="animate-spin" /> : <RotateCcw size={11} />} Rollback
                        </button>
                      )}
                    </div>
                  </div>
                  {/* Reject reason input */}
                  {rejectId === p.promotion_id && (
                    <div className="mt-3 flex items-center gap-2">
                      <input value={rejectReason} onChange={e => setRejectReason(e.target.value)}
                        placeholder="Rejection reason (optional)..."
                        className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs outline-none" />
                      <button onClick={() => handleReject(p.promotion_id)}
                        disabled={actionLoading === p.promotion_id}
                        className="text-xs text-white bg-red-500 rounded-lg px-3 py-1.5 cursor-pointer hover:bg-red-600">Confirm Reject</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Env Diff tab */}
      {tab === "diff" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <select value={diffEnvA} onChange={e => setDiffEnvA(e.target.value)}
              className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs outline-none">
              {ENVIRONMENTS.map(e => <option key={e.id} value={e.id}>{e.label}</option>)}
            </select>
            <ArrowRight size={14} className="text-slate-400 shrink-0" />
            <select value={diffEnvB} onChange={e => setDiffEnvB(e.target.value)}
              className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs outline-none">
              {ENVIRONMENTS.map(e => <option key={e.id} value={e.id}>{e.label}</option>)}
            </select>
            <button onClick={handleDiff} disabled={diffLoading || diffEnvA === diffEnvB}
              className={cn("flex items-center gap-1 text-xs font-medium text-white bg-slate-800 rounded-lg px-3 py-2 cursor-pointer hover:bg-slate-900 transition",
                (diffLoading || diffEnvA === diffEnvB) && "opacity-50 cursor-not-allowed")}>
              {diffLoading ? <Loader2 size={11} className="animate-spin" /> : <GitCompare size={11} />} Compare
            </button>
          </div>
          {diffResult && (
            <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-3 text-xs flex-wrap">
                <span className="font-semibold text-slate-900">{diffResult.env_a?.toUpperCase()} vs {diffResult.env_b?.toUpperCase()}</span>
                <span className="text-slate-400">·</span>
                {diffResult[`only_in_${diffResult.env_a}`]?.length > 0 && (
                  <span className="text-amber-600">Only in {diffResult.env_a?.toUpperCase()}: {diffResult[`only_in_${diffResult.env_a}`].length}</span>
                )}
                {diffResult[`only_in_${diffResult.env_b}`]?.length > 0 && (
                  <span className="text-blue-600">Only in {diffResult.env_b?.toUpperCase()}: {diffResult[`only_in_${diffResult.env_b}`].length}</span>
                )}
                {diffResult.different?.length > 0 && (
                  <span className="text-red-600">Different: {diffResult.different.length}</span>
                )}
                <span className="text-emerald-600">Identical: {diffResult.identical || 0}</span>
              </div>
              {diffResult.different?.length > 0 && (
                <div className="space-y-1">
                  {diffResult.different.map((d, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2 text-xs">
                      <span className="font-medium text-slate-700">{d.asset}</span>
                      <span className="text-slate-500">v{d.version_a} → v{d.version_b}</span>
                    </div>
                  ))}
                </div>
              )}
              {(diffResult[`only_in_${diffResult.env_a}`]?.length === 0 && diffResult[`only_in_${diffResult.env_b}`]?.length === 0 && diffResult.different?.length === 0) && (
                <div className="text-xs text-slate-400 text-center py-4">Environments are in sync</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Locks tab */}
      {tab === "locks" && (
        <div className="space-y-2">
          {ENVIRONMENTS.map(env => {
            const beCfg = backendEnvs.find(e => e.env_id === env.id);
            const locked = beCfg?.is_locked;
            return (
              <div key={env.id} className="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={cn("w-2.5 h-2.5 rounded-full", env.dot)} />
                  <div>
                    <div className="text-sm font-medium text-slate-900">{env.label}</div>
                    <div className="text-[11px] text-slate-500">
                      {locked ? `Locked by ${beCfg.locked_by || "admin"}` : "Unlocked — editable"}
                    </div>
                  </div>
                </div>
                <button onClick={() => locked ? unlockEnvironment(env.id) : lockEnvironment(env.id)}
                  className={cn("flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border cursor-pointer transition",
                    locked ? "text-emerald-600 border-emerald-200 hover:bg-emerald-50" : "text-red-500 border-red-200 hover:bg-red-50")}>
                  {locked ? <><Unlock size={11} /> Unlock</> : <><Lock size={11} /> Lock</>}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// GlobalEnvSwitcher — the persistent dropdown in the top header
// ═══════════════════════════════════════════════════════════════════

export default function GlobalEnvSwitcher() {
  const { currentEnv, switchEnv, permissions, backendEnvs, pendingApprovals, fetchEnvironments, fetchPromotions } = useEnvStore();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const current = ENV_MAP[currentEnv];

  useEffect(() => {
    fetchEnvironments();
    fetchPromotions();
  }, []);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold cursor-pointer transition",
          current.bg, current.text, current.border,
          "hover:shadow-sm"
        )}
      >
        <span className={cn("w-2 h-2 rounded-full", current.dot)} />
        {current.label}
        {pendingApprovals.length > 0 && (
          <span className="w-4 h-4 rounded-full bg-red-500 text-white text-[11px] font-bold flex items-center justify-center">{pendingApprovals.length}</span>
        )}
        <ChevronDown size={12} className={cn("transition", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 w-72 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="px-3 py-2 border-b border-slate-100">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Switch Environment</div>
          </div>
          {ENVIRONMENTS.map((env) => {
            const perm = permissions[env.id];
            const isCurrent = currentEnv === env.id;
            const beCfg = backendEnvs.find(e => e.env_id === env.id);
            const locked = beCfg?.is_locked;
            const disabled = !perm?.canView;

            return (
              <button
                key={env.id}
                onClick={() => {
                  if (!disabled && !isCurrent) {
                    switchEnv(env.id);
                    setOpen(false);
                  }
                }}
                disabled={disabled}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 text-left transition",
                  isCurrent ? "bg-slate-50" : disabled ? "opacity-40 cursor-not-allowed" : "hover:bg-slate-50 cursor-pointer"
                )}
              >
                <span className={cn("w-2.5 h-2.5 rounded-full shrink-0", env.dot)} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-900">{env.label}</span>
                    {isCurrent && (
                      <span className="text-[11px] bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-full font-semibold">CURRENT</span>
                    )}
                    {locked && <Lock size={10} className="text-red-400" />}
                    {disabled && !locked && <Lock size={11} className="text-slate-400" />}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{env.description}</div>
                  {perm && !disabled && (
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[11px] text-slate-400">
                        {locked ? "Locked" : perm.canEdit ? "View & Edit" : "View only"}
                      </span>
                    </div>
                  )}
                </div>
              </button>
            );
          })}
          {pendingApprovals.length > 0 && (
            <div className="px-3 py-2 border-t border-slate-100 bg-amber-50/50">
              <div className="text-[11px] font-semibold text-amber-700 flex items-center gap-1">
                <AlertTriangle size={10} /> {pendingApprovals.length} pending approval{pendingApprovals.length !== 1 ? "s" : ""}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
