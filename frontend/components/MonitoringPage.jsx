"use client";
import { useState, useEffect } from "react";
import { Activity, Zap, DollarSign, Clock, RefreshCw, ChevronLeft, ChevronRight, Loader2, Users, Layers, Copy, ExternalLink, Star, Filter, Search, X, Hash, BarChart3, ScrollText, AlertTriangle, History } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

function apiFetch(url, opts = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("jai_token") : null;
  return fetch(url, { ...opts, headers: { ...opts.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) } });
}

function Badge({ children, variant = "default", className = "" }) {
  const colors = {
    default: "bg-slate-100 text-slate-600 border-slate-200",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    error: "bg-red-50 text-red-700 border-red-200",
    info: "bg-blue-50 text-blue-700 border-blue-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
    purple: "bg-violet-50 text-violet-700 border-violet-200",
    cyan: "bg-cyan-50 text-cyan-700 border-cyan-200",
  };
  return <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium border ${colors[variant] || colors.default} ${className}`}>{children}</span>;
}

function cn(...classes) { return classes.filter(Boolean).join(" "); }

export default function MonitoringPage() {
  const [tab, setTab] = useState("Tracing");
  const [status, setStatus] = useState(null);
  const [traces, setTraces] = useState([]);
  const [generations, setGenerations] = useState([]);
  const [scores, setScores] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [traceDetail, setTraceDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailTab, setDetailTab] = useState("Preview");
  const [selectedObs, setSelectedObs] = useState(null);
  const [modelFilter, setModelFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // LLM Logs state (merged from LLMLogsPage)
  const [llmLogs, setLlmLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [diagnostics, setDiagnostics] = useState(null);
  const [logFilter, setLogFilter] = useState({ status: "", provider: "" });
  const [logPage, setLogPage] = useState(1);
  const LOG_PAGE_SIZE = 25;

  const loadLogs = () => {
    setLogsLoading(true);
    let url = `${API}/llm-logs?limit=200`;
    if (logFilter.status) url += `&status=${logFilter.status}`;
    if (logFilter.provider) url += `&provider=${logFilter.provider}`;
    apiFetch(url).then(r => r.json()).then(d => { setLlmLogs(d.logs || []); setLogsLoading(false); setLogPage(1); }).catch(() => setLogsLoading(false));
    apiFetch(`${API}/llm-logs/diagnostics/summary?period_minutes=60`).then(r => r.json()).then(setDiagnostics).catch(() => {});
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiFetch(`${API}/monitoring/status`).then(r => r.json()).catch(() => ({ enabled: false, connected: false })),
      apiFetch(`${API}/monitoring/traces?limit=100`).then(r => r.json()).catch(() => ({ traces: [] })),
      apiFetch(`${API}/monitoring/generations?limit=100`).then(r => r.json()).catch(() => ({ generations: [] })),
      apiFetch(`${API}/monitoring/scores?limit=100`).then(r => r.json()).catch(() => ({ scores: [] })),
      apiFetch(`${API}/monitoring/metrics`).then(r => r.json()).catch(() => null),
    ]).then(([st, tr, gn, sc, mt]) => {
      setStatus(st);
      setTraces(tr.traces || []);
      setGenerations(gn.generations || []);
      setScores(sc.scores || []);
      setMetrics(mt);
      setLoading(false);
    });
    loadLogs();
  }, []);

  useEffect(() => {
    if (tab === "LLMLogs" || tab === "Diagnostics") loadLogs();
  }, [logFilter]);

  const refresh = () => {
    setLoading(true);
    Promise.all([
      apiFetch(`${API}/monitoring/traces?limit=100`).then(r => r.json()).catch(() => ({ traces: [] })),
      apiFetch(`${API}/monitoring/generations?limit=100`).then(r => r.json()).catch(() => ({ generations: [] })),
      apiFetch(`${API}/monitoring/scores?limit=100`).then(r => r.json()).catch(() => ({ scores: [] })),
      apiFetch(`${API}/monitoring/metrics`).then(r => r.json()).catch(() => null),
    ]).then(([tr, gn, sc, mt]) => {
      setTraces(tr.traces || []);
      setGenerations(gn.generations || []);
      setScores(sc.scores || []);
      setMetrics(mt);
      setLoading(false);
    });
    loadLogs();
  };

  const logTotalPages = Math.max(1, Math.ceil(llmLogs.length / LOG_PAGE_SIZE));
  const pagedLogs = llmLogs.slice((logPage - 1) * LOG_PAGE_SIZE, logPage * LOG_PAGE_SIZE);

  const loadTraceDetail = async (traceId) => {
    setDetailLoading(true);
    setDetailTab("Preview");
    setSelectedObs(null);
    try {
      const r = await apiFetch(`${API}/monitoring/traces/${traceId}`);
      if (r.ok) setTraceDetail(await r.json());
    } catch {}
    setDetailLoading(false);
  };

  const openTrace = (t) => { setSelectedTrace(t); loadTraceDetail(t.trace_id); };
  const backToList = () => { setSelectedTrace(null); setTraceDetail(null); setSelectedObs(null); };

  const fmtTime = (ts) => { if (!ts) return "\u2014"; try { return new Date(ts).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }); } catch { return ts; } };
  const fmtFull = (ts) => { if (!ts) return "\u2014"; try { return new Date(ts).toISOString().replace("T", " ").replace("Z", ""); } catch { return ts; } };

  const uniqueModels = [...new Set(generations.map(g => g.model).filter(Boolean))];
  const filteredGenerations = modelFilter ? generations.filter(g => g.model === modelFilter) : generations;

  const filteredTraces = searchQuery
    ? traces.filter(t => (t.name || "").toLowerCase().includes(searchQuery.toLowerCase()) || (t.user_id || "").toLowerCase().includes(searchQuery.toLowerCase()) || (t.tags || []).some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase())))
    : traces;

  // ── Sidebar nav items ──
  const sidebarItems = [
    { section: "Observability", items: [
      { id: "Tracing", label: "Tracing", icon: Activity },
      { id: "LLMLogs", label: "LLM Logs", icon: ScrollText },
      { id: "Sessions", label: "Sessions", icon: Layers },
      { id: "Users", label: "Users", icon: Users },
    ]},
    { section: "Metrics", items: [
      { id: "Dashboard", label: "Dashboard", icon: BarChart3 },
      { id: "Diagnostics", label: "Diagnostics", icon: AlertTriangle },
    ]},
    { section: "Evaluation", items: [
      { id: "Scores", label: "Scores", icon: Star },
    ]},
  ];

  // ── Trace detail view (Langfuse-style) ──
  const TraceDetailView = () => {
    if (!selectedTrace) return null;
    const detail = traceDetail;
    const observations = detail?.observations || [];
    const activeObs = selectedObs ? observations.find(o => o.id === selectedObs) : null;
    const activeData = activeObs || detail;
    const isRoot = !selectedObs;

    // Build tree from observations (flat → nested by parent_observation_id)
    const buildTree = (obs) => {
      const roots = obs.filter(o => !o.parent_observation_id);
      const children = (parentId) => obs.filter(o => o.parent_observation_id === parentId);
      return { roots, children };
    };
    const { roots, children } = buildTree(observations);

    // Timeline tree node
    const TreeNode = ({ obs, depth = 0 }) => {
      const kids = children(obs.id);
      const isSelected = selectedObs === obs.id;
      const typeColors = { GENERATION: "bg-violet-500", SPAN: "bg-sky-400", EVENT: "bg-amber-400" };
      const typeIcons = { GENERATION: "✦", SPAN: "→", EVENT: "⚡" };
      return (
        <div>
          <div onClick={() => setSelectedObs(isSelected ? null : obs.id)}
            className={cn("flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-50 transition border-l-2",
              isSelected ? "border-l-violet-500 bg-violet-50/50" : "border-l-transparent",
              depth > 0 && "ml-4"
            )}>
            <span className={cn("w-4 h-4 rounded flex items-center justify-center text-white text-[11px] shrink-0",
              typeColors[obs.type] || "bg-slate-400")}>{typeIcons[obs.type] || "•"}</span>
            <span className="text-xs font-medium text-slate-800 truncate flex-1">{obs.name || obs.type}</span>
            {obs.type === "GENERATION" && obs.model && <span className="text-[11px] text-slate-400">{obs.model}</span>}
            {obs.level === "ERROR" && <Badge variant="error">ERROR</Badge>}
            <span className="text-[11px] text-slate-400 font-mono shrink-0">{obs.latency_ms ? `${obs.latency_ms.toFixed(1)}s` : ""}</span>
            {obs.total_tokens > 0 && <span className="text-[11px] text-slate-400 font-mono shrink-0">{obs.input_tokens} → {obs.output_tokens} (Σ {obs.total_tokens})</span>}
            {obs.total_cost > 0 && <span className="text-[11px] text-emerald-600 font-mono shrink-0">${obs.total_cost.toFixed(5)}</span>}
          </div>
          {kids.map(k => <TreeNode key={k.id} obs={k} depth={depth + 1} />)}
        </div>
      );
    };

    return (
      <div className="space-y-0">
        {/* Back button + trace header */}
        <div className="flex items-center gap-2 mb-3">
          <button onClick={backToList} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 cursor-pointer bg-transparent border-none transition">
            <ChevronLeft size={14} /> Back to traces
          </button>
        </div>

        {/* Trace header bar (like Langfuse) */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[11px] text-slate-400 font-mono">Trace:</span>
              <span className="text-xs font-mono text-slate-600">{selectedTrace.trace_id}</span>
              <button onClick={() => navigator.clipboard?.writeText(selectedTrace.trace_id)} className="text-slate-300 hover:text-slate-500 cursor-pointer"><Copy size={11} /></button>
            </div>
            <div className="flex items-center gap-2 text-xs mb-2">
              <span className="font-semibold text-slate-900 text-sm">{selectedTrace.name || "Trace"}</span>
              <Badge variant={selectedTrace.status === "error" ? "error" : "success"}>{selectedTrace.status}</Badge>
            </div>
            {/* Metadata badges */}
            <div className="flex items-center gap-2 flex-wrap">
              {selectedTrace.session_id && <Badge variant="cyan">Session: {selectedTrace.session_id}</Badge>}
              {selectedTrace.user_id && <Badge variant="purple">User: {selectedTrace.user_id}</Badge>}
              {(selectedTrace.tags || []).map(t => <Badge key={t} variant="info">{t}</Badge>)}
              {selectedTrace.latency_ms > 0 && <span className="text-[11px] text-slate-500">Latency: {(selectedTrace.latency_ms / 1000).toFixed(2)}s</span>}
              {(detail?.total_tokens > 0 || observations.some(o => o.total_tokens > 0)) && (
                <span className="text-[11px] text-slate-500">
                  {observations.reduce((s, o) => s + (o.input_tokens || 0), 0)} → {observations.reduce((s, o) => s + (o.output_tokens || 0), 0)}
                  {" "}(Σ {observations.reduce((s, o) => s + (o.total_tokens || 0), 0)})
                </span>
              )}
              <span className="text-[11px] text-slate-400">{fmtFull(selectedTrace.timestamp)}</span>
            </div>
          </div>

          {/* Two-panel layout: left=tree, right=detail */}
          <div className="flex" style={{ minHeight: "500px" }}>
            {/* Left: Timeline tree */}
            <div className="w-[380px] shrink-0 border-r border-slate-200 overflow-y-auto">
              <div className="px-3 py-2 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-500 uppercase">Timeline</span>
              </div>
              {/* Root trace node */}
              <div onClick={() => setSelectedObs(null)}
                className={cn("flex items-center gap-2 px-3 py-2.5 cursor-pointer hover:bg-slate-50 border-l-2 border-b border-slate-100",
                  !selectedObs ? "border-l-blue-500 bg-blue-50/30" : "border-l-transparent")}>
                <span className="w-4 h-4 rounded bg-blue-500 flex items-center justify-center text-white text-[11px] shrink-0">T</span>
                <span className="text-xs font-semibold text-slate-800 flex-1">{selectedTrace.name || "trace"}</span>
                {selectedTrace.latency_ms > 0 && <span className="text-[11px] text-slate-400 font-mono">{(selectedTrace.latency_ms / 1000).toFixed(2)}s</span>}
              </div>
              {detailLoading ? (
                <div className="p-4 text-xs text-slate-400 flex items-center gap-2"><Loader2 size={12} className="animate-spin" /> Loading...</div>
              ) : (
                <div>
                  {roots.map(obs => <TreeNode key={obs.id} obs={obs} />)}
                  {observations.filter(o => !o.parent_observation_id).length === 0 && observations.length > 0 && (
                    observations.map(obs => <TreeNode key={obs.id} obs={obs} />)
                  )}
                  {observations.length === 0 && (
                    <div className="p-4 text-xs text-slate-400">No observations</div>
                  )}
                </div>
              )}
            </div>

            {/* Right: Detail panel */}
            <div className="flex-1 overflow-y-auto">
              {/* Detail tabs */}
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 flex items-center gap-4">
                {["Preview", "Scores", "Metadata", "JSON"].map(t => (
                  <button key={t} onClick={() => setDetailTab(t)}
                    className={cn("text-xs font-medium cursor-pointer pb-0.5 border-b-2 transition",
                      detailTab === t ? "text-slate-900 border-slate-900" : "text-slate-400 border-transparent hover:text-slate-600")}>
                    {t}
                  </button>
                ))}
              </div>

              <div className="p-4 space-y-4">
                {detailTab === "Preview" && (() => {
                  const rawInput = isRoot ? (detail?.input || selectedTrace.input || "—") : (activeObs?.input || "—");
                  const rawOutput = isRoot ? (detail?.output || selectedTrace.output || "—") : (activeObs?.output || "—");

                  // Extract readable content from API payloads
                  const extractContent = (raw) => {
                    if (!raw || raw === "—") return { content: "—", hasFullPayload: false };
                    let parsed = raw;
                    if (typeof raw === "string") {
                      try { parsed = JSON.parse(raw); } catch {
                        // Handle Python dict repr (single quotes → double quotes)
                        try { parsed = JSON.parse(raw.replace(/'/g, '"')); } catch { return { content: raw, hasFullPayload: false }; }
                      }
                    }
                    // OpenAI-style messages array
                    if (Array.isArray(parsed)) {
                      const msgs = parsed.filter(m => m.role && m.content);
                      if (msgs.length > 0) {
                        const formatted = msgs.map(m => `**${m.role}:** ${m.content}`).join("\n\n");
                        return { content: formatted, hasFullPayload: true, messages: msgs };
                      }
                    }
                    // Object with messages array (e.g. { messages: [...], model: "..." })
                    if (parsed && typeof parsed === "object" && Array.isArray(parsed.messages)) {
                      const msgs = parsed.messages.filter(m => m.content);
                      if (msgs.length > 0) {
                        const formatted = msgs.map(m => `**${m.role || "unknown"}:** ${m.content}`).join("\n\n");
                        return { content: formatted, hasFullPayload: true, messages: msgs };
                      }
                    }
                    // Object with content field
                    if (parsed && typeof parsed === "object" && parsed.content) {
                      return { content: parsed.content, hasFullPayload: true };
                    }
                    // Object with text field
                    if (parsed && typeof parsed === "object" && parsed.text) {
                      return { content: parsed.text, hasFullPayload: true };
                    }
                    // Fallback: just stringify
                    if (typeof parsed === "object") {
                      return { content: JSON.stringify(parsed, null, 2), hasFullPayload: false };
                    }
                    return { content: String(parsed), hasFullPayload: false };
                  };

                  const inputData = extractContent(rawInput);
                  const outputData = extractContent(rawOutput);
                  const showFullPayload = typeof window !== "undefined" && window._monShowFull;

                  return (
                    <>
                      {/* Input */}
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs font-semibold text-slate-600">Input</span>
                          <div className="flex items-center gap-2">
                            {!isRoot && activeObs?.model && <Badge variant="info">{activeObs.model}</Badge>}
                            {inputData.messages && (
                              <span className="text-[11px] text-slate-400">{inputData.messages.length} message{inputData.messages.length !== 1 ? "s" : ""}</span>
                            )}
                          </div>
                        </div>
                        {inputData.messages ? (
                          <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 max-h-64 overflow-auto space-y-2">
                            {inputData.messages.map((m, i) => (
                              <div key={i} className={cn("rounded-lg px-3 py-2 text-xs leading-relaxed",
                                m.role === "user" ? "bg-blue-50 border border-blue-100" :
                                m.role === "assistant" ? "bg-emerald-50 border border-emerald-100" :
                                m.role === "system" ? "bg-amber-50 border border-amber-100" :
                                "bg-white border border-slate-200"
                              )}>
                                <div className="text-[11px] font-semibold text-slate-500 uppercase mb-0.5">{m.role}</div>
                                <div className="text-slate-700 whitespace-pre-wrap">{m.content}</div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <pre className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-xs text-slate-700 whitespace-pre-wrap max-h-64 overflow-auto leading-relaxed">
                            {inputData.content}
                          </pre>
                        )}
                      </div>
                      {/* Output */}
                      <div>
                        <div className="text-xs font-semibold text-slate-600 mb-1.5">Output</div>
                        {outputData.messages ? (
                          <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 max-h-96 overflow-auto space-y-2">
                            {outputData.messages.map((m, i) => (
                              <div key={i} className={cn("rounded-lg px-3 py-2 text-xs leading-relaxed",
                                m.role === "assistant" ? "bg-emerald-50 border border-emerald-100" : "bg-white border border-slate-200"
                              )}>
                                <div className="text-[11px] font-semibold text-slate-500 uppercase mb-0.5">{m.role}</div>
                                <div className="text-slate-700 whitespace-pre-wrap">{m.content}</div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <pre className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-xs text-slate-700 whitespace-pre-wrap max-h-96 overflow-auto leading-relaxed">
                            {outputData.content}
                          </pre>
                        )}
                      </div>
                      {/* Full API Payload toggle */}
                      {(inputData.hasFullPayload || outputData.hasFullPayload) && (
                        <details className="border border-slate-200 rounded-lg overflow-hidden">
                          <summary className="px-3 py-2 bg-slate-50 text-xs font-medium text-slate-500 cursor-pointer hover:bg-slate-100 select-none flex items-center gap-1.5">
                            <ChevronRight size={12} className="details-arrow transition-transform" />
                            Show Full API Request / Response
                          </summary>
                          <div className="p-3 space-y-3 bg-white">
                            <div>
                              <div className="text-[11px] font-semibold text-slate-400 uppercase mb-1">Raw Input</div>
                              <pre className="bg-slate-50 border border-slate-100 rounded-lg p-2.5 text-[11px] text-slate-600 whitespace-pre-wrap max-h-48 overflow-auto font-mono leading-relaxed">
                                {typeof rawInput === "object" ? JSON.stringify(rawInput, null, 2) : rawInput}
                              </pre>
                            </div>
                            <div>
                              <div className="text-[11px] font-semibold text-slate-400 uppercase mb-1">Raw Output</div>
                              <pre className="bg-slate-50 border border-slate-100 rounded-lg p-2.5 text-[11px] text-slate-600 whitespace-pre-wrap max-h-48 overflow-auto font-mono leading-relaxed">
                                {typeof rawOutput === "object" ? JSON.stringify(rawOutput, null, 2) : rawOutput}
                              </pre>
                            </div>
                          </div>
                        </details>
                      )}
                      {/* Stats: shown for both root trace (aggregated) and individual observations */}
                      {(() => {
                        const stats = isRoot ? {
                          type: "Trace",
                          latency: selectedTrace.latency_ms || observations.reduce((s, o) => Math.max(s, o.latency_ms || 0), 0),
                          inTok: observations.reduce((s, o) => s + (o.input_tokens || 0), 0),
                          outTok: observations.reduce((s, o) => s + (o.output_tokens || 0), 0),
                          totalTok: observations.reduce((s, o) => s + (o.total_tokens || 0), 0),
                          cost: observations.reduce((s, o) => s + (o.total_cost || 0), 0),
                          model: observations.find(o => o.model)?.model || "",
                        } : activeObs ? {
                          type: activeObs.type,
                          latency: activeObs.latency_ms || 0,
                          inTok: activeObs.input_tokens || 0,
                          outTok: activeObs.output_tokens || 0,
                          totalTok: activeObs.total_tokens || 0,
                          cost: activeObs.total_cost || 0,
                          model: activeObs.model || "",
                        } : null;
                        if (!stats) return null;
                        const hasTokens = stats.inTok > 0 || stats.outTok > 0;
                        return (
                          <div className="grid grid-cols-4 gap-3 text-xs border-t border-slate-100 pt-3">
                            <div><span className="text-slate-400 block">{isRoot ? "Model" : "Type"}</span><span className="text-slate-700">{isRoot ? (stats.model || "—") : stats.type}</span></div>
                            <div><span className="text-slate-400 block">Latency</span><span className="text-slate-700">{stats.latency ? `${stats.latency.toFixed ? stats.latency.toFixed(1) : stats.latency}ms` : "—"}</span></div>
                            <div><span className="text-slate-400 block">Tokens</span><span className="font-mono text-slate-700">{hasTokens ? `${stats.inTok} → ${stats.outTok} (Σ ${stats.totalTok})` : "—"}</span></div>
                            <div><span className="text-slate-400 block">Cost</span><span className="font-mono text-slate-700">{stats.cost > 0 ? `$${stats.cost.toFixed(6)}` : "—"}</span></div>
                          </div>
                        );
                      })()}
                    </>
                  );
                })()}

                {detailTab === "Scores" && (
                  <div>
                    {scores.filter(s => s.trace_id === selectedTrace.trace_id).length === 0 ? (
                      <div className="text-xs text-slate-400 py-4 text-center">No scores for this trace</div>
                    ) : (
                      <div className="space-y-2">
                        {scores.filter(s => s.trace_id === selectedTrace.trace_id).map(s => (
                          <div key={s.score_id} className="bg-slate-50 border border-slate-100 rounded-lg p-3 flex items-center gap-4">
                            <span className="text-xs font-medium text-slate-700">{s.name}</span>
                            <span className={cn("font-mono font-bold text-sm", (s.value ?? 0) >= 0.7 ? "text-emerald-600" : (s.value ?? 0) >= 0.4 ? "text-amber-600" : "text-red-600")}>{s.value}</span>
                            {s.comment && <span className="text-xs text-slate-400 flex-1">{s.comment}</span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {detailTab === "Metadata" && (
                  <div>
                    <pre className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-xs text-slate-600 font-mono whitespace-pre-wrap">
                      {JSON.stringify(isRoot ? (detail?.metadata || selectedTrace.metadata || {}) : (activeObs?.metadata || {}), null, 2)}
                    </pre>
                  </div>
                )}

                {detailTab === "JSON" && (() => {
                  const data = isRoot
                    ? { ...selectedTrace, ...(detail || {}), observations: (detail?.observations || []).map(o => ({ id: o.id, type: o.type, name: o.name, model: o.model, input: o.input, output: o.output, usage: { input_tokens: o.input_tokens, output_tokens: o.output_tokens, total_tokens: o.total_tokens }, latency_ms: o.latency_ms, total_cost: o.total_cost, level: o.level, metadata: o.metadata })) }
                    : activeObs || {};
                  return (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-600">{isRoot ? "Full Trace" : `Observation: ${activeObs?.name || activeObs?.type}`}</span>
                        <button onClick={() => navigator.clipboard?.writeText(JSON.stringify(data, null, 2))}
                          className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-600 cursor-pointer">
                          <Copy size={11} /> Copy JSON
                        </button>
                      </div>
                      <pre className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-[11px] text-slate-600 font-mono whitespace-pre-wrap max-h-[600px] overflow-auto leading-relaxed">
                        {JSON.stringify(data, null, 2)}
                      </pre>
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-[calc(100vh-48px)]">
      {/* Sidebar nav (Langfuse-style) */}
      <div className="w-48 bg-white border-r border-slate-200 shrink-0 overflow-y-auto">
        <div className="p-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className={cn("w-2 h-2 rounded-full", status?.connected ? "bg-emerald-500" : "bg-slate-300")} />
            <span className="text-xs font-semibold text-slate-700">Langfuse</span>
          </div>
        </div>
        {sidebarItems.map(section => (
          <div key={section.section} className="py-2">
            <div className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">{section.section}</div>
            {section.items.map(item => (
              <button key={item.id} onClick={() => { setTab(item.id); if (selectedTrace) backToList(); }}
                className={cn("w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 cursor-pointer transition",
                  tab === item.id ? "text-slate-900 bg-slate-100 font-medium" : "text-slate-500 hover:bg-slate-50 hover:text-slate-700")}>
                <item.icon size={13} /> {item.label}
              </button>
            ))}
          </div>
        ))}
        <div className="p-3 border-t border-slate-100 mt-2">
          <button onClick={refresh} className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 cursor-pointer">
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 animate-fade-up max-w-7xl mx-auto space-y-5">
          {loading && <div className="text-sm text-slate-400 py-8 text-center"><Loader2 size={16} className="animate-spin inline mr-2" />Loading monitoring data...</div>}

          {/* ══ TRACING TAB ══ */}
          {!loading && tab === "Tracing" && (
            selectedTrace ? <TraceDetailView /> : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-900">Traces</h2>
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search traces..."
                        className="pl-8 pr-3 py-1.5 border border-slate-200 rounded-lg text-xs bg-white outline-none w-48" />
                    </div>
                    <span className="text-xs text-slate-400">{filteredTraces.length} traces</span>
                  </div>
                </div>
                {/* KPI row */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                    { label: "Total Traces", value: metrics?.total_traces ?? traces.length, icon: Activity, color: "text-blue-600", bg: "bg-blue-50" },
                    { label: "Total Tokens", value: (metrics?.total_tokens || generations.reduce((s, g) => s + (g.total_tokens || 0), 0)).toLocaleString(), icon: Zap, color: "text-violet-600", bg: "bg-violet-50" },
                    { label: "Total Cost", value: `$${(metrics?.total_cost ?? 0).toFixed(4)}`, icon: DollarSign, color: "text-emerald-600", bg: "bg-emerald-50" },
                    { label: "Avg Latency", value: `${(metrics?.avg_latency_ms ?? 0).toFixed(0)} ms`, icon: Clock, color: "text-orange-600", bg: "bg-orange-50" },
                  ].map(k => (
                    <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-slate-500">{k.label}</span>
                        <div className={cn("w-7 h-7 rounded-lg flex items-center justify-center", k.bg)}><k.icon size={14} className={k.color} /></div>
                      </div>
                      <div className="text-xl font-bold text-slate-900">{k.value}</div>
                    </div>
                  ))}
                </div>
                {/* Trace table */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                  {filteredTraces.length === 0 ? (
                    <div className="p-8 text-center space-y-2">
                      <Activity size={32} className="mx-auto text-slate-300" />
                      <div className="text-sm text-slate-500 font-medium">No traces yet</div>
                      <div className="text-xs text-slate-400">Make LLM calls or use the Playground to generate traces.</div>
                    </div>
                  ) : (
                    <table className="w-full text-xs">
                      <thead><tr className="border-b border-slate-200 bg-slate-50">
                        {["Name", "User", "Status", "Model", "Tokens", "Latency", "Cost", "Time"].map(h => <th key={h} className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">{h}</th>)}
                      </tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {filteredTraces.map(t => (
                          <tr key={t.trace_id} onClick={() => openTrace(t)} className="hover:bg-slate-50 cursor-pointer transition">
                            <td className="px-4 py-2.5 font-medium text-slate-800 max-w-[180px] truncate">{t.name || "—"}</td>
                            <td className="px-4 py-2 text-slate-500 max-w-[120px] truncate">{t.user_id || "—"}</td>
                            <td className="px-4 py-2"><Badge variant={t.status === "error" ? "error" : "success"}>{t.status}</Badge></td>
                            <td className="px-4 py-2 text-slate-500">{(t.tags || []).filter(tg => tg !== "gateway").join(", ") || "—"}</td>
                            <td className="px-4 py-2 text-slate-600 font-mono">{t.total_tokens || 0}</td>
                            <td className="px-4 py-2 text-slate-600">{t.latency_ms ? `${(t.latency_ms / 1000).toFixed(2)}s` : "—"}</td>
                            <td className="px-4 py-2 text-slate-600 font-mono">${(t.total_cost || 0).toFixed(4)}</td>
                            <td className="px-4 py-2 text-slate-400">{fmtTime(t.timestamp)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            )
          )}

          {/* ══ SESSIONS TAB ══ */}
          {!loading && tab === "Sessions" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">Sessions</h2>
              <p className="text-xs text-slate-400">Group related traces by session for multi-turn conversations.</p>
              {(() => {
                const sessionMap = {};
                traces.forEach(t => { if (t.session_id) { if (!sessionMap[t.session_id]) sessionMap[t.session_id] = { id: t.session_id, count: 0, first: t.timestamp, last: t.timestamp }; sessionMap[t.session_id].count++; if (t.timestamp > sessionMap[t.session_id].last) sessionMap[t.session_id].last = t.timestamp; if (t.timestamp < sessionMap[t.session_id].first) sessionMap[t.session_id].first = t.timestamp; } });
                const sessionList = Object.values(sessionMap).sort((a, b) => (b.last || "").localeCompare(a.last || ""));
                return sessionList.length === 0 ? (
                  <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-sm text-slate-400">No sessions found. Set session_id in your API calls to group traces.</div>
                ) : (
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full text-xs">
                      <thead><tr className="border-b border-slate-200 bg-slate-50">
                        {["Session ID", "Traces", "First Seen", "Last Activity"].map(h => <th key={h} className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">{h}</th>)}
                      </tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {sessionList.map(s => (
                          <tr key={s.id} className="hover:bg-slate-50">
                            <td className="px-4 py-2.5 font-mono font-medium text-slate-800">{s.id}</td>
                            <td className="px-4 py-2 text-slate-600">{s.count}</td>
                            <td className="px-4 py-2 text-slate-400">{fmtTime(s.first)}</td>
                            <td className="px-4 py-2 text-slate-400">{fmtTime(s.last)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              })()}
            </div>
          )}

          {/* ══ USERS TAB ══ */}
          {!loading && tab === "Users" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">Users</h2>
              <p className="text-xs text-slate-400">See which users are generating LLM traces.</p>
              {(() => {
                const userMap = {};
                traces.forEach(t => { if (t.user_id) { if (!userMap[t.user_id]) userMap[t.user_id] = { id: t.user_id, count: 0, tokens: 0, last: t.timestamp }; userMap[t.user_id].count++; userMap[t.user_id].tokens += (t.total_tokens || 0); if (t.timestamp > userMap[t.user_id].last) userMap[t.user_id].last = t.timestamp; } });
                const userList = Object.values(userMap).sort((a, b) => b.count - a.count);
                return userList.length === 0 ? (
                  <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-sm text-slate-400">No user data. Set user_id in your API calls to track users.</div>
                ) : (
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full text-xs">
                      <thead><tr className="border-b border-slate-200 bg-slate-50">
                        {["User ID", "Traces", "Tokens", "Last Active"].map(h => <th key={h} className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">{h}</th>)}
                      </tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {userList.map(u => (
                          <tr key={u.id} className="hover:bg-slate-50">
                            <td className="px-4 py-2.5 font-medium text-slate-800">{u.id}</td>
                            <td className="px-4 py-2 text-slate-600 font-mono">{u.count}</td>
                            <td className="px-4 py-2 text-slate-600 font-mono">{u.tokens.toLocaleString()}</td>
                            <td className="px-4 py-2 text-slate-400">{fmtTime(u.last)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              })()}
            </div>
          )}

          {/* ══ DASHBOARD TAB ══ */}
          {!loading && tab === "Dashboard" && (
            <div className="space-y-5">
              <h2 className="text-lg font-semibold text-slate-900">Dashboard</h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: "Total Traces", value: metrics?.total_traces ?? traces.length },
                  { label: "P95 Latency", value: `${(metrics?.p95_latency_ms || 0).toFixed(0)} ms` },
                  { label: "Error Rate", value: `${(metrics?.error_rate || 0).toFixed(1)}%` },
                  { label: "Models Used", value: metrics?.model_breakdown?.length || uniqueModels.length },
                ].map(k => (
                  <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4">
                    <div className="text-xs font-medium text-slate-500 mb-1">{k.label}</div>
                    <div className="text-lg font-bold text-slate-900">{k.value}</div>
                  </div>
                ))}
              </div>
              {/* Model breakdown */}
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200"><h3 className="text-xs font-semibold text-slate-600 uppercase">Model Breakdown</h3></div>
                {(metrics?.model_breakdown || []).length === 0 ? (
                  <div className="p-6 text-sm text-slate-400 text-center">No model usage data yet.</div>
                ) : (
                  <table className="w-full text-xs">
                    <thead><tr className="border-b border-slate-200">
                      {["Model", "Calls", "Tokens", "Cost", "Avg Latency"].map(h => <th key={h} className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">{h}</th>)}
                    </tr></thead>
                    <tbody className="divide-y divide-slate-100">
                      {(metrics?.model_breakdown || []).map(m => (
                        <tr key={m.model}>
                          <td className="px-4 py-2.5 font-medium text-slate-800">{m.model}</td>
                          <td className="px-4 py-2 text-slate-600 font-mono">{m.count}</td>
                          <td className="px-4 py-2 text-slate-600 font-mono">{m.tokens.toLocaleString()}</td>
                          <td className="px-4 py-2 text-slate-600 font-mono">${m.cost.toFixed(4)}</td>
                          <td className="px-4 py-2 text-slate-600">{m.avg_latency_ms.toFixed(0)} ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              {/* Daily volume */}
              {metrics?.daily_counts?.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
                  <h3 className="text-xs font-semibold text-slate-600 uppercase">Daily Trace Volume</h3>
                  <div className="flex items-end gap-1 h-32">
                    {metrics.daily_counts.map(d => {
                      const maxC = Math.max(...metrics.daily_counts.map(x => x.count), 1);
                      const h = Math.max((d.count / maxC) * 100, 4);
                      return (
                        <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                          <span className="text-[11px] text-slate-500 font-mono">{d.count}</span>
                          <div className="w-full bg-blue-500 rounded-t" style={{ height: `${h}%` }} />
                          <span className="text-[8px] text-slate-400 -rotate-45 origin-top-left whitespace-nowrap">{d.date.slice(5)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ══ LLM LOGS TAB ══ */}
          {!loading && tab === "LLMLogs" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">LLM Logs</h2>
                <span className="text-xs text-slate-400">{llmLogs.length} logs</span>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <select value={logFilter.status} onChange={e => setLogFilter(p => ({ ...p, status: e.target.value }))} className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs outline-none w-32"><option value="">All Status</option><option value="success">Success</option><option value="error">Error</option></select>
                <select value={logFilter.provider} onChange={e => setLogFilter(p => ({ ...p, provider: e.target.value }))} className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs outline-none w-32"><option value="">All Providers</option><option value="google">Google</option><option value="anthropic">Anthropic</option><option value="openai">OpenAI</option></select>
              </div>
              {logsLoading ? (
                <div className="text-slate-400 text-sm py-8 text-center"><Loader2 size={16} className="animate-spin inline mr-2" />Loading logs...</div>
              ) : llmLogs.length === 0 ? (
                <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
                  <ScrollText size={32} className="mx-auto text-slate-300 mb-2" />
                  <div className="text-sm text-slate-500 font-medium">No LLM logs yet</div>
                  <div className="text-xs text-slate-400">LLM request/response logs will appear here.</div>
                </div>
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
                          <td className="px-3 py-2"><Badge variant={l.status === "success" ? "success" : "error"}>{l.status}</Badge></td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </div>
                  {logTotalPages > 1 && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-400">Showing {(logPage - 1) * LOG_PAGE_SIZE + 1}\u2013{Math.min(logPage * LOG_PAGE_SIZE, llmLogs.length)} of {llmLogs.length}</span>
                      <div className="flex items-center gap-1">
                        <button onClick={() => setLogPage(Math.max(1, logPage - 1))} disabled={logPage === 1}
                          className={cn("px-2.5 py-1 rounded-lg text-xs border cursor-pointer transition", logPage === 1 ? "opacity-40 cursor-not-allowed border-slate-200 text-slate-400" : "border-slate-200 text-slate-600 hover:bg-slate-50")}>Prev</button>
                        {Array.from({ length: Math.min(logTotalPages, 7) }, (_, i) => {
                          let p;
                          if (logTotalPages <= 7) p = i + 1;
                          else if (logPage <= 4) p = i + 1;
                          else if (logPage >= logTotalPages - 3) p = logTotalPages - 6 + i;
                          else p = logPage - 3 + i;
                          return (
                            <button key={p} onClick={() => setLogPage(p)}
                              className={cn("w-7 h-7 rounded-lg text-xs font-medium cursor-pointer transition", p === logPage ? "bg-jai-primary text-white" : "text-slate-500 hover:bg-slate-100")}>{p}</button>
                          );
                        })}
                        <button onClick={() => setLogPage(Math.min(logTotalPages, logPage + 1))} disabled={logPage === logTotalPages}
                          className={cn("px-2.5 py-1 rounded-lg text-xs border cursor-pointer transition", logPage === logTotalPages ? "opacity-40 cursor-not-allowed border-slate-200 text-slate-400" : "border-slate-200 text-slate-600 hover:bg-slate-50")}>Next</button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ══ DIAGNOSTICS TAB ══ */}
          {!loading && tab === "Diagnostics" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">Diagnostics</h2>
              {diagnostics ? (
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                  {[
                    { label: "Requests", value: diagnostics.total_requests, icon: Activity, color: "text-blue-600", bg: "bg-blue-50" },
                    { label: "Error Rate", value: `${diagnostics.error_rate}%`, icon: AlertTriangle, color: "text-red-600", bg: "bg-red-50" },
                    { label: "Avg Latency", value: `${diagnostics.avg_latency_ms}ms`, icon: Clock, color: "text-orange-600", bg: "bg-orange-50" },
                    { label: "Tokens", value: diagnostics.total_tokens, icon: Zap, color: "text-violet-600", bg: "bg-violet-50" },
                    { label: "Cost", value: `$${diagnostics.total_cost_usd}`, icon: DollarSign, color: "text-emerald-600", bg: "bg-emerald-50" },
                  ].map(k => (
                    <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-slate-500">{k.label}</span>
                        <div className={cn("w-7 h-7 rounded-lg flex items-center justify-center", k.bg)}><k.icon size={14} className={k.color} /></div>
                      </div>
                      <div className="text-xl font-bold text-slate-900">{k.value}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-sm text-slate-400">No diagnostics data available. Make some LLM calls first.</div>
              )}
            </div>
          )}

          {/* ══ SCORES TAB ══ */}
          {!loading && tab === "Scores" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">Scores</h2>
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                {scores.length === 0 ? (
                  <div className="p-8 text-center text-sm text-slate-400">No evaluation scores recorded yet.</div>
                ) : (
                  <table className="w-full text-xs">
                    <thead><tr className="border-b border-slate-200 bg-slate-50">
                      {["Score Name", "Value", "Trace ID", "Comment", "Time"].map(h => <th key={h} className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">{h}</th>)}
                    </tr></thead>
                    <tbody className="divide-y divide-slate-100">
                      {scores.map(s => (
                        <tr key={s.score_id} className="hover:bg-slate-50">
                          <td className="px-4 py-2.5 font-medium text-slate-800">{s.name}</td>
                          <td className="px-4 py-2"><span className={cn("font-mono font-bold", (s.value ?? 0) >= 0.7 ? "text-emerald-600" : (s.value ?? 0) >= 0.4 ? "text-amber-600" : "text-red-600")}>{s.value ?? "—"}</span></td>
                          <td className="px-4 py-2 font-mono text-slate-500 max-w-[150px] truncate">{s.trace_id}</td>
                          <td className="px-4 py-2 text-slate-500 max-w-[200px] truncate">{s.comment || "—"}</td>
                          <td className="px-4 py-2 text-slate-400">{fmtTime(s.timestamp)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
