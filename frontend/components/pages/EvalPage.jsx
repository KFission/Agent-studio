"use client";
import { useState, useEffect, useRef } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, Tabs, StatCard, toast, relativeTime } from "../shared/StudioUI";
import {
  Play, Send, BarChart3, Box, Clock, DollarSign, Zap, Check, X,
  ChevronDown, History, RefreshCw, Loader2, Eye, Save, AlertCircle,
  Shield, Target, Brain,
} from "lucide-react";

const PROVIDER_COLORS = { google: "bg-blue-50 text-blue-700 border-blue-200", openai: "bg-emerald-50 text-emerald-700 border-emerald-200", anthropic: "bg-amber-50 text-amber-700 border-amber-200", ollama: "bg-purple-50 text-purple-700 border-purple-200" };
const PROVIDER_LABELS = { google: "Google", openai: "OpenAI", anthropic: "Anthropic", ollama: "Ollama" };

export default function EvalPage() {
  const [systemPrompt, setSystemPrompt] = useState("You are a procurement analyst AI. Extract and classify information from the given input with precision. Always structure your output clearly.");
  const [userInput, setUserInput] = useState("Classify this procurement request: 'We need {{quantity}} units of {{item}} by {{deadline}}.'");
  const [variables, setVariables] = useState({});
  const [selModels, setSelModels] = useState([]);
  const [temperature, setTemperature] = useState(0.3);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [results, setResults] = useState(null);
  const [running, setRunning] = useState(false);
  const [runStatuses, setRunStatuses] = useState({});
  const [viewMode, setViewMode] = useState("battle");
  const [expandedCards, setExpandedCards] = useState({});
  const [savedRuns, setSavedRuns] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [models, setModels] = useState([]);
  const [referenceText, setReferenceText] = useState("");
  const [llmJudgeEnabled, setLlmJudgeEnabled] = useState(false);
  const [judgeModel, setJudgeModel] = useState("gemini-2.5-flash");
  const [scoringMetrics, setScoringMetrics] = useState(["rouge_l", "bleu", "contains"]);

  useEffect(() => {
    apiFetch(`${API}/models`).then(r => r.json()).then(d => {
      const m = d.models || [];
      setModels(m);
      // Auto-select first 2 available models
      if (m.length > 0 && selModels.length === 0) {
        setSelModels(m.slice(0, Math.min(2, m.length)).map(x => x.model_id));
      }
      // Set judge model to first available
      if (m.length > 0) setJudgeModel(m[0].model_id);
    }).catch(() => {});
    apiFetch(`${API}/eval/runs?limit=10`).then(r => r.json()).then(d => setSavedRuns(d.runs || [])).catch(() => {});
  }, []);

  // Auto-detect {{variables}} in user input
  useEffect(() => {
    const matches = userInput.match(/\{\{(\w+)\}\}/g) || [];
    const varNames = [...new Set(matches.map(m => m.replace(/[{}]/g, "")))];
    setVariables(prev => {
      const next = {};
      varNames.forEach(v => { next[v] = prev[v] || ""; });
      return next;
    });
  }, [userInput]);

  const resolvedInput = () => {
    let text = userInput;
    Object.entries(variables).forEach(([k, v]) => {
      text = text.replace(new RegExp(`\\{\\{${k}\\}\\}`, "g"), v || `{{${k}}}`);
    });
    return text;
  };

  const toggle = (id) => {
    setSelModels(prev => {
      if (prev.includes(id)) return prev.filter(m => m !== id);
      if (prev.length >= 4) return prev;
      return [...prev, id];
    });
  };

  const availableModels = models.map(m => ({
    id: m.model_id,
    label: m.display_name || m.model_id,
    provider: m.provider || "unknown",
    tier: "fast",
    input: (m.pricing?.input_cost_per_1k || 0) * 1000,
    output: (m.pricing?.output_cost_per_1k || 0) * 1000,
  }));

  const run = async () => {
    setRunning(true); setResults(null);
    const statuses = {};
    selModels.forEach(m => { statuses[m] = "running"; });
    setRunStatuses({ ...statuses });

    const fullPrompt = systemPrompt ? `${systemPrompt}\n\n${resolvedInput()}` : resolvedInput();
    const payload = { prompt: fullPrompt, model_ids: selModels, temperature, max_tokens: maxTokens };
    if (referenceText.trim()) {
      payload.reference_text = referenceText.trim();
      payload.scoring_metrics = scoringMetrics;
    }
    if (llmJudgeEnabled) {
      payload.llm_judge_enabled = true;
      payload.judge_model_id = judgeModel;
    }

    // Use SSE streaming endpoint — results arrive as each model completes
    try {
      const r = await apiFetch(`${API}/eval/stream`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      const streamedResults = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop(); // keep incomplete line in buffer
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.event === "result") {
              streamedResults.push(evt);
              statuses[evt.model_id] = evt.status === "completed" ? "success" : "error";
              setRunStatuses({ ...statuses });
              // Update results progressively
              setResults(prev => {
                const results = [...(prev?.results || [])];
                const idx = results.findIndex(x => x.model_id === evt.model_id);
                if (idx >= 0) results[idx] = evt; else results.push(evt);
                return { ...prev, results };
              });
            }
          } catch {}
        }
      }
    } catch (e) {
      setResults(prev => ({ ...prev, error: e.message }));
      selModels.forEach(m => { statuses[m] = "error"; });
      setRunStatuses({ ...statuses });
    }
    setRunning(false);
  };

  const saveRun = async () => {
    if (!results) return;
    setSavedRuns(prev => [{ run_id: `run_${Date.now()}`, prompt_preview: resolvedInput().slice(0, 80), models_tested: selModels.length, status: "completed", total_cost: results.total_cost || 0, fastest_model: results.fastest_model || "—", cheapest_model: results.cheapest_model || "—", created_at: new Date().toISOString() }, ...prev]);
  };

  const completed = results?.results?.filter(r => r.status === "completed") || [];
  const fastest = completed.length > 0 ? completed.reduce((a, b) => a.latency_ms < b.latency_ms ? a : b) : null;
  const cheapest = completed.length > 0 ? completed.reduce((a, b) => parseFloat(a.cost_usd) < parseFloat(b.cost_usd) ? a : b) : null;
  const bestValue = completed.length > 1 ? completed.reduce((a, b) => {
    const scoreA = (1 / (a.latency_ms || 999)) / (parseFloat(a.cost_usd) || 0.001);
    const scoreB = (1 / (b.latency_ms || 999)) / (parseFloat(b.cost_usd) || 0.001);
    return scoreA > scoreB ? a : b;
  }) : null;
  const scoredResults = completed.filter(r => r.quality_scores?.aggregate_score != null);
  const bestQuality = scoredResults.length > 0 ? scoredResults.reduce((a, b) => (a.quality_scores?.aggregate_score || 0) > (b.quality_scores?.aggregate_score || 0) ? a : b) : null;
  const hasScoring = scoredResults.length > 0;

  const AVAILABLE_METRICS = [
    { id: "rouge_l", label: "ROUGE-L", desc: "How much of the key phrasing from your reference appears in the output, in the right order" },
    { id: "bleu", label: "BLEU", desc: "How closely the wording matches your reference, phrase by phrase" },
    { id: "contains", label: "Contains", desc: "Checks whether the output includes specific text from your reference" },
    { id: "exact_match", label: "Exact Match", desc: "Pass/fail — does the output match the reference word-for-word?" },
    { id: "levenshtein", label: "Levenshtein", desc: "How many character edits would be needed to turn the output into the reference" },
    { id: "semantic_similarity", label: "Word Overlap", desc: "How many of the same words appear in both the output and reference" },
  ];
  const METRIC_LABEL_MAP = Object.fromEntries(AVAILABLE_METRICS.map(m => [m.id, m.label]));

  const QualityBar = ({ score, size = "sm" }) => {
    const pct = Math.round((score || 0) * 100);
    const color = pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-500" : "bg-red-500";
    const textColor = pct >= 80 ? "text-emerald-600" : pct >= 60 ? "text-amber-600" : "text-red-600";
    return (
      <div className="flex items-center gap-1.5">
        <div className={cn("flex-1 rounded-full overflow-hidden", size === "sm" ? "h-1.5 bg-slate-100" : "h-2 bg-slate-100")}>
          <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
        </div>
        <span className={cn("font-bold", textColor, size === "sm" ? "text-[11px] w-8" : "text-xs w-10")}>{pct}%</span>
      </div>
    );
  };

  const varNames = Object.keys(variables);
  const hasVars = varNames.length > 0;

  const statusIcon = (status) => {
    if (status === "queued") return <Clock size={12} className="text-slate-400 animate-pulse" />;
    if (status === "running") return <RefreshCw size={12} className="text-amber-500 animate-spin" />;
    if (status === "success") return <Check size={12} className="text-emerald-600" />;
    return <AlertCircle size={12} className="text-red-500" />;
  };

  return (
    <div className="p-6 animate-fade-up max-w-[1400px] mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Eval Studio</h1>
          <p className="text-sm text-slate-500 mt-0.5">Side-by-side LLM benchmarking — find the right model for every task</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowHistory(!showHistory)} className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 cursor-pointer bg-white transition">
            <History size={12} /> History ({savedRuns.length})
          </button>
        </div>
      </div>

      {/* History panel */}
      {showHistory && savedRuns.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">Recent Eval Runs</h3>
          <div className="divide-y divide-slate-100">
            {savedRuns.slice(0, 5).map((r, i) => (
              <div key={i} className="flex items-center gap-4 py-2 text-xs">
                <span className="text-slate-400 w-28" title={new Date(r.created_at).toLocaleString()}>{relativeTime(r.created_at)}</span>
                <span className="text-slate-700 flex-1 truncate">{r.prompt_preview}</span>
                <span className="text-slate-500">{r.models_tested} models</span>
                <span className="text-emerald-600 font-medium">${r.total_cost?.toFixed(4)}</span>
                <span className="text-sky-600">{r.fastest_model}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left Column: Config */}
        <div className="lg:col-span-1 space-y-4">
          {/* Model Selector */}
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold text-slate-500 uppercase">Models (max 4)</h3>
              <span className="text-[11px] text-slate-400">{selModels.length}/4 selected</span>
            </div>
            <div className="space-y-1.5">
              {availableModels.map(m => {
                const selected = selModels.includes(m.id);
                const disabled = !selected && selModels.length >= 4;
                const providerColor = PROVIDER_COLORS[m.provider] || "bg-slate-50 text-slate-600 border-slate-200";
                return (
                  <div key={m.id}
                    onClick={() => !disabled && toggle(m.id)}
                    className={cn("flex items-center gap-2.5 p-2 rounded-lg border cursor-pointer transition",
                      selected ? "border-[#F2B3C6] bg-[#FDF1F5]" : disabled ? "border-slate-100 bg-slate-50 opacity-40 cursor-not-allowed" : "border-slate-200 bg-white hover:border-slate-300")}>
                    <div className={cn("w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition",
                      selected ? "bg-jai-primary border-jai-primary" : "border-slate-300")}>
                      {selected && <Check size={10} className="text-white" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-slate-900">{m.label}</div>
                      <div className="text-[11px] text-slate-400">${m.input}/M in · ${m.output}/M out</div>
                    </div>
                    <span className={cn("text-[11px] px-1.5 py-0.5 rounded-full border font-medium", providerColor)}>{PROVIDER_LABELS[m.provider] || m.provider}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Global Settings */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase">Settings</h3>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] text-slate-500">Temperature</label>
                <span className="text-[11px] font-mono text-slate-700 font-bold">{temperature}</span>
              </div>
              <input type="range" min="0" max="1" step="0.05" value={temperature} onChange={e => setTemperature(parseFloat(e.target.value))} className="w-full accent-jai-primary" />
              <div className="flex justify-between text-[11px] text-slate-400"><span>Precise</span><span>Creative</span></div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] text-slate-500">Max Tokens</label>
                <span className="text-[11px] font-mono text-slate-700 font-bold">{maxTokens}</span>
              </div>
              <input type="range" min="256" max="16384" step="256" value={maxTokens} onChange={e => setMaxTokens(parseInt(e.target.value))} className="w-full accent-jai-primary" />
              <div className="flex justify-between text-[11px] text-slate-400"><span>256</span><span>16K</span></div>
            </div>
          </div>

          {/* Quality Scoring Config */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-1.5">
              <Target size={12} className="text-jai-primary" />
              <h3 className="text-xs font-semibold text-slate-500 uppercase">Quality Scoring</h3>
            </div>
            <div>
              <label className="text-[11px] text-slate-500 block mb-1">Reference / Expected Answer</label>
              <textarea value={referenceText} onChange={e => setReferenceText(e.target.value)}
                placeholder="Paste the expected or ideal response to compare against..."
                className="w-full border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-mono outline-none resize-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200"
                style={{ minHeight: "56px" }} />
              <div className="text-[11px] text-slate-400 mt-0.5">Enables BLEU, ROUGE-L, and other reference-based metrics</div>
            </div>
            {referenceText.trim() && (
              <div>
                <label className="text-[11px] text-slate-500 block mb-1.5">Scoring Metrics</label>
                <div className="space-y-1">
                  {AVAILABLE_METRICS.map(m => {
                    const active = scoringMetrics.includes(m.id);
                    return (
                      <button key={m.id}
                        onClick={() => setScoringMetrics(prev => active ? prev.filter(x => x !== m.id) : [...prev, m.id])}
                        className={cn("w-full text-left px-2.5 py-1.5 rounded-lg border cursor-pointer transition",
                          active ? "bg-[#FDF1F5] border-[#F2B3C6]" : "bg-white border-slate-200 hover:border-slate-300")}>
                        <div className="flex items-center gap-2">
                          <div className={cn("w-3.5 h-3.5 rounded border-2 flex items-center justify-center flex-shrink-0 transition",
                            active ? "bg-jai-primary border-jai-primary" : "border-slate-300")}>
                            {active && <Check size={8} className="text-white" />}
                          </div>
                          <span className={cn("text-[11px] font-semibold", active ? "text-jai-primary" : "text-slate-600")}>{m.label}</span>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5 pl-[22px] leading-snug">{m.desc}</div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            <div className="border-t border-slate-100 pt-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Brain size={11} className="text-violet-500" />
                  <span className="text-[11px] font-medium text-slate-700">LLM-as-Judge</span>
                </div>
                <button onClick={() => setLlmJudgeEnabled(!llmJudgeEnabled)}
                  className={cn("w-8 h-4.5 rounded-full transition cursor-pointer relative",
                    llmJudgeEnabled ? "bg-jai-primary" : "bg-slate-200")}>
                  <div className={cn("absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white shadow transition",
                    llmJudgeEnabled ? "left-4" : "left-0.5")} />
                </button>
              </div>
              <div className="text-[11px] text-slate-400 mt-1">Uses an LLM to evaluate relevance, coherence, helpfulness, accuracy, and safety</div>
              {llmJudgeEnabled && (
                <div className="mt-2">
                  <label className="text-[11px] text-slate-500 block mb-1">Judge Model</label>
                  <select value={judgeModel} onChange={e => setJudgeModel(e.target.value)}
                    className="w-full border border-slate-200 rounded-lg px-2 py-1 text-xs outline-none focus:border-slate-300">
                    {models.map(m => <option key={m.model_id} value={m.model_id}>{m.display_name || m.model_id}</option>)}
                    {models.length === 0 && <option value="">No models available</option>}
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Variables sidebar */}
          {hasVars && (
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">Variables</h3>
              <p className="text-[11px] text-slate-400 mb-3">Auto-detected from {"{{"}...{"}}"} in your user input</p>
              <div className="space-y-2">
                {varNames.map(v => (
                  <div key={v}>
                    <label className="text-[11px] font-mono text-slate-500 block mb-0.5">{`{{${v}}}`}</label>
                    <input value={variables[v] || ""} onChange={e => setVariables(prev => ({ ...prev, [v]: e.target.value }))}
                      placeholder={`Value for ${v}...`}
                      className="w-full border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Prompt + Results */}
        <div className="lg:col-span-2 space-y-4">
          {/* Prompt Editor */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-500 uppercase">System Prompt</h3>
              <span className="text-[11px] text-slate-400">{(systemPrompt || "").length} chars</span>
            </div>
            <textarea value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)}
              placeholder="You are a helpful AI assistant specialized in..."
              className="w-full px-4 py-3 text-sm font-mono text-slate-900 outline-none resize-none border-none"
              style={{ minHeight: "100px" }} />
            <div className="px-4 py-3 border-t border-slate-100">
              <div className="flex items-center justify-between mb-1.5">
                <h3 className="text-xs font-semibold text-slate-500 uppercase">User Input</h3>
                {hasVars && <span className="text-[11px] text-violet-500">{varNames.length} variable{varNames.length !== 1 ? "s" : ""} detected</span>}
              </div>
              <textarea value={userInput} onChange={e => setUserInput(e.target.value)}
                placeholder="Enter your test message... Use {{variable_name}} for dynamic placeholders"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono text-slate-900 outline-none resize-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200"
                style={{ minHeight: "60px" }} />
              {hasVars && (
                <div className="mt-2 bg-slate-50 border border-slate-100 rounded-lg px-3 py-2">
                  <div className="text-[11px] text-slate-400 mb-1">Resolved preview:</div>
                  <div className="text-xs text-slate-700 font-mono">{resolvedInput()}</div>
                </div>
              )}
            </div>
          </div>

          {/* Run button */}
          <div className="flex items-center gap-3">
            <button onClick={run} disabled={running || !selModels.length}
              className={cn("flex items-center gap-2 bg-jai-primary text-white rounded-lg px-5 py-2.5 text-sm font-semibold cursor-pointer shadow-sm hover:bg-jai-primary-hover transition",
                (running || !selModels.length) && "opacity-50 cursor-not-allowed")}>
              <Play size={14} /> {running ? "Running Battle..." : `Run Battle (${selModels.length} model${selModels.length !== 1 ? "s" : ""})`}
            </button>
            {results?.results && (
              <>
                <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg p-0.5">
                  <button onClick={() => setViewMode("battle")} className={cn("px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition", viewMode === "battle" ? "bg-slate-100 text-slate-900" : "text-slate-400 hover:text-slate-600")}>Battle Grid</button>
                  <button onClick={() => setViewMode("table")} className={cn("px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition", viewMode === "table" ? "bg-slate-100 text-slate-900" : "text-slate-400 hover:text-slate-600")}>Comparison</button>
                </div>
                <button onClick={saveRun} className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 cursor-pointer bg-white ml-auto">
                  <Save size={12} /> Save Run
                </button>
              </>
            )}
          </div>

          {/* BATTLE GRID VIEW — show all selected models, with loading state for pending ones */}
          {(results?.results || running) && viewMode === "battle" && (
            <div className={cn("grid gap-4", selModels.length === 1 ? "grid-cols-1" : selModels.length === 2 ? "grid-cols-2" : selModels.length === 3 ? "grid-cols-3" : "grid-cols-2")}>
              {selModels.map((modelId, i) => {
                const r = (results?.results || []).find(x => x.model_id === modelId);
                const status = runStatuses[modelId] || "running";

                // Model still running — show loading card
                if (!r) {
                  const am = availableModels.find(x => x.id === modelId);
                  return (
                    <div key={modelId} className="bg-white border border-slate-200 rounded-xl overflow-hidden animate-pulse">
                      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
                        <RefreshCw size={12} className="text-amber-500 animate-spin" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-slate-900 truncate">{am?.label || modelId}</div>
                          <div className="text-[11px] text-slate-400">{PROVIDER_LABELS[am?.provider] || am?.provider || ""}</div>
                        </div>
                      </div>
                      <div className="px-4 py-8 flex flex-col items-center gap-2">
                        <Loader2 size={24} className="text-jai-primary animate-spin" />
                        <div className="text-xs text-slate-400">Running evaluation...</div>
                      </div>
                    </div>
                  );
                }

                const isFastest = fastest && r.model_name === fastest.model_name;
                const isCheapest = cheapest && r.model_name === cheapest.model_name;
                const isBestVal = bestValue && r.model_name === bestValue.model_name && completed.length > 1;
                return (
                  <div key={i} className={cn("bg-white border rounded-xl overflow-hidden transition",
                    r.status === "completed" ? "border-slate-200" : "border-red-200")}>
                    {/* Card header */}
                    <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
                      {statusIcon(status)}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-slate-900 truncate">{r.model_name}</div>
                        <div className="text-[11px] text-slate-400">{PROVIDER_LABELS[r.provider] || r.provider || ""}</div>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        {isFastest && <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-sky-100 text-sky-700 font-bold">⚡ Top Speed</span>}
                        {isCheapest && <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-bold">💰 Cheapest</span>}
                        {isBestVal && !isFastest && !isCheapest && <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-bold">⭐ Best Value</span>}
                      </div>
                    </div>
                    {/* Metrics */}
                    {r.status === "completed" ? (
                      <>
                        <div className="px-4 py-2.5 grid grid-cols-3 gap-2 bg-slate-50 border-b border-slate-100">
                          <div className="text-center">
                            <div className={cn("text-sm font-bold", isFastest ? "text-sky-600" : "text-slate-800")}>{(r.latency_ms / 1000).toFixed(1)}s</div>
                            <div className="text-[11px] text-slate-400">Latency</div>
                          </div>
                          <div className="text-center">
                            <div className="text-sm font-bold text-slate-800">{(r.input_tokens || 0) + (r.output_tokens || 0)}</div>
                            <div className="text-[11px] text-slate-400">{r.input_tokens}↑ {r.output_tokens}↓</div>
                          </div>
                          <div className="text-center">
                            <div className={cn("text-sm font-bold", isCheapest ? "text-emerald-600" : "text-slate-800")}>${r.cost_usd}</div>
                            <div className="text-[11px] text-slate-400">Cost</div>
                          </div>
                        </div>
                        {/* Quality Scores */}
                        {r.quality_scores && !r.quality_scores.error && (
                          <div className="px-4 py-2.5 border-b border-slate-100 bg-violet-50/50">
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="text-[11px] font-semibold text-violet-500 uppercase">Quality Score</span>
                              {bestQuality && r.model_name === bestQuality.model_name && (
                                <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-violet-100 text-violet-700 font-bold">&#x1f3c6; Best Quality</span>
                              )}
                            </div>
                            <QualityBar score={r.quality_scores.aggregate_score} size="md" />
                            {r.quality_scores.reference_scores?.length > 0 && (
                              <div className="mt-1.5 space-y-0.5">
                                {r.quality_scores.reference_scores.map((s, si) => (
                                  <div key={si} className="flex items-center gap-2">
                                    <span className="text-[11px] text-slate-500 w-20 truncate">{METRIC_LABEL_MAP[s.metric] || s.metric}</span>
                                    <QualityBar score={s.score} />
                                  </div>
                                ))}
                              </div>
                            )}
                            {r.quality_scores.judge && (
                              <div className="mt-2 pt-1.5 border-t border-violet-100">
                                <div className="flex items-center gap-1 mb-1">
                                  <Brain size={10} className="text-violet-500" />
                                  <span className="text-[11px] font-semibold text-violet-600">LLM Judge ({r.quality_scores.judge.model})</span>
                                </div>
                                <QualityBar score={r.quality_scores.judge.overall_score} size="md" />
                                {r.quality_scores.judge.criteria_scores?.map((cs, ci) => (
                                  <div key={ci} className="flex items-center gap-2 mt-0.5">
                                    <span className="text-[11px] text-slate-500 w-20 truncate capitalize">{cs.criterion}</span>
                                    <QualityBar score={cs.normalized_score || cs.score / 5} />
                                  </div>
                                ))}
                                {r.quality_scores.judge.reasoning && (
                                  <div className="text-[11px] text-slate-500 italic mt-1">{r.quality_scores.judge.reasoning}</div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                        {/* Output */}
                        <div className="px-4 py-3">
                          <div className="text-xs text-slate-700 font-mono leading-relaxed whitespace-pre-wrap max-h-[400px] overflow-y-auto scrollbar-thin">
                            {r.response_preview || "No output"}
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="px-4 py-6 text-center">
                        <AlertCircle size={20} className="mx-auto text-red-400 mb-1.5" />
                        <div className="text-xs text-red-500">{r.error || "Model evaluation failed"}</div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* COMPARISON TABLE VIEW */}
          {results?.results && viewMode === "table" && (
            <div className="bg-white border border-slate-200 rounded-xl overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-400 uppercase w-32">Metric</th>
                    {results.results.map((r, i) => (
                      <th key={i} className="text-left px-4 py-3">
                        <div className="text-xs font-semibold text-slate-900">{r.model_name}</div>
                        <div className="text-[11px] text-slate-400 font-normal">{PROVIDER_LABELS[r.provider] || r.provider || ""}</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr>
                    <td className="px-4 py-2.5 text-[11px] text-slate-500 font-semibold uppercase">Status</td>
                    {results.results.map((r, i) => (
                      <td key={i} className="px-4 py-2.5">
                        <Badge variant={r.status === "completed" ? "success" : "danger"}>{r.status}</Badge>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-4 py-2.5 text-[11px] text-slate-500 font-semibold uppercase">Latency</td>
                    {results.results.map((r, i) => (
                      <td key={i} className="px-4 py-2.5">
                        <span className={cn("text-sm font-bold", fastest && r.model_name === fastest.model_name ? "text-sky-600" : "text-slate-800")}>
                          {r.latency_ms ? `${(r.latency_ms / 1000).toFixed(2)}s` : "—"}
                        </span>
                        {fastest && r.model_name === fastest.model_name && <span className="ml-1.5 text-[11px] px-1.5 py-0.5 rounded-full bg-sky-100 text-sky-700 font-bold">⚡ Fastest</span>}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-4 py-2.5 text-[11px] text-slate-500 font-semibold uppercase">Input Tokens</td>
                    {results.results.map((r, i) => <td key={i} className="px-4 py-2.5 text-sm text-slate-800 font-mono">{r.input_tokens || "—"}</td>)}
                  </tr>
                  <tr>
                    <td className="px-4 py-2.5 text-[11px] text-slate-500 font-semibold uppercase">Output Tokens</td>
                    {results.results.map((r, i) => <td key={i} className="px-4 py-2.5 text-sm text-slate-800 font-mono">{r.output_tokens || "—"}</td>)}
                  </tr>
                  <tr>
                    <td className="px-4 py-2.5 text-[11px] text-slate-500 font-semibold uppercase">Cost</td>
                    {results.results.map((r, i) => (
                      <td key={i} className="px-4 py-2.5">
                        <span className={cn("text-sm font-bold", cheapest && r.model_name === cheapest.model_name ? "text-emerald-600" : "text-slate-800")}>
                          ${r.cost_usd || "—"}
                        </span>
                        {cheapest && r.model_name === cheapest.model_name && <span className="ml-1.5 text-[11px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-bold">💰 Cheapest</span>}
                      </td>
                    ))}
                  </tr>
                  {hasScoring && (
                    <tr className="bg-violet-50/50">
                      <td className="px-4 py-2.5 text-[11px] text-violet-500 font-semibold uppercase">Quality Score</td>
                      {results.results.map((r, i) => (
                        <td key={i} className="px-4 py-2.5">
                          {r.quality_scores?.aggregate_score != null ? (
                            <div>
                              <QualityBar score={r.quality_scores.aggregate_score} size="md" />
                              {bestQuality && r.model_name === bestQuality.model_name && (
                                <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-violet-100 text-violet-700 font-bold">&#x1f3c6; Best</span>
                              )}
                            </div>
                          ) : <span className="text-xs text-slate-400">—</span>}
                        </td>
                      ))}
                    </tr>
                  )}
                  {hasScoring && scoredResults[0]?.quality_scores?.reference_scores?.map((_, mi) => {
                    const metricName = scoredResults[0].quality_scores.reference_scores[mi]?.metric;
                    if (!metricName) return null;
                    return (
                      <tr key={`metric-${mi}`}>
                        <td className="px-4 py-2 text-[11px] text-slate-400 font-medium pl-8">{METRIC_LABEL_MAP[metricName] || metricName}</td>
                        {results.results.map((r, i) => {
                          const ms = r.quality_scores?.reference_scores?.[mi];
                          return (
                            <td key={i} className="px-4 py-2">
                              {ms ? <QualityBar score={ms.score} /> : <span className="text-xs text-slate-400">—</span>}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                  {hasScoring && scoredResults.some(r => r.quality_scores?.judge) && (
                    <tr className="bg-violet-50/30">
                      <td className="px-4 py-2.5 text-[11px] text-violet-500 font-semibold uppercase">
                        <div className="flex items-center gap-1"><Brain size={10} /> LLM Judge</div>
                      </td>
                      {results.results.map((r, i) => (
                        <td key={i} className="px-4 py-2.5">
                          {r.quality_scores?.judge ? (
                            <div>
                              <QualityBar score={r.quality_scores.judge.overall_score} size="md" />
                              <div className="text-[11px] text-slate-400 mt-0.5 italic line-clamp-2">{r.quality_scores.judge.reasoning}</div>
                            </div>
                          ) : <span className="text-xs text-slate-400">—</span>}
                        </td>
                      ))}
                    </tr>
                  )}
                  <tr>
                    <td className="px-4 py-2.5 text-[11px] text-slate-500 font-semibold uppercase align-top">Output</td>
                    {results.results.map((r, i) => (
                      <td key={i} className="px-4 py-2.5 text-xs text-slate-700 font-mono max-w-[320px]">
                        <div className="line-clamp-4 whitespace-pre-wrap leading-relaxed">{r.response_preview || r.error || "—"}</div>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Summary bar */}
          {results?.results && completed.length > 0 && (
            <div className="bg-gradient-to-r from-[#1B2A4A] to-[#2d3f5e] rounded-xl px-5 py-3 flex items-center gap-6 text-white">
              <div className="text-[11px] uppercase tracking-wider text-white/60 font-semibold">Battle Summary</div>
              <div className="flex-1 flex items-center gap-6 text-xs">
                {fastest && <div>⚡ <strong>Fastest:</strong> {fastest.model_name} ({(fastest.latency_ms / 1000).toFixed(1)}s)</div>}
                {cheapest && <div>💰 <strong>Cheapest:</strong> {cheapest.model_name} (${cheapest.cost_usd})</div>}
                {bestQuality && <div>&#x1f3c6; <strong>Best Quality:</strong> {bestQuality.model_name} ({Math.round((bestQuality.quality_scores?.aggregate_score || 0) * 100)}%)</div>}
                <div>📊 <strong>Models:</strong> {completed.length}/{selModels.length} completed</div>
                {results.total_cost !== undefined && <div>🏷️ <strong>Total Cost:</strong> ${results.total_cost.toFixed(4)}</div>}
              </div>
            </div>
          )}

          {/* Empty state */}
          {!results && !running && (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
              <Zap size={36} className="mx-auto text-slate-300 mb-3" />
              <div className="text-base font-medium text-slate-500 mb-1">Ready for Battle</div>
              <div className="text-sm text-slate-400 max-w-md mx-auto">Select models, configure your prompt, and hit "Run Battle" to see side-by-side performance, cost, and quality comparison.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
