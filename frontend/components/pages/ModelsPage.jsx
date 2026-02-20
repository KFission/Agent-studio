"use client";
import { useState, useEffect, useRef } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, SearchInput, EmptyState, Tabs, StatCard, toast, confirmAction } from "../shared/StudioUI";
import {
  Box, Plus, Trash2, Check, X, Eye, ExternalLink, Search, Cloud,
  Activity, DollarSign, AlertTriangle, RefreshCw, Zap, Edit3, Copy, Loader2,
  FolderKanban, CheckCircle2, Upload, KeyRound,
} from "lucide-react";

export default function ModelsPage() {
  const [tab, setTab] = useState("models"); // "models" | "providers"
  const [models, setModels] = useState([]); const [integrations, setIntegrations] = useState([]);
  const [groups, setGroups] = useState([]); const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(""); const [provFilter, setProvFilter] = useState("all");
  const [assignOpen, setAssignOpen] = useState(null); const [selGroups, setSelGroups] = useState([]);
  const [pushOpen, setPushOpen] = useState(null); const [pushSelGroups, setPushSelGroups] = useState([]);
  // Add provider form
  const [showCreate, setShowCreate] = useState(false);
  const emptyForm = { name: "", provider: "google", auth_type: "api_key", api_key: "", service_account_json: null, description: "", endpoint_url: "", project_id: "", location: "us-central1", default_model: "", registered_models: [], rate_limit_rpm: 0 };
  const [form, setForm] = useState(emptyForm);
  const [saFileName, setSaFileName] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [selectedModels, setSelectedModels] = useState([]);
  const fileInputRef = useRef(null);

  const load = (retry = true) => {
    setLoading(true);
    apiFetch(`${API}/models`).then(r => r.json()).then(d => { setModels(d.models || []); setLoading(false); })
      .catch(() => { if (retry) { setTimeout(() => load(false), 1500); } else { setLoading(false); } });
    apiFetch(`${API}/integrations`).then(r => r.json()).then(d => setIntegrations(d.integrations || [])).catch(() => {});
    apiFetch(`${API}/groups`).then(r => r.json()).then(d => setGroups(d.groups || [])).catch(() => {});
  };
  useEffect(load, []);

  const providers = [
    { id: "google", label: "Google Gemini", authTypes: ["api_key", "service_account"] },
    { id: "openai", label: "OpenAI", authTypes: ["api_key"] },
    { id: "anthropic", label: "Anthropic", authTypes: ["api_key"] },
    { id: "ollama", label: "Ollama (Local)", authTypes: ["api_key"] },
  ];
  const pc = { google: "success", anthropic: "purple", openai: "info", ollama: "warning" };
  const getProvider = (pid) => providers.find(p => p.id === pid) || { label: pid, authTypes: ["api_key"] };
  const curProv = providers.find(p => p.id === form.provider) || providers[0];
  const hasCredentials = form.auth_type === "service_account" ? !!form.service_account_json : !!form.api_key;

  // File upload handler for service account JSON
  const handleSAFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSaFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const json = JSON.parse(ev.target.result);
        setForm(p => ({ ...p, service_account_json: json, project_id: json.project_id || p.project_id }));
      } catch { toast.error("Invalid JSON file"); setSaFileName(""); }
    };
    reader.readAsText(file);
  };

  const resetCreate = () => { setShowCreate(false); setForm(emptyForm); setSaFileName(""); setTestResult(null); setSelectedModels([]); if (fileInputRef.current) fileInputRef.current.value = ""; };

  const testConnection = async () => {
    setTesting(true); setTestResult(null);
    try {
      const body = { ...form };
      if (form.auth_type === "service_account") body.endpoint_url = form.location || "us-central1";
      const ac = new AbortController(); const tid = setTimeout(() => ac.abort(), 30000); const r = await apiFetch(`${API}/integrations/test-connection`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: ac.signal }); clearTimeout(tid);
      const d = await r.json();
      setTestResult(d);
      if (d.status === "success" && d.models?.length > 0) {
        const top = d.models.filter(m => /gemini-2|gpt-4o|claude-sonnet|claude-3/.test(m)).slice(0, 5);
        setSelectedModels(top.length > 0 ? top : d.models.slice(0, 3));
        const def = d.models.find(m => m.includes("gemini-2.5-flash")) || d.models.find(m => m.includes("gemini-2.0-flash")) || d.models.find(m => m.includes("gpt-4o")) || d.models[0];
        setForm(p => ({ ...p, default_model: def || "" }));
        toast.success(`Connected! ${d.models.length} models available`);
      } else if (d.status === "error") { toast.error(d.error || "Connection failed"); }
    } catch (e) { setTestResult({ status: "error", error: e.message, models: [] }); toast.error("Connection failed"); }
    setTesting(false);
  };

  const saveIntegration = async () => {
    const body = { ...form, registered_models: selectedModels };
    if (form.auth_type === "service_account") body.endpoint_url = form.location || "us-central1";
    await apiFetch(`${API}/integrations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    toast.success(`"${form.name}" saved with ${selectedModels.length} models`);
    resetCreate(); load();
  };

  const deleteIntegration = async (id) => { const ok = await confirmAction({ title: "Remove Provider", message: "This will remove this provider and unregister its models. Agents using these models may stop working.", confirmLabel: "Remove" }); if (!ok) return; await apiFetch(`${API}/integrations/${id}`, { method: "DELETE" }); load(); toast.success("Provider removed"); };
  const testExisting = async (id) => {
    const r = await apiFetch(`${API}/integrations/${id}/test`, { method: "POST" });
    const d = await r.json(); load();
    if (d.status === "success") toast.success(`Healthy — ${(d.models || []).length} models`);
    else toast.error(d.error || "Test failed");
  };

  const pushModelsToGroups = async (modelId) => {
    for (const gid of selGroups) {
      await apiFetch(`${API}/groups/${gid}/models`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model_ids: [modelId] }) });
    }
    setAssignOpen(null); setSelGroups([]);
    apiFetch(`${API}/groups`).then(r => r.json()).then(d => setGroups(d.groups || [])).catch(() => {});
  };
  const pushIntToGroups = async (intId) => {
    await apiFetch(`${API}/integrations/${intId}/push`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ group_ids: pushSelGroups }) });
    setPushOpen(null); setPushSelGroups([]); load();
  };

  const getModelGroups = (modelId) => groups.filter(g => (g.allowed_model_ids || []).includes(modelId));
  const modelProviders = [...new Set(models.map(m => m.provider))];
  const filtered = models.filter(m => {
    if (provFilter !== "all" && m.provider !== provFilter) return false;
    if (search && !m.display_name?.toLowerCase().includes(search.toLowerCase()) && !m.model_name?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div><h1 className="text-xl font-semibold text-slate-900">Model Library</h1><p className="text-sm text-slate-500 mt-1">Connect providers, discover models, and manage team access</p></div>
        <button onClick={() => { setTab("providers"); setShowCreate(true); }} className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} /> Add Provider</button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-lg p-0.5 w-fit">
        <button onClick={() => setTab("models")} className={cn("px-4 py-1.5 rounded-md text-sm font-medium cursor-pointer transition", tab === "models" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700")}>Registered Models {models.length > 0 && <span className="text-xs text-slate-400 ml-1">({models.length})</span>}</button>
        <button onClick={() => setTab("providers")} className={cn("px-4 py-1.5 rounded-md text-sm font-medium cursor-pointer transition", tab === "providers" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700")}>Providers {integrations.length > 0 && <span className="text-xs text-slate-400 ml-1">({integrations.length})</span>}</button>
      </div>

      {/* ═══ TAB: Registered Models ═══ */}
      {tab === "models" && (<>
        {models.length === 0 ? (
          <EmptyState icon={<Box size={24} />} illustration="start" title="No models registered" description="Add an AI provider to discover and register models automatically." action={<button onClick={() => { setTab("providers"); setShowCreate(true); }} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} className="inline mr-1" />Add Provider</button>} />
        ) : (<>
          <div className="flex items-center gap-3 flex-wrap">
            <SearchInput value={search} onChange={setSearch} placeholder="Search models..." />
            <div className="flex gap-1.5">
              <button onClick={() => setProvFilter("all")} className={cn("px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer border transition", provFilter === "all" ? "bg-slate-900 border-slate-900 text-white" : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50")}>All</button>
              {modelProviders.map(p => <button key={p} onClick={() => setProvFilter(p)} className={cn("px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer border transition capitalize", provFilter === p ? "bg-slate-900 border-slate-900 text-white" : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50")}>{p}</button>)}
            </div>
            <span className="text-xs text-slate-400">{filtered.length} model{filtered.length !== 1 ? "s" : ""}</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filtered.map(m => {
              const mg = getModelGroups(m.model_id);
              return (
                <div key={m.model_id} className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-md transition">
                  <div className="p-4">
                    <div className="flex justify-between mb-1.5">
                      <div className="min-w-0 flex-1"><div className="text-sm font-semibold text-slate-900 truncate">{m.display_name}</div><div className="text-[11px] text-slate-400 font-mono mt-0.5">{m.model_name}</div></div>
                      <Badge variant={pc[m.provider] || "outline"}>{m.provider}</Badge>
                    </div>
                    <div className="text-xs text-slate-500 mb-2 line-clamp-2">{m.description}</div>
                    {mg.length > 0 && <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-slate-100">{mg.map(g => <Badge key={g.group_id} variant="brand">{g.name}</Badge>)}</div>}
                  </div>
                  <div className="px-4 py-2 border-t border-slate-100 flex justify-between items-center">
                    <span className="text-[11px] text-slate-400">{m.pricing?.input_cost_per_1k > 0 ? `$${m.pricing.input_cost_per_1k}/1K in · $${m.pricing.output_cost_per_1k}/1K out` : "Free — local"}</span>
                    <div className="relative">
                      <button onClick={() => { setAssignOpen(assignOpen === m.model_id ? null : m.model_id); setSelGroups(mg.map(g => g.group_id)); }}
                        className="text-[11px] text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer"><FolderKanban size={11} /> Assign</button>
                      {assignOpen === m.model_id && (
                        <div className="absolute bottom-full right-0 mb-1 w-56 bg-white border border-slate-200 rounded-xl shadow-lg z-50 p-3 space-y-2">
                          <div className="text-xs font-semibold text-slate-900">Assign to Teams</div>
                          {groups.length === 0 ? <div className="text-xs text-slate-400">No teams created</div> : (
                            <div className="space-y-1 max-h-40 overflow-y-auto">{groups.map(g => (
                              <label key={g.group_id} className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                                <input type="checkbox" checked={selGroups.includes(g.group_id)} onChange={e => setSelGroups(p => e.target.checked ? [...p, g.group_id] : p.filter(id => id !== g.group_id))} className="accent-emerald-500" />{g.name}
                              </label>
                            ))}</div>
                          )}
                          <div className="flex gap-2 pt-1">
                            <button onClick={() => setAssignOpen(null)} className="px-2 py-1 text-[11px] border border-slate-200 rounded-lg cursor-pointer">Cancel</button>
                            <button onClick={() => pushModelsToGroups(m.model_id)} className="px-2 py-1 text-[11px] bg-jai-primary text-white rounded-lg cursor-pointer font-medium">Save</button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>)}
      </>)}

      {/* ═══ TAB: Providers ═══ */}
      {tab === "providers" && (<>
        {/* Add Provider Form */}
        {showCreate && (
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <h3 className="text-base font-semibold text-slate-900">Connect AI Provider</h3>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs font-medium text-slate-500">Provider</label>
                <select value={form.provider} onChange={e => { setForm(p => ({ ...p, provider: e.target.value, auth_type: "api_key", api_key: "", service_account_json: null, default_model: "" })); setSaFileName(""); setTestResult(null); setSelectedModels([]); }} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none">
                  {providers.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                </select>
              </div>
              <div><label className="text-xs font-medium text-slate-500">Name</label><input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder={`My ${curProv.label} Integration`} /></div>
            </div>

            {/* Auth type toggle for providers that support multiple */}
            {curProv.authTypes.length > 1 && (
              <div>
                <label className="text-xs font-medium text-slate-500">Authentication Method</label>
                <div className="flex gap-2 mt-1">
                  {curProv.authTypes.map(at => (
                    <button key={at} onClick={() => { setForm(p => ({ ...p, auth_type: at, service_account_json: null, api_key: "" })); setSaFileName(""); setTestResult(null); setSelectedModels([]); }}
                      className={cn("px-3 py-1.5 rounded-lg text-sm font-medium border cursor-pointer transition", form.auth_type === at ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50")}>
                      {at === "api_key" ? "API Key" : "Service Account JSON"}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Credentials */}
            {form.auth_type === "api_key" ? (
              <div><label className="text-xs font-medium text-slate-500">API Key</label><input type="password" value={form.api_key} onChange={e => setForm(p => ({ ...p, api_key: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none font-mono" placeholder={form.provider === "google" ? "AIza..." : "sk-..."} /></div>
            ) : (
              <div>
                <label className="text-xs font-medium text-slate-500">Service Account JSON</label>
                <input ref={fileInputRef} type="file" accept=".json" onChange={handleSAFileUpload} className="hidden" />
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={e => e.preventDefault()}
                  onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) { const dt = new DataTransfer(); dt.items.add(f); fileInputRef.current.files = dt.files; handleSAFileUpload({ target: { files: [f] } }); } }}
                  className={cn("mt-1 border-2 border-dashed rounded-xl px-4 py-5 text-center cursor-pointer transition hover:border-slate-400",
                    form.service_account_json ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-slate-50")}>
                  {form.service_account_json ? (
                    <div className="text-sm">
                      <CheckCircle2 size={20} className="mx-auto text-emerald-500 mb-1" />
                      <div className="font-medium text-emerald-700">{saFileName}</div>
                      <div className="text-xs text-emerald-600 mt-0.5">Project: {form.service_account_json.project_id || "—"} · Client: {form.service_account_json.client_email?.split("@")[0] || "—"}</div>
                      <button onClick={e => { e.stopPropagation(); setForm(p => ({ ...p, service_account_json: null })); setSaFileName(""); if (fileInputRef.current) fileInputRef.current.value = ""; }}
                        className="mt-2 text-xs text-red-500 hover:text-red-700 cursor-pointer">Remove</button>
                    </div>
                  ) : (
                    <div>
                      <Upload size={20} className="mx-auto text-slate-400 mb-1" />
                      <div className="text-sm text-slate-600 font-medium">Drop your .json key file here or click to browse</div>
                      <div className="text-xs text-slate-400 mt-0.5">The service account JSON file downloaded from GCP Console</div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Location for service account */}
            {form.provider === "google" && form.auth_type === "service_account" && (
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs font-medium text-slate-500">GCP Project ID</label><input value={form.project_id} onChange={e => setForm(p => ({ ...p, project_id: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder={form.service_account_json?.project_id || "auto-detected from JSON"} /></div>
                <div><label className="text-xs font-medium text-slate-500">Region / Location</label>
                  <select value={form.location} onChange={e => setForm(p => ({ ...p, location: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none">
                    <option value="us-central1">us-central1 (Iowa)</option>
                    <option value="us-east1">us-east1 (S. Carolina)</option>
                    <option value="us-west1">us-west1 (Oregon)</option>
                    <option value="europe-west1">europe-west1 (Belgium)</option>
                    <option value="europe-west4">europe-west4 (Netherlands)</option>
                    <option value="asia-northeast1">asia-northeast1 (Tokyo)</option>
                    <option value="asia-southeast1">asia-southeast1 (Singapore)</option>
                  </select>
                </div>
              </div>
            )}
            {form.provider === "google" && form.auth_type === "api_key" && (
              <div><label className="text-xs font-medium text-slate-500">Project ID (optional for API key)</label><input value={form.project_id} onChange={e => setForm(p => ({ ...p, project_id: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="my-gcp-project" /></div>
            )}
            {form.provider === "ollama" && (
              <div><label className="text-xs font-medium text-slate-500">Endpoint URL</label><input value={form.endpoint_url} onChange={e => setForm(p => ({ ...p, endpoint_url: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="http://localhost:11434" /></div>
            )}

            <div><label className="text-xs font-medium text-slate-500">Description (optional)</label><input value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="Production key for Gemini models" /></div>

            {/* Test Connection */}
            <div className="pt-2 border-t border-slate-100">
              <button onClick={testConnection} disabled={!form.name || !hasCredentials || testing}
                className={cn("flex items-center gap-2 bg-slate-800 text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer transition", (!form.name || !hasCredentials || testing) && "opacity-50 cursor-not-allowed")}>
                {testing ? <><Loader2 size={14} className="animate-spin" /> Testing...</> : <><Zap size={14} /> Test Connection</>}
              </button>
            </div>

            {/* Test Result */}
            {testResult && (
              <div className={cn("rounded-lg p-4 text-sm", testResult.status === "success" ? "bg-emerald-50 border border-emerald-200" : "bg-red-50 border border-red-200")}>
                {testResult.status === "success" ? (
                  <div>
                    <div className="flex items-center gap-2 text-emerald-700 font-semibold"><CheckCircle2 size={16} /> Connection successful — {testResult.models.length} models found</div>
                    <div className="mt-3">
                      <div className="text-xs font-semibold text-slate-700 mb-1.5">Select models to register:</div>
                      <div className="max-h-48 overflow-y-auto space-y-1 bg-white rounded-lg border border-slate-200 p-2">
                        {testResult.models.map(m => (
                          <label key={m} className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer hover:bg-slate-50 rounded px-2 py-1">
                            <input type="checkbox" checked={selectedModels.includes(m)} onChange={e => setSelectedModels(p => e.target.checked ? [...p, m] : p.filter(x => x !== m))} className="accent-emerald-500" />
                            <span className="font-mono">{m}</span>
                          </label>
                        ))}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1">{selectedModels.length} selected</div>
                    </div>
                    {selectedModels.length > 0 && (
                      <div className="mt-3">
                        <label className="text-xs font-semibold text-slate-700">Default model:</label>
                        <select value={form.default_model} onChange={e => setForm(p => ({ ...p, default_model: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none mt-1 font-mono">
                          {selectedModels.map(m => <option key={m} value={m}>{m}</option>)}
                        </select>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-red-700"><span className="font-semibold">Connection failed:</span> {testResult.error}</div>
                )}
              </div>
            )}

            {/* Save / Cancel */}
            <div className="flex gap-2 pt-2">
              <button onClick={resetCreate} className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 cursor-pointer hover:bg-slate-50">Cancel</button>
              <button onClick={saveIntegration} disabled={!form.name || !hasCredentials || selectedModels.length === 0}
                className={cn("bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer", (!form.name || !hasCredentials || selectedModels.length === 0) && "opacity-50 cursor-not-allowed")}>
                Save Provider ({selectedModels.length} models)
              </button>
            </div>
          </div>
        )}

        {/* Provider cards */}
        {integrations.length === 0 && !showCreate ? (
          <EmptyState icon={<Zap size={24} />} illustration="start" title="No providers connected" description="Connect an AI provider (Google Gemini, OpenAI, Anthropic) to discover and register models." action={<button onClick={() => setShowCreate(true)} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} className="inline mr-1" />Add Provider</button>} />
        ) : (
          <div className="space-y-4">
            {integrations.map(i => {
              const prov = getProvider(i.provider);
              const assignedGroups = groups.filter(g => (i.assigned_group_ids || []).includes(g.group_id));
              return (
                <div key={i.integration_id} className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                  <div className="p-5">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center text-white text-sm font-bold", i.provider === "openai" ? "bg-emerald-600" : i.provider === "anthropic" ? "bg-violet-600" : i.provider === "google" ? "bg-blue-600" : "bg-amber-600")}>
                          {prov.label[0]}
                        </div>
                        <div>
                          <div className="text-base font-semibold text-slate-900">{i.name}</div>
                          <div className="text-xs text-slate-500 mt-0.5">{prov.label} · {i.auth_type === "service_account" ? "Service Account" : "API Key"} {i.default_model && <span className="text-slate-400">· Default: <span className="font-mono">{i.default_model}</span></span>}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={i.status === "active" ? "success" : i.status === "error" ? "danger" : "outline"}>{i.status}</Badge>
                        <button onClick={() => testExisting(i.integration_id)} className="text-xs text-slate-500 hover:text-slate-900 border border-slate-200 rounded-lg px-2.5 py-1 cursor-pointer">Test</button>
                      </div>
                    </div>
                    {i.description && <div className="text-sm text-slate-500 mt-2">{i.description}</div>}
                    <div className="flex items-center gap-4 mt-3 text-xs text-slate-400">
                      <span><KeyRound size={11} className="inline mr-1" />{i.api_key_masked || i.auth_type}</span>
                      {(i.registered_models || []).length > 0 && <span>{(i.registered_models || []).length} models registered</span>}
                    </div>
                    {(i.registered_models || []).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {(i.registered_models || []).map(m => <span key={m} className="text-[11px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{m}</span>)}
                      </div>
                    )}
                    <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] text-slate-400 font-semibold uppercase">Teams:</span>
                        {assignedGroups.length === 0 ? <span className="text-xs text-slate-400 italic">All teams</span> : assignedGroups.map(g => <Badge key={g.group_id} variant="brand">{g.name}</Badge>)}
                      </div>
                      <div className="flex items-center gap-2 relative">
                        <button onClick={() => { setPushOpen(pushOpen === i.integration_id ? null : i.integration_id); setPushSelGroups((i.assigned_group_ids || []).slice()); }}
                          className="text-xs text-jai-primary font-medium hover:underline flex items-center gap-1 cursor-pointer"><FolderKanban size={12} /> Assign Teams</button>
                        {pushOpen === i.integration_id && (
                          <div className="absolute bottom-full right-0 mb-1 w-64 bg-white border border-slate-200 rounded-xl shadow-lg z-50 p-3 space-y-2">
                            <div className="text-xs font-semibold text-slate-900">Assign to Teams</div>
                            {groups.length === 0 ? <div className="text-xs text-slate-400">No teams created. Go to Teams page first.</div> : (
                              <div className="space-y-1 max-h-40 overflow-y-auto">{groups.map(g => (
                                <label key={g.group_id} className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                                  <input type="checkbox" checked={pushSelGroups.includes(g.group_id)} onChange={e => setPushSelGroups(p => e.target.checked ? [...p, g.group_id] : p.filter(id => id !== g.group_id))} className="accent-emerald-500" />
                                  {g.name} {g.lob && <span className="text-[11px] text-slate-400">({g.lob})</span>}
                                </label>
                              ))}</div>
                            )}
                            <div className="flex gap-2 pt-1">
                              <button onClick={() => setPushOpen(null)} className="px-2 py-1 text-xs border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50">Cancel</button>
                              <button onClick={() => pushIntToGroups(i.integration_id)} className="px-2 py-1 text-xs bg-jai-primary text-white rounded-lg cursor-pointer font-medium">Save</button>
                            </div>
                          </div>
                        )}
                        <button onClick={() => deleteIntegration(i.integration_id)} className="text-xs text-red-400 hover:text-red-600 cursor-pointer"><Trash2 size={13} /></button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </>)}
    </div>
  );
}
