"use client";
import { useState, useEffect } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, SearchInput, EmptyState, StatCard, Tabs, relativeTime } from "../shared/StudioUI";
import { ScrollText, Search, Eye, Clock, DollarSign, Check, X, AlertTriangle, History } from "lucide-react";

export default function LLMLogsPage() {
  const [logs, setLogs] = useState([]); const [loading, setLoading] = useState(true);
  const [diagnostics, setDiagnostics] = useState(null);
  const [filter, setFilter] = useState({ model: "", status: "", provider: "" });
  const [tab, setTab] = useState("Logs");
  const [page, setLogPage] = useState(1);
  const PAGE_SIZE = 25;
  const load = (retry = true) => {
    setLoading(true);
    let url = `${API}/llm-logs?limit=200`;
    if (filter.status) url += `&status=${filter.status}`;
    if (filter.provider) url += `&provider=${filter.provider}`;
    fetch(url).then(r => r.json()).then(d => { setLogs(d.logs || []); setLoading(false); setLogPage(1); })
      .catch(() => { if (retry) { setTimeout(() => load(false), 1500); } else { setLoading(false); } });
    apiFetch(`${API}/llm-logs/diagnostics/summary?period_minutes=60`).then(r => r.json()).then(setDiagnostics).catch(() => {});
  };
  useEffect(() => { load(); }, [filter]);
  const totalPages = Math.max(1, Math.ceil(logs.length / PAGE_SIZE));
  const pagedLogs = logs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div className="flex items-center gap-2"><ScrollText size={20} className="text-slate-500" /><h1 className="text-xl font-semibold text-slate-900">Logs & Diagnostics</h1><p className="text-sm text-slate-400 ml-2 mt-0.5">LLM request/response logs and system health</p></div>
      <Tabs tabs={["Logs", "Diagnostics"]} active={tab} onChange={setTab} />
      {tab === "Diagnostics" && diagnostics && (
        <div className="space-y-4">
          <div className="grid grid-cols-5 gap-3">
            <StatCard label="Requests" value={diagnostics.total_requests} /><StatCard label="Error Rate" value={`${diagnostics.error_rate}%`} /><StatCard label="Avg Latency" value={`${diagnostics.avg_latency_ms}ms`} /><StatCard label="Tokens" value={diagnostics.total_tokens} /><StatCard label="Cost" value={`$${diagnostics.total_cost_usd}`} />
          </div>
        </div>
      )}
      {tab === "Logs" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 flex-wrap">
            <select value={filter.status} onChange={e => setFilter(p => ({ ...p, status: e.target.value }))} className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none w-36"><option value="">All Status</option><option value="success">Success</option><option value="error">Error</option></select>
            <select value={filter.provider} onChange={e => setFilter(p => ({ ...p, provider: e.target.value }))} className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none w-36"><option value="">All Providers</option><option value="google">Google</option><option value="anthropic">Anthropic</option><option value="openai">OpenAI</option></select>
            <button onClick={load} className="flex items-center gap-1 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 cursor-pointer hover:bg-slate-50"><History size={14} /> Refresh</button>
            <div className="flex-1" />
            <span className="text-xs text-slate-400">{logs.length} logs</span>
          </div>
          {loading ? <div className="text-slate-400 text-sm">Loading logs...</div> : logs.length === 0 ? (
            <EmptyState icon={<ScrollText size={24} />} illustration="analytics" title="No LLM logs yet" description="LLM request/response logs will appear here." />
          ) : (
            <>
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-xs">
                  <thead><tr className="border-b border-slate-200 bg-slate-50">{["Time", "Model", "Provider", "Tokens", "Latency", "Cost", "Status"].map(h => <th key={h} className="text-left px-3 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">{h}</th>)}</tr></thead>
                  <tbody className="divide-y divide-slate-100">{pagedLogs.map((l, i) => (
                    <tr key={i} className="hover:bg-slate-50 transition">
                      <td className="px-3 py-2 text-slate-400">{new Date(l.timestamp).toLocaleTimeString()}</td>
                      <td className="px-3 py-2 font-medium text-slate-900">{l.model}</td>
                      <td className="px-3 py-2 text-slate-500">{l.provider}</td>
                      <td className="px-3 py-2 text-slate-900">{l.total_tokens}</td>
                      <td className={cn("px-3 py-2", l.latency_ms > 2000 ? "text-amber-600" : "text-slate-900")}>{l.latency_ms}ms</td>
                      <td className="px-3 py-2 text-emerald-600">${l.cost_usd}</td>
                      <td className="px-3 py-2"><Badge variant={l.status === "success" ? "success" : "danger"}>{l.status}</Badge></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, logs.length)} of {logs.length}</span>
                  <div className="flex items-center gap-1">
                    <button onClick={() => setLogPage(Math.max(1, page - 1))} disabled={page === 1}
                      className={cn("px-2.5 py-1 rounded-lg text-xs border cursor-pointer transition", page === 1 ? "opacity-40 cursor-not-allowed border-slate-200 text-slate-400" : "border-slate-200 text-slate-600 hover:bg-slate-50")}>Prev</button>
                    {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                      let p;
                      if (totalPages <= 7) p = i + 1;
                      else if (page <= 4) p = i + 1;
                      else if (page >= totalPages - 3) p = totalPages - 6 + i;
                      else p = page - 3 + i;
                      return (
                        <button key={p} onClick={() => setLogPage(p)}
                          className={cn("w-7 h-7 rounded-lg text-xs font-medium cursor-pointer transition", p === page ? "bg-jai-primary text-white" : "text-slate-500 hover:bg-slate-100")}>{p}</button>
                      );
                    })}
                    <button onClick={() => setLogPage(Math.min(totalPages, page + 1))} disabled={page === totalPages}
                      className={cn("px-2.5 py-1 rounded-lg text-xs border cursor-pointer transition", page === totalPages ? "opacity-40 cursor-not-allowed border-slate-200 text-slate-400" : "border-slate-200 text-slate-600 hover:bg-slate-50")}>Next</button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
