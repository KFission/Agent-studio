"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { cn } from "../../lib/cn";
import {
  Search, Check, X, AlertCircle, Bell, AlertTriangle, ChevronRight,
  Zap, Copy, Play,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

// ═══════════════════════════════════════════════════════════════════
// BADGE
// ═══════════════════════════════════════════════════════════════════

const BADGE_VARIANTS = {
  outline: "bg-white text-slate-500 border-slate-200",
  brand: "bg-jai-primary-light text-jai-primary border-jai-primary-border",
  info: "bg-sky-50 text-sky-600 border-sky-200",
  success: "bg-emerald-50 text-emerald-600 border-emerald-200",
  warning: "bg-amber-50 text-amber-600 border-amber-200",
  danger: "bg-red-50 text-red-600 border-red-200",
  purple: "bg-violet-50 text-violet-600 border-violet-200",
};

function Badge({ children, variant = "outline", className }) {
  return (
    <span className={cn("inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full border", BADGE_VARIANTS[variant] || BADGE_VARIANTS.outline, className)}>
      {children}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════
// SEARCH INPUT
// ═══════════════════════════════════════════════════════════════════

function SearchInput({ value, onChange, placeholder = "Search..." }) {
  return (
    <div className="relative max-w-[360px] w-full">
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-300" size={15} />
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full bg-white border border-slate-200 rounded-lg py-2 pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition placeholder:text-slate-400" />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// EMPTY STATE
// ═══════════════════════════════════════════════════════════════════

function EmptyState({ icon, illustration, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-xl py-12 px-6 text-center">
      {illustration ? (
        <img src={`/illustrations/${illustration}.svg`} alt={title} width={120} height={120} className="mb-4 opacity-80" draggable={false} />
      ) : (
        <div className="w-16 h-16 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-400 mb-4">{icon}</div>
      )}
      <div className="text-base font-semibold text-slate-900">{title}</div>
      <div className="text-sm text-slate-500 mt-2 max-w-[400px]">{description}</div>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// SKELETON
// ═══════════════════════════════════════════════════════════════════

function Skeleton({ className }) {
  return <div className={cn("animate-pulse rounded-lg bg-slate-100", className)} />;
}

function PageSkeleton() {
  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div className="space-y-2"><Skeleton className="h-5 w-40" /><Skeleton className="h-3 w-64" /></div>
        <Skeleton className="h-9 w-32 rounded-lg" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1,2,3].map(i => (
          <div key={i} className="bg-white border border-slate-200/80 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-3"><Skeleton className="w-10 h-10 rounded-xl" /><div className="flex-1 space-y-1.5"><Skeleton className="h-4 w-2/3" /><Skeleton className="h-3 w-full" /></div></div>
            <div className="flex gap-2"><Skeleton className="h-5 w-14 rounded-full" /><Skeleton className="h-5 w-14 rounded-full" /></div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// TOAST NOTIFICATION SYSTEM
// ═══════════════════════════════════════════════════════════════════

let _toastListeners = [];
let _toastId = 0;
const toastStore = { toasts: [], add(t) { const id = ++_toastId; const toast = { id, ...t, createdAt: Date.now() }; this.toasts = [...this.toasts, toast]; _toastListeners.forEach(fn => fn(this.toasts)); setTimeout(() => this.remove(id), t.duration || 4000); return id; }, remove(id) { this.toasts = this.toasts.filter(t => t.id !== id); _toastListeners.forEach(fn => fn(this.toasts)); }, subscribe(fn) { _toastListeners.push(fn); return () => { _toastListeners = _toastListeners.filter(l => l !== fn); }; } };

function toast(message, type = "success") { return toastStore.add({ message, type }); }
toast.success = (msg) => toast(msg, "success");
toast.error = (msg) => toast(msg, "error");
toast.info = (msg) => toast(msg, "info");
toast.warning = (msg) => toast(msg, "warning");

const TOAST_STYLES = { success: "bg-emerald-50 border-emerald-200 text-emerald-800", error: "bg-red-50 border-red-200 text-red-800", info: "bg-sky-50 border-sky-200 text-sky-800", warning: "bg-amber-50 border-amber-200 text-amber-800" };
const TOAST_ICONS = { success: Check, error: AlertCircle, info: Bell, warning: AlertTriangle };

function ToastContainer() {
  const [toasts, setToasts] = useState([]);
  useEffect(() => toastStore.subscribe(setToasts), []);
  if (!toasts.length) return null;
  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map(t => {
        const Icon = TOAST_ICONS[t.type] || Check;
        return (
          <div key={t.id} className={cn("flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-lg text-sm font-medium animate-in slide-in-from-right", TOAST_STYLES[t.type] || TOAST_STYLES.info)}
            style={{ animation: "slideInRight 0.25s ease-out" }}>
            <Icon size={15} className="shrink-0" />
            <span className="flex-1">{t.message}</span>
            <button onClick={() => toastStore.remove(t.id)} className="text-current opacity-40 hover:opacity-70 cursor-pointer"><X size={13} /></button>
          </div>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// CONFIRM DIALOG
// ═══════════════════════════════════════════════════════════════════

let _confirmResolve = null;
let _confirmState = { open: false, title: "", message: "", confirmLabel: "Confirm", variant: "danger" };
let _confirmListeners = [];
function confirmAction({ title, message, confirmLabel = "Delete", variant = "danger" }) {
  return new Promise((resolve) => {
    _confirmResolve = resolve;
    _confirmState = { open: true, title, message, confirmLabel, variant };
    _confirmListeners.forEach(fn => fn({ ..._confirmState }));
  });
}

function ConfirmDialog() {
  const [state, setState] = useState({ open: false });
  useEffect(() => { _confirmListeners.push(setState); return () => { _confirmListeners = _confirmListeners.filter(l => l !== setState); }; }, []);
  if (!state.open) return null;
  const close = (result) => { setState({ open: false }); _confirmResolve?.(result); _confirmResolve = null; };
  const btnClass = state.variant === "danger" ? "bg-red-600 hover:bg-red-700 text-white" : "bg-slate-800 hover:bg-slate-900 text-white";
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => close(false)}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6" onClick={e => e.stopPropagation()}>
        <h3 className="text-base font-semibold text-slate-900">{state.title}</h3>
        <p className="text-sm text-slate-500 mt-2">{state.message}</p>
        <div className="flex justify-end gap-2 mt-6">
          <button onClick={() => close(false)} className="px-4 py-2 text-sm font-medium text-slate-600 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50 transition">Cancel</button>
          <button onClick={() => close(true)} className={cn("px-4 py-2 text-sm font-medium rounded-lg cursor-pointer transition", btnClass)}>{state.confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// TABS & STAT CARD
// ═══════════════════════════════════════════════════════════════════

function Tabs({ tabs, active, onChange }) {
  return (
    <div className="inline-flex bg-slate-100 rounded-lg p-0.5">
      {tabs.map(t => (
        <button key={t} onClick={() => onChange(t)}
          className={cn("px-4 py-1.5 rounded-md text-sm font-medium cursor-pointer border-none transition",
            active === t ? "bg-white text-slate-900 shadow-sm" : "bg-transparent text-slate-500")}>
          {t}
        </button>
      ))}
    </div>
  );
}

function StatCard({ label, value, icon: Icon, trend, className }) {
  const isUp = typeof trend === "string" && trend.startsWith("+");
  const isDown = typeof trend === "string" && trend.startsWith("-");
  return (
    <div className={cn("bg-white border border-slate-200/80 rounded-xl p-4 relative overflow-hidden group hover:shadow-sm transition-shadow", className)}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{label}</span>
        {Icon && <div className="w-7 h-7 rounded-lg bg-slate-50 flex items-center justify-center"><Icon size={14} className="text-slate-400" /></div>}
      </div>
      <div className="text-2xl font-bold text-slate-900 tracking-tight">{value}</div>
      {trend && <div className={cn("text-[11px] font-medium mt-1.5", isUp ? "text-emerald-600" : isDown ? "text-red-500" : "text-slate-400")}>{trend}</div>}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// BREADCRUMBS
// ═══════════════════════════════════════════════════════════════════

function Breadcrumbs({ items }) {
  if (!items || items.length <= 1) return null;
  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-400 px-6 py-2 bg-slate-50/50 border-b border-slate-100">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && <ChevronRight size={10} className="text-slate-300" />}
          {item.onClick ? (
            <button onClick={item.onClick} className="text-slate-500 hover:text-slate-800 cursor-pointer transition">{item.label}</button>
          ) : (
            <span className={i === items.length - 1 ? "text-slate-700 font-medium" : ""}>{item.label}</span>
          )}
        </span>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════

function relativeTime(dateStr) {
  if (!dateStr) return "";
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  if (diff < 0) return "just now";
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return new Date(dateStr).toLocaleDateString();
}

function useAutoResize(ref, value) {
  useEffect(() => {
    if (ref.current) { ref.current.style.height = "auto"; ref.current.style.height = ref.current.scrollHeight + "px"; }
  }, [value, ref]);
}

// ═══════════════════════════════════════════════════════════════════
// API SNIPPET MODAL
// ═══════════════════════════════════════════════════════════════════

function ApiSnippetModal({ type, id, name, onClose }) {
  const [snippet, setSnippet] = useState(null);
  const [lang, setLang] = useState("curl");
  const [copied, setCopied] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (!id) return;
    const endpoint = type === "agent" ? `${API}/agents/${id}/api-snippet` : `${API}/workflows/${id}/api-snippet`;
    fetch(endpoint).then(r => r.json()).then(setSnippet).catch(() => {});
  }, [id, type]);

  const copy = (text) => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  const testInvoke = async () => {
    setTesting(true); setTestResult(null);
    try {
      const endpoint = type === "agent" ? `${API}/agents/${id}/invoke` : `${API}/workflows/${id}/invoke`;
      const body = type === "agent"
        ? { message: "Hello, what can you help me with?", temperature: 0.7, max_tokens: 4096 }
        : { message: "Test invocation", input_data: { query: "test" } };
      const r = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setTestResult(await r.json());
    } catch (e) { setTestResult({ status: "error", error: e.message }); }
    setTesting(false);
  };

  const code = snippet ? (lang === "curl" ? snippet.curl : snippet.python) : "";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between flex-shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <Zap size={16} className="text-amber-500" />
              <span className="text-base font-semibold text-slate-900">API — {type === "agent" ? "Agent" : "Workflow"} as a Service</span>
            </div>
            <div className="text-sm text-slate-500 mt-0.5">{name}</div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-900 hover:bg-slate-100 cursor-pointer"><X size={16} /></button>
        </div>
        {snippet && (
          <div className="px-6 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
            <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 font-semibold">POST</span>
            <span className="text-xs text-slate-600 font-mono">{snippet.endpoint}</span>
            <div className="flex-1" />
            <span className="text-[11px] text-slate-400">Requires API Token (Bearer)</span>
          </div>
        )}
        <div className="px-6 py-3 flex items-center gap-2 border-b border-slate-100 flex-shrink-0">
          <button onClick={() => setLang("curl")} className={cn("px-3 py-1 rounded-md text-xs font-medium cursor-pointer border-none transition", lang === "curl" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600")}>curl</button>
          <button onClick={() => setLang("python")} className={cn("px-3 py-1 rounded-md text-xs font-medium cursor-pointer border-none transition", lang === "python" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600")}>Python</button>
          <div className="flex-1" />
          <button onClick={() => copy(code)} className="text-xs text-slate-500 hover:text-slate-900 border border-slate-200 rounded-lg px-2.5 py-1 cursor-pointer flex items-center gap-1">
            {copied ? <><Check size={11} /> Copied</> : <><Copy size={11} /> Copy</>}
          </button>
          <button onClick={testInvoke} disabled={testing || !snippet} className={cn("text-xs bg-emerald-600 text-white rounded-lg px-2.5 py-1 cursor-pointer flex items-center gap-1 font-medium", (testing || !snippet) && "opacity-50")}>
            <Play size={11} /> {testing ? "Running..." : "Test"}
          </button>
        </div>
        <div className="overflow-y-auto flex-1">
          {snippet ? (
            <pre className="px-6 py-4 text-[11px] font-mono text-slate-300 bg-[#1e293b] leading-relaxed whitespace-pre-wrap min-h-[120px]">{code}</pre>
          ) : (
            <div className="p-8 text-center text-sm text-slate-400">Loading snippet...</div>
          )}
          {testResult && (
            <div className="px-6 py-4 border-t border-slate-200 bg-slate-50">
              <div className="flex items-center gap-2 mb-2">
                <span className={cn("text-xs font-semibold", testResult.status === "success" || testResult.status === "completed" ? "text-emerald-600" : "text-red-500")}>
                  {testResult.status === "success" || testResult.status === "completed" ? "Success" : "Error"}
                </span>
                {testResult.latency_ms && <span className="text-[11px] text-slate-400">{testResult.latency_ms}ms</span>}
                {testResult.total_latency_ms && <span className="text-[11px] text-slate-400">{testResult.total_latency_ms}ms</span>}
                {testResult.cost_usd !== undefined && <span className="text-[11px] text-slate-400">${testResult.cost_usd}</span>}
                {testResult.usage && <span className="text-[11px] text-slate-400">{testResult.usage.total_tokens} tokens</span>}
                {testResult.steps_completed !== undefined && <span className="text-[11px] text-slate-400">{testResult.steps_completed}/{testResult.steps_total} steps</span>}
              </div>
              <pre className="text-[11px] font-mono text-slate-700 bg-white border border-slate-200 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap max-h-48">
                {testResult.output ? (typeof testResult.output === "string" ? testResult.output : JSON.stringify(testResult.output, null, 2)) : testResult.error || "No output"}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export {
  API,
  BADGE_VARIANTS,
  Badge,
  SearchInput,
  EmptyState,
  Skeleton,
  PageSkeleton,
  toastStore,
  toast,
  TOAST_STYLES,
  TOAST_ICONS,
  ToastContainer,
  confirmAction,
  ConfirmDialog,
  Tabs,
  StatCard,
  Breadcrumbs,
  relativeTime,
  useAutoResize,
  ApiSnippetModal,
};
