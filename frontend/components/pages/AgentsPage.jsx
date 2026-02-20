"use client";
import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { createPortal } from "react-dom";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import useEnvStore from "../../stores/envStore";
import { EnvVersionMeta } from "../EnvironmentSwitcher";
import { API, Badge, SearchInput, EmptyState, StatCard, toast, confirmAction, ApiSnippetModal, relativeTime } from "../shared/StudioUI";
import { Bot, Brain, Wrench, MessageSquare, Edit3, Plus, Search, Copy, ExternalLink, RefreshCw, Trash2, MoreVertical, ChevronRight, LayoutGrid, Activity, Clock, DollarSign, Zap, History, ArrowRight, GitCompare, RotateCcw, Loader2, ChevronDown, ArrowUpRight, Lock, Unlock, CheckCircle2, XCircle, AlertTriangle, Upload, Download } from "lucide-react";

function AgentCardMenu({ agent, onEdit, onClone, onApi, onExport, onToggleStatus, onDelete, canEdit }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const btnRef = useRef(null);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const close = (e) => {
      if (menuRef.current && menuRef.current.contains(e.target)) return;
      if (btnRef.current && btnRef.current.contains(e.target)) return;
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
    { icon: RefreshCw, label: agent.status === "active" ? "Set to Draft" : "Set to Active", action: onToggleStatus },
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
        <div ref={menuRef} className="fixed w-44 bg-white rounded-xl shadow-2xl border border-slate-200 py-1 z-[9999]"
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

function AgentListOverflow({ onTemplates, onImport, onExportAll, importLoading, canEdit, hasAgents }) {
  const [open, setOpen] = useState(false);
  const btnRef = useRef(null);
  const menuRef = useRef(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (!open) return;
    const close = (e) => {
      if (menuRef.current?.contains(e.target) || btnRef.current?.contains(e.target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const toggle = () => {
    if (!open && btnRef.current) {
      const r = btnRef.current.getBoundingClientRect();
      setPos({ top: r.bottom + 4, left: r.right - 176 });
    }
    setOpen(!open);
  };

  const items = [
    { icon: LayoutGrid, label: "Browse Templates", action: () => { setOpen(false); onTemplates(); } },
    canEdit && { icon: importLoading ? Loader2 : Upload, label: "Import Agent", action: () => { setOpen(false); onImport(); } },
    hasAgents && { icon: Download, label: "Export All", action: () => { setOpen(false); onExportAll(); } },
  ].filter(Boolean);

  return (
    <>
      <button ref={btnRef} onClick={toggle}
        className="w-9 h-9 flex items-center justify-center rounded-lg border border-slate-200 text-slate-400 hover:text-slate-700 hover:bg-slate-50 cursor-pointer transition">
        <MoreVertical size={15} />
      </button>
      {open && typeof document !== "undefined" && createPortal(
        <div ref={menuRef} className="fixed w-44 bg-white rounded-xl shadow-2xl border border-slate-200 py-1 z-[9999] animate-scale-in"
          style={{ top: pos.top, left: pos.left }}>
          {items.map((item, i) => (
            <button key={i} onClick={item.action}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-left text-[13px] text-slate-600 hover:bg-slate-50 hover:text-slate-900 cursor-pointer transition">
              <item.icon size={14} className={cn("shrink-0", item.icon === Loader2 && "animate-spin")} />
              {item.label}
            </button>
          ))}
        </div>,
        document.body
      )}
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════
// PAGE: Agents (agent-centric with card → chat/edit/runs/deploy)
// ═══════════════════════════════════════════════════════════════════

export default function AgentsPage({ setPage, setChatAgent, setEditAgent }) {
  const currentEnv = useEnvStore(s => s.currentEnv);
  const canEditEnv = useEnvStore(s => s.canEdit);
  const requestPromotion = useEnvStore(s => s.requestPromotion);
  const [agents, setAgents] = useState([]); const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(""); const [tab, setTab] = useState("All Agents");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", context: "", rag_enabled: false });
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [apiOpenAgent, setApiOpenAgent] = useState(null);
  const [cloneTarget, setCloneTarget] = useState(null);
  const [cloneName, setCloneName] = useState("");
  const cloneInputRef = useRef(null);
  const importInputRef = useRef(null);
  const [importLoading, setImportLoading] = useState(false);

  // Version history, diff & rollback state
  const [versions, setVersions] = useState([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [diffData, setDiffData] = useState(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [showDiffModal, setShowDiffModal] = useState(false);
  const [rollbackLoading, setRollbackLoading] = useState(false);
  // Promotion state
  const [showPromoteModal, setShowPromoteModal] = useState(false);
  const [promoteTarget, setPromoteTarget] = useState("qa");
  const [promoteLoading, setPromoteLoading] = useState(false);

  const load = (retry = true) => {
    setLoading(true);
    apiFetch(`${API}/agents`).then(r => r.json()).then(d => { setAgents(d.agents || []); setLoading(false); })
      .catch(() => {
        if (retry) { setTimeout(() => load(false), 1500); }
        else { setLoading(false); }
      });
  };
  useEffect(() => { load(); }, []);

  // Load version history when an agent is selected
  const loadVersions = async (agentId) => {
    setVersionsLoading(true);
    try {
      const r = await apiFetch(`${API}/agents/${agentId}/versions`);
      const data = await r.json();
      setVersions(data.versions || []);
    } catch { setVersions([]); }
    setVersionsLoading(false);
  };
  useEffect(() => { if (selectedAgent) loadVersions(selectedAgent.agent_id); }, [selectedAgent?.agent_id]);

  const loadDiff = async (agentId, vA, vB) => {
    setDiffLoading(true);
    try {
      const r = await apiFetch(`${API}/agents/${agentId}/diff/${vA}/${vB}`);
      const data = await r.json();
      setDiffData(data);
      setShowDiffModal(true);
    } catch { toast.error("Failed to load diff"); }
    setDiffLoading(false);
  };

  const doRollback = async (agentId, version) => {
    const ok = await confirmAction({ title: "Rollback Agent", message: `Rollback to version ${version}? A new version will be created from the v${version} snapshot.`, confirmLabel: "Rollback" });
    if (!ok) return;
    setRollbackLoading(true);
    try {
      const r = await apiFetch(`${API}/agents/${agentId}/rollback/${version}?rolled_back_by=admin`, { method: "POST" });
      if (!r.ok) throw new Error("Rollback failed");
      const data = await r.json();
      toast.success(`Rolled back to v${version} → new v${data.new_version}`);
      load(); loadVersions(agentId);
      setSelectedAgent(prev => prev ? { ...prev, version: data.new_version } : prev);
    } catch { toast.error("Rollback failed"); }
    setRollbackLoading(false);
  };

  const doPromote = async (agent) => {
    setPromoteLoading(true);
    try {
      const detail = await apiFetch(`${API}/agents/${agent.agent_id}`).then(r => r.json());
      await requestPromotion({
        assetType: "agent", assetId: agent.agent_id, assetName: agent.name,
        fromEnv: currentEnv, toEnv: promoteTarget,
        configJson: detail, fromVersion: agent.version,
      });
      toast.success(`Promotion requested: ${agent.name} → ${promoteTarget.toUpperCase()}`);
      setShowPromoteModal(false);
    } catch (e) { toast.error(e.message || "Promotion failed"); }
    setPromoteLoading(false);
  };
  const filtered = agents.filter(a => a.name.toLowerCase().includes(search.toLowerCase()));

  const create = async () => {
    try {
      await apiFetch(`${API}/agents`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
      setShowCreate(false); setForm({ name: "", description: "", context: "", rag_enabled: false }); load();
      toast.success(`Agent "${form.name}" created`);
    } catch (e) { toast.error("Failed to create agent"); }
  };

  const openCloneDialog = (agent) => { setCloneTarget(agent); setCloneName(agent.name + " (Copy)"); setTimeout(() => cloneInputRef.current?.select(), 50); };
  const doClone = async () => {
    if (!cloneTarget || !cloneName.trim()) return;
    try {
      await apiFetch(`${API}/agents/${cloneTarget.agent_id}/clone?name=${encodeURIComponent(cloneName.trim())}`, { method: "POST" });
      toast.success(`Cloned as "${cloneName.trim()}"`);
      setCloneTarget(null); load();
    } catch { toast.error("Clone failed"); }
  };
  const deleteAgent = async (agent) => {
    const ok = await confirmAction({ title: "Delete Agent", message: `Permanently delete "${agent.name}"? This will remove all versions, memory, and chat history for this agent.`, confirmLabel: "Delete Agent" });
    if (!ok) return;
    await apiFetch(`${API}/agents/${agent.agent_id}`, { method: "DELETE" }); load(); toast.success(`Agent "${agent.name}" deleted`);
    if (selectedAgent?.agent_id === agent.agent_id) setSelectedAgent(null);
  };
  const toggleAgentStatus = async (agent) => {
    const newStatus = agent.status === "active" ? "draft" : "active";
    await apiFetch(`${API}/agents/${agent.agent_id}/status/${newStatus}`, { method: "POST" }); load();
    toast.success(`${agent.name} → ${newStatus}`);
  };
  const exportAgent = async (agent) => {
    try {
      const r = await apiFetch(`${API}/agents/${agent.agent_id}/export`);
      const data = await r.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob); const a = document.createElement("a");
      a.href = url; a.download = `${agent.name.replace(/\s+/g, "_").toLowerCase()}_export.json`; a.click(); URL.revokeObjectURL(url);
      toast.success("Agent exported as JSON");
    } catch { toast.error("Export failed"); }
  };

  const exportAll = async () => {
    if (!filtered.length) return;
    try {
      const r = await apiFetch(`${API}/agents/export-bulk`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_ids: filtered.map(a => a.agent_id) }),
      });
      const data = await r.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob); const a = document.createElement("a");
      a.href = url; a.download = `agents_bulk_export_${new Date().toISOString().slice(0, 10)}.json`; a.click(); URL.revokeObjectURL(url);
      toast.success(`Exported ${data.count} agent${data.count !== 1 ? "s" : ""}`);
    } catch { toast.error("Bulk export failed"); }
  };

  const importAgent = async (file) => {
    setImportLoading(true);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      // Support both single-agent and bulk export formats
      if (parsed.agents && Array.isArray(parsed.agents)) {
        const r = await apiFetch(`${API}/agents/import-bulk`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(parsed),
        });
        const data = await r.json();
        toast.success(`Imported ${data.imported_count} agent${data.imported_count !== 1 ? "s" : ""}${data.error_count ? ` (${data.error_count} failed)` : ""}`);
      } else {
        const r = await apiFetch(`${API}/agents/import`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ agent_data: parsed, import_as_draft: true }),
        });
        const data = await r.json();
        toast.success(`Imported "${data.name}" as draft`);
      }
      load();
    } catch (e) { toast.error(e.message || "Import failed — invalid JSON file"); }
    setImportLoading(false);
    if (importInputRef.current) importInputRef.current.value = "";
  };

  // Agent detail view
  if (selectedAgent) {
    return (
      <div className="p-6 animate-fade-up max-w-5xl mx-auto space-y-6">
        <button onClick={() => setSelectedAgent(null)} className="text-sm text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer">
          <ChevronRight size={14} className="rotate-180" /> Back to Agents
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">{selectedAgent.name}</h1>
            <p className="text-sm text-slate-500 mt-1">{selectedAgent.description || "No description"}</p>
            <div className="flex gap-2 mt-3">
              {selectedAgent.rag_enabled && <Badge variant="brand"><Brain size={12} /> RAG</Badge>}
              {selectedAgent.tools_count > 0 && <Badge variant="info"><Wrench size={12} /> {selectedAgent.tools_count} Tools</Badge>}
              <Badge variant="outline">v{selectedAgent.version}</Badge>
              <Badge variant="outline">{selectedAgent.category || "agent"}</Badge>
            </div>
            <EnvVersionMeta assetId={selectedAgent.agent_id} className="mt-2" />
          </div>
          <div className="flex items-center gap-2">
            <span className={cn("text-xs font-semibold px-2.5 py-1 rounded-full", selectedAgent.status === "active" ? "text-emerald-600 bg-emerald-50" : "text-slate-400 bg-slate-100")}>{selectedAgent.status === "active" ? "● Active" : "○ Draft"}</span>
            <button onClick={() => { setChatAgent(selectedAgent.agent_id); setPage("Chat"); }}
              className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover transition">
              <MessageSquare size={14} /> Chat
            </button>
            {canEditEnv() && <button onClick={() => { setEditAgent(selectedAgent); setPage("AgentBuilder"); }}
              className="flex items-center gap-2 bg-white border border-slate-200 text-slate-700 rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-slate-50">
              <Edit3 size={14} /> Edit
            </button>}
            <AgentCardMenu agent={selectedAgent} onEdit={() => { setEditAgent(selectedAgent); setPage("AgentBuilder"); }} onClone={() => openCloneDialog(selectedAgent)} onApi={() => setApiOpenAgent(selectedAgent.agent_id)} onExport={() => exportAgent(selectedAgent)} onToggleStatus={() => toggleAgentStatus(selectedAgent)} onDelete={() => deleteAgent(selectedAgent)} canEdit={canEditEnv()} />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard label="Total Runs" value="—" icon={Activity} />
          <StatCard label="Avg Latency" value="—" icon={Clock} />
          <StatCard label="Cost (30d)" value="—" icon={DollarSign} />
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-900">Configuration</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><span className="text-slate-500">Model:</span> <span className="text-slate-900 font-medium">{selectedAgent.model || "gemini-2.5-flash"}</span></div>
            <div><span className="text-slate-500">RAG:</span> <span className="text-slate-900 font-medium">{selectedAgent.rag_enabled ? "Enabled" : "Disabled"}</span></div>
            <div className="col-span-2"><span className="text-slate-500">System Prompt:</span>
              <pre className="mt-1 p-3 bg-slate-50 rounded-lg text-xs font-mono text-slate-700 whitespace-pre-wrap">{selectedAgent.context || "No system prompt configured"}</pre>
            </div>
          </div>
        </div>

        {/* Version History — real from backend */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2"><History size={14} className="text-slate-400" /> Version History</h3>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Current: v{selectedAgent.version || 1}</span>
              <button onClick={() => loadVersions(selectedAgent.agent_id)} className="text-xs text-slate-400 hover:text-slate-700 cursor-pointer"><RefreshCw size={12} /></button>
            </div>
          </div>
          {versionsLoading ? (
            <div className="p-6 text-center text-sm text-slate-400"><Loader2 size={14} className="inline animate-spin mr-1" /> Loading versions...</div>
          ) : versions.length === 0 ? (
            <div className="p-6 text-center text-sm text-slate-400">No version history available</div>
          ) : (
            <div className="divide-y divide-slate-50">
              {versions.slice().reverse().map((v, i) => {
                const isCurrent = v.version === selectedAgent.version;
                const isFirst = v.version === 1;
                return (
                  <div key={v.version} className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50/50 transition">
                    <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold",
                      isCurrent ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-400")}>
                      v{v.version}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-slate-900">
                        {isCurrent ? "Current version" : isFirst ? "Initial creation" : `Version ${v.version}`}
                        {v.status && <Badge variant={v.status === "active" ? "success" : "default"} className="ml-2">{v.status}</Badge>}
                      </div>
                      <div className="text-xs text-slate-400">{relativeTime(v.updated_at)}</div>
                    </div>
                    {isCurrent ? (
                      <Badge variant="success">Current</Badge>
                    ) : (
                      <div className="flex gap-1.5">
                        <button onClick={() => loadDiff(selectedAgent.agent_id, v.version, selectedAgent.version)}
                          disabled={diffLoading}
                          className="text-xs text-slate-500 hover:text-slate-900 border border-slate-200 rounded-lg px-2 py-1 cursor-pointer hover:bg-slate-50 flex items-center gap-1 transition">
                          <GitCompare size={11} /> Diff
                        </button>
                        {canEditEnv() && (
                          <button onClick={() => doRollback(selectedAgent.agent_id, v.version)}
                            disabled={rollbackLoading}
                            className="text-xs text-amber-600 hover:text-amber-800 border border-amber-200 rounded-lg px-2 py-1 cursor-pointer hover:bg-amber-50 flex items-center gap-1 transition">
                            <RotateCcw size={11} /> Rollback
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Promote to Environment */}
        {currentEnv !== "prod" && (
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2"><ArrowUpRight size={14} className="text-slate-400" /> Environment Promotion</h3>
                <p className="text-xs text-slate-500 mt-1">Promote this agent to a higher environment</p>
              </div>
              <button onClick={() => setShowPromoteModal(true)}
                className="flex items-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-blue-700 transition">
                <ArrowRight size={14} /> Promote
              </button>
            </div>
          </div>
        )}

        {/* Diff Modal */}
        {showDiffModal && diffData && (
          <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setShowDiffModal(false)}>
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between shrink-0">
                <div>
                  <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2"><GitCompare size={16} /> Version Diff</h3>
                  <p className="text-xs text-slate-500 mt-0.5">v{diffData.version_a} → v{diffData.version_b} · {diffData.total_changes} change{diffData.total_changes !== 1 ? "s" : ""}</p>
                </div>
                <button onClick={() => setShowDiffModal(false)} className="text-slate-400 hover:text-slate-700 cursor-pointer"><XCircle size={18} /></button>
              </div>
              <div className="flex-1 overflow-y-auto p-6 space-y-3">
                {diffData.total_changes === 0 ? (
                  <div className="text-center text-sm text-slate-400 py-8">No differences between these versions</div>
                ) : (
                  diffData.changes.map((ch, i) => (
                    <div key={i} className="border border-slate-200 rounded-lg overflow-hidden">
                      <div className="px-4 py-2 bg-slate-50 border-b border-slate-100">
                        <span className="text-xs font-semibold text-slate-700">{ch.field}</span>
                      </div>
                      <div className="grid grid-cols-2 divide-x divide-slate-100">
                        <div className="p-3">
                          <div className="text-[11px] font-semibold text-red-500 uppercase mb-1">v{diffData.version_a}</div>
                          <pre className="text-xs text-slate-600 whitespace-pre-wrap font-mono bg-red-50/50 rounded p-2 max-h-40 overflow-auto">
                            {typeof ch[`v${diffData.version_a}`] === "object" ? JSON.stringify(ch[`v${diffData.version_a}`], null, 2) : String(ch[`v${diffData.version_a}`] ?? "—")}
                          </pre>
                        </div>
                        <div className="p-3">
                          <div className="text-[11px] font-semibold text-emerald-500 uppercase mb-1">v{diffData.version_b}</div>
                          <pre className="text-xs text-slate-600 whitespace-pre-wrap font-mono bg-emerald-50/50 rounded p-2 max-h-40 overflow-auto">
                            {typeof ch[`v${diffData.version_b}`] === "object" ? JSON.stringify(ch[`v${diffData.version_b}`], null, 2) : String(ch[`v${diffData.version_b}`] ?? "—")}
                          </pre>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Promote Modal */}
        {showPromoteModal && selectedAgent && (
          <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setShowPromoteModal(false)}>
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
              <div className="px-6 py-4 border-b border-slate-200">
                <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2"><ArrowRight size={16} /> Promote Agent</h3>
                <p className="text-xs text-slate-500 mt-0.5">Promote <strong>{selectedAgent.name}</strong> (v{selectedAgent.version}) from {currentEnv.toUpperCase()}</p>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1.5">Target Environment</label>
                  <select value={promoteTarget} onChange={e => setPromoteTarget(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none">
                    {["dev", "qa", "uat", "prod"].filter(e => {
                      const order = ["dev", "qa", "uat", "prod"];
                      return order.indexOf(e) > order.indexOf(currentEnv);
                    }).map(e => <option key={e} value={e}>{e.toUpperCase()}</option>)}
                  </select>
                </div>
                {promoteTarget === "prod" && (
                  <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3">
                    <AlertTriangle size={14} className="text-red-500 mt-0.5 shrink-0" />
                    <div className="text-xs text-red-700">Production promotion requires approval before deployment.</div>
                  </div>
                )}
                {promoteTarget === "uat" && (
                  <div className="flex items-start gap-2 bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <AlertTriangle size={14} className="text-blue-500 mt-0.5 shrink-0" />
                    <div className="text-xs text-blue-700">UAT promotion requires stakeholder approval.</div>
                  </div>
                )}
                {promoteTarget === "qa" && (
                  <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3">
                    <CheckCircle2 size={14} className="text-amber-600 mt-0.5 shrink-0" />
                    <div className="text-xs text-amber-700">QA promotion is auto-approved and will deploy immediately.</div>
                  </div>
                )}
              </div>
              <div className="px-6 py-3 border-t border-slate-100 flex justify-end gap-2">
                <button onClick={() => setShowPromoteModal(false)} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50">Cancel</button>
                <button onClick={() => doPromote(selectedAgent)} disabled={promoteLoading}
                  className={cn("px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg cursor-pointer hover:bg-blue-700 transition flex items-center gap-2", promoteLoading && "opacity-60")}>
                  {promoteLoading ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                  Promote to {promoteTarget.toUpperCase()}
                </button>
              </div>
            </div>
          </div>
        )}

        {apiOpenAgent === selectedAgent.agent_id && <ApiSnippetModal type="agent" id={selectedAgent.agent_id} name={selectedAgent.name} onClose={() => setApiOpenAgent(null)} />}
      </div>
    );
  }

  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <div><h1 className="text-xl font-semibold text-slate-900">Agents</h1><p className="text-sm text-slate-500 mt-1">Create, configure, and deploy AI agents from templates or scratch</p></div>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <SearchInput value={search} onChange={setSearch} placeholder="Search agents..." />
        <div className="flex-1" />
        <input ref={importInputRef} type="file" accept=".json" className="hidden" onChange={e => { if (e.target.files?.[0]) importAgent(e.target.files[0]); }} />
        {/* Overflow menu for secondary actions */}
        <AgentListOverflow onTemplates={() => setPage("Templates")} onImport={() => importInputRef.current?.click()} onExportAll={exportAll} importLoading={importLoading} canEdit={canEditEnv()} hasAgents={filtered.length > 0} />
        {/* Single primary CTA */}
        {canEditEnv() && <button onClick={() => setPage("AgentBuilder")} className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover transition shadow-sm">
          <Plus size={14} /> New Agent
        </button>}
      </div>
      {showCreate && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
          <h3 className="text-base font-semibold text-slate-900">Create Agent</h3>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs text-slate-500">Name</label><input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="My Agent" /></div>
            <div><label className="text-xs text-slate-500">Description</label><input value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="What does this agent do?" /></div>
          </div>
          <div><label className="text-xs text-slate-500">Context</label><textarea value={form.context} onChange={e => setForm(p => ({ ...p, context: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none h-16 resize-y" placeholder="System context..." /></div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-900"><input type="checkbox" checked={form.rag_enabled} onChange={e => setForm(p => ({ ...p, rag_enabled: e.target.checked }))} className="accent-emerald-500" /> Enable RAG</label>
            <div className="flex-1" />
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 cursor-pointer hover:bg-slate-50">Cancel</button>
            <button onClick={create} disabled={!form.name} className={cn("bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer", !form.name && "opacity-50")}>Create Agent</button>
          </div>
        </div>
      )}
      <div className="text-sm font-medium text-slate-700">{filtered.length} {filtered.length === 1 ? "Agent" : "Agents"}</div>
      {filtered.length === 0 && !loading ? (
        <EmptyState icon={<Search size={24} />} illustration="search" title="No agents found" description="We couldn't find any agents matching your search." action={<button onClick={() => setShowCreate(true)} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} className="inline mr-1" />Create Agent</button>} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(a => (
            <div key={a.agent_id} className="flex">
              <div className="flex flex-col w-full bg-white border border-slate-200/80 rounded-xl overflow-hidden hover:shadow-lg hover:-translate-y-0.5 hover:border-slate-300 transition-all duration-200 cursor-pointer" onClick={() => setSelectedAgent(a)}>
                <div className="p-5 flex-1 flex flex-col">
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-base font-semibold text-slate-900">{a.name}</div>
                    <Badge variant="outline">{a.category || "agent"}</Badge>
                  </div>
                  <div className="text-sm text-slate-500 mt-2 line-clamp-2 flex-1">{a.description || "\u00A0"}</div>
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {a.rag_enabled && <Badge variant="brand"><Brain size={10} /> RAG</Badge>}
                    {a.tools_count > 0 && <Badge variant="info"><Wrench size={10} /> Tools</Badge>}
                    <Badge variant="outline">v{a.version}</Badge>
                  </div>
                </div>
                <div className="px-5 py-3 border-t border-slate-100 flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className={cn("text-[11px] font-semibold px-2 py-0.5 rounded-full", a.status === "active" ? "text-emerald-600 bg-emerald-50" : "text-slate-400 bg-slate-100")}>{a.status === "active" ? "● Active" : "○ Draft"}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <AgentCardMenu agent={a} onEdit={() => { setEditAgent(a); setPage("AgentBuilder"); }} onClone={() => openCloneDialog(a)} onApi={() => setApiOpenAgent(a.agent_id)} onExport={() => exportAgent(a)} onToggleStatus={() => toggleAgentStatus(a)} onDelete={() => deleteAgent(a)} canEdit={canEditEnv()} />
                    <button onClick={e => { e.stopPropagation(); setChatAgent(a.agent_id); setPage("Chat"); }} className="text-xs text-white bg-jai-primary rounded-lg px-3 py-1.5 flex items-center gap-1 cursor-pointer font-medium hover:bg-jai-primary-hover transition"><MessageSquare size={12} /> Chat</button>
                  </div>
                </div>
              </div>
              {apiOpenAgent === a.agent_id && <ApiSnippetModal type="agent" id={a.agent_id} name={a.name} onClose={() => setApiOpenAgent(null)} />}
            </div>
          ))}
        </div>
      )}

      {/* Clone Agent Dialog */}
      {cloneTarget && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setCloneTarget(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6" onClick={e => e.stopPropagation()}>
            <h3 className="text-base font-semibold text-slate-900">Clone Agent</h3>
            <p className="text-sm text-slate-500 mt-1">Create a copy of <span className="font-medium text-slate-700">{cloneTarget.name}</span> with a new name.</p>
            <div className="mt-4">
              <label className="text-xs font-medium text-slate-500 block mb-1">New Agent Name</label>
              <input ref={cloneInputRef} value={cloneName} onChange={e => setCloneName(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") doClone(); if (e.key === "Escape") setCloneTarget(null); }}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition"
                placeholder="Enter a name for the cloned agent..." autoFocus />
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setCloneTarget(null)} className="px-4 py-2 text-sm font-medium text-slate-600 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50 transition">Cancel</button>
              <button onClick={doClone} disabled={!cloneName.trim()} className={cn("px-4 py-2 text-sm font-medium text-white bg-slate-800 rounded-lg cursor-pointer hover:bg-slate-900 transition", !cloneName.trim() && "opacity-50 cursor-not-allowed")}>
                <Copy size={13} className="inline mr-1.5 -mt-0.5" />Clone Agent
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
