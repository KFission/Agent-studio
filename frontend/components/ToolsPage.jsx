"use client";
import { useState, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import apiFetch from "../lib/apiFetch";
import { cn } from "../lib/cn";
import {
  Wrench, Plus, Search, Play, Trash2, Edit3, Copy, X, Check, ChevronDown,
  Code, Globe, Link2, AlertCircle, Clock, Zap, ChevronRight, RefreshCw,
  Eye, EyeOff,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

// ═══════════════════════════════════════════════════════════════════
// SHARED TINY COMPONENTS
// ═══════════════════════════════════════════════════════════════════

function Badge({ children, variant = "outline", className = "" }) {
  const v = {
    outline: "border border-slate-200 text-slate-500 bg-white",
    brand: "bg-blue-50 text-blue-700 border border-blue-200",
    success: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    error: "bg-red-50 text-red-700 border border-red-200",
    info: "bg-violet-50 text-violet-700 border border-violet-200",
    warn: "bg-amber-50 text-amber-700 border border-amber-200",
  };
  return <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold uppercase tracking-wide", v[variant] || v.outline, className)}>{children}</span>;
}

function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
      {tabs.map(t => (
        <button key={t} onClick={() => onChange(t)}
          className={cn("px-4 py-1.5 rounded-md text-xs font-medium transition cursor-pointer",
            active === t ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700")}>
          {t}
        </button>
      ))}
    </div>
  );
}

const TYPE_META = {
  code: { label: "Code", icon: Code, color: "text-violet-600", bg: "bg-violet-50", border: "border-violet-200", desc: "Python or JavaScript" },
  rest_api: { label: "REST API", icon: Globe, color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-200", desc: "HTTP request" },
  mcp: { label: "MCP", icon: Link2, color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200", desc: "MCP Connector" },
};

const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"];
const METHOD_COLORS = { GET: "text-emerald-600", POST: "text-amber-600", PUT: "text-blue-600", PATCH: "text-violet-600", DELETE: "text-red-600", HEAD: "text-slate-500", OPTIONS: "text-slate-500" };

// ═══════════════════════════════════════════════════════════════════
// KEY-VALUE EDITOR (Postman-style)
// ═══════════════════════════════════════════════════════════════════

function KVEditor({ rows, onChange, keyPlaceholder = "Key", valuePlaceholder = "Value", showDescription = false }) {
  const update = (i, field, val) => { const next = [...rows]; next[i] = { ...next[i], [field]: val }; onChange(next); };
  const remove = (i) => onChange(rows.filter((_, idx) => idx !== i));
  const add = () => onChange([...rows, { key: "", value: "", description: "", enabled: true }]);
  return (
    <div className="space-y-1">
      {rows.length > 0 && (
        <div className="grid gap-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wide px-1" style={{ gridTemplateColumns: showDescription ? "28px 1fr 1fr 1fr 28px" : "28px 1fr 1fr 28px" }}>
          <span></span><span>{keyPlaceholder}</span><span>{valuePlaceholder}</span>{showDescription && <span>Description</span>}<span></span>
        </div>
      )}
      {rows.map((r, i) => (
        <div key={i} className="grid gap-2 items-center" style={{ gridTemplateColumns: showDescription ? "28px 1fr 1fr 1fr 28px" : "28px 1fr 1fr 28px" }}>
          <input type="checkbox" checked={r.enabled !== false} onChange={e => update(i, "enabled", e.target.checked)} className="w-4 h-4 accent-blue-600 cursor-pointer" />
          <input value={r.key || ""} onChange={e => update(i, "key", e.target.value)} placeholder={keyPlaceholder}
            className="border border-slate-200 rounded-md px-2.5 py-1.5 text-xs text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400 font-mono" />
          <input value={r.value || ""} onChange={e => update(i, "value", e.target.value)} placeholder={valuePlaceholder}
            className="border border-slate-200 rounded-md px-2.5 py-1.5 text-xs text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400 font-mono" />
          {showDescription && (
            <input value={r.description || ""} onChange={e => update(i, "description", e.target.value)} placeholder="Description"
              className="border border-slate-200 rounded-md px-2.5 py-1.5 text-xs text-slate-500 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400" />
          )}
          <button onClick={() => remove(i)} className="text-slate-300 hover:text-red-500 cursor-pointer transition"><Trash2 size={13} /></button>
        </div>
      ))}
      <button onClick={add} className="text-xs text-blue-600 hover:text-blue-800 cursor-pointer mt-1 flex items-center gap-1"><Plus size={12} /> Add row</button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// CODE EDITOR (simple textarea with line numbers)
// ═══════════════════════════════════════════════════════════════════

function CodeEditor({ value, onChange, language = "python" }) {
  const lines = (value || "").split("\n").length;
  return (
    <div className="relative border border-slate-200 rounded-lg overflow-hidden bg-slate-900">
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-800 border-b border-slate-700">
        <span className="text-[11px] text-slate-400 font-mono uppercase">{language}</span>
        <span className="text-[11px] text-slate-500">{lines} lines</span>
      </div>
      <textarea
        value={value || ""}
        onChange={e => onChange(e.target.value)}
        spellCheck={false}
        className="w-full min-h-[280px] bg-slate-900 text-slate-100 text-xs font-mono p-3 resize-y focus:outline-none leading-relaxed"
        placeholder={language === "python"
          ? "def run(params):\n    \"\"\"params is a dict of inputs\"\"\"\n    return {\"result\": \"hello\"}"
          : "function run(params) {\n  // params is an object of inputs\n  return { result: \"hello\" };\n}"}
      />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// AUTH CONFIG EDITOR
// ═══════════════════════════════════════════════════════════════════

function AuthEditor({ authType, authConfig, onTypeChange, onConfigChange }) {
  const [showSecrets, setShowSecrets] = useState(false);
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-slate-600 w-20">Type</label>
        <select value={authType} onChange={e => onTypeChange(e.target.value)}
          className="border border-slate-200 rounded-md px-2.5 py-1.5 text-xs bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-400">
          <option value="none">No Auth</option>
          <option value="bearer">Bearer Token</option>
          <option value="api_key">API Key</option>
          <option value="basic">Basic Auth</option>
        </select>
        {authType !== "none" && (
          <button onClick={() => setShowSecrets(!showSecrets)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
            {showSecrets ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        )}
      </div>
      {authType === "bearer" && (
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-600 w-20">Token</label>
          <input type={showSecrets ? "text" : "password"} value={authConfig.token || ""} onChange={e => onConfigChange({ ...authConfig, token: e.target.value })}
            placeholder="Bearer token" className="flex-1 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-blue-400" />
        </div>
      )}
      {authType === "api_key" && (
        <>
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-600 w-20">Key name</label>
            <input value={authConfig.key_name || "X-API-Key"} onChange={e => onConfigChange({ ...authConfig, key_name: e.target.value })}
              className="flex-1 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-blue-400" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-600 w-20">Key value</label>
            <input type={showSecrets ? "text" : "password"} value={authConfig.key_value || ""} onChange={e => onConfigChange({ ...authConfig, key_value: e.target.value })}
              placeholder="API key value" className="flex-1 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-blue-400" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-600 w-20">Add to</label>
            <select value={authConfig.key_in || "header"} onChange={e => onConfigChange({ ...authConfig, key_in: e.target.value })}
              className="border border-slate-200 rounded-md px-2.5 py-1.5 text-xs bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-400">
              <option value="header">Header</option>
              <option value="query">Query Param</option>
            </select>
          </div>
        </>
      )}
      {authType === "basic" && (
        <>
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-600 w-20">Username</label>
            <input value={authConfig.username || ""} onChange={e => onConfigChange({ ...authConfig, username: e.target.value })}
              className="flex-1 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-blue-400" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-600 w-20">Password</label>
            <input type={showSecrets ? "text" : "password"} value={authConfig.password || ""} onChange={e => onConfigChange({ ...authConfig, password: e.target.value })}
              className="flex-1 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-blue-400" />
          </div>
        </>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// RESPONSE VIEWER
// ═══════════════════════════════════════════════════════════════════

function ResponseViewer({ result }) {
  const [viewTab, setViewTab] = useState("Body");
  if (!result) return null;
  const isJson = typeof result.output === "object";
  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-700">Response</span>
          {result.status_code && (
            <Badge variant={result.status_code >= 200 && result.status_code < 400 ? "success" : "error"}>{result.status_code}</Badge>
          )}
          <Badge variant={result.success ? "success" : "error"}>{result.success ? "Success" : "Error"}</Badge>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-slate-400">
          {result.latency_ms > 0 && <span><Clock size={10} className="inline mr-0.5" />{result.latency_ms.toFixed(0)} ms</span>}
        </div>
      </div>
      <div className="flex gap-1 px-4 pt-2">
        {["Body", result.headers ? "Headers" : null, result.logs?.length ? "Logs" : null, result.error ? "Error" : null].filter(Boolean).map(t => (
          <button key={t} onClick={() => setViewTab(t)}
            className={cn("px-3 py-1 rounded-md text-[11px] font-medium cursor-pointer transition",
              viewTab === t ? "bg-slate-200 text-slate-800" : "text-slate-400 hover:text-slate-600")}>{t}</button>
        ))}
      </div>
      <div className="p-4 max-h-80 overflow-auto">
        {viewTab === "Body" && (
          <pre className="text-xs font-mono text-slate-700 whitespace-pre-wrap">{isJson ? JSON.stringify(result.output, null, 2) : (result.output ?? "No output")}</pre>
        )}
        {viewTab === "Headers" && result.headers && (
          <div className="space-y-1">{Object.entries(result.headers).map(([k, v]) => (
            <div key={k} className="flex gap-2 text-xs"><span className="font-mono font-semibold text-slate-600 min-w-[140px]">{k}</span><span className="font-mono text-slate-500 break-all">{v}</span></div>
          ))}</div>
        )}
        {viewTab === "Logs" && result.logs?.length > 0 && (
          <pre className="text-xs font-mono text-slate-600 whitespace-pre-wrap">{result.logs.join("\n")}</pre>
        )}
        {viewTab === "Error" && result.error && (
          <div className="text-xs text-red-600 font-mono whitespace-pre-wrap">{result.error}</div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// TOOL EDITOR / BUILDER DIALOG
// ═══════════════════════════════════════════════════════════════════

const EMPTY_REST = { method: "GET", url: "", headers: [], query_params: [], auth_type: "none", auth_config: {}, body_type: "none", body_raw: "", body_form: [], timeout_seconds: 30, follow_redirects: true, verify_ssl: true };
const EMPTY_CODE = { language: "python", code: "", timeout_seconds: 30, packages: [] };
const EMPTY_MCP = { server_url: "", tool_name: "", auth_type: "none", auth_config: {}, headers: [], timeout_seconds: 30, input_schema: {}, description_from_server: "" };

function ToolEditor({ tool, onSave, onCancel, onTest }) {
  const isEdit = !!tool?.tool_id;
  const [name, setName] = useState(tool?.name || "");
  const [description, setDescription] = useState(tool?.description || "");
  const [toolType, setToolType] = useState(tool?.tool_type || "rest_api");
  const [tags, setTags] = useState((tool?.tags || []).join(", "));

  // REST API state
  const rc = tool?.rest_api_config || EMPTY_REST;
  const [method, setMethod] = useState(rc.method || "GET");
  const [url, setUrl] = useState(rc.url || "");
  const [headers, setHeaders] = useState(rc.headers || []);
  const [queryParams, setQueryParams] = useState(rc.query_params || []);
  const [authType, setAuthType] = useState(rc.auth_type || "none");
  const [authConfig, setAuthConfig] = useState(rc.auth_config || {});
  const [bodyType, setBodyType] = useState(rc.body_type || "none");
  const [bodyRaw, setBodyRaw] = useState(rc.body_raw || "");
  const [bodyForm, setBodyForm] = useState(rc.body_form || []);
  const [restTab, setRestTab] = useState("Params");

  // Code state
  const cc = tool?.code_config || EMPTY_CODE;
  const [language, setLanguage] = useState(cc.language || "python");
  const [code, setCode] = useState(cc.code || "");

  // MCP state
  const mc = tool?.mcp_config || EMPTY_MCP;
  const [mcpServerUrl, setMcpServerUrl] = useState(mc.server_url || "");
  const [mcpToolName, setMcpToolName] = useState(mc.tool_name || "");
  const [mcpAuthType, setMcpAuthType] = useState(mc.auth_type || "none");
  const [mcpAuthConfig, setMcpAuthConfig] = useState(mc.auth_config || {});
  const [mcpHeaders, setMcpHeaders] = useState(mc.headers || []);
  const [mcpTab, setMcpTab] = useState("Connection");
  const [mcpDiscoveredTools, setMcpDiscoveredTools] = useState([]);
  const [mcpDiscovering, setMcpDiscovering] = useState(false);

  // Test state
  const [testInputs, setTestInputs] = useState("{}");
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  const buildPayload = () => {
    const payload = { name, description, tool_type: toolType, tags: tags.split(",").map(t => t.trim()).filter(Boolean) };
    if (toolType === "rest_api") {
      payload.rest_api_config = { method, url, headers, query_params: queryParams, auth_type: authType, auth_config: authConfig, body_type: bodyType, body_raw: bodyRaw, body_form: bodyForm, timeout_seconds: 30, follow_redirects: true, verify_ssl: true };
    } else if (toolType === "code") {
      payload.code_config = { language, code, timeout_seconds: 30, packages: [] };
    } else if (toolType === "mcp") {
      payload.mcp_config = { server_url: mcpServerUrl, tool_name: mcpToolName, auth_type: mcpAuthType, auth_config: mcpAuthConfig, headers: mcpHeaders, timeout_seconds: 30 };
    }
    return payload;
  };

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const payload = buildPayload();
      const endpoint = isEdit ? `${API}/tools/${tool.tool_id}` : `${API}/tools`;
      const method_ = isEdit ? "PUT" : "POST";
      const resp = await fetch(endpoint, { method: method_, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = await resp.json();
      onSave(data);
    } catch (e) { console.error(e); } finally { setSaving(false); }
  };

  const handleTest = async () => {
    if (!name.trim()) return;
    setTesting(true); setTestResult(null);
    try {
      // Save first if new
      let toolId = tool?.tool_id;
      if (!toolId) {
        const payload = buildPayload();
        const resp = await apiFetch(`${API}/tools`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        const data = await resp.json();
        toolId = data.tool_id;
      } else {
        // Update before testing
        const payload = buildPayload();
        await apiFetch(`${API}/tools/${toolId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      }
      let inputs = {};
      try { inputs = JSON.parse(testInputs); } catch {}
      const resp = await apiFetch(`${API}/tools/${toolId}/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ inputs }) });
      const result = await resp.json();
      setTestResult(result);
      // Propagate tool_id if this was a new tool
      if (!tool?.tool_id && toolId) {
        tool = { ...tool, tool_id: toolId };
      }
    } catch (e) { setTestResult({ success: false, error: e.message }); } finally { setTesting(false); }
  };

  const discoverMcpTools = async () => {
    if (!mcpServerUrl) return;
    setMcpDiscovering(true);
    try {
      const resp = await apiFetch(`${API}/tools/mcp/discover`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ server_url: mcpServerUrl, headers: {} }) });
      const data = await resp.json();
      setMcpDiscoveredTools(data.tools || []);
    } catch (e) { setMcpDiscoveredTools([]); } finally { setMcpDiscovering(false); }
  };

  return (
    createPortal(<div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-start justify-center pt-8 overflow-y-auto pb-8" onClick={onCancel}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl border border-slate-200" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div>
            <h2 className="text-base font-semibold text-slate-900">{isEdit ? "Edit Tool" : "Create Tool"}</h2>
            <p className="text-xs text-slate-500 mt-0.5">Configure and test your tool</p>
          </div>
          <button onClick={onCancel} className="text-slate-400 hover:text-slate-700 cursor-pointer p-1"><X size={18} /></button>
        </div>

        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Name *</label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="My Tool"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Tags</label>
              <input value={tags} onChange={e => setTags(e.target.value)} placeholder="tag1, tag2"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="What does this tool do?"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none h-16" />
          </div>

          {/* Tool Type Selector */}
          {!isEdit && (
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-2">Tool Type</label>
              <div className="grid grid-cols-3 gap-3">
                {Object.entries(TYPE_META).map(([key, meta]) => (
                  <button key={key} onClick={() => setToolType(key)}
                    className={cn("border rounded-xl p-4 text-left cursor-pointer transition",
                      toolType === key ? `${meta.bg} ${meta.border} ring-2 ring-offset-1 ring-blue-400` : "border-slate-200 hover:border-slate-300 bg-white")}>
                    <div className="flex items-center gap-2 mb-1">
                      <meta.icon size={16} className={meta.color} />
                      <span className="text-sm font-semibold text-slate-900">{meta.label}</span>
                    </div>
                    <span className="text-[11px] text-slate-500">{meta.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── REST API CONFIG ─────────────────────────────────── */}
          {toolType === "rest_api" && (
            <div className="space-y-4">
              {/* URL bar (Postman-style) */}
              <div className="flex gap-2">
                <select value={method} onChange={e => setMethod(e.target.value)}
                  className={cn("border border-slate-200 rounded-lg px-3 py-2 text-sm font-bold bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 w-[120px]", METHOD_COLORS[method] || "text-slate-700")}>
                  {HTTP_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
                <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://api.example.com/v1/resource"
                  className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono bg-white focus:outline-none focus:ring-2 focus:ring-blue-400" />
              </div>

              {/* Postman-style tabs */}
              <Tabs tabs={["Params", "Headers", "Auth", "Body"]} active={restTab} onChange={setRestTab} />

              {restTab === "Params" && (
                <KVEditor rows={queryParams} onChange={setQueryParams} keyPlaceholder="Parameter" valuePlaceholder="Value" showDescription />
              )}
              {restTab === "Headers" && (
                <KVEditor rows={headers} onChange={setHeaders} keyPlaceholder="Header" valuePlaceholder="Value" showDescription />
              )}
              {restTab === "Auth" && (
                <AuthEditor authType={authType} authConfig={authConfig} onTypeChange={setAuthType} onConfigChange={setAuthConfig} />
              )}
              {restTab === "Body" && (
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    {["none", "json", "form", "raw"].map(bt => (
                      <label key={bt} className="flex items-center gap-1.5 cursor-pointer">
                        <input type="radio" name="bodyType" checked={bodyType === bt} onChange={() => setBodyType(bt)} className="accent-blue-600" />
                        <span className="text-xs text-slate-600 capitalize">{bt === "none" ? "None" : bt === "json" ? "JSON" : bt === "form" ? "Form Data" : "Raw"}</span>
                      </label>
                    ))}
                  </div>
                  {bodyType === "json" && (
                    <textarea value={bodyRaw} onChange={e => setBodyRaw(e.target.value)} rows={8} placeholder='{\n  "key": "value"\n}'
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-y" />
                  )}
                  {bodyType === "form" && (
                    <KVEditor rows={bodyForm} onChange={setBodyForm} keyPlaceholder="Field" valuePlaceholder="Value" />
                  )}
                  {bodyType === "raw" && (
                    <textarea value={bodyRaw} onChange={e => setBodyRaw(e.target.value)} rows={8} placeholder="Raw body content"
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-y" />
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── CODE CONFIG ────────────────────────────────────── */}
          {toolType === "code" && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <label className="text-xs font-medium text-slate-600">Language</label>
                <div className="flex gap-2">
                  {[["python", "Python"], ["javascript", "JavaScript"]].map(([val, label]) => (
                    <button key={val} onClick={() => setLanguage(val)}
                      className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border cursor-pointer transition",
                        language === val ? "bg-slate-900 border-slate-900 text-white" : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50")}>
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1">Code</label>
                <p className="text-[11px] text-slate-400 mb-2">
                  Define a <code className="bg-slate-100 px-1 rounded text-[11px]">run(params)</code> function that receives a dict/object and returns a dict/object.
                </p>
                <CodeEditor value={code} onChange={setCode} language={language} />
              </div>
            </div>
          )}

          {/* ── MCP CONFIG ─────────────────────────────────────── */}
          {toolType === "mcp" && (
            <div className="space-y-4">
              <Tabs tabs={["Connection", "Auth", "Headers"]} active={mcpTab} onChange={setMcpTab} />

              {mcpTab === "Connection" && (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-medium text-slate-600 block mb-1">MCP Server URL</label>
                    <div className="flex gap-2">
                      <input value={mcpServerUrl} onChange={e => setMcpServerUrl(e.target.value)} placeholder="http://localhost:3001/mcp"
                        className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono bg-white focus:outline-none focus:ring-2 focus:ring-blue-400" />
                      <button onClick={discoverMcpTools} disabled={mcpDiscovering || !mcpServerUrl}
                        className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-2 text-xs font-medium bg-white hover:bg-slate-50 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition">
                        <RefreshCw size={12} className={mcpDiscovering ? "animate-spin" : ""} />
                        {mcpDiscovering ? "Discovering..." : "Discover Tools"}
                      </button>
                    </div>
                  </div>
                  {mcpDiscoveredTools.length > 0 && (
                    <div>
                      <label className="text-xs font-medium text-slate-600 block mb-2">Available Tools ({mcpDiscoveredTools.length})</label>
                      <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto">
                        {mcpDiscoveredTools.map((t, i) => (
                          <button key={i} onClick={() => { setMcpToolName(t.name); }}
                            className={cn("text-left border rounded-lg p-3 cursor-pointer transition",
                              mcpToolName === t.name ? "border-blue-400 bg-blue-50 ring-1 ring-blue-400" : "border-slate-200 hover:border-slate-300 bg-white")}>
                            <div className="text-xs font-semibold text-slate-800">{t.name}</div>
                            {t.description && <div className="text-[11px] text-slate-500 mt-0.5">{t.description}</div>}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  <div>
                    <label className="text-xs font-medium text-slate-600 block mb-1">Tool Name</label>
                    <input value={mcpToolName} onChange={e => setMcpToolName(e.target.value)} placeholder="tool-name"
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono bg-white focus:outline-none focus:ring-2 focus:ring-blue-400" />
                  </div>
                </div>
              )}
              {mcpTab === "Auth" && (
                <AuthEditor authType={mcpAuthType} authConfig={mcpAuthConfig} onTypeChange={setMcpAuthType} onConfigChange={setMcpAuthConfig} />
              )}
              {mcpTab === "Headers" && (
                <KVEditor rows={mcpHeaders} onChange={setMcpHeaders} keyPlaceholder="Header" valuePlaceholder="Value" />
              )}
            </div>
          )}

          {/* ── TEST / PLAYGROUND ──────────────────────────────── */}
          <div className="border-t border-slate-200 pt-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-800">Test</h3>
              <button onClick={handleTest} disabled={testing || !name.trim()}
                className="flex items-center gap-1.5 bg-emerald-600 text-white rounded-lg px-4 py-1.5 text-xs font-medium cursor-pointer hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition">
                <Play size={12} /> {testing ? "Running..." : "Run Test"}
              </button>
            </div>
            {toolType === "code" && (
              <div>
                <label className="text-[11px] font-medium text-slate-500 block mb-1">Input Parameters (JSON)</label>
                <textarea value={testInputs} onChange={e => setTestInputs(e.target.value)} rows={3}
                  placeholder='{"key": "value"}'
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none" />
              </div>
            )}
            {toolType === "mcp" && (
              <div>
                <label className="text-[11px] font-medium text-slate-500 block mb-1">Tool Arguments (JSON)</label>
                <textarea value={testInputs} onChange={e => setTestInputs(e.target.value)} rows={3}
                  placeholder='{"query": "example"}'
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none" />
              </div>
            )}
            {testResult && <ResponseViewer result={testResult} />}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl">
          <button onClick={onCancel} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900 cursor-pointer transition">Cancel</button>
          <button onClick={handleSave} disabled={saving || !name.trim()}
            className="flex items-center gap-1.5 bg-jai-primary text-white rounded-lg px-5 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition">
            <Check size={14} /> {saving ? "Saving..." : isEdit ? "Update Tool" : "Create Tool"}
          </button>
        </div>
      </div>
    </div>, document.body)
  );
}

// ═══════════════════════════════════════════════════════════════════
// MAIN TOOLS PAGE
// ═══════════════════════════════════════════════════════════════════

export default function ToolsPage() {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingTool, setEditingTool] = useState(null);

  const loadTools = useCallback(() => {
    setLoading(true);
    apiFetch(`${API}/tools`)
      .then(r => r.json())
      .then(d => { setTools(d.tools || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => { loadTools(); }, [loadTools]);

  const filtered = tools.filter(t => {
    if (typeFilter !== "all" && t.tool_type !== typeFilter) return false;
    if (search && !t.name.toLowerCase().includes(search.toLowerCase()) && !(t.description || "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleCreate = () => { setEditingTool(null); setEditorOpen(true); };
  const handleEdit = async (toolId) => {
    try {
      const resp = await apiFetch(`${API}/tools/${toolId}`);
      const data = await resp.json();
      setEditingTool(data);
      setEditorOpen(true);
    } catch (e) { console.error(e); }
  };
  const handleDelete = async (toolId) => {
    try {
      await apiFetch(`${API}/tools/${toolId}`, { method: "DELETE" });
      loadTools();
    } catch (e) { console.error(e); }
  };
  const handleSaved = () => { setEditorOpen(false); setEditingTool(null); loadTools(); };

  const typeCounts = tools.reduce((acc, t) => { acc[t.tool_type] = (acc[t.tool_type] || 0) + 1; return acc; }, {});

  return (
    <div className="p-6 animate-fade-up max-w-7xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench size={20} className="text-slate-500" />
          <h1 className="text-lg font-semibold text-slate-900">Tool Registry</h1>
          <Badge variant="outline">{tools.length}</Badge>
        </div>
        <button onClick={handleCreate}
          className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover transition">
          <Plus size={14} /> Create Tool
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Total Tools", value: tools.length, icon: Wrench, color: "text-slate-600", bg: "bg-slate-50" },
          { label: "Code Tools", value: typeCounts.code || 0, icon: Code, color: "text-violet-600", bg: "bg-violet-50" },
          { label: "REST API Tools", value: typeCounts.rest_api || 0, icon: Globe, color: "text-blue-600", bg: "bg-blue-50" },
          { label: "MCP Connectors", value: typeCounts.mcp || 0, icon: Link2, color: "text-emerald-600", bg: "bg-emerald-50" },
        ].map(k => (
          <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-3.5">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wide">{k.label}</span>
              <div className={cn("w-6 h-6 rounded-md flex items-center justify-center", k.bg)}><k.icon size={13} className={k.color} /></div>
            </div>
            <div className="text-xl font-bold text-slate-900">{k.value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search tools..."
            className="w-full border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
        <div className="flex gap-1.5">
          {[["all", "All"], ["code", "Code"], ["rest_api", "REST API"], ["mcp", "MCP"]].map(([val, label]) => (
            <button key={val} onClick={() => setTypeFilter(val)}
              className={cn("px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer border transition",
                typeFilter === val ? "bg-slate-900 border-slate-900 text-white" : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50")}>
              {label}
            </button>
          ))}
        </div>
        <span className="text-xs text-slate-400 shrink-0">{filtered.length} tool{filtered.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Tool Grid */}
      {loading ? <div className="text-slate-400 text-sm py-6 text-center">Loading tools...</div> : filtered.length === 0 ? (
        <div className="text-center py-12">
          <Wrench size={32} className="mx-auto text-slate-300 mb-3" />
          <div className="text-sm font-medium text-slate-500">{search || typeFilter !== "all" ? "No tools match your filter" : "No tools yet"}</div>
          <div className="text-xs text-slate-400 mt-1 mb-4">Create Code, REST API, or MCP tools to extend agent capabilities.</div>
          <button onClick={handleCreate} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover transition">
            <Plus size={14} className="inline mr-1" />Create Tool
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map(t => {
            const meta = TYPE_META[t.tool_type] || TYPE_META.rest_api;
            return (
              <div key={t.tool_id} className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-md transition group">
                <div className="p-4">
                  <div className="flex items-start gap-3 mb-2">
                    <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5", meta.bg)}>
                      <meta.icon size={15} className={meta.color} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-slate-900 truncate">{t.name}</div>
                      <div className="text-xs text-slate-500 mt-0.5 line-clamp-2">{t.description || "No description"}</div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    <Badge variant="outline">{meta.label}</Badge>
                    <Badge variant={t.status === "active" ? "success" : "warn"}>{t.status}</Badge>
                    {t.executions > 0 && <Badge variant="info">{t.executions} runs</Badge>}
                    {t.tags?.map(tag => <Badge key={tag} variant="brand">{tag}</Badge>)}
                  </div>
                  {t.executions > 0 && (
                    <div className="flex items-center gap-4 mt-2.5 text-[11px] text-slate-400">
                      <span><Clock size={10} className="inline mr-0.5" />{t.avg_latency_ms?.toFixed(0)} ms avg</span>
                      <span><Zap size={10} className="inline mr-0.5" />{t.success_rate?.toFixed(0)}% success</span>
                    </div>
                  )}
                </div>
                <div className="px-4 py-2 border-t border-slate-100 flex justify-between items-center opacity-70 group-hover:opacity-100 transition">
                  <span className="text-[11px] text-slate-400 font-mono truncate">{t.tool_id}</span>
                  <div className="flex items-center gap-1">
                    <button onClick={() => handleEdit(t.tool_id)} className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer px-1.5 py-0.5 rounded hover:bg-slate-100 transition">
                      <Edit3 size={11} /> Edit
                    </button>
                    <button onClick={() => handleDelete(t.tool_id)} className="text-xs text-slate-400 hover:text-red-600 cursor-pointer px-1.5 py-0.5 rounded hover:bg-red-50 transition">
                      <Trash2 size={11} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Editor Dialog */}
      {editorOpen && (
        <ToolEditor tool={editingTool} onSave={handleSaved} onCancel={() => { setEditorOpen(false); setEditingTool(null); }} />
      )}
    </div>
  );
}
