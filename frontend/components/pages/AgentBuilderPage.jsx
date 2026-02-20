"use client";
import { useState, useEffect, useRef } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, toast } from "../shared/StudioUI";
import {
  Bot, Box, FileText, Wrench, Shield, Layers, Cloud, Zap, Check, X,
  ChevronDown, ChevronRight, ArrowRight, AlertTriangle, Brain, Database, Search, Send, MessageSquare,
  Play, Clock, DollarSign, Save, Loader2,
} from "lucide-react";

function estimateTokens(text) {
  if (!text) return 0;
  return Math.ceil(text.length / 3.8);
}

const BUILDER_STEPS = [
  { id: "identity", label: "Identity", icon: Bot },
  { id: "model", label: "Model", icon: Box },
  { id: "prompt", label: "System Prompt", icon: FileText },
  { id: "tools", label: "Tools & Knowledge", icon: Wrench },
  { id: "guardrails", label: "Guardrails", icon: Shield },
  { id: "memory", label: "Memory", icon: Layers },
  { id: "deploy", label: "Deploy", icon: Cloud },
];

const TOOL_CATEGORIES = {
  "built-in": { label: "Built-in Capabilities", icon: "⚡", order: 0 },
  "enterprise-connector": { label: "Enterprise Connectors", icon: "🔗", order: 1 },
  "data-connector": { label: "Data & Analytics", icon: "📊", order: 2 },
  "ai-tool": { label: "AI / LLM Tools", icon: "🤖", order: 3 },
  "other": { label: "Other Tools", icon: "🔧", order: 4 },
};

const GUARDRAIL_TYPE_META = {
  pii_detection: { label: "PII Detection", color: "danger", icon: "\u{1F6E1}\uFE0F" },
  prompt_injection: { label: "Prompt Injection", color: "danger", icon: "\u{1F512}" },
  profanity: { label: "Profanity Filter", color: "danger", icon: "\u{1F92C}" },
  regex_match: { label: "Regex Match", color: "warning", icon: "\u{1F524}" },
  valid_length: { label: "Length Limit", color: "info", icon: "\u{1F4CF}" },
  reading_time: { label: "Reading Time", color: "info", icon: "\u23F1\uFE0F" },
  custom: { label: "Custom", color: "outline", icon: "\u2699\uFE0F" },
};

const ACTION_COLORS = { block: "danger", warn: "warning", redact: "info", log: "outline" };

const SDLC_STAGES = [
  { id: "dev", label: "Development", color: "bg-slate-400", desc: "Build & iterate" },
  { id: "qa", label: "QA", color: "bg-amber-500", desc: "Automated tests & review" },
  { id: "uat", label: "UAT", color: "bg-blue-500", desc: "User acceptance testing" },
  { id: "prod", label: "Production", color: "bg-emerald-500", desc: "Live deployment" },
];

export default function AgentBuilderPage({ setPage, editAgent }) {
  const isEdit = !!editAgent;
  const [step, setStep] = useState("identity");
  const [tools, setTools] = useState([]);
  const [guardrails, setGuardrails] = useState([]);
  const [models, setModels] = useState([]);
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [saving, setSaving] = useState(false);
  const [testOpen, setTestOpen] = useState(false);
  const [testMessages, setTestMessages] = useState([]);
  const [testInput, setTestInput] = useState("");
  const [testLoading, setTestLoading] = useState(false);
  const [testMeta, setTestMeta] = useState(null);
  const [toolSearch, setToolSearch] = useState("");
  const [collapsedCats, setCollapsedCats] = useState([]);
  const [improvingPrompt, setImprovingPrompt] = useState(false);

  const defaultAgent = {
    name: "", description: "", tags: [],
    model_config: { model_id: "gemini-2.5-flash", temperature: 0.3, max_tokens: 4096, system_prompt: "", fallback_model_id: "" },
    rag_enabled: false, rag_config: { collection_ids: [], top_k: 5, score_threshold: 0.7 },
    memory_enabled: true, memory_config: { short_term_enabled: true, long_term_enabled: true, short_term_max_messages: 50, summarize_after: 20 },
    selected_tools: [], selected_guardrails_pre: [], selected_guardrails_post: [],
    deploy: { stage: "dev", owner_id: "admin", is_public: false, require_approval: false, rate_limit_rpm: 60 },
    context: "",
  };

  // Agent form state — pre-fill from editAgent if editing
  const [agent, setAgent] = useState(() => {
    if (!editAgent) return defaultAgent;
    return {
      ...defaultAgent,
      name: editAgent.name || "", description: editAgent.description || "",
      tags: editAgent.tags || [],
      model_config: { ...defaultAgent.model_config, model_id: editAgent.model || editAgent.model_config?.model_id || "gemini-2.5-flash", system_prompt: editAgent.context || editAgent.model_config?.system_prompt || "" },
      rag_enabled: !!editAgent.rag_enabled,
      rag_config: { ...defaultAgent.rag_config, collection_ids: editAgent.rag_config?.collection_ids || editAgent.knowledge_base_ids || [], top_k: editAgent.rag_config?.top_k || 5, score_threshold: editAgent.rag_config?.score_threshold || 0.7 },
      context: editAgent.context || "",
      selected_tools: (editAgent.tools || []).map(t => typeof t === "string" ? t : t.tool_id),
      deploy: { ...defaultAgent.deploy, stage: editAgent.deploy_stage || "dev" },
    };
  });

  const upd = (path, val) => {
    setAgent(prev => {
      const next = { ...prev };
      const parts = path.split(".");
      let obj = next;
      for (let i = 0; i < parts.length - 1; i++) { obj[parts[i]] = { ...obj[parts[i]] }; obj = obj[parts[i]]; }
      obj[parts[parts.length - 1]] = val;
      return next;
    });
  };

  const addTag = (tag) => { if (tag && !agent.tags.includes(tag)) upd("tags", [...agent.tags, tag]); };
  const removeTag = (tag) => upd("tags", agent.tags.filter(t => t !== tag));

  useEffect(() => {
    apiFetch(`${API}/tools`).then(r => r.json()).then(d => setTools(d.tools || [])).catch(() => {});
    apiFetch(`${API}/guardrails`).then(r => r.json()).then(d => setGuardrails(d.rules || [])).catch(() => {});
    apiFetch(`${API}/models`).then(r => r.json()).then(d => setModels(d.models || [])).catch(() => {});
    apiFetch(`${API}/knowledge-bases`).then(r => r.json()).then(d => setKnowledgeBases(d.knowledge_bases || [])).catch(() => {});
  }, []);

  const improvePrompt = async () => {
    setImprovingPrompt(true);
    try {
      const r = await apiFetch(`${API}/prompts/improve`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_prompt: agent.model_config.system_prompt,
          agent_name: agent.name,
          agent_description: agent.description,
          model_id: agent.model_config.model_id,
        }),
      });
      if (!r.ok) throw new Error("API error");
      const data = await r.json();
      upd("model_config.system_prompt", data.improved_prompt);
      toast.success(`Prompt improved via ${data.model} (${data.latency_ms}ms, ${data.input_tokens + data.output_tokens} tokens)`);
    } catch (e) { toast.error("AI improve failed — check your model integration"); }
    setImprovingPrompt(false);
  };

  const promptTokens = estimateTokens(agent.model_config.system_prompt);
  const contextTokens = estimateTokens(agent.context);
  const totalSystemTokens = promptTokens + contextTokens;
  const promptWords = (agent.model_config.system_prompt || "").trim().split(/\s+/).filter(Boolean).length;

  const saveAgent = async () => {
    setSaving(true);
    try {
      const body = {
        name: agent.name, description: agent.description, tags: agent.tags,
        model_config: agent.model_config, context: agent.context,
        rag_enabled: agent.rag_enabled, rag_config: agent.rag_config,
        knowledge_base_ids: agent.rag_config.collection_ids,
        memory_enabled: agent.memory_enabled,
        owner_id: agent.deploy.owner_id,
      };
      if (isEdit && editAgent.agent_id) {
        await apiFetch(`${API}/agents/${editAgent.agent_id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        toast.success(`Agent "${agent.name}" updated`);
      } else {
        await apiFetch(`${API}/agents`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        toast.success(`Agent "${agent.name}" created`);
      }
      setPage("Agents");
    } catch (e) { console.error(e); toast.error("Failed to save agent"); }
    setSaving(false);
  };

  const sendTestMessage = async () => {
    if (!testInput.trim()) return;
    const userMsg = { role: "user", content: testInput };
    setTestMessages(prev => [...prev, userMsg]);
    setTestInput(""); setTestLoading(true); setTestMeta(null);
    const startTime = Date.now();
    try {
      const res = await apiFetch(`${API}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: testInput, model: agent.model_config.model_id, system_prompt: agent.model_config.system_prompt, temperature: agent.model_config.temperature, max_tokens: agent.model_config.max_tokens }),
      });
      const data = await res.json();
      const elapsed = Date.now() - startTime;
      setTestMessages(prev => [...prev, { role: "assistant", content: data.response || data.content || "No response" }]);
      setTestMeta({
        latency_ms: elapsed,
        input_tokens: data.usage?.prompt_tokens || estimateTokens(testInput + agent.model_config.system_prompt),
        output_tokens: data.usage?.completion_tokens || estimateTokens(data.response || ""),
        model: agent.model_config.model_id,
        cost_est: ((data.usage?.prompt_tokens || 0) * 0.00001 + (data.usage?.completion_tokens || 0) * 0.00003).toFixed(6),
      });
    } catch (e) {
      setTestMessages(prev => [...prev, { role: "assistant", content: `Error: ${e.message}` }]);
    }
    setTestLoading(false);
  };

  // ── Section renderers ───────────────────────────────────────────
  const renderIdentity = () => (
    <div className="space-y-5">
      <div>
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Agent Name *</label>
        <input value={agent.name} onChange={e => upd("name", e.target.value)} placeholder="e.g. Procurement Analyst"
          className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition" />
      </div>
      <div>
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Description</label>
        <textarea value={agent.description} onChange={e => upd("description", e.target.value)} placeholder="What does this agent do? What problems does it solve?"
          className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition h-20 resize-y" />
      </div>
      <div>
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Tags</label>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {agent.tags.map(t => (
            <span key={t} className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded-full">
              {t} <button onClick={() => removeTag(t)} className="text-slate-400 hover:text-red-500 cursor-pointer"><X size={10} /></button>
            </span>
          ))}
        </div>
        <input placeholder="Type a tag and press Enter..." onKeyDown={e => { if (e.key === "Enter" && e.target.value.trim()) { addTag(e.target.value.trim()); e.target.value = ""; } }}
          className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition" />
      </div>
      <div>
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Additional Context</label>
        <textarea value={agent.context} onChange={e => upd("context", e.target.value)} placeholder="Additional context injected into every call (e.g. company rules, domain knowledge)..."
          className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition h-24 resize-y font-mono text-xs" />
        <div className="text-[11px] text-slate-400 mt-1">{estimateTokens(agent.context)} tokens · {(agent.context || "").trim().split(/\s+/).filter(Boolean).length} words</div>
      </div>
    </div>
  );

  const renderModel = () => (
    <div className="space-y-5">
      <div>
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Primary Model</label>
        <select value={agent.model_config.model_id} onChange={e => upd("model_config.model_id", e.target.value)}
          className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition">
          {models.length > 0 ? models.map(m => <option key={m.model_id} value={m.model_id}>{m.model_id} — {m.provider}</option>) : (
            <>
              <option value="gemini-2.5-flash">gemini-2.5-flash — Google</option>
              <option value="gemini-2.5-pro">gemini-2.5-pro — Google</option>
              <option value="gpt-4o">gpt-4o — OpenAI</option>
              <option value="gpt-4o-mini">gpt-4o-mini — OpenAI</option>
              <option value="claude-sonnet-4">claude-sonnet-4 — Anthropic</option>
              <option value="claude-3.5-haiku">claude-3.5-haiku — Anthropic</option>
            </>
          )}
        </select>
      </div>
      <div>
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Fallback Model</label>
        <select value={agent.model_config.fallback_model_id} onChange={e => upd("model_config.fallback_model_id", e.target.value)}
          className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition">
          <option value="">None</option>
          {models.length > 0 ? models.filter(m => m.model_id !== agent.model_config.model_id).map(m => <option key={m.model_id} value={m.model_id}>{m.model_id} — {m.provider}</option>) : (
            <>
              <option value="gemini-2.5-flash">gemini-2.5-flash — Google</option>
              <option value="gemini-2.5-pro">gemini-2.5-pro — Google</option>
              <option value="gpt-4o">gpt-4o — OpenAI</option>
              <option value="gpt-4o-mini">gpt-4o-mini — OpenAI</option>
              <option value="claude-sonnet-4">claude-sonnet-4 — Anthropic</option>
              <option value="claude-3.5-haiku">claude-3.5-haiku — Anthropic</option>
            </>
          )}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Temperature: {agent.model_config.temperature}</label>
          <input type="range" min="0" max="1" step="0.05" value={agent.model_config.temperature}
            onChange={e => upd("model_config.temperature", parseFloat(e.target.value))} className="w-full accent-jai-primary" />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1"><span>Precise (0)</span><span>Creative (1)</span></div>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Max Tokens: {agent.model_config.max_tokens}</label>
          <input type="range" min="256" max="32768" step="256" value={agent.model_config.max_tokens}
            onChange={e => upd("model_config.max_tokens", parseInt(e.target.value))} className="w-full accent-jai-primary" />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1"><span>256</span><span>32K</span></div>
        </div>
      </div>
      <div className="bg-slate-50 border border-slate-100 rounded-lg p-4">
        <div className="text-[11px] font-semibold text-slate-400 uppercase mb-2">Model Info</div>
        <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
          <div><span className="text-slate-400">Model:</span> {agent.model_config.model_id}</div>
          <div><span className="text-slate-400">Temp:</span> {agent.model_config.temperature}</div>
          <div><span className="text-slate-400">Max Output:</span> {agent.model_config.max_tokens} tokens</div>
          <div><span className="text-slate-400">Fallback:</span> {agent.model_config.fallback_model_id || "None"}</div>
        </div>
      </div>
    </div>
  );

  const renderPrompt = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">System Prompt</label>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span className={cn("px-1.5 py-0.5 rounded", promptTokens > 3000 ? "bg-amber-50 text-amber-600" : "bg-slate-50 text-slate-500")}>{promptTokens} tokens</span>
            <span className="bg-slate-50 text-slate-500 px-1.5 py-0.5 rounded">{promptWords} words</span>
          </div>
          <button onClick={improvePrompt} disabled={improvingPrompt}
            className={cn("flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 cursor-pointer bg-blue-50 px-2 py-1 rounded-lg font-medium transition", improvingPrompt && "opacity-60 cursor-wait")}>
            {improvingPrompt ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
            {improvingPrompt ? "Improving..." : "AI Improve"}
          </button>
        </div>
      </div>
      <textarea value={agent.model_config.system_prompt} onChange={e => upd("model_config.system_prompt", e.target.value)}
        disabled={improvingPrompt}
        placeholder="You are a helpful procurement analyst agent. You help users analyze spend data, manage suppliers, and optimize procurement processes..."
        className={cn("w-full bg-white border border-slate-200 rounded-lg px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition font-mono resize-y", improvingPrompt && "opacity-50 cursor-wait bg-slate-50")}
        style={{ minHeight: "280px" }} />
      {promptTokens > 0 && (
        <div className="bg-slate-50 border border-slate-100 rounded-lg p-3">
          <div className="text-[11px] font-semibold text-slate-400 uppercase mb-2">Token Estimate</div>
          <div className="grid grid-cols-4 gap-3 text-xs">
            <div><span className="text-slate-400">System prompt:</span> <span className="font-mono font-semibold text-slate-700">{promptTokens}</span></div>
            <div><span className="text-slate-400">Context:</span> <span className="font-mono font-semibold text-slate-700">{contextTokens}</span></div>
            <div><span className="text-slate-400">Total fixed:</span> <span className="font-mono font-semibold text-slate-900">{totalSystemTokens}</span></div>
            <div><span className="text-slate-400">Budget left:</span> <span className={cn("font-mono font-semibold", agent.model_config.max_tokens - totalSystemTokens < 500 ? "text-red-600" : "text-emerald-600")}>{Math.max(0, agent.model_config.max_tokens - totalSystemTokens)}</span></div>
          </div>
          {totalSystemTokens > agent.model_config.max_tokens * 0.5 && (
            <div className="mt-2 text-[11px] text-amber-600 flex items-center gap-1"><AlertTriangle size={10} /> System prompt uses over 50% of max token budget</div>
          )}
        </div>
      )}
    </div>
  );

  const toggleCat = (cat) => setCollapsedCats(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]);

  const renderTools = () => {
    const filteredTools = tools.filter(t => !toolSearch || t.name.toLowerCase().includes(toolSearch.toLowerCase()) || (t.description || "").toLowerCase().includes(toolSearch.toLowerCase()));
    // Group by category
    const grouped = {};
    filteredTools.forEach(t => {
      const cat = t.category || "other";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(t);
    });
    const sortedCats = Object.keys(grouped).sort((a, b) => (TOOL_CATEGORIES[a]?.order ?? 99) - (TOOL_CATEGORIES[b]?.order ?? 99));

    return (
      <div className="space-y-4">
        {/* RAG — Knowledge Retrieval with KB selection */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            <span>⚡</span> Knowledge Retrieval
          </div>
          <div onClick={() => upd("rag_enabled", !agent.rag_enabled)}
            className={cn("rounded-lg border p-3 cursor-pointer transition", agent.rag_enabled ? "border-[#F2B3C6] bg-[#FDF1F5]" : "border-slate-200 bg-white hover:border-slate-300")}>
            <div className="flex items-center gap-3">
              <div className={cn("w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition",
                agent.rag_enabled ? "bg-jai-primary border-jai-primary" : "border-slate-300")}>
                {agent.rag_enabled && <Check size={12} className="text-white" />}
              </div>
              <Brain size={16} className="text-emerald-600" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-900">Knowledge Retrieval (RAG)</div>
                <div className="text-xs text-slate-500">Retrieve relevant documents from your knowledge bases and inject into context</div>
              </div>
              <Badge variant="brand">built-in</Badge>
            </div>
          </div>
          {agent.rag_enabled && (
            <div className="ml-0 space-y-3" onClick={e => e.stopPropagation()}>
              {/* KB Selection */}
              <div className="bg-white border border-slate-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-[11px] font-semibold text-slate-500 uppercase">Knowledge Bases</label>
                  <span className="text-[11px] text-slate-400">{agent.rag_config.collection_ids.length} selected</span>
                </div>
                {knowledgeBases.length === 0 ? (
                  <div className="text-center py-4">
                    <Database size={20} className="mx-auto text-slate-300 mb-1.5" />
                    <div className="text-xs text-slate-400 mb-2">No knowledge bases created yet</div>
                    <button onClick={(e) => { e.stopPropagation(); setPage("KnowledgeBases"); }}
                      className="text-xs text-jai-primary font-medium hover:underline cursor-pointer">Create Knowledge Base →</button>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {knowledgeBases.map(kb => {
                      const isSelected = agent.rag_config.collection_ids.includes(kb.kb_id);
                      return (
                        <div key={kb.kb_id}
                          onClick={(e) => {
                            e.stopPropagation();
                            const next = isSelected
                              ? agent.rag_config.collection_ids.filter(id => id !== kb.kb_id)
                              : [...agent.rag_config.collection_ids, kb.kb_id];
                            upd("rag_config.collection_ids", next);
                          }}
                          className={cn("flex items-center gap-2.5 p-2.5 rounded-lg border cursor-pointer transition",
                            isSelected ? "border-[#F2B3C6] bg-[#FDF1F5]" : "border-slate-100 bg-slate-50 hover:border-slate-300")}>
                          <div className={cn("w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition",
                            isSelected ? "bg-jai-primary border-jai-primary" : "border-slate-300")}>
                            {isSelected && <Check size={10} className="text-white" />}
                          </div>
                          <Database size={14} className={cn("shrink-0", isSelected ? "text-jai-primary" : "text-slate-400")} />
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-medium text-slate-900">{kb.name}</div>
                            <div className="text-[11px] text-slate-400 truncate">{kb.description}</div>
                          </div>
                          <div className="text-right shrink-0">
                            <div className="text-[11px] text-slate-500">{kb.documents} docs</div>
                            <div className="text-[11px] text-slate-400">{kb.chunks} chunks</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
              {/* RAG Config */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] text-slate-500 block mb-0.5">Top K (chunks per query)</label>
                  <input type="number" min="1" max="20" value={agent.rag_config.top_k} onChange={e => upd("rag_config.top_k", parseInt(e.target.value) || 5)}
                    className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-xs outline-none" />
                </div>
                <div>
                  <label className="text-[11px] text-slate-500 block mb-0.5">Score Threshold (0–1)</label>
                  <input type="number" min="0" max="1" step="0.05" value={agent.rag_config.score_threshold} onChange={e => upd("rag_config.score_threshold", parseFloat(e.target.value) || 0.7)}
                    className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-xs outline-none" />
                </div>
              </div>
              {agent.rag_config.collection_ids.length > 0 && (
                <div className="bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 text-[11px] text-slate-500">
                  Agent will search across <strong className="text-slate-700">{agent.rag_config.collection_ids.length}</strong> knowledge base{agent.rag_config.collection_ids.length !== 1 ? "s" : ""}, retrieving top <strong className="text-slate-700">{agent.rag_config.top_k}</strong> chunks with score ≥ <strong className="text-slate-700">{agent.rag_config.score_threshold}</strong>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Search + count */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" size={13} />
            <input value={toolSearch} onChange={e => setToolSearch(e.target.value)} placeholder="Filter tools..."
              className="w-full bg-white border border-slate-200 rounded-lg py-1.5 pl-7 pr-3 text-xs outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition" />
          </div>
          <span className="text-[11px] text-slate-400 shrink-0">{agent.selected_tools.length} selected</span>
        </div>

        {/* Categorized grid */}
        {tools.length === 0 ? <div className="text-sm text-slate-400 text-center py-4">No tools registered.</div> : (
          <div className="space-y-3">
            {sortedCats.map(cat => {
              const meta = TOOL_CATEGORIES[cat] || TOOL_CATEGORIES.other;
              const catTools = grouped[cat];
              const collapsed = collapsedCats.includes(cat);
              const selectedCount = catTools.filter(t => agent.selected_tools.includes(t.tool_id)).length;
              return (
                <div key={cat}>
                  <button onClick={() => toggleCat(cat)}
                    className="w-full flex items-center gap-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider py-1 cursor-pointer hover:text-slate-700 transition">
                    <span>{meta.icon}</span>
                    <span>{meta.label}</span>
                    <span className="text-slate-300 font-normal">({selectedCount}/{catTools.length})</span>
                    <div className="flex-1" />
                    <ChevronDown size={12} className={cn("transition", collapsed && "-rotate-90")} />
                  </button>
                  {!collapsed && (
                    <div className="grid grid-cols-2 gap-2 mt-1">
                      {catTools.map(t => {
                        const selected = agent.selected_tools.includes(t.tool_id);
                        return (
                          <div key={t.tool_id} onClick={() => upd("selected_tools", selected ? agent.selected_tools.filter(id => id !== t.tool_id) : [...agent.selected_tools, t.tool_id])}
                            className={cn("flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer transition",
                              selected ? "border-[#F2B3C6] bg-[#FDF1F5]" : "border-slate-200 bg-white hover:border-slate-300")}>
                            <div className={cn("w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition",
                              selected ? "bg-jai-primary border-jai-primary" : "border-slate-300")}>
                              {selected && <Check size={10} className="text-white" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-xs font-medium text-slate-900 leading-tight">{t.name}</div>
                              <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{t.description || "No description"}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const renderGuardrails = () => {
    const deployed = guardrails.filter(g => g.enabled && g.is_deployed);
    const beforeLLM = deployed.filter(g => g.applies_to === "input" || g.applies_to === "both");
    const afterLLM = deployed.filter(g => g.applies_to === "output" || g.applies_to === "both");
    const totalSelected = agent.selected_guardrails_pre.length + agent.selected_guardrails_post.length;

    const renderGuardrailList = (items, field) => (
      <div className="space-y-1.5">
        {items.map(g => {
          const meta = GUARDRAIL_TYPE_META[g.rule_type] || GUARDRAIL_TYPE_META.custom;
          const selected = agent[field].includes(g.rule_id);
          return (
            <div key={g.rule_id} onClick={() => upd(field, selected ? agent[field].filter(id => id !== g.rule_id) : [...agent[field], g.rule_id])}
              className={cn("flex items-center gap-2.5 p-2.5 rounded-lg border cursor-pointer transition",
                selected ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white hover:border-slate-300")}>
              <div className={cn("w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition",
                selected ? "bg-emerald-600 border-emerald-600" : "border-slate-300")}>
                {selected && <Check size={10} className="text-white" />}
              </div>
              <span className="text-sm">{meta.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-slate-900">{g.name}</div>
                <div className="text-[11px] text-slate-400 mt-0.5 truncate">{g.description}</div>
              </div>
              <Badge variant={ACTION_COLORS[g.action] || "outline"} className="text-[11px]">{g.action}</Badge>
            </div>
          );
        })}
        {items.length === 0 && <div className="text-xs text-slate-400 text-center py-3">No deployed guards for this phase. Deploy guards in the Guardrails page.</div>}
      </div>
    );

    return (
      <div className="space-y-5">
        <div className="text-xs text-slate-400">{totalSelected} guardrails active &middot; {deployed.length} deployed</div>

        {deployed.length === 0 ? (
          <div className="text-center py-6 space-y-2">
            <Shield size={20} className="text-slate-300 mx-auto" />
            <div className="text-sm text-slate-400">No guards deployed yet</div>
            <div className="text-xs text-slate-400">Deploy guards in the <span className="font-medium text-slate-600">Guardrails</span> page, then select them here.</div>
          </div>
        ) : (
          <>
            {/* Before LLM */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div className="px-4 py-3 bg-amber-50 border-b border-amber-100 flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center"><ArrowRight size={12} className="text-amber-600" /></div>
                <div>
                  <div className="text-xs font-semibold text-amber-800">Before LLM</div>
                  <div className="text-[11px] text-amber-600">Applied to user input before it reaches the model — block injections, redact PII, validate format</div>
                </div>
                <div className="flex-1" />
                <span className="text-[11px] font-mono text-amber-500">{agent.selected_guardrails_pre.length}/{beforeLLM.length}</span>
              </div>
              <div className="p-3">{renderGuardrailList(beforeLLM, "selected_guardrails_pre")}</div>
            </div>

            {/* LLM */}
            <div className="flex items-center justify-center gap-2 text-slate-300">
              <div className="h-px flex-1 bg-slate-200" />
              <div className="flex items-center gap-1.5 bg-slate-100 rounded-full px-3 py-1.5">
                <Brain size={12} className="text-slate-500" />
                <span className="text-[11px] text-slate-500 font-semibold">LLM Processing</span>
              </div>
              <div className="h-px flex-1 bg-slate-200" />
            </div>

            {/* After LLM */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div className="px-4 py-3 bg-blue-50 border-b border-blue-100 flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center"><Check size={12} className="text-blue-600" /></div>
                <div>
                  <div className="text-xs font-semibold text-blue-800">After LLM</div>
                  <div className="text-[11px] text-blue-600">Applied to model output before returning to user — check profanity, validate length, redact sensitive data</div>
                </div>
                <div className="flex-1" />
                <span className="text-[11px] font-mono text-blue-500">{agent.selected_guardrails_post.length}/{afterLLM.length}</span>
              </div>
              <div className="p-3">{renderGuardrailList(afterLLM, "selected_guardrails_post")}</div>
            </div>
          </>
        )}
      </div>
    );
  };

  const renderMemory = () => (
    <div className="space-y-5">
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Short-term Memory</label>
          <button onClick={() => upd("memory_config.short_term_enabled", !agent.memory_config.short_term_enabled)}
            className={cn("w-10 h-5 rounded-full transition relative cursor-pointer", agent.memory_config.short_term_enabled ? "bg-emerald-500" : "bg-slate-300")}>
            <div className={cn("w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all shadow-sm", agent.memory_config.short_term_enabled ? "left-5" : "left-0.5")} />
          </button>
        </div>
        {agent.memory_config.short_term_enabled && (
          <div className="bg-slate-50 border border-slate-100 rounded-lg p-4">
            <label className="text-xs text-slate-500 block mb-1">Max Messages in Context</label>
            <input type="number" min="5" max="200" value={agent.memory_config.short_term_max_messages}
              onChange={e => upd("memory_config.short_term_max_messages", parseInt(e.target.value) || 50)}
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" />
          </div>
        )}
      </div>
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Long-term Memory</label>
          <button onClick={() => upd("memory_config.long_term_enabled", !agent.memory_config.long_term_enabled)}
            className={cn("w-10 h-5 rounded-full transition relative cursor-pointer", agent.memory_config.long_term_enabled ? "bg-emerald-500" : "bg-slate-300")}>
            <div className={cn("w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all shadow-sm", agent.memory_config.long_term_enabled ? "left-5" : "left-0.5")} />
          </button>
        </div>
        {agent.memory_config.long_term_enabled && (
          <div className="bg-slate-50 border border-slate-100 rounded-lg p-4 space-y-3">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Summarize After (messages)</label>
              <input type="number" min="5" max="100" value={agent.memory_config.summarize_after}
                onChange={e => upd("memory_config.summarize_after", parseInt(e.target.value) || 20)}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" />
            </div>
            <p className="text-[11px] text-slate-400">Long-term memory stores key facts and conversation summaries across sessions.</p>
          </div>
        )}
      </div>
    </div>
  );

  const renderDeploy = () => {
    const currentStageIdx = SDLC_STAGES.findIndex(s => s.id === agent.deploy.stage);
    return (
      <div className="space-y-5">
        {/* SDLC Pipeline */}
        <div>
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-3">Deployment Stage</label>
          <div className="flex items-center gap-0">
            {SDLC_STAGES.map((stage, i) => {
              const isActive = agent.deploy.stage === stage.id;
              const isPast = i < currentStageIdx;
              const isNext = i === currentStageIdx + 1;
              return (
                <div key={stage.id} className="flex items-center flex-1">
                  <button onClick={() => upd("deploy.stage", stage.id)}
                    className={cn("flex-1 relative rounded-lg border-2 p-3 cursor-pointer transition text-center",
                      isActive ? "border-blue-500 bg-blue-50 shadow-sm" : isPast ? "border-emerald-200 bg-emerald-50" : "border-slate-200 bg-white hover:border-slate-300")}>
                    <div className={cn("w-7 h-7 rounded-full mx-auto mb-1.5 flex items-center justify-center text-white text-xs font-bold",
                      isActive ? stage.color : isPast ? "bg-emerald-500" : "bg-slate-200")}>
                      {isPast ? <Check size={14} /> : i + 1}
                    </div>
                    <div className={cn("text-xs font-semibold", isActive ? "text-jai-primary" : isPast ? "text-emerald-700" : "text-slate-500")}>{stage.label}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{stage.desc}</div>
                    {isNext && (
                      <div className="absolute -top-2 left-1/2 -translate-x-1/2 text-[8px] font-semibold text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded-full">NEXT</div>
                    )}
                  </button>
                  {i < SDLC_STAGES.length - 1 && (
                    <div className={cn("w-4 h-0.5 shrink-0", i < currentStageIdx ? "bg-emerald-400" : "bg-slate-200")} />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Promote button */}
        {currentStageIdx < SDLC_STAGES.length - 1 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-jai-primary">Promote to {SDLC_STAGES[currentStageIdx + 1]?.label}</div>
              <div className="text-[11px] text-blue-600 mt-0.5">
                {currentStageIdx === 0 && "Run automated tests before promoting to QA"}
                {currentStageIdx === 1 && "Requires QA sign-off to promote to UAT"}
                {currentStageIdx === 2 && "Requires UAT approval and change request to promote to Production"}
              </div>
            </div>
            <button onClick={() => upd("deploy.stage", SDLC_STAGES[currentStageIdx + 1].id)}
              className="flex items-center gap-1 bg-jai-primary text-white rounded-lg px-3 py-1.5 text-xs font-medium cursor-pointer">
              <ArrowRight size={12} /> Promote
            </button>
          </div>
        )}
        {currentStageIdx === SDLC_STAGES.length - 1 && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 flex items-center gap-2">
            <Check size={14} className="text-emerald-600" />
            <span className="text-xs font-semibold text-emerald-800">This agent is deployed to Production</span>
          </div>
        )}

        <hr className="border-slate-100" />

        {/* Owner & Access */}
        <div>
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Owner</label>
          <input value={agent.deploy.owner_id} onChange={e => upd("deploy.owner_id", e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-4 py-3">
            <span className="text-sm text-slate-700">Public Access</span>
            <button onClick={() => upd("deploy.is_public", !agent.deploy.is_public)}
              className={cn("w-10 h-5 rounded-full transition relative cursor-pointer", agent.deploy.is_public ? "bg-emerald-500" : "bg-slate-300")}>
              <div className={cn("w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all shadow-sm", agent.deploy.is_public ? "left-5" : "left-0.5")} />
            </button>
          </div>
          <div className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-4 py-3">
            <span className="text-sm text-slate-700">Require Approval</span>
            <button onClick={() => upd("deploy.require_approval", !agent.deploy.require_approval)}
              className={cn("w-10 h-5 rounded-full transition relative cursor-pointer", agent.deploy.require_approval ? "bg-emerald-500" : "bg-slate-300")}>
              <div className={cn("w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all shadow-sm", agent.deploy.require_approval ? "left-5" : "left-0.5")} />
            </button>
          </div>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Rate Limit (requests/min)</label>
          <input type="number" min="1" max="1000" value={agent.deploy.rate_limit_rpm} onChange={e => upd("deploy.rate_limit_rpm", parseInt(e.target.value) || 60)}
            className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition" />
        </div>

        {/* Deployment info */}
        <div className="bg-slate-50 border border-slate-100 rounded-lg p-4">
          <div className="text-[11px] font-semibold text-slate-400 uppercase mb-2">Endpoint Info</div>
          <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
            <div><span className="text-slate-400">Endpoint:</span> /agents/&lt;id&gt;/invoke</div>
            <div><span className="text-slate-400">Auth:</span> Bearer Token</div>
            <div><span className="text-slate-400">Rate:</span> {agent.deploy.rate_limit_rpm} RPM</div>
            <div><span className="text-slate-400">Stage:</span> <span className="font-semibold">{SDLC_STAGES[currentStageIdx]?.label}</span></div>
          </div>
        </div>
      </div>
    );
  };

  const STEP_RENDERERS = { identity: renderIdentity, model: renderModel, prompt: renderPrompt, tools: renderTools, guardrails: renderGuardrails, memory: renderMemory, deploy: renderDeploy };
  const currentStepIdx = BUILDER_STEPS.findIndex(s => s.id === step);

  return (
    <div className="flex h-full flex-col">
      {/* Progress bar (item 10) */}
      <div className="h-0.5 bg-slate-100 flex-shrink-0">
        <div className="h-full bg-gradient-to-r from-jai-primary to-jai-primary/60 transition-all duration-300" style={{ width: `${((currentStepIdx + 1) / BUILDER_STEPS.length) * 100}%` }} />
      </div>
      <div className="flex flex-1 min-h-0">
      {/* Left sidebar — steps nav */}
      <div className="w-56 border-r border-slate-200 bg-white shrink-0 flex flex-col">
        <div className="p-4 border-b border-slate-100">
          <button onClick={() => setPage("Agents")} className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer mb-2">
            <ChevronRight size={12} className="rotate-180" /> Back to Agents
          </button>
          <h2 className="text-base font-semibold text-slate-900">{isEdit ? "Edit Agent" : "New Agent"}</h2>
          <p className="text-[11px] text-slate-400 mt-0.5">{isEdit ? `Editing ${editAgent.name}` : "Configure all aspects of your agent"}</p>
        </div>
        <div className="flex-1 p-2 space-y-0.5 overflow-y-auto">
          {BUILDER_STEPS.map((s, i) => {
            const Icon = s.icon;
            const active = step === s.id;
            const done = i < currentStepIdx;
            return (
              <button key={s.id} onClick={() => setStep(s.id)}
                className={cn("w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm cursor-pointer transition text-left",
                  active ? "bg-[#FDF1F5] text-jai-primary font-medium" : "text-slate-600 hover:bg-slate-50")}>
                <div className={cn("w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0",
                  active ? "bg-jai-primary text-white" : done ? "bg-emerald-100 text-emerald-600" : "bg-slate-100 text-slate-400")}>
                  {done ? <Check size={12} /> : i + 1}
                </div>
                <span className="truncate">{s.label}</span>
              </button>
            );
          })}
        </div>
        <div className="p-3 border-t border-slate-100 space-y-2">
          <button onClick={saveAgent} disabled={!agent.name || saving}
            className={cn("w-full flex items-center justify-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2.5 text-sm font-medium cursor-pointer transition",
              (!agent.name || saving) && "opacity-50 cursor-not-allowed")}>
            {saving ? "Saving..." : isEdit ? "Update Agent" : "Create Agent"}
          </button>
          <button onClick={() => setTestOpen(!testOpen)}
            className="w-full flex items-center justify-center gap-2 border border-slate-200 text-slate-700 rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-slate-50 transition">
            <Play size={13} /> {testOpen ? "Hide Test" : "Test Agent"}
          </button>
        </div>
      </div>

      {/* Center — form content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-6">
          <div className="flex items-center gap-2 mb-5">
            {(() => { const Icon = BUILDER_STEPS[currentStepIdx]?.icon || Bot; return <Icon size={18} className="text-jai-primary" />; })()}
            <h3 className="text-lg font-semibold text-slate-900">{BUILDER_STEPS[currentStepIdx]?.label}</h3>
          </div>
          {STEP_RENDERERS[step]?.()}
          {/* Step navigation */}
          <div className="flex items-center justify-between mt-8 pt-4 border-t border-slate-100">
            <button disabled={currentStepIdx === 0} onClick={() => setStep(BUILDER_STEPS[currentStepIdx - 1]?.id)}
              className={cn("flex items-center gap-1 text-sm text-slate-500 cursor-pointer hover:text-slate-900 transition", currentStepIdx === 0 && "opacity-30 cursor-not-allowed")}>
              <ChevronRight size={14} className="rotate-180" /> Previous
            </button>
            {currentStepIdx < BUILDER_STEPS.length - 1 ? (
              <button onClick={() => setStep(BUILDER_STEPS[currentStepIdx + 1]?.id)}
                className="flex items-center gap-1 text-sm text-jai-primary font-medium cursor-pointer hover:text-[#C73D65] transition">
                Next <ChevronRight size={14} />
              </button>
            ) : (
              <button onClick={saveAgent} disabled={!agent.name || saving}
                className={cn("flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer transition",
                  (!agent.name || saving) && "opacity-50 cursor-not-allowed")}>
                {isEdit ? "Update Agent" : "Create Agent"}
              </button>
            )}
          </div>
        </div>
      </div>

      </div>{/* close inner flex */}
      {/* Right panel — Test chat */}
      {testOpen && (
        <div className="w-[360px] border-l border-slate-200 bg-white shrink-0 flex flex-col">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Test Agent</h3>
            <button onClick={() => setTestOpen(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer"><X size={14} /></button>
          </div>
          {/* Test meta / token info */}
          {testMeta && (
            <div className="px-4 py-2 bg-slate-50 border-b border-slate-100">
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                <div><span className="text-slate-400">Model:</span> <span className="font-mono text-slate-600">{testMeta.model}</span></div>
                <div><span className="text-slate-400">Latency:</span> <span className="font-mono text-slate-600">{testMeta.latency_ms}ms</span></div>
                <div><span className="text-slate-400">Input tokens:</span> <span className="font-mono text-blue-600">{testMeta.input_tokens}</span></div>
                <div><span className="text-slate-400">Output tokens:</span> <span className="font-mono text-emerald-600">{testMeta.output_tokens}</span></div>
                <div className="col-span-2"><span className="text-slate-400">Est. cost:</span> <span className="font-mono text-slate-600">${testMeta.cost_est}</span></div>
              </div>
            </div>
          )}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {testMessages.length === 0 && (
              <div className="text-center text-sm text-slate-400 py-8">Send a message to test your agent configuration.</div>
            )}
            {testMessages.map((m, i) => (
              <div key={i} className={cn("flex gap-2", m.role === "user" ? "flex-row-reverse" : "flex-row")}>
                <div className={cn("w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0",
                  m.role === "user" ? "bg-jai-primary text-white" : "bg-slate-100 text-slate-700")}>
                  {m.role === "user" ? "U" : "AI"}
                </div>
                <div className={cn("max-w-[80%] px-3 py-2 rounded-lg text-xs leading-relaxed",
                  m.role === "user" ? "bg-jai-primary text-white" : "bg-slate-100 text-slate-900")}>
                  {m.content}
                </div>
              </div>
            ))}
            {testLoading && <div className="text-xs text-slate-400 animate-pulse">Thinking...</div>}
          </div>
          <div className="p-3 border-t border-slate-100">
            <div className="flex gap-2">
              <input value={testInput} onChange={e => setTestInput(e.target.value)} onKeyDown={e => e.key === "Enter" && sendTestMessage()}
                placeholder="Test message..." className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition" />
              <button onClick={sendTestMessage} disabled={!testInput.trim() || testLoading}
                className={cn("bg-jai-primary text-white rounded-lg px-3 py-2 cursor-pointer", (!testInput.trim() || testLoading) && "opacity-50 cursor-not-allowed")}>
                <Send size={12} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
