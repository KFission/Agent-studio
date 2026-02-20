"use client";
import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import apiFetch from "../lib/apiFetch";
import useEnvStore from "../stores/envStore";

import REGISTRY, {
  NODE_CATEGORIES, getAllNodeTypes, getNodeDef, getDefaultConfig,
  validateNodeConfig, isTriggerNode, isBranchingNode, isTerminalNode,
  canConnect, EXAMPLE_WORKFLOWS,
} from "../stores/nodeRegistry";
import NodePropertyPanel, { resolveIcon } from "./NodePropertyPanel";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
  Panel,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { cn } from "../lib/cn";
import {
  Bot, GitFork, Play, Save, Plus,
  X, ChevronRight, ChevronDown, Trash2, Zap,
  FileText, LayoutGrid, Search, Copy, Check, Edit3,
  Braces, AlertCircle, RefreshCw, CheckCircle2, Sparkles, MoreVertical, ExternalLink,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

// ═══════════════════════════════════════════════════════════════════
// UNIVERSAL NODE COMPONENT — data-driven from registry
// ═══════════════════════════════════════════════════════════════════

function UniversalNode({ data, selected, id }) {
  const def = getNodeDef(data._nodeType);
  if (!def) return null;

  const Icon = resolveIcon(def.icon);
  const execStatus = data._execStatus;
  const hasOutput = data._outputData && Object.keys(data._outputData).length > 0;
  const [showJson, setShowJson] = useState(false);
  const validation = validateNodeConfig(data._nodeType, data.config || {});
  const hasErrors = validation.errors.length > 0;

  const tint10 = def.color + "18";
  const tint25 = def.color + "40";

  return (
    <div
      className={cn(
        "rounded-xl border transition-all relative overflow-hidden",
        selected ? "shadow-lg ring-2 ring-offset-1" : "shadow-sm hover:shadow-md",
        execStatus === "running" && "animate-pulse",
      )}
      style={{
        borderColor: execStatus === "success" ? "#10b981" : execStatus === "error" ? "#ef4444" : execStatus === "running" ? "#f59e0b" : selected ? def.color : "#e5e7eb",
        background: `linear-gradient(135deg, ${tint10}, #ffffff 60%)`,
        ...(selected ? { "--tw-ring-color": tint25 } : {}),
        minWidth: 170,
        maxWidth: 220,
      }}
    >
      {/* Left accent bar */}
      <div className="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl" style={{ background: def.color }} />

      {/* Input handles */}
      {def.inputHandles.length === 1 && (
        <Handle type="target" position={Position.Top} id={def.inputHandles[0].id}
          className="!w-2.5 !h-2.5 !border-2 !border-white !-top-1.5 !rounded-full"
          style={{ background: def.color }} />
      )}
      {def.multiInput && def.inputHandles.map((h, i) => (
        <Handle key={h.id} type="target" position={Position.Top} id={h.id}
          className="!w-2.5 !h-2.5 !border-2 !border-white !-top-1.5 !rounded-full"
          style={{ left: `${((i + 1) / (def.inputHandles.length + 1)) * 100}%`, background: def.color }} />
      ))}

      <div className="flex items-center gap-2.5 px-3 py-2.5 pl-4">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: tint25, color: def.color }}>
          <Icon size={14} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-semibold text-slate-800 truncate leading-tight">{data.label || def.label}</div>
          {data.subtitle && <div className="text-[11px] text-slate-400 truncate leading-tight mt-0.5">{data.subtitle}</div>}
        </div>
        {hasErrors && <AlertCircle size={11} className="text-red-400 shrink-0" />}
        {execStatus === "success" && <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />}
        {execStatus === "error" && <AlertCircle size={13} className="text-red-500 shrink-0" />}
        {execStatus === "running" && <RefreshCw size={11} className="text-amber-500 animate-spin shrink-0" />}
      </div>

      {/* JSON preview */}
      {hasOutput && (
        <div className="px-3 pl-4 pb-2">
          <button onClick={e => { e.stopPropagation(); setShowJson(!showJson); }}
            className="text-[11px] text-slate-400 hover:text-slate-600 flex items-center gap-0.5 cursor-pointer transition">
            <Braces size={9} /> {showJson ? "Hide" : "Data"}
          </button>
          {showJson && (
            <pre className="mt-1 text-[8px] font-mono text-slate-500 bg-white/60 border border-slate-100 rounded-lg p-1.5 max-h-20 overflow-auto whitespace-pre-wrap backdrop-blur-sm">
              {JSON.stringify(data._outputData, null, 1)}
            </pre>
          )}
        </div>
      )}

      {/* Output handles */}
      {def.outputHandles.length === 1 && (
        <Handle type="source" position={Position.Bottom} id={def.outputHandles[0].id}
          className="!w-2.5 !h-2.5 !border-2 !border-white !-bottom-1.5 !rounded-full"
          style={{ background: def.color }} />
      )}
      {def.outputHandles.length > 1 && def.outputHandles.map((h, i) => (
        <Handle key={h.id} type="source" position={Position.Bottom} id={h.id}
          className="!w-2.5 !h-2.5 !border-2 !border-white !-bottom-1.5 !rounded-full"
          style={{
            left: `${((i + 1) / (def.outputHandles.length + 1)) * 100}%`,
            background: h.color || def.color,
          }} />
      ))}
      {/* Handle labels for branching nodes */}
      {def.outputHandles.length > 1 && (
        <div className="flex justify-between px-2 pl-4 pb-1">
          {def.outputHandles.map(h => (
            <span key={h.id} className="text-[7px] font-semibold tracking-wide uppercase" style={{ color: h.color || def.color }}>{h.label}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// Build nodeTypes map for ReactFlow from registry
const nodeTypes = {};
Object.keys(REGISTRY).forEach(type => {
  nodeTypes[type] = (props) => <UniversalNode {...props} />;
});

// ═══════════════════════════════════════════════════════════════════
// NODE LIBRARY (left sidebar) — searchable, categorized
// ═══════════════════════════════════════════════════════════════════

function NodeLibrary() {
  const allNodes = getAllNodeTypes();
  const [expanded, setExpanded] = useState(NODE_CATEGORIES.map(c => c.id));
  const [search, setSearch] = useState("");
  const toggle = (id) => setExpanded(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);

  const filteredCats = NODE_CATEGORIES.map(cat => {
    const items = allNodes.filter(n => n.category === cat.id).filter(n =>
      !search || n.label.toLowerCase().includes(search.toLowerCase()) || n.desc.toLowerCase().includes(search.toLowerCase())
    );
    return { ...cat, items };
  }).filter(cat => cat.items.length > 0);

  return (
    <div className="w-60 bg-gradient-to-b from-slate-50/80 to-white border-r border-slate-200/60 flex flex-col overflow-hidden flex-shrink-0">
      <div className="px-4 py-3 border-b border-slate-100/80 flex items-center gap-2">
        <div className="w-5 h-5 rounded-md bg-slate-900 flex items-center justify-center">
          <Plus size={11} className="text-white" />
        </div>
        <span className="text-xs font-semibold text-slate-700 tracking-tight">Node Library</span>
        <span className="text-[11px] text-slate-400 ml-auto">{allNodes.length}</span>
      </div>
      <div className="px-3 pt-2.5 pb-1.5">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-300" size={12} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search nodes..."
            className="w-full bg-white border border-slate-200/80 rounded-lg py-2 pl-8 pr-3 text-[11px] text-slate-600 outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition placeholder:text-slate-300" />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-2.5 py-1.5 space-y-1">
        {filteredCats.map(cat => (
          <div key={cat.id}>
            <button onClick={() => toggle(cat.id)}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-[11px] font-semibold uppercase tracking-wider text-slate-500 hover:text-slate-700 hover:bg-slate-100/50 cursor-pointer transition">
              <div className="w-1.5 h-1.5 rounded-full ring-2 ring-offset-1" style={{ background: cat.color, ringColor: cat.color + "40" }} />
              <span>{cat.label}</span>
              <span className="text-[11px] text-slate-300 font-normal">({cat.items.length})</span>
              <div className="flex-1" />
              {expanded.includes(cat.id) ? <ChevronDown size={10} className="text-slate-300" /> : <ChevronRight size={10} className="text-slate-300" />}
            </button>
            {expanded.includes(cat.id) && (
              <div className="space-y-0.5 mb-1.5 mt-0.5">
                {cat.items.map(item => {
                  const Icon = resolveIcon(item.icon);
                  const chipBg = item.color + "18";
                  return (
                    <div
                      key={item.type}
                      draggable
                      onDragStart={e => { e.dataTransfer.setData("application/reactflow", item.type); e.dataTransfer.effectAllowed = "move"; }}
                      className="flex items-center gap-2.5 px-2 py-2 rounded-lg cursor-grab hover:bg-white hover:shadow-sm active:shadow-inner transition-all group border border-transparent hover:border-slate-200/60"
                    >
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-105"
                        style={{ background: chipBg, color: item.color }}>
                        <Icon size={13} />
                      </div>
                      <div className="min-w-0">
                        <div className="text-[11px] font-medium text-slate-700 group-hover:text-slate-900 transition">{item.label}</div>
                        <div className="text-[11px] text-slate-400 truncate leading-tight">{item.desc}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// WORKFLOW LIST
// ═══════════════════════════════════════════════════════════════════

function WfApiModal({ id, name, onClose }) {
  const [snippet, setSnippet] = useState(null);
  const [lang, setLang] = useState("curl");
  const [copied, setCopied] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (!id) return;
    apiFetch(`${API}/workflows/${id}/api-snippet`).then(r => r.json()).then(setSnippet).catch(() => {});
  }, [id]);

  const doCopy = (text) => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  const testInvoke = async () => {
    setTesting(true); setTestResult(null);
    try {
      const r = await apiFetch(`${API}/workflows/${id}/invoke`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: "Test invocation", input_data: { query: "test" } }) });
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
              <span className="text-base font-semibold text-slate-900">API — Workflow as a Service</span>
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
          <button onClick={() => doCopy(code)} className="text-xs text-slate-500 hover:text-slate-900 border border-slate-200 rounded-lg px-2.5 py-1 cursor-pointer flex items-center gap-1">
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
                <span className={cn("text-xs font-semibold", testResult.status === "completed" || testResult.status === "success" ? "text-emerald-600" : "text-red-500")}>{testResult.status}</span>
                {testResult.total_latency_ms && <span className="text-[11px] text-slate-400">{testResult.total_latency_ms}ms</span>}
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

function toast(msg, type = "success") {
  // lightweight inline — mirrors AgentStudio's global toast
  if (typeof window !== "undefined" && window.__jaiToast) { window.__jaiToast(msg, type); return; }
  console.log(`[${type}] ${msg}`);
}
function confirmAction({ title, message, confirmLabel = "Delete" }) {
  return new Promise(resolve => {
    if (typeof window !== "undefined" && window.__jaiConfirm) { window.__jaiConfirm({ title, message, confirmLabel, resolve }); return; }
    resolve(window.confirm(`${title}\n\n${message}`));
  });
}

function WorkflowCardMenu({ workflow, onEdit, onClone, onApi, onExport, onDelete, canEdit }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const btnRef = useRef(null);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const close = (e) => {
      if (menuRef.current?.contains(e.target) || btnRef.current?.contains(e.target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const toggle = (e) => {
    e.stopPropagation();
    if (!open && btnRef.current) {
      const r = btnRef.current.getBoundingClientRect();
      setPos({ top: r.bottom + 4, left: r.right - 176 });
    }
    setOpen(!open);
  };

  const items = [
    canEdit && { icon: Edit3, label: "Edit", action: onEdit },
    { icon: Copy, label: "Clone", action: onClone },
    { icon: Zap, label: "API Snippet", action: onApi },
    { icon: ExternalLink, label: "Export JSON", action: onExport },
    canEdit && "divider",
    canEdit && { icon: Trash2, label: "Delete", action: onDelete, danger: true },
  ].filter(Boolean);

  return (
    <>
      <button ref={btnRef} onClick={toggle}
        className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer transition">
        <MoreVertical size={14} />
      </button>
      {open && typeof document !== "undefined" && createPortal(
        <div ref={menuRef} className="fixed w-44 bg-white rounded-xl shadow-2xl border border-slate-200 py-1 z-[9999] animate-scale-in"
          style={{ top: pos.top, left: pos.left }} onClick={e => e.stopPropagation()}>
          {items.map((item, i) =>
            item === "divider" ? (
              <div key={i} className="border-t border-slate-100 my-1" />
            ) : (
              <button key={i} onClick={() => { setOpen(false); item.action(); }}
                className={cn("w-full flex items-center gap-2.5 px-3 py-2 text-left text-[13px] cursor-pointer transition",
                  item.danger ? "text-red-500 hover:bg-red-50" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900")}>
                <item.icon size={14} className="shrink-0" />
                {item.label}
              </button>
            )
          )}
        </div>,
        document.body
      )}
    </>
  );
}

function WorkflowList({ workflows, onOpen, onCreate, onDelete, onClone }) {
  const [apiOpen, setApiOpen] = useState(null);
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState("grid");
  const currentEnv = useEnvStore(s => s.currentEnv);
  const canEditEnv = useEnvStore(s => s.canEdit);
  const [cloneTarget, setCloneTarget] = useState(null);
  const [cloneName, setCloneName] = useState("");
  const cloneRef = useRef(null);

  const openCloneDialog = (w) => { setCloneTarget(w); setCloneName(w.name + " (Copy)"); setTimeout(() => cloneRef.current?.select(), 50); };
  const doClone = async () => {
    if (!cloneTarget || !cloneName.trim()) return;
    try {
      await apiFetch(`${API}/orchestrator/pipelines`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: cloneName.trim(), description: cloneTarget.description || "", pattern: cloneTarget.pattern || "sequential", steps: cloneTarget.steps || [], tags: cloneTarget.tags || [] }),
      });
      toast(`Cloned as "${cloneName.trim()}"`);
      setCloneTarget(null); onClone?.();
    } catch { toast("Clone failed", "error"); }
  };
  const handleDelete = async (w) => {
    const ok = await confirmAction({ title: "Delete Workflow", message: `Permanently delete "${w.name}"? This cannot be undone.`, confirmLabel: "Delete Workflow" });
    if (!ok) return;
    onDelete(w.pipeline_id);
    toast(`Workflow "${w.name}" deleted`);
  };
  const exportWorkflow = (w) => {
    const blob = new Blob([JSON.stringify(w, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = `${w.name.replace(/\s+/g, "_").toLowerCase()}_workflow.json`; a.click(); URL.revokeObjectURL(url);
    toast("Workflow exported");
  };

  const filtered = workflows.filter(w => !search || w.name.toLowerCase().includes(search.toLowerCase()) || (w.description || "").toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Workflows</h1>
          <p className="text-sm text-slate-500 mt-1">Visual workflow automations connecting agents, tools, and logic</p>
        </div>
        {canEditEnv() && <button onClick={onCreate} className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} /> New Workflow</button>}
      </div>
      {workflows.length > 0 && (
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search workflows..."
              className="w-full bg-white border border-slate-200 rounded-lg py-2 pl-8 pr-3 text-sm text-slate-900 outline-none focus:border-slate-400 transition" />
          </div>
          <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg p-0.5">
            <button onClick={() => setViewMode("grid")} className={cn("p-1.5 rounded cursor-pointer transition", viewMode === "grid" ? "bg-slate-100 text-slate-900" : "text-slate-400 hover:text-slate-600")}><LayoutGrid size={14} /></button>
            <button onClick={() => setViewMode("list")} className={cn("p-1.5 rounded cursor-pointer transition", viewMode === "list" ? "bg-slate-100 text-slate-900" : "text-slate-400 hover:text-slate-600")}><FileText size={14} /></button>
          </div>
          <span className="text-xs text-slate-400">{filtered.length} workflow{filtered.length !== 1 ? "s" : ""}</span>
        </div>
      )}
      {workflows.length === 0 ? (
        <div className="text-center py-16">
          <GitFork size={40} className="mx-auto text-slate-300 mb-3" />
          <div className="text-base font-medium text-slate-500">No workflows yet</div>
          <div className="text-sm text-slate-400 mt-1 mb-4">Create a visual workflow to connect agents, tools, and logic into automations.</div>
          <button onClick={onCreate} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} className="inline mr-1" />New Workflow</button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-sm text-slate-400">No workflows match "{search}"</div>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(w => (
            <div key={w.pipeline_id} className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-md transition cursor-pointer" onClick={() => onOpen(w)}>
              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm font-semibold text-slate-900 line-clamp-1">{w.name}</div>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium shrink-0">{w.pattern || "visual"}</span>
                </div>
                {w.description && <div className="text-xs text-slate-500 mt-1.5 line-clamp-2">{w.description}</div>}
                <div className="flex flex-wrap gap-1.5 mt-2.5">
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{(w.steps || []).length || (w.metadata?.node_count || 0)} nodes</span>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">v{w.version || 1}</span>
                </div>
              </div>
              <div className="px-4 py-2.5 border-t border-slate-100 flex items-center justify-between">
                <span className={cn("text-[11px] font-medium px-1.5 py-0.5 rounded-full border", w.status === "active" ? "text-emerald-600 border-emerald-200 bg-emerald-50" : "text-slate-500 border-slate-200 bg-slate-50")}>{w.status === "active" ? "Active" : "Draft"}</span>
                <div className="flex items-center gap-1.5">
                  <WorkflowCardMenu
                    workflow={w}
                    onEdit={() => onOpen(w)}
                    onClone={() => openCloneDialog(w)}
                    onApi={() => setApiOpen(w.pipeline_id)}
                    onExport={() => exportWorkflow(w)}
                    onDelete={() => handleDelete(w)}
                    canEdit={canEditEnv()}
                  />
                  <button onClick={e => { e.stopPropagation(); onOpen(w); }} className="text-xs text-white bg-jai-primary rounded-lg px-3 py-1.5 flex items-center gap-1 cursor-pointer font-medium hover:bg-jai-primary-hover transition"><Edit3 size={12} /> Open</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100">
          {filtered.map(w => (
            <div key={w.pipeline_id} className="flex items-center gap-4 px-4 py-3 hover:bg-slate-50 cursor-pointer transition group" onClick={() => onOpen(w)}>
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0"><GitFork size={14} className="text-blue-600" /></div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-900 truncate">{w.name}</div>
                {w.description && <div className="text-xs text-slate-500 truncate mt-0.5">{w.description}</div>}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">{w.pattern || "visual"}</span>
                <span className="text-[11px] text-slate-400">{(w.steps || []).length || (w.metadata?.node_count || 0)} nodes</span>
                <span className="text-[11px] text-slate-400">v{w.version || 1}</span>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <span className={cn("text-[11px] font-medium px-1.5 py-0.5 rounded-full border", w.status === "active" ? "text-emerald-600 border-emerald-200 bg-emerald-50" : "text-slate-500 border-slate-200 bg-slate-50")}>{w.status === "active" ? "Active" : "Draft"}</span>
                <WorkflowCardMenu
                  workflow={w}
                  onEdit={() => onOpen(w)}
                  onClone={() => openCloneDialog(w)}
                  onApi={() => setApiOpen(w.pipeline_id)}
                  onExport={() => exportWorkflow(w)}
                  onDelete={() => handleDelete(w)}
                  canEdit={canEditEnv()}
                />
              </div>
            </div>
          ))}
        </div>
      )}
      {apiOpen && <WfApiModal id={apiOpen} name={workflows.find(w => w.pipeline_id === apiOpen)?.name || ""} onClose={() => setApiOpen(null)} />}

      {/* Clone Workflow Dialog */}
      {cloneTarget && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setCloneTarget(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6" onClick={e => e.stopPropagation()}>
            <h3 className="text-base font-semibold text-slate-900">Clone Workflow</h3>
            <p className="text-sm text-slate-500 mt-1">Create a copy of <span className="font-medium text-slate-700">{cloneTarget.name}</span> with a new name.</p>
            <div className="mt-4">
              <label className="text-xs font-medium text-slate-500 block mb-1">New Workflow Name</label>
              <input ref={cloneRef} value={cloneName} onChange={e => setCloneName(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") doClone(); if (e.key === "Escape") setCloneTarget(null); }}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition"
                placeholder="Enter a name for the cloned workflow..." autoFocus />
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setCloneTarget(null)} className="px-4 py-2 text-sm font-medium text-slate-600 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50 transition">Cancel</button>
              <button onClick={doClone} disabled={!cloneName.trim()} className={cn("px-4 py-2 text-sm font-medium text-white bg-slate-800 rounded-lg cursor-pointer hover:bg-slate-900 transition", !cloneName.trim() && "opacity-50 cursor-not-allowed")}>
                <Copy size={13} className="inline mr-1.5 -mt-0.5" />Clone Workflow
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// CANVAS (the main ReactFlow builder)
// ═══════════════════════════════════════════════════════════════════

let idCounter = 0;
const genId = () => `node_${++idCounter}_${Date.now()}`;

// ═══════════════════════════════════════════════════════════════════
// TOPOLOGICAL SORT + EXECUTION RUNNER
// ═══════════════════════════════════════════════════════════════════

function topoSort(nodes, edges) {
  const adj = {}; const inDeg = {};
  nodes.forEach(n => { adj[n.id] = []; inDeg[n.id] = 0; });
  edges.forEach(e => { if (adj[e.source]) { adj[e.source].push(e.target); inDeg[e.target] = (inDeg[e.target] || 0) + 1; } });
  const queue = nodes.filter(n => (inDeg[n.id] || 0) === 0).map(n => n.id);
  const order = [];
  while (queue.length) {
    const id = queue.shift(); order.push(id);
    (adj[id] || []).forEach(t => { inDeg[t]--; if (inDeg[t] === 0) queue.push(t); });
  }
  return order;
}

// ═══════════════════════════════════════════════════════════════════
// EXAMPLE WORKFLOW PICKER
// ═══════════════════════════════════════════════════════════════════

function ExampleWorkflowPicker({ onSelect }) {
  return (
    <div className="flex flex-col items-center gap-5">
      <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center">
        <GitFork size={24} className="text-slate-400" />
      </div>
      <div className="text-center">
        <div className="text-sm font-medium text-slate-600">Drag nodes from the library to start</div>
        <div className="text-xs text-slate-400 mt-1">or pick a template below</div>
      </div>
      <div className="flex gap-2.5 flex-wrap justify-center">
        {Object.entries(EXAMPLE_WORKFLOWS).map(([key, wf]) => (
          <button key={key} onClick={() => onSelect(wf)}
            className="flex items-center gap-2 bg-white border border-slate-200/80 rounded-xl px-4 py-2.5 text-xs text-slate-600 hover:border-slate-300 hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer shadow-sm">
            <Sparkles size={12} className="text-slate-400" /> {wf.name}
          </button>
        ))}
      </div>
    </div>
  );
}

function CanvasInner({ workflow, agents, tools, onSave, onBack, onRefreshAgents }) {
  const initialNodes = useMemo(() => (workflow?.metadata?.rf_nodes || []).map(n => ({ ...n, data: { ...n.data, _nodeType: n.type } })), [workflow]);
  const initialEdges = useMemo(() => workflow?.metadata?.rf_edges || [], [workflow]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState(null);
  const [wfName, setWfName] = useState(workflow?.name || "Untitled Workflow");
  const [wfDesc, setWfDesc] = useState(workflow?.description || "");
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const reactFlowWrapper = useRef(null);
  const { screenToFlowPosition } = useReactFlow();

  // Connection validation
  const onConnect = useCallback((params) => {
    // Validate connection using registry
    const sourceNode = nodes.find(n => n.id === params.source);
    const targetNode = nodes.find(n => n.id === params.target);
    if (sourceNode && targetNode && !canConnect(sourceNode.type, targetNode.type)) return;

    setEdges(eds => addEdge({
      ...params,
      type: "smoothstep",
      animated: false,
      markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "#94a3b8" },
      style: { stroke: "#94a3b8", strokeWidth: 2 },
    }, eds));
  }, [setEdges, nodes]);

  const onDragOver = useCallback(e => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; }, []);

  const onDrop = useCallback(e => {
    e.preventDefault();
    const type = e.dataTransfer.getData("application/reactflow");
    if (!type) return;
    const def = getNodeDef(type);
    if (!def) return;
    const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
    const defaultConfig = getDefaultConfig(type);
    const newNode = {
      id: genId(),
      type,
      position,
      data: { label: def.label, subtitle: "", notes: "", _nodeType: type, config: defaultConfig },
    };
    setNodes(nds => [...nds, newNode]);
  }, [screenToFlowPosition, setNodes]);

  const onNodeClick = useCallback((_, node) => setSelectedNode(node), []);
  const onPaneClick = useCallback(() => setSelectedNode(null), []);

  const handleUpdateNodeData = useCallback((nodeId, newData) => {
    setNodes(nds => nds.map(n => n.id === nodeId ? { ...n, data: { ...newData, _nodeType: n.type } } : n));
    setSelectedNode(prev => prev?.id === nodeId ? { ...prev, data: { ...newData, _nodeType: prev.type } } : prev);
  }, [setNodes]);

  const handleDeleteNode = useCallback((nodeId) => {
    setNodes(nds => nds.filter(n => n.id !== nodeId));
    setEdges(eds => eds.filter(e => e.source !== nodeId && e.target !== nodeId));
    setSelectedNode(null);
  }, [setNodes, setEdges]);

  // Load an example workflow
  const loadExample = useCallback((example) => {
    setNodes(example.nodes.map(n => ({ ...n, data: { ...n.data, _nodeType: n.type, config: n.data.config || getDefaultConfig(n.type) } })));
    setEdges(example.edges.map(e => ({
      ...e,
      type: "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "#94a3b8" },
      style: { stroke: "#94a3b8", strokeWidth: 2 },
    })));
    setWfName(example.name);
    setWfDesc(example.description);
  }, [setNodes, setEdges]);

  // ── EXECUTE WORKFLOW (simulated topological sort runner) ──
  const executeWorkflow = useCallback(async () => {
    if (executing) return;
    setExecuting(true);

    setNodes(nds => nds.map(n => ({ ...n, data: { ...n.data, _execStatus: undefined, _outputData: undefined, _inputData: undefined } })));
    setEdges(eds => eds.map(e => ({ ...e, animated: false, style: { stroke: "#94a3b8", strokeWidth: 2 } })));

    await new Promise(r => setTimeout(r, 200));
    const order = topoSort(nodes, edges);

    setNodes(nds => nds.map(n => ({ ...n, data: { ...n.data, _execStatus: "queued" } })));
    await new Promise(r => setTimeout(r, 300));

    const nodeOutputs = {};

    for (const nodeId of order) {
      const node = nodes.find(n => n.id === nodeId);
      if (!node) continue;

      setNodes(nds => nds.map(n => n.id === nodeId ? { ...n, data: { ...n.data, _execStatus: "running" } } : n));

      const incomingEdges = edges.filter(e => e.target === nodeId);
      if (incomingEdges.length > 0) {
        setEdges(eds => eds.map(e =>
          incomingEdges.some(ie => ie.id === e.id)
            ? { ...e, animated: true, style: { stroke: "#3b82f6", strokeWidth: 3 } }
            : e
        ));
      }

      const inputData = {};
      incomingEdges.forEach(e => {
        if (nodeOutputs[e.source]) Object.assign(inputData, nodeOutputs[e.source]);
      });

      await new Promise(r => setTimeout(r, 300 + Math.random() * 500));

      // Get mock output from registry
      const def = getNodeDef(node.type);
      const output = def?.mockOutput || { result: "ok" };
      nodeOutputs[nodeId] = output;

      setNodes(nds => nds.map(n => n.id === nodeId ? { ...n, data: { ...n.data, _execStatus: "success", _outputData: output, _inputData: inputData } } : n));

      if (incomingEdges.length > 0) {
        setEdges(eds => eds.map(e =>
          incomingEdges.some(ie => ie.id === e.id)
            ? { ...e, animated: false, style: { stroke: "#10b981", strokeWidth: 2.5 } }
            : e
        ));
      }
    }

    setExecuting(false);
  }, [executing, nodes, edges, setNodes, setEdges]);

  const clearExecution = useCallback(() => {
    setNodes(nds => nds.map(n => ({ ...n, data: { ...n.data, _execStatus: undefined, _outputData: undefined, _inputData: undefined } })));
    setEdges(eds => eds.map(e => ({ ...e, animated: false, style: { stroke: "#94a3b8", strokeWidth: 2 } })));
  }, [setNodes, setEdges]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    const cleanData = (d) => { const { _execStatus, _outputData, _inputData, ...rest } = d; return rest; };
    const payload = {
      name: wfName, description: wfDesc, pattern: "visual",
      steps: nodes.filter(n => n.type === "runAgent").map((n, i) => ({ agent_id: n.data.config?.agentId || "", agent_name: n.data.label || "", order: i })),
      metadata: {
        rf_nodes: nodes.map(n => ({ id: n.id, type: n.type, position: n.position, data: cleanData(n.data) })),
        rf_edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target, sourceHandle: e.sourceHandle, targetHandle: e.targetHandle })),
        node_count: nodes.length, edge_count: edges.length,
      },
    };
    try {
      if (workflow?.pipeline_id) {
        await apiFetch(`${API}/orchestrator/pipelines/${workflow.pipeline_id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      } else {
        await apiFetch(`${API}/orchestrator/pipelines`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      }
      onSave?.();
    } catch (err) { console.error("Save failed", err); }
    setSaving(false);
  }, [wfName, wfDesc, nodes, edges, workflow, onSave]);

  const selNodeObj = useMemo(() => nodes.find(n => n.id === selectedNode?.id), [nodes, selectedNode]);
  const completedCount = nodes.filter(n => n.data._execStatus === "success").length;
  const [showLibrary, setShowLibrary] = useState(false);

  // Auto-show properties when a node is selected
  const showProps = !!selNodeObj;

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar — single dominant CTA pattern */}
      <div className="h-12 bg-white/80 backdrop-blur-md border-b border-slate-200/60 flex items-center px-4 gap-2.5 flex-shrink-0">
        <button onClick={onBack} className="text-xs text-slate-400 hover:text-slate-700 flex items-center gap-1 cursor-pointer transition">
          <ChevronRight size={13} className="rotate-180" /> Back
        </button>
        <div className="h-5 w-px bg-slate-200/60" />
        <input value={wfName} onChange={e => setWfName(e.target.value)} className="text-sm font-semibold text-slate-800 border-none outline-none bg-transparent min-w-[180px] placeholder:text-slate-300" placeholder="Workflow name..." />
        <div className="flex-1" />
        {/* Toggle buttons for panels */}
        <button onClick={() => setShowLibrary(p => !p)}
          className={cn("flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium cursor-pointer transition border",
            showLibrary ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-500 border-slate-200 hover:border-slate-300 hover:text-slate-700")}>
          <Plus size={11} /> Nodes
        </button>
        <div className="h-5 w-px bg-slate-200/60" />
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400 bg-slate-50 rounded-md px-2 py-1">
          <span>{nodes.length} nodes</span>
          <span className="text-slate-300">·</span>
          <span>{edges.length} edges</span>
        </div>
        {completedCount > 0 && (
          <button onClick={clearExecution} className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-600 cursor-pointer transition">
            <X size={11} /> Clear
          </button>
        )}
        {/* Primary CTA: Execute when ready, Save otherwise */}
        {executing ? (
          <button disabled className="flex items-center gap-1.5 bg-amber-500 text-white rounded-lg px-3.5 py-1.5 text-xs font-medium opacity-80 cursor-not-allowed">
            <RefreshCw size={11} className="animate-spin" /> Running...
          </button>
        ) : (
          <button onClick={executeWorkflow} disabled={nodes.length === 0}
            className={cn("flex items-center gap-1.5 bg-slate-800 text-white rounded-lg px-3.5 py-1.5 text-xs font-medium cursor-pointer hover:bg-slate-900 transition shadow-sm", nodes.length === 0 && "opacity-40 cursor-not-allowed")}>
            <Play size={11} /> Execute
          </button>
        )}
        <button onClick={handleSave} disabled={saving} className={cn("flex items-center gap-1.5 bg-white border border-slate-200 text-slate-700 rounded-lg px-3.5 py-1.5 text-xs font-medium cursor-pointer hover:bg-slate-50 hover:border-slate-300 transition shadow-sm", saving && "opacity-50")}>
          <Save size={11} /> {saving ? "Saving..." : "Save"}
        </button>
      </div>

      {/* Execution progress bar */}
      {executing && (
        <div className="h-0.5 bg-slate-100 relative overflow-hidden flex-shrink-0">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 to-emerald-500" style={{ width: `${(completedCount / Math.max(nodes.length, 1)) * 100}%`, transition: "width 0.4s ease-out" }} />
        </div>
      )}

      {/* Main area: Canvas full-width, panels as overlays */}
      <div className="flex-1 relative overflow-hidden">
        {/* Node Library — overlay on left */}
        {showLibrary && (
          <div className="absolute left-0 top-0 bottom-0 z-20 animate-slide-in-left">
            <NodeLibrary />
          </div>
        )}

        {/* Canvas — full width always */}
        <div className="absolute inset-0" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={() => { onPaneClick(); }}
            nodeTypes={nodeTypes}
            defaultEdgeOptions={{
              type: "smoothstep",
              animated: false,
              markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "#94a3b8" },
              style: { stroke: "#94a3b8", strokeWidth: 2 },
            }}
            fitView
            proOptions={{ hideAttribution: true }}
            className="bg-[#fafbfc]"
          >
            <Background variant="dots" gap={20} size={0.8} color="#d4d8dd" />
            <Controls showInteractive={false} className="!bg-white !border-slate-200 !rounded-lg !shadow-sm" />
            <MiniMap
              nodeColor={n => {
                if (n.data?._execStatus === "success") return "#10b981";
                if (n.data?._execStatus === "running") return "#f59e0b";
                if (n.data?._execStatus === "error") return "#ef4444";
                const def = getNodeDef(n.type);
                return def?.color || "#94a3b8";
              }}
              maskColor="rgba(241,245,249,0.7)"
              className="!bg-white !border-slate-200 !rounded-lg"
            />
            {nodes.length === 0 && (
              <Panel position="center">
                <div className="text-center p-8">
                  <ExampleWorkflowPicker onSelect={loadExample} />
                </div>
              </Panel>
            )}
          </ReactFlow>
        </div>

        {/* Properties Panel — overlay on right, shown when node selected */}
        {showProps && (
          <div className="absolute right-0 top-0 bottom-0 z-20 shadow-xl animate-slide-in-left">
            <NodePropertyPanel
              node={selNodeObj}
              agents={agents}
              tools={tools}
              onUpdate={handleUpdateNodeData}
              onDelete={handleDeleteNode}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function Canvas(props) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}

// ═══════════════════════════════════════════════════════════════════
// MAIN EXPORT: WorkflowsPage
// ═══════════════════════════════════════════════════════════════════

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState([]);
  const [agents, setAgents] = useState([]);
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // null = list view, object = canvas view

  const load = useCallback(() => {
    Promise.all([
      apiFetch(`${API}/orchestrator/pipelines`).then(r => r.json()).catch(() => ({ pipelines: [] })),
      apiFetch(`${API}/agents`).then(r => r.json()).catch(() => ({ agents: [] })),
      apiFetch(`${API}/tools`).then(r => r.json()).catch(() => ({ tools: [] })),
      apiFetch(`${API}/langgraph/assistants`).then(r => r.json()).catch(() => ({ assistants: [] })),
    ]).then(([wf, ag, tl, lg]) => {
      setWorkflows(wf.pipelines || []);
      const localAgents = (ag.agents || []).map(a => ({ ...a, source: "local" }));
      const lgAgents = (lg.assistants || []).map(a => ({
        agent_id: a.assistant_id, assistant_id: a.assistant_id, name: a.name,
        description: a.description, model: a.model, status: "active", source: "langgraph",
      }));
      setAgents([...localAgents, ...lgAgents]);
      setTools(tl.tools || []);
      setLoading(false);
    });
  }, []);

  useEffect(() => { load(); }, [load]);

  const refreshAgents = useCallback(() => {
    Promise.all([
      apiFetch(`${API}/agents`).then(r => r.json()).catch(() => ({ agents: [] })),
      apiFetch(`${API}/langgraph/assistants`).then(r => r.json()).catch(() => ({ assistants: [] })),
    ]).then(([ag, lg]) => {
      const localAgents = (ag.agents || []).map(a => ({ ...a, source: "local" }));
      const lgAgents = (lg.assistants || []).map(a => ({
        agent_id: a.assistant_id, assistant_id: a.assistant_id, name: a.name,
        description: a.description, model: a.model, status: "active", source: "langgraph",
      }));
      setAgents([...localAgents, ...lgAgents]);
    });
  }, []);

  const createNew = () => setEditing({ name: "Untitled Workflow", description: "", metadata: { rf_nodes: [], rf_edges: [] } });

  const openWorkflow = (wf) => setEditing(wf);

  const deleteWorkflow = async (id) => {
    await apiFetch(`${API}/orchestrator/pipelines/${id}`, { method: "DELETE" });
    load();
  };

  const onSave = () => { setEditing(null); load(); };

  if (loading) return <div className="p-6 text-slate-400 text-sm">Loading workflows...</div>;

  if (editing) {
    return (
      <div className="h-full flex flex-col">
        <Canvas
          workflow={editing}
          agents={agents}
          tools={tools}
          onSave={onSave}
          onBack={() => setEditing(null)}
          onRefreshAgents={refreshAgents}
        />
      </div>
    );
  }

  return (
    <WorkflowList
      workflows={workflows}
      onOpen={openWorkflow}
      onCreate={createNew}
      onDelete={deleteWorkflow}
      onClone={load}
    />
  );
}
