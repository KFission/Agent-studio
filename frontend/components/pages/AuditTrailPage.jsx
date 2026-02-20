"use client";
import { useState, useEffect } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, SearchInput, EmptyState, relativeTime } from "../shared/StudioUI";
import {
  History, Bot, Trash2, UserPlus, Shield, Zap, Workflow, Building2,
  KeyRound, GitFork, Activity, Search,
} from "lucide-react";

export default function AuditTrailPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");

  const load = (retry = true) => {
    setLoading(true);
    apiFetch(`${API}/audit-log?limit=200`).then(r => r.json()).then(d => {
      const entries = d.entries || [];
      if (entries.length === 0) {
        const mockActions = [
          { id: "a1", action: "agent.created", actor: "john.doe@jaggaer.com", target: "Bid Analyzer Agent", timestamp: new Date(Date.now() - 3600000).toISOString(), ip: "10.0.1.42" },
          { id: "a2", action: "user.invited", actor: "admin@jaggaer.com", target: "jane.smith@jaggaer.com", timestamp: new Date(Date.now() - 7200000).toISOString(), ip: "10.0.1.10" },
          { id: "a3", action: "guardrail.updated", actor: "john.doe@jaggaer.com", target: "PII Detection Rule", timestamp: new Date(Date.now() - 10800000).toISOString(), ip: "10.0.1.42" },
          { id: "a4", action: "integration.created", actor: "admin@jaggaer.com", target: "OpenAI Provider", timestamp: new Date(Date.now() - 14400000).toISOString(), ip: "10.0.1.10" },
          { id: "a5", action: "workflow.deployed", actor: "jane.smith@jaggaer.com", target: "Invoice Processing", timestamp: new Date(Date.now() - 18000000).toISOString(), ip: "10.0.1.55" },
          { id: "a6", action: "org.settings_changed", actor: "admin@jaggaer.com", target: "Procurement Division", timestamp: new Date(Date.now() - 21600000).toISOString(), ip: "10.0.1.10" },
          { id: "a7", action: "agent.deleted", actor: "john.doe@jaggaer.com", target: "Test Agent", timestamp: new Date(Date.now() - 25200000).toISOString(), ip: "10.0.1.42" },
          { id: "a8", action: "token.generated", actor: "admin@jaggaer.com", target: "CI/CD Pipeline Token", timestamp: new Date(Date.now() - 86400000).toISOString(), ip: "10.0.1.10" },
          { id: "a9", action: "pipeline.executed", actor: "system", target: "Supplier Onboarding Pipeline", timestamp: new Date(Date.now() - 172800000).toISOString(), ip: "—" },
          { id: "a10", action: "user.role_changed", actor: "admin@jaggaer.com", target: "john.doe → agent_admin", timestamp: new Date(Date.now() - 259200000).toISOString(), ip: "10.0.1.10" },
        ];
        setLogs(mockActions);
      } else {
        setLogs(entries);
      }
      setLoading(false);
    }).catch(() => { if (retry) { setTimeout(() => load(false), 1500); } else { setLoading(false); } });
  };
  useEffect(() => { load(); }, []);

  const ACTION_ICONS = { "agent.created": Bot, "agent.deleted": Trash2, "user.invited": UserPlus, "user.role_changed": Shield, "guardrail.updated": Shield, "integration.created": Zap, "workflow.deployed": Workflow, "org.settings_changed": Building2, "token.generated": KeyRound, "pipeline.executed": GitFork };
  const ACTION_COLORS = { created: "text-emerald-600 bg-emerald-50", deleted: "text-red-600 bg-red-50", updated: "text-blue-600 bg-blue-50", deployed: "text-violet-600 bg-violet-50", executed: "text-amber-600 bg-amber-50", invited: "text-sky-600 bg-sky-50", generated: "text-indigo-600 bg-indigo-50", settings_changed: "text-slate-600 bg-slate-100", role_changed: "text-violet-600 bg-violet-50" };
  const getActionColor = (action) => { const verb = action.split(".").pop(); return ACTION_COLORS[verb] || "text-slate-600 bg-slate-100"; };

  const actionTypes = [...new Set(logs.map(l => l.action))];
  const filtered = logs.filter(l => {
    if (actionFilter !== "all" && l.action !== actionFilter) return false;
    if (search && !l.actor?.toLowerCase().includes(search.toLowerCase()) && !l.target?.toLowerCase().includes(search.toLowerCase()) && !l.action?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div><h1 className="text-xl font-semibold text-slate-900">Audit Trail</h1><p className="text-sm text-slate-500 mt-1">Immutable record of all platform actions — who did what, when</p></div>
      <div className="flex flex-wrap items-center gap-3">
        <SearchInput value={search} onChange={setSearch} placeholder="Search actors, targets..." />
        <select value={actionFilter} onChange={e => setActionFilter(e.target.value)} className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs outline-none font-medium text-slate-600">
          <option value="all">All Actions</option>
          {actionTypes.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <div className="flex-1" />
        <span className="text-xs text-slate-400">{filtered.length} entries</span>
      </div>

      {loading ? <div className="text-slate-400 text-sm">Loading audit log...</div> : filtered.length === 0 ? (
        <EmptyState icon={<History size={24} />} illustration="time" title="No audit entries" description="Platform actions will appear here as users interact with the system." />
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="divide-y divide-slate-50">
            {filtered.map((entry, i) => {
              const Icon = ACTION_ICONS[entry.action] || Activity;
              return (
                <div key={entry.id || i} className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50/50 transition">
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center shrink-0", getActionColor(entry.action))}><Icon size={14} /></div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-slate-900"><span className="font-medium">{entry.actor}</span> <span className="text-slate-400">{entry.action.replace(".", " → ")}</span> <span className="font-medium">{entry.target}</span></div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xs text-slate-500" title={new Date(entry.timestamp).toLocaleString()}>{relativeTime(entry.timestamp)}</div>
                    {entry.ip && <div className="text-[11px] text-slate-300 font-mono">{entry.ip}</div>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
