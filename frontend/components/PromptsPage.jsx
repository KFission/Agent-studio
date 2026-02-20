"use client";
import { useState, useEffect, useCallback } from "react";
import {
  Plus, FileText, Edit3, Check, Tag, Play, ChevronDown, Copy,
  X, Clock, Search, Beaker, Code, MoreVertical,
  ChevronLeft, Loader2, Bell, ExternalLink, RefreshCw
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

function apiFetch(url, opts = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("jai_token") : null;
  return fetch(url, { ...opts, headers: { ...opts.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) } });
}

function cn(...c) { return c.filter(Boolean).join(" "); }

function Badge({ children, variant = "default", dot = false }) {
  const colors = {
    default: "bg-slate-100 text-slate-600 border-slate-200",
    production: "bg-emerald-50 text-emerald-700 border-emerald-200",
    latest: "bg-blue-50 text-blue-700 border-blue-200",
    experiment: "bg-violet-50 text-violet-700 border-violet-200",
    brand: "bg-[#FDF1F5] text-jai-primary border-[#F2B3C6]",
  };
  const dotColors = { production: "bg-emerald-500", latest: "bg-blue-500", experiment: "bg-violet-500" };
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium border ${colors[variant] || colors.default}`}>
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full", dotColors[variant] || "bg-slate-400")} />}
      {children}
    </span>
  );
}

function copyText(t) { try { navigator.clipboard?.writeText(t); } catch {} }

const labelVariant = (l) => l === "production" ? "production" : l === "latest" ? "latest" : l.startsWith("experiment") ? "experiment" : "default";

const fmtDate = (ts) => {
  if (!ts) return "—";
  try { return new Date(ts).toLocaleString(undefined, { month: "numeric", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }); } catch { return ts; }
};
const fmtShort = (ts) => {
  if (!ts) return "—";
  try { return new Date(ts).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); } catch { return ts; }
};

const extractVars = (content) => {
  if (!content) return [];
  const text = typeof content === "string" ? content : JSON.stringify(content);
  return [...new Set((text.match(/\{\{(\w+)\}\}/g) || []).map(v => v.slice(2, -2)))];
};

/* ────────────────────────────────────────────────────────────────────────
   Chat message card — matches Langfuse's System / Assistant / User cards
   ──────────────────────────────────────────────────────────────────────── */
function ChatMessageCard({ role, content }) {
  const bgByRole = { system: "bg-white", assistant: "bg-emerald-50/30", user: "bg-white" };
  return (
    <div className={cn("border border-slate-200 rounded-lg overflow-hidden", bgByRole[role] || "bg-white")}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
        <span className="text-sm font-semibold text-slate-900 capitalize">{role}</span>
        <button onClick={() => copyText(content)} className="text-slate-300 hover:text-slate-500 cursor-pointer p-0.5" title="Copy"><Copy size={14} /></button>
      </div>
      <div className="px-4 py-3">
        <pre className="text-[13px] text-slate-800 whitespace-pre-wrap leading-relaxed font-mono">{content}</pre>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════
   PromptsPage — Langfuse-style prompt management
   ════════════════════════════════════════════════════════════════════════ */
export default function PromptsPage({ onNavigate }) {
  /* ── state ── */
  const [view, setView] = useState("list");
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  // detail state
  const [promptName, setPromptName] = useState(null);
  const [promptMeta, setPromptMeta] = useState(null);
  const [allVersions, setAllVersions] = useState([]);
  const [selVer, setSelVer] = useState(null);
  const [verDetail, setVerDetail] = useState(null);
  const [versionSearch, setVersionSearch] = useState("");
  const [topTab, setTopTab] = useState("Versions");
  const [detailTab, setDetailTab] = useState("Prompt");
  const [linkedGens, setLinkedGens] = useState([]);
  const [metrics, setMetrics] = useState(null);
  // editing
  const [editing, setEditing] = useState(false);
  const [editMessages, setEditMessages] = useState([]);
  const [editText, setEditText] = useState("");
  const [editConfig, setEditConfig] = useState({});
  const [saving, setSaving] = useState(false);
  // create dialog
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name: "", type: "chat", prompt: "", config: { model: "gemini-2.5-flash", temperature: 0.7 }, tags: "" });
  // experiment
  const [showExperiment, setShowExperiment] = useState(false);
  const [expDatasets, setExpDatasets] = useState([]);
  const [expModels, setExpModels] = useState([]);
  const [expForm, setExpForm] = useState({ datasetName: "", modelId: "", runName: "", temperature: 0.7, maxTokens: 1024 });
  const [expNewDataset, setExpNewDataset] = useState({ name: "", description: "" });
  const [expNewItems, setExpNewItems] = useState([{ input: "{}", expectedOutput: "" }]);
  const [expStep, setExpStep] = useState("select"); // "select" | "create-dataset" | "running" | "results"
  const [expRunning, setExpRunning] = useState(false);
  const [expResults, setExpResults] = useState(null);

  /* ── data loading ── */
  const loadList = useCallback(async () => {
    setLoading(true);
    try { const r = await apiFetch(`${API}/prompts?limit=100`); const d = await r.json(); setPrompts(d.data || []); } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { loadList(); }, [loadList]);

  const openPrompt = async (p) => {
    setPromptName(p.name);
    setPromptMeta(p);
    setView("detail");
    setTopTab("Versions");
    setDetailTab("Prompt");
    setEditing(false);
    setAllVersions([]);
    setLinkedGens([]);
    setMetrics(null);
    try {
      const r = await apiFetch(`${API}/prompts/${encodeURIComponent(p.name)}/versions`);
      if (r.ok) {
        const d = await r.json();
        const vers = d.versions || [];
        setAllVersions(vers);
        if (vers.length > 0) {
          const latest = vers[vers.length - 1];
          setSelVer(latest.version);
          setVerDetail(latest);
        }
      }
    } catch {}
    // linked generations (best effort)
    try {
      const r = await apiFetch(`${API}/monitoring/generations?limit=100`);
      if (r.ok) { const d = await r.json(); setLinkedGens((d.generations || []).filter(g => (g.metadata?.prompt_name === p.name) || (g.promptName === p.name))); }
    } catch {}
  };

  const selectVersion = async (ver) => {
    setSelVer(ver);
    setDetailTab("Prompt");
    setEditing(false);
    try {
      const r = await apiFetch(`${API}/prompts/${encodeURIComponent(promptName)}?version=${ver}`);
      if (r.ok) setVerDetail(await r.json());
    } catch {}
  };

  const backToList = () => { setView("list"); setPromptName(null); setPromptMeta(null); setVerDetail(null); setAllVersions([]); loadList(); };

  const loadMetrics = async () => {
    try { const r = await apiFetch(`${API}/monitoring/metrics`); if (r.ok) setMetrics(await r.json()); } catch {}
  };

  /* ── actions ── */
  const startEdit = () => {
    if (!verDetail) { setEditing(true); setEditMessages([{ role: "system", content: "", _id: 0 }]); setEditText(""); setEditConfig({}); return; }
    const p = verDetail.prompt;
    if (verDetail.type === "chat" && Array.isArray(p)) {
      setEditMessages(p.map((m, i) => ({ ...m, _id: i })));
    } else {
      setEditText(typeof p === "string" ? p : JSON.stringify(p, null, 2));
    }
    setEditConfig(verDetail.config || {});
    setEditing(true);
  };

  const saveNewVersion = async () => {
    if (!promptName) return;
    setSaving(true);
    try {
      const type = verDetail?.type || "text";
      const prompt = type === "chat" ? editMessages.map(({ _id, ...m }) => m) : editText;
      const r = await apiFetch(`${API}/prompts`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: promptName, prompt, type, config: editConfig, labels: ["latest"], tags: promptMeta?.tags || [] }),
      });
      if (r.ok) { setEditing(false); openPrompt({ ...promptMeta, name: promptName }); }
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const createPrompt = async () => {
    if (!createForm.name.trim() || !createForm.prompt.trim()) return;
    setSaving(true);
    try {
      let prompt = createForm.prompt;
      if (createForm.type === "chat") { try { prompt = JSON.parse(prompt); } catch { prompt = [{ role: "system", content: prompt }]; } }
      const tags = createForm.tags.split(",").map(t => t.trim()).filter(Boolean);
      await apiFetch(`${API}/prompts`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: createForm.name, prompt, type: createForm.type, config: createForm.config, labels: ["latest"], tags }),
      });
      setShowCreate(false);
      setCreateForm({ name: "", type: "chat", prompt: "", config: { model: "gemini-2.5-flash", temperature: 0.7 }, tags: "" });
      loadList();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const promoteLabel = async (ver, label) => {
    try {
      await apiFetch(`${API}/prompts/${encodeURIComponent(promptName)}/labels?version=${ver}&label=${label}`, { method: "POST" });
      openPrompt({ ...promptMeta, name: promptName });
    } catch {}
  };

  /* ── experiment actions ── */
  const openExperiment = async () => {
    setShowExperiment(true);
    setExpStep("select");
    setExpResults(null);
    setExpRunning(false);
    try {
      const [dsR, mR] = await Promise.all([
        apiFetch(`${API}/experiments/datasets?limit=50`),
        apiFetch(`${API}/models`),
      ]);
      if (dsR.ok) { const d = await dsR.json(); setExpDatasets(d.data || []); }
      if (mR.ok) { const d = await mR.json(); setExpModels(d.models || []); }
    } catch {}
  };

  const createDatasetAndItems = async () => {
    if (!expNewDataset.name.trim()) return;
    try {
      const r = await apiFetch(`${API}/experiments/datasets`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: expNewDataset.name, description: expNewDataset.description }),
      });
      if (!r.ok) return;
      // Add items
      for (const item of expNewItems) {
        let input;
        try { input = JSON.parse(item.input); } catch { input = { text: item.input }; }
        await apiFetch(`${API}/experiments/dataset-items`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ dataset_name: expNewDataset.name, input, expected_output: item.expectedOutput || null }),
        });
      }
      setExpForm(f => ({ ...f, datasetName: expNewDataset.name }));
      setExpStep("select");
      // Refresh datasets
      const dsR = await apiFetch(`${API}/experiments/datasets?limit=50`);
      if (dsR.ok) { const d = await dsR.json(); setExpDatasets(d.data || []); }
    } catch (e) { console.error(e); }
  };

  const runExperiment = async () => {
    if (!expForm.datasetName || !expForm.modelId || !verDetail) return;
    setExpRunning(true);
    setExpStep("running");
    try {
      const r = await apiFetch(`${API}/experiments/run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_name: expForm.datasetName,
          prompt_name: promptName,
          prompt_version: verDetail.version,
          model_id: expForm.modelId,
          run_name: expForm.runName || undefined,
          temperature: expForm.temperature,
          max_tokens: expForm.maxTokens,
        }),
      });
      if (r.ok) {
        setExpResults(await r.json());
        setExpStep("results");
      } else {
        const err = await r.json().catch(() => ({ detail: "Failed" }));
        setExpResults({ error: err.detail || JSON.stringify(err) });
        setExpStep("results");
      }
    } catch (e) { setExpResults({ error: e.message }); setExpStep("results"); }
    setExpRunning(false);
  };

  const openInPlayground = () => {
    if (!verDetail) return;
    const data = { name: promptName, version: verDetail.version, prompt: verDetail.prompt, type: verDetail.type || "text", config: verDetail.config || {} };
    try { localStorage.setItem("jai_playground_prompt", JSON.stringify(data)); } catch {}
    if (onNavigate) onNavigate("LLMPlayground");
  };

  /* ── filtered versions ── */
  const filteredVersions = versionSearch
    ? allVersions.filter(v => String(v.version).includes(versionSearch) || (v.labels || []).some(l => l.toLowerCase().includes(versionSearch.toLowerCase())) || (v.createdBy || "").toLowerCase().includes(versionSearch.toLowerCase()))
    : allVersions;

  /* ══════════════════════════════════════════════════════
     RENDER — Prompt List
     ══════════════════════════════════════════════════════ */
  if (view === "list") {
    return (
      <div className="p-6 animate-fade-up max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-5">
          <div><h1 className="text-xl font-semibold text-slate-900">Prompts</h1><p className="text-sm text-slate-500 mt-0.5">Manage prompt templates with versioning, labels, and config</p></div>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 bg-slate-900 text-white rounded-lg px-3.5 py-2 text-xs font-medium cursor-pointer hover:bg-slate-800"><Plus size={14} /> New</button>
        </div>

        {/* Create dialog */}
        {showCreate && (
          <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center" onClick={() => setShowCreate(false)}>
            <div className="bg-white border border-slate-200 rounded-xl p-5 w-[520px] space-y-4 shadow-xl" onClick={e => e.stopPropagation()}>
              <h2 className="text-sm font-semibold text-slate-900">Create New Prompt</h2>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs font-medium text-slate-500 block mb-1">Name</label>
                  <input value={createForm.name} onChange={e => setCreateForm(p => ({ ...p, name: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="my-prompt-template" /></div>
                <div><label className="text-xs font-medium text-slate-500 block mb-1">Type</label>
                  <select value={createForm.type} onChange={e => setCreateForm(p => ({ ...p, type: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none">
                    <option value="chat">Chat (messages)</option><option value="text">Text</option>
                  </select></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs font-medium text-slate-500 block mb-1">Model</label>
                  <input value={createForm.config.model} onChange={e => setCreateForm(p => ({ ...p, config: { ...p.config, model: e.target.value } }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" /></div>
                <div><label className="text-xs font-medium text-slate-500 block mb-1">Temperature</label>
                  <input type="number" step="0.1" min="0" max="2" value={createForm.config.temperature} onChange={e => setCreateForm(p => ({ ...p, config: { ...p.config, temperature: parseFloat(e.target.value) || 0 } }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" /></div>
              </div>
              <div><label className="text-xs font-medium text-slate-500 block mb-1">Tags (comma-separated)</label>
                <input value={createForm.tags} onChange={e => setCreateForm(p => ({ ...p, tags: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="agent, classification" /></div>
              <div><label className="text-xs font-medium text-slate-500 block mb-1">Prompt Content</label>
                <textarea value={createForm.prompt} onChange={e => setCreateForm(p => ({ ...p, prompt: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono outline-none h-40 resize-y"
                  placeholder={createForm.type === "chat" ? '[{"role":"system","content":"You are..."},{"role":"user","content":"{{question}}"}]' : "You are a {{role}}..."} /></div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer hover:bg-slate-50">Cancel</button>
                <button onClick={createPrompt} disabled={!createForm.name || !createForm.prompt || saving}
                  className={cn("bg-slate-900 text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer", (!createForm.name || !createForm.prompt) && "opacity-50")}>
                  {saving ? "Creating..." : "Create"}
                </button>
              </div>
            </div>
          </div>
        )}

        {loading && <div className="text-sm text-slate-400 py-8 text-center"><Loader2 size={16} className="animate-spin inline mr-2" />Loading prompts...</div>}
        {!loading && prompts.length === 0 && <div className="py-16 text-center"><FileText size={32} className="mx-auto text-slate-300 mb-3" /><div className="text-sm text-slate-500">No prompts yet</div></div>}
        {!loading && prompts.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-xs">
              <thead><tr className="border-b border-slate-200 bg-slate-50/80">
                {["Name", "Type", "Labels", "Tags", "Versions", "Last Updated"].map(h => <th key={h} className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase text-[11px] tracking-wide">{h}</th>)}
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {prompts.map(p => (
                  <tr key={p.name} onClick={() => openPrompt(p)} className="hover:bg-slate-50 cursor-pointer transition">
                    <td className="px-4 py-3 font-semibold text-slate-900"><div className="flex items-center gap-2"><FileText size={14} className="text-slate-400 shrink-0" />{p.name}</div></td>
                    <td className="px-4 py-3"><Badge>{p.type || "text"}</Badge></td>
                    <td className="px-4 py-3"><div className="flex gap-1 flex-wrap">{(p.labels || []).map(l => <Badge key={l} variant={labelVariant(l)} dot>{l}</Badge>)}</div></td>
                    <td className="px-4 py-3"><div className="flex gap-1 flex-wrap">{(p.tags || []).slice(0, 3).map(t => <span key={t} className="text-[11px] bg-slate-100 text-slate-500 rounded px-1.5 py-0.5">{t}</span>)}</div></td>
                    <td className="px-4 py-3 text-slate-600">{(p.versions || []).length}</td>
                    <td className="px-4 py-3 text-slate-400">{fmtShort(p.lastUpdatedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════
     RENDER — Prompt Detail (Langfuse style)
     ══════════════════════════════════════════════════════ */
  return (
    <div className="h-[calc(100vh-48px)] flex flex-col overflow-hidden bg-white">
      {/* ── Top bar: breadcrumb ── */}
      <div className="px-5 py-2.5 border-b border-slate-200 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <button onClick={backToList} className="text-slate-400 hover:text-slate-700 cursor-pointer"><ChevronLeft size={16} /></button>
          <Badge variant="brand">Prompt</Badge>
          <span className="text-sm font-semibold text-slate-900">{promptName}</span>
          {(promptMeta?.tags || []).map(t => (
            <span key={t} className="text-[11px] bg-slate-100 text-slate-500 rounded px-1.5 py-0.5 border border-slate-200 flex items-center gap-1"><Tag size={9} />{t}</span>
          ))}
        </div>
        <button className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-600 cursor-pointer hover:bg-slate-50 bg-white"><Copy size={12} /> Duplicate</button>
      </div>

      {/* ── Top tabs ── */}
      <div className="px-5 bg-white border-b border-slate-200 flex items-center gap-6 shrink-0">
        {["Versions", "Metrics"].map(t => (
          <button key={t} onClick={() => { setTopTab(t); if (t === "Metrics" && !metrics) loadMetrics(); }}
            className={cn("py-2.5 text-sm font-medium cursor-pointer border-b-2 transition",
              topTab === t ? "text-blue-600 border-blue-600" : "text-slate-500 border-transparent hover:text-slate-700")}>{t}</button>
        ))}
      </div>

      {/* ── Main area ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* ── Left sidebar: version list ── */}
        {topTab === "Versions" && (
          <div className="w-64 bg-white border-r border-slate-200 flex flex-col shrink-0 overflow-hidden">
            <div className="p-3 space-y-2 shrink-0">
              <div className="relative">
                <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input value={versionSearch} onChange={e => setVersionSearch(e.target.value)} placeholder="Search versions"
                  className="w-full pl-8 pr-3 py-1.5 border border-slate-200 rounded-lg text-xs outline-none bg-white" />
              </div>
              <button onClick={startEdit}
                className="w-full flex items-center justify-center gap-1.5 bg-slate-900 text-white rounded-lg px-3 py-2 text-xs font-medium cursor-pointer hover:bg-slate-800">
                <Plus size={14} /> New
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
              {[...filteredVersions].reverse().map(v => {
                const active = selVer === v.version && !editing;
                return (
                  <div key={v.version} onClick={() => selectVersion(v.version)}
                    className={cn("px-3 py-2.5 rounded-lg cursor-pointer transition border",
                      active ? "bg-blue-50/60 border-blue-200" : "border-transparent hover:bg-slate-50")}>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-bold text-slate-800"># {v.version}</span>
                      <div className="flex gap-1 flex-wrap">
                        {(v.labels || []).map(l => <Badge key={l} variant={labelVariant(l)} dot>{l}</Badge>)}
                      </div>
                    </div>
                    <div className="text-[11px] text-slate-500 leading-snug">{v.commitMessage || ""}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{fmtDate(v.createdAt)}{v.createdBy ? ` by ${v.createdBy}` : ""}</div>
                  </div>
                );
              })}
              {filteredVersions.length === 0 && allVersions.length > 0 && <div className="text-xs text-slate-400 p-3 text-center">No matching versions</div>}
              {allVersions.length === 0 && <div className="text-xs text-slate-400 p-3 text-center"><Loader2 size={14} className="animate-spin inline mr-1" />Loading...</div>}
            </div>
          </div>
        )}

        {/* ── Right: content ── */}
        <div className="flex-1 overflow-y-auto bg-slate-50/50">
          {/* ═══ Metrics tab ═══ */}
          {topTab === "Metrics" && (
            <div className="p-6 animate-fade-up max-w-3xl space-y-4">
              <h3 className="text-sm font-semibold text-slate-700">Prompt Metrics</h3>
              {metrics ? (
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-white border border-slate-200 rounded-xl p-4"><div className="text-[11px] text-slate-400 uppercase font-semibold mb-1">Total Traces</div><div className="text-2xl font-bold text-slate-800">{metrics.total_traces ?? 0}</div></div>
                  <div className="bg-white border border-slate-200 rounded-xl p-4"><div className="text-[11px] text-slate-400 uppercase font-semibold mb-1">Linked Generations</div><div className="text-2xl font-bold text-slate-800">{linkedGens.length}</div></div>
                  <div className="bg-white border border-slate-200 rounded-xl p-4"><div className="text-[11px] text-slate-400 uppercase font-semibold mb-1">Versions</div><div className="text-2xl font-bold text-slate-800">{allVersions.length}</div></div>
                </div>
              ) : <div className="text-xs text-slate-400"><Loader2 size={14} className="animate-spin inline mr-1" />Loading metrics...</div>}
            </div>
          )}

          {/* ═══ Editing mode ═══ */}
          {topTab === "Versions" && editing && (
            <div className="p-5 space-y-4 max-w-4xl">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">Create New Version</h3>
                <div className="flex items-center gap-2">
                  <button onClick={() => setEditing(false)} className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs text-slate-600 cursor-pointer hover:bg-white bg-white">Cancel</button>
                  <button onClick={saveNewVersion} disabled={saving}
                    className={cn("bg-slate-900 text-white rounded-lg px-4 py-1.5 text-xs font-medium cursor-pointer", saving && "opacity-50")}>
                    {saving ? "Saving..." : "Save"}
                  </button>
                </div>
              </div>
              {/* Config */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
                <div className="text-xs font-semibold text-slate-600">Config</div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="text-[11px] text-slate-500 block mb-1">Model</label>
                    <input value={editConfig.model || ""} onChange={e => setEditConfig(c => ({ ...c, model: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" /></div>
                  <div><label className="text-[11px] text-slate-500 block mb-1">Temperature</label>
                    <input type="number" step="0.1" min="0" max="2" value={editConfig.temperature ?? 0.7} onChange={e => setEditConfig(c => ({ ...c, temperature: parseFloat(e.target.value) || 0 }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" /></div>
                </div>
              </div>
              {/* Messages editor for chat type */}
              {(verDetail?.type === "chat" || (!verDetail && createForm.type === "chat")) ? (
                <div className="space-y-3">
                  {editMessages.map((m, i) => (
                    <div key={m._id ?? i} className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100 bg-slate-50/80">
                        <select value={m.role} onChange={e => { const msgs = [...editMessages]; msgs[i] = { ...msgs[i], role: e.target.value }; setEditMessages(msgs); }}
                          className="text-xs font-semibold bg-transparent outline-none cursor-pointer text-slate-700">
                          <option value="system">System</option><option value="assistant">Assistant</option><option value="user">User</option>
                        </select>
                        <button onClick={() => setEditMessages(editMessages.filter((_, j) => j !== i))} className="text-slate-300 hover:text-red-500 cursor-pointer"><X size={14} /></button>
                      </div>
                      <textarea value={m.content} onChange={e => { const msgs = [...editMessages]; msgs[i] = { ...msgs[i], content: e.target.value }; setEditMessages(msgs); }}
                        className="w-full px-4 py-3 text-sm font-mono outline-none resize-y min-h-[60px]" />
                    </div>
                  ))}
                  <div className="flex gap-2">
                    <button onClick={() => setEditMessages([...editMessages, { role: "user", content: "", _id: Date.now() }])}
                      className="flex items-center gap-1 border border-dashed border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-500 cursor-pointer hover:bg-white bg-white/50"><Plus size={12} /> Message</button>
                    <button onClick={() => setEditMessages([...editMessages, { role: "user", content: "{{placeholder}}", _id: Date.now() + 1 }])}
                      className="flex items-center gap-1 border border-dashed border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-500 cursor-pointer hover:bg-white bg-white/50"><Plus size={12} /> Placeholder</button>
                  </div>
                </div>
              ) : (
                <div className="bg-white border border-slate-200 rounded-lg">
                  <textarea value={editText} onChange={e => setEditText(e.target.value)}
                    className="w-full px-4 py-3 text-sm font-mono outline-none resize-y min-h-[200px] rounded-lg" spellCheck={false} />
                </div>
              )}
            </div>
          )}

          {/* ═══ Version detail ═══ */}
          {topTab === "Versions" && !editing && verDetail && (
            <div className="p-5 max-w-4xl">
              {/* Version header row — matches Langfuse */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-slate-800"># {verDetail.version}</span>
                  <span className="text-sm text-slate-500">{verDetail.commitMessage || ""}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button onClick={openInPlayground}
                    className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-600 cursor-pointer hover:bg-white bg-white">
                    <RefreshCw size={12} /> Playground
                  </button>
                  <button onClick={openExperiment} className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-600 cursor-pointer hover:bg-white bg-white">
                    <Beaker size={12} /> Experiment
                  </button>
                  <button className="text-slate-400 hover:text-slate-600 cursor-pointer p-1.5"><Bell size={14} /></button>
                  <button className="text-slate-400 hover:text-slate-600 cursor-pointer p-1.5"><MoreVertical size={14} /></button>
                </div>
              </div>

              {/* Detail tabs row */}
              <div className="flex items-center gap-5 mb-5 border-b border-slate-200">
                {["Prompt", "Config", "Linked Generations", "Use Prompt"].map(t => (
                  <button key={t} onClick={() => setDetailTab(t)}
                    className={cn("pb-2.5 text-sm font-medium cursor-pointer border-b-2 transition",
                      detailTab === t ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600")}>{t}</button>
                ))}
              </div>

              {/* ─── Prompt tab ─── */}
              {detailTab === "Prompt" && (
                <div className="space-y-4">
                  {verDetail.type === "chat" && Array.isArray(verDetail.prompt) ? (
                    verDetail.prompt.map((m, i) => <ChatMessageCard key={i} role={m.role} content={m.content} />)
                  ) : (
                    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
                        <span className="text-sm font-semibold text-slate-900">Prompt</span>
                        <button onClick={() => copyText(typeof verDetail.prompt === "string" ? verDetail.prompt : JSON.stringify(verDetail.prompt))} className="text-slate-300 hover:text-slate-500 cursor-pointer p-0.5"><Copy size={14} /></button>
                      </div>
                      <div className="px-4 py-3">
                        <pre className="text-[13px] text-slate-800 whitespace-pre-wrap leading-relaxed font-mono">{typeof verDetail.prompt === "string" ? verDetail.prompt : JSON.stringify(verDetail.prompt, null, 2)}</pre>
                      </div>
                    </div>
                  )}
                  {/* Variables hint */}
                  {(() => { const vars = extractVars(verDetail.prompt); return vars.length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap text-xs text-slate-400 pt-1">
                      <span className="font-semibold uppercase text-[11px]">Variables:</span>
                      {vars.map(v => <Badge key={v} variant="latest">{`{{${v}}}`}</Badge>)}
                    </div>
                  ); })()}

                  {/* Promote to production action */}
                  {!(verDetail.labels || []).includes("production") && (
                    <button onClick={() => promoteLabel(verDetail.version, "production")}
                      className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium hover:underline cursor-pointer mt-2">
                      <Tag size={11} /> Promote to production
                    </button>
                  )}
                </div>
              )}

              {/* ─── Config tab ─── */}
              {detailTab === "Config" && (
                <div className="bg-white border border-slate-200 rounded-lg p-4">
                  <pre className="text-xs font-mono text-slate-700 whitespace-pre-wrap">{JSON.stringify(verDetail.config || {}, null, 2)}</pre>
                  <div className="mt-4 grid grid-cols-3 gap-4 text-xs border-t border-slate-100 pt-4">
                    <div><span className="text-slate-400 block mb-0.5">Type</span><span className="text-slate-700 font-medium">{verDetail.type || "text"}</span></div>
                    <div><span className="text-slate-400 block mb-0.5">Created</span><span className="text-slate-700">{fmtDate(verDetail.createdAt)}</span></div>
                    <div><span className="text-slate-400 block mb-0.5">Created By</span><span className="text-slate-700">{verDetail.createdBy || "API"}</span></div>
                  </div>
                </div>
              )}

              {/* ─── Linked Generations tab ─── */}
              {detailTab === "Linked Generations" && (
                <div>
                  {linkedGens.length === 0 ? (
                    <div className="text-center py-12 text-sm text-slate-400">No linked generations found for this prompt</div>
                  ) : (
                    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                      <table className="w-full text-xs">
                        <thead><tr className="border-b border-slate-200 bg-slate-50/80">
                          {["ID", "Model", "Input Tokens", "Output Tokens", "Latency", "Created"].map(h => <th key={h} className="text-left px-4 py-2 font-semibold text-slate-500 uppercase text-[11px]">{h}</th>)}
                        </tr></thead>
                        <tbody className="divide-y divide-slate-100">
                          {linkedGens.map((g, i) => (
                            <tr key={i} className="hover:bg-slate-50">
                              <td className="px-4 py-2 font-mono text-slate-600">{(g.id || "").slice(0, 8)}...</td>
                              <td className="px-4 py-2 text-slate-700">{g.model || "—"}</td>
                              <td className="px-4 py-2 text-slate-600">{g.usage?.input ?? g.inputTokens ?? "—"}</td>
                              <td className="px-4 py-2 text-slate-600">{g.usage?.output ?? g.outputTokens ?? "—"}</td>
                              <td className="px-4 py-2 text-slate-600">{g.latency ? `${(g.latency / 1000).toFixed(1)}s` : "—"}</td>
                              <td className="px-4 py-2 text-slate-400">{fmtShort(g.startTime || g.createdAt)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* ─── Use Prompt tab ─── */}
              {detailTab === "Use Prompt" && (
                <div className="space-y-5">
                  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                    <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-600">Python (Langfuse SDK)</span>
                      <button onClick={() => copyText(`from langfuse import Langfuse\nlf = Langfuse()\nprompt = lf.get_prompt("${promptName}", version=${verDetail.version})\ncompiled = prompt.compile(${extractVars(verDetail.prompt).map(v => `${v}="..."`).join(", ")})`)}
                        className="text-slate-300 hover:text-slate-500 cursor-pointer"><Copy size={13} /></button>
                    </div>
                    <pre className="px-4 py-3 text-xs font-mono text-slate-700 whitespace-pre-wrap leading-relaxed">{`from langfuse import Langfuse

lf = Langfuse()
prompt = lf.get_prompt("${promptName}", version=${verDetail.version})
compiled = prompt.compile(${extractVars(verDetail.prompt).map(v => `${v}="..."`).join(", ")})`}</pre>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                    <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-600">REST API (cURL)</span>
                      <button onClick={() => copyText(`curl "${API}/prompts/${encodeURIComponent(promptName)}?version=${verDetail.version}"`)}
                        className="text-slate-300 hover:text-slate-500 cursor-pointer"><Copy size={13} /></button>
                    </div>
                    <pre className="px-4 py-3 text-xs font-mono text-slate-700 whitespace-pre-wrap leading-relaxed">{`curl "${API}/prompts/${encodeURIComponent(promptName)}?version=${verDetail.version}"

# Render with variables
curl -X POST "${API}/prompts/render" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "${promptName}", "version": ${verDetail.version}, "variables": {${extractVars(verDetail.prompt).map(v => `"${v}": "..."`).join(", ")}}}'`}</pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* No version selected */}
          {topTab === "Versions" && !editing && !verDetail && allVersions.length > 0 && (
            <div className="flex items-center justify-center h-full"><div className="text-sm text-slate-400">Select a version from the left</div></div>
          )}
        </div>
      </div>

      {/* ════ Experiment Modal ════ */}
      {showExperiment && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => !expRunning && setShowExperiment(false)}>
          <div className="bg-white border border-slate-200 rounded-xl shadow-2xl w-[680px] max-h-[85vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <Beaker size={16} className="text-violet-500" />
                <span className="text-sm font-semibold text-slate-900">Run Experiment</span>
                <Badge variant="brand">{promptName} v{verDetail?.version}</Badge>
              </div>
              <button onClick={() => !expRunning && setShowExperiment(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer"><X size={16} /></button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {/* ── Step: Select dataset + model ── */}
              {expStep === "select" && (
                <>
                  <div>
                    <label className="text-xs font-semibold text-slate-600 block mb-1.5">Dataset</label>
                    <div className="flex gap-2">
                      <select value={expForm.datasetName} onChange={e => setExpForm(f => ({ ...f, datasetName: e.target.value }))}
                        className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none">
                        <option value="">Select a dataset...</option>
                        {expDatasets.map(ds => <option key={ds.name} value={ds.name}>{ds.name}{ds.description ? ` — ${ds.description}` : ""}</option>)}
                      </select>
                      <button onClick={() => setExpStep("create-dataset")}
                        className="flex items-center gap-1 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-600 cursor-pointer hover:bg-slate-50 bg-white shrink-0">
                        <Plus size={12} /> New Dataset
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-600 block mb-1.5">Model</label>
                    <select value={expForm.modelId} onChange={e => setExpForm(f => ({ ...f, modelId: e.target.value }))}
                      className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none">
                      <option value="">Select a model...</option>
                      {expModels.map(m => <option key={m.model_id} value={m.model_id}>{m.display_name || m.model_id}</option>)}
                    </select>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div><label className="text-[11px] text-slate-500 block mb-1">Run Name (optional)</label>
                      <input value={expForm.runName} onChange={e => setExpForm(f => ({ ...f, runName: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="auto-generated" /></div>
                    <div><label className="text-[11px] text-slate-500 block mb-1">Temperature</label>
                      <input type="number" step="0.1" min="0" max="2" value={expForm.temperature} onChange={e => setExpForm(f => ({ ...f, temperature: parseFloat(e.target.value) || 0 }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" /></div>
                    <div><label className="text-[11px] text-slate-500 block mb-1">Max Tokens</label>
                      <input type="number" step="128" min="1" max="32768" value={expForm.maxTokens} onChange={e => setExpForm(f => ({ ...f, maxTokens: parseInt(e.target.value) || 1024 }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" /></div>
                  </div>
                  <div className="flex justify-end pt-2">
                    <button onClick={runExperiment} disabled={!expForm.datasetName || !expForm.modelId}
                      className={cn("bg-violet-600 text-white rounded-lg px-5 py-2 text-sm font-medium cursor-pointer hover:bg-violet-700", (!expForm.datasetName || !expForm.modelId) && "opacity-50")}>
                      <div className="flex items-center gap-1.5"><Play size={14} /> Run Experiment</div>
                    </button>
                  </div>
                </>
              )}

              {/* ── Step: Create dataset ── */}
              {expStep === "create-dataset" && (
                <>
                  <div className="flex items-center gap-2 mb-2">
                    <button onClick={() => setExpStep("select")} className="text-xs text-blue-500 hover:underline cursor-pointer flex items-center gap-1"><ChevronLeft size={12} /> Back</button>
                    <span className="text-sm font-semibold text-slate-800">Create New Dataset</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="text-xs text-slate-500 block mb-1">Dataset Name</label>
                      <input value={expNewDataset.name} onChange={e => setExpNewDataset(d => ({ ...d, name: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="my-test-dataset" /></div>
                    <div><label className="text-xs text-slate-500 block mb-1">Description</label>
                      <input value={expNewDataset.description} onChange={e => setExpNewDataset(d => ({ ...d, description: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="Test cases for..." /></div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs font-semibold text-slate-600">Test Cases</label>
                      <button onClick={() => setExpNewItems([...expNewItems, { input: "{}", expectedOutput: "" }])}
                        className="flex items-center gap-1 text-xs text-blue-500 cursor-pointer hover:underline"><Plus size={11} /> Add Row</button>
                    </div>
                    <div className="space-y-2">
                      {expNewItems.map((item, i) => (
                        <div key={i} className="flex gap-2 items-start">
                          <div className="flex-1">
                            <label className="text-[11px] text-slate-400 block mb-0.5">Input (JSON variables)</label>
                            <textarea value={item.input} onChange={e => { const items = [...expNewItems]; items[i] = { ...items[i], input: e.target.value }; setExpNewItems(items); }}
                              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono outline-none resize-none h-16"
                              placeholder={'{"user_message": "...", "categories": "..."}'} />
                          </div>
                          <div className="flex-1">
                            <label className="text-[11px] text-slate-400 block mb-0.5">Expected Output (optional)</label>
                            <textarea value={item.expectedOutput} onChange={e => { const items = [...expNewItems]; items[i] = { ...items[i], expectedOutput: e.target.value }; setExpNewItems(items); }}
                              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono outline-none resize-none h-16"
                              placeholder="Expected classification..." />
                          </div>
                          <button onClick={() => expNewItems.length > 1 && setExpNewItems(expNewItems.filter((_, j) => j !== i))}
                            className="mt-5 text-slate-300 hover:text-red-400 cursor-pointer"><X size={14} /></button>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex justify-end pt-2">
                    <button onClick={createDatasetAndItems} disabled={!expNewDataset.name.trim() || expNewItems.length === 0}
                      className={cn("bg-slate-900 text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer", !expNewDataset.name.trim() && "opacity-50")}>
                      Create Dataset
                    </button>
                  </div>
                </>
              )}

              {/* ── Step: Running ── */}
              {expStep === "running" && (
                <div className="py-12 text-center">
                  <Loader2 size={28} className="animate-spin text-violet-500 mx-auto mb-3" />
                  <div className="text-sm text-slate-600 font-medium">Running experiment...</div>
                  <div className="text-xs text-slate-400 mt-1">Executing prompt against each test case with {expForm.modelId}</div>
                </div>
              )}

              {/* ── Step: Results ── */}
              {expStep === "results" && expResults && (
                <>
                  {expResults.error ? (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{expResults.error}</div>
                  ) : (
                    <>
                      <div className="grid grid-cols-4 gap-3">
                        <div className="bg-white border border-slate-200 rounded-lg p-3"><div className="text-[11px] text-slate-400 uppercase font-semibold mb-1">Total Items</div><div className="text-xl font-bold text-slate-800">{expResults.total_items}</div></div>
                        <div className="bg-white border border-slate-200 rounded-lg p-3"><div className="text-[11px] text-slate-400 uppercase font-semibold mb-1">Completed</div><div className="text-xl font-bold text-emerald-600">{expResults.completed}</div></div>
                        <div className="bg-white border border-slate-200 rounded-lg p-3"><div className="text-[11px] text-slate-400 uppercase font-semibold mb-1">Errors</div><div className="text-xl font-bold text-red-500">{expResults.errors}</div></div>
                        <div className="bg-white border border-slate-200 rounded-lg p-3"><div className="text-[11px] text-slate-400 uppercase font-semibold mb-1">Model</div><div className="text-sm font-semibold text-slate-700 truncate">{expResults.model_id}</div></div>
                      </div>
                      <div className="text-xs font-semibold text-slate-600 mt-2">Results</div>
                      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                        <table className="w-full text-xs">
                          <thead><tr className="border-b border-slate-200 bg-slate-50/80">
                            <th className="text-left px-3 py-2 font-semibold text-slate-500 text-[11px] uppercase w-10">#</th>
                            <th className="text-left px-3 py-2 font-semibold text-slate-500 text-[11px] uppercase">Input</th>
                            <th className="text-left px-3 py-2 font-semibold text-slate-500 text-[11px] uppercase">Output</th>
                            <th className="text-left px-3 py-2 font-semibold text-slate-500 text-[11px] uppercase">Expected</th>
                            <th className="text-left px-3 py-2 font-semibold text-slate-500 text-[11px] uppercase w-20">Latency</th>
                            <th className="text-left px-3 py-2 font-semibold text-slate-500 text-[11px] uppercase w-16">Tokens</th>
                          </tr></thead>
                          <tbody className="divide-y divide-slate-100">
                            {(expResults.results || []).map((r, i) => (
                              <tr key={i} className={r.error ? "bg-red-50/50" : ""}>
                                <td className="px-3 py-2 text-slate-400">{i + 1}</td>
                                <td className="px-3 py-2 text-slate-700 max-w-[140px] truncate font-mono">{typeof r.input === "object" ? JSON.stringify(r.input) : r.input}</td>
                                <td className="px-3 py-2 text-slate-800 max-w-[180px]"><div className="truncate">{r.output}</div></td>
                                <td className="px-3 py-2 text-slate-500 max-w-[140px] truncate">{r.expected_output || "—"}</td>
                                <td className="px-3 py-2 text-slate-600">{r.latency_ms?.toFixed(0)}ms</td>
                                <td className="px-3 py-2 text-slate-600">{(r.input_tokens || 0) + (r.output_tokens || 0)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                  <div className="flex justify-between pt-2">
                    <button onClick={() => setExpStep("select")} className="text-xs text-blue-500 hover:underline cursor-pointer flex items-center gap-1"><ChevronLeft size={12} /> Run another</button>
                    <button onClick={() => setShowExperiment(false)} className="px-4 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-medium cursor-pointer">Done</button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
