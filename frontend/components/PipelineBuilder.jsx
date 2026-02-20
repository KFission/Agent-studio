"use client";
import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import apiFetch from "../lib/apiFetch";
import useEnvStore from "../stores/envStore";
import { EnvBadge } from "./EnvironmentSwitcher";
import { cn } from "../lib/cn";
import {
  Bot, ArrowRight, GitFork, Play, Save, Plus, X, ChevronRight, ChevronLeft,
  Search, Edit3, Trash2, Crown, Layers, Check, RefreshCw, AlertCircle,
  Clock, Zap, Copy, Settings, ArrowDown, ChevronDown, CheckCircle2,
  LayoutGrid, List, Filter, ArrowUpDown, MoreVertical, Braces, ExternalLink,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

// ═══════════════════════════════════════════════════════════════════
// PATTERN DEFINITIONS
// ═══════════════════════════════════════════════════════════════════

const PATTERNS = [
  {
    id: "sequential", label: "Sequential", icon: ArrowRight, color: "#10b981",
    tagline: "The Chain",
    desc: "Agent A → Agent B → Agent C. Output of one becomes context for the next.",
    diagram: "A → B → C",
    useCases: ["Multi-step reasoning", "Document processing pipelines", "Classification → extraction → summarization"],
  },
  {
    id: "parallel", label: "Parallel", icon: Layers, color: "#f59e0b",
    tagline: "The Broadcast",
    desc: "One prompt sent to multiple agents simultaneously. Results merged at the end.",
    diagram: "⇉ Fork & Merge",
    useCases: ["Multi-perspective analysis", "Ensemble voting", "Parallel specialist review"],
  },
  {
    id: "supervisor", label: "Supervisor", icon: Crown, color: "#8b5cf6",
    tagline: "The Brain",
    desc: "A manager agent decides which worker to call based on the query. Can loop.",
    diagram: "⊛ Hub & Spoke",
    useCases: ["Intent-based routing", "Complex multi-tool orchestration", "Adaptive agent selection"],
  },
];

// ═══════════════════════════════════════════════════════════════════
// SAMPLE PIPELINES (mock data until backend is wired)
// ═══════════════════════════════════════════════════════════════════

const SAMPLE_PIPELINES = [
  {
    pipeline_id: "pl-001", name: "Customer Support Triage", pattern: "sequential",
    description: "Classify tickets, extract entities, generate responses",
    steps: [
      { agent_id: "", agent_name: "Classifier", role: "Classify intent", order: 0 },
      { agent_id: "", agent_name: "Entity Extractor", role: "Extract key info", order: 1 },
      { agent_id: "", agent_name: "Response Writer", role: "Draft reply", order: 2 },
    ],
    config: {},
    runs_count: 47, last_run: "2025-02-11T09:30:00Z", status: "active",
    created_at: "2025-01-15T08:00:00Z",
  },
  {
    pipeline_id: "pl-002", name: "Contract Review Panel", pattern: "parallel",
    description: "Three specialist agents review a contract simultaneously",
    steps: [
      { agent_id: "", agent_name: "Legal Analyst", role: "Legal risk review", order: 0 },
      { agent_id: "", agent_name: "Financial Analyst", role: "Financial terms review", order: 1 },
      { agent_id: "", agent_name: "Compliance Checker", role: "Regulatory compliance", order: 2 },
    ],
    config: { mergeStrategy: "summary", summarizerAgent: "Summary Writer" },
    runs_count: 12, last_run: "2025-02-10T14:15:00Z", status: "active",
    created_at: "2025-01-20T10:00:00Z",
  },
  {
    pipeline_id: "pl-003", name: "Smart Help Desk", pattern: "supervisor",
    description: "Supervisor routes queries to the right specialist agent",
    steps: [
      { agent_id: "", agent_name: "Supervisor", role: "manager", order: 0 },
      { agent_id: "", agent_name: "Coder", role: "worker", order: 1 },
      { agent_id: "", agent_name: "Writer", role: "worker", order: 2 },
      { agent_id: "", agent_name: "Analyst", role: "worker", order: 3 },
    ],
    config: { orchestrationLogic: "Route based on intent:\n- Code questions → Coder\n- Writing tasks → Writer\n- Data analysis → Analyst" },
    runs_count: 83, last_run: "2025-02-11T12:00:00Z", status: "active",
    created_at: "2025-01-10T14:00:00Z",
  },
  {
    pipeline_id: "pl-004", name: "Document Enrichment Chain", pattern: "sequential",
    description: "Parse PDF, extract metadata, classify, and index into knowledge base",
    steps: [
      { agent_id: "", agent_name: "PDF Parser", role: "Extract raw text", order: 0 },
      { agent_id: "", agent_name: "Metadata Extractor", role: "Extract title, author, dates", order: 1 },
      { agent_id: "", agent_name: "Classifier", role: "Assign category & tags", order: 2 },
      { agent_id: "", agent_name: "Indexer", role: "Write to knowledge base", order: 3 },
    ],
    config: {},
    runs_count: 211, last_run: "2025-02-11T11:45:00Z", status: "active",
    created_at: "2024-12-05T09:00:00Z",
  },
  {
    pipeline_id: "pl-005", name: "Supplier Risk Assessment", pattern: "parallel",
    description: "Run financial, compliance, and ESG risk checks in parallel",
    steps: [
      { agent_id: "", agent_name: "Financial Risk Scorer", role: "Credit & financial health", order: 0 },
      { agent_id: "", agent_name: "Compliance Checker", role: "Sanctions & regulatory", order: 1 },
      { agent_id: "", agent_name: "ESG Analyst", role: "Environmental & social", order: 2 },
      { agent_id: "", agent_name: "Geo-Risk Evaluator", role: "Country & region risk", order: 3 },
    ],
    config: { mergeStrategy: "raw" },
    runs_count: 34, last_run: "2025-02-09T16:00:00Z", status: "active",
    created_at: "2025-01-25T11:00:00Z",
  },
  {
    pipeline_id: "pl-006", name: "RFP Auto-Responder", pattern: "supervisor",
    description: "Supervisor delegates RFP sections to domain-specialist agents",
    steps: [
      { agent_id: "", agent_name: "RFP Coordinator", role: "manager", order: 0 },
      { agent_id: "", agent_name: "Technical Writer", role: "worker", order: 1 },
      { agent_id: "", agent_name: "Pricing Analyst", role: "worker", order: 2 },
      { agent_id: "", agent_name: "Legal Drafter", role: "worker", order: 3 },
      { agent_id: "", agent_name: "Compliance Writer", role: "worker", order: 4 },
    ],
    config: { orchestrationLogic: "Analyze each RFP section:\n- Technical specs → Technical Writer\n- Pricing tables → Pricing Analyst\n- T&C / liability → Legal Drafter\n- Certifications → Compliance Writer" },
    runs_count: 8, last_run: "2025-02-08T10:30:00Z", status: "active",
    created_at: "2025-02-01T13:00:00Z",
  },
  {
    pipeline_id: "pl-007", name: "Invoice Reconciliation", pattern: "sequential",
    description: "Extract line items, match POs, flag discrepancies",
    steps: [
      { agent_id: "", agent_name: "Invoice Parser", role: "Extract line items", order: 0 },
      { agent_id: "", agent_name: "PO Matcher", role: "Match to purchase orders", order: 1 },
      { agent_id: "", agent_name: "Discrepancy Flagger", role: "Flag mismatches", order: 2 },
    ],
    config: {},
    runs_count: 0, last_run: null, status: "draft",
    created_at: "2025-02-11T08:00:00Z",
  },
  {
    pipeline_id: "pl-008", name: "Legacy Content Migrator (v1)", pattern: "sequential",
    description: "Old migration pipeline — superseded by v2",
    steps: [
      { agent_id: "", agent_name: "Scraper", role: "Pull legacy content", order: 0 },
      { agent_id: "", agent_name: "Reformatter", role: "Convert format", order: 1 },
    ],
    config: {},
    runs_count: 152, last_run: "2025-01-05T17:00:00Z", status: "inactive",
    created_at: "2024-11-01T12:00:00Z",
  },
];

// ═══════════════════════════════════════════════════════════════════
// SHARED SMALL COMPONENTS
// ═══════════════════════════════════════════════════════════════════

/** Safely coerce pipeline.steps to an array (API may return an integer count) */
function safeSteps(steps) { return Array.isArray(steps) ? steps : []; }

function Badge({ children, color }) {
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full border"
      style={{ background: color ? `${color}15` : undefined, color: color || "#64748b", borderColor: color ? `${color}40` : "#e2e8f0" }}>
      {children}
    </span>
  );
}

function StepConnector({ label }) {
  return (
    <div className="flex flex-col items-center py-1">
      <div className="w-px h-5 bg-slate-300" />
      {label && (
        <button className="text-[11px] text-blue-500 hover:text-blue-700 cursor-pointer -my-0.5">
          {label}
        </button>
      )}
      <div className="w-px h-5 bg-slate-300" />
      <ArrowDown size={10} className="text-slate-400 -mt-1" />
    </div>
  );
}

function AgentDropdown({ value, agents, onChange, placeholder = "Select agent..." }) {
  return (
    <select value={value || ""} onChange={e => onChange(e.target.value)}
      className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-400 transition cursor-pointer">
      <option value="">{placeholder}</option>
      {agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.name}</option>)}
    </select>
  );
}

// ═══════════════════════════════════════════════════════════════════
// PATTERN SELECTION (Create — Step 1)
// ═══════════════════════════════════════════════════════════════════

function PatternPicker({ onSelect, onBack }) {
  return (
    <div className="p-6 animate-fade-up max-w-4xl mx-auto">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900 cursor-pointer mb-6">
        <ChevronLeft size={16} /> Back to Pipelines
      </button>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-semibold text-slate-900">Choose an Orchestration Pattern</h1>
        <p className="text-sm text-slate-500 mt-2">Each pattern defines how your agents collaborate. Pick the one that fits your use case.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {PATTERNS.map(p => (
          <div key={p.id} onClick={() => onSelect(p.id)}
            className="bg-white border-2 border-slate-200 rounded-2xl p-6 cursor-pointer hover:border-slate-400 hover:shadow-lg transition group">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-sm" style={{ background: p.color }}>
                <p.icon size={20} />
              </div>
              <div>
                <div className="text-base font-semibold text-slate-900">{p.label}</div>
                <div className="text-xs text-slate-400 font-medium">{p.tagline}</div>
              </div>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed mb-4">{p.desc}</p>
            {/* Visual diagram placeholder */}
            <div className="bg-slate-50 border border-slate-100 rounded-xl p-4 mb-4 text-center">
              {p.id === "sequential" && (
                <div className="flex items-center justify-center gap-2 text-xs font-medium text-slate-500">
                  <span className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded">Input</span>
                  <ArrowRight size={12} className="text-slate-400" />
                  <span className="px-2 py-1 bg-white border border-slate-200 rounded">Agent A</span>
                  <ArrowRight size={12} className="text-slate-400" />
                  <span className="px-2 py-1 bg-white border border-slate-200 rounded">Agent B</span>
                  <ArrowRight size={12} className="text-slate-400" />
                  <span className="px-2 py-1 bg-red-100 text-red-700 rounded">Output</span>
                </div>
              )}
              {p.id === "parallel" && (
                <div className="flex flex-col items-center gap-1.5 text-xs font-medium text-slate-500">
                  <span className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded">Input</span>
                  <div className="flex items-center gap-3">
                    <div className="w-px h-3 bg-slate-300" />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-1 bg-white border border-slate-200 rounded">Agent A</span>
                    <span className="px-2 py-1 bg-white border border-slate-200 rounded">Agent B</span>
                    <span className="px-2 py-1 bg-white border border-slate-200 rounded">Agent C</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-px h-3 bg-slate-300" />
                  </div>
                  <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded">Merge</span>
                </div>
              )}
              {p.id === "supervisor" && (
                <div className="flex flex-col items-center gap-2 text-xs font-medium text-slate-500">
                  <span className="px-2.5 py-1.5 bg-violet-100 text-violet-700 rounded-lg font-semibold flex items-center gap-1"><Crown size={10} /> Manager</span>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-1 bg-white border border-slate-200 rounded text-[11px]">Worker 1</span>
                    <span className="px-2 py-1 bg-white border border-slate-200 rounded text-[11px]">Worker 2</span>
                    <span className="px-2 py-1 bg-white border border-slate-200 rounded text-[11px]">Worker 3</span>
                  </div>
                </div>
              )}
            </div>
            <div className="space-y-1">
              {p.useCases.map((uc, i) => (
                <div key={i} className="text-[11px] text-slate-400 flex items-start gap-1.5">
                  <Check size={10} className="text-emerald-500 mt-0.5 shrink-0" /> {uc}
                </div>
              ))}
            </div>
            <div className="mt-4 text-center">
              <span className="text-xs font-medium text-slate-400 group-hover:text-slate-600 transition">Click to select →</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// AGENT ASSIGNMENT — SEQUENTIAL
// ═══════════════════════════════════════════════════════════════════

function SequentialEditor({ pipeline, agents, onChange }) {
  const steps = safeSteps(pipeline.steps);
  const addStep = () => onChange({ ...pipeline, steps: [...steps, { agent_id: "", agent_name: "", role: "", order: steps.length }] });
  const removeStep = (i) => onChange({ ...pipeline, steps: steps.filter((_, j) => j !== i).map((s, j) => ({ ...s, order: j })) });
  const updateStep = (i, updates) => onChange({ ...pipeline, steps: steps.map((s, j) => j === i ? { ...s, ...updates } : s) });

  return (
    <div className="max-w-md mx-auto py-4">
      {/* Input node */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 text-center">
        <div className="text-xs font-semibold text-emerald-700 uppercase tracking-wide">Input</div>
        <div className="text-[11px] text-emerald-500 mt-0.5">Pipeline trigger</div>
      </div>

      {steps.map((step, i) => (
        <div key={i}>
          <StepConnector label="Configure mapping ↗" />
          <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 relative group">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center text-[11px] font-bold text-white">{i + 1}</div>
              <input value={step.role || ""} onChange={e => updateStep(i, { role: e.target.value })}
                placeholder={`Step ${i + 1} — describe role`}
                className="flex-1 text-xs text-slate-500 outline-none bg-transparent placeholder-slate-300" />
              {steps.length > 1 && (
                <button onClick={() => removeStep(i)} className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500 cursor-pointer transition"><X size={14} /></button>
              )}
            </div>
            <AgentDropdown value={step.agent_id} agents={agents} onChange={v => {
              const ag = agents.find(a => a.agent_id === v);
              updateStep(i, { agent_id: v, agent_name: ag?.name || "" });
            }} />
          </div>
        </div>
      ))}

      <StepConnector />

      {/* Output node */}
      <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-center">
        <div className="text-xs font-semibold text-red-700 uppercase tracking-wide">Output</div>
        <div className="text-[11px] text-red-400 mt-0.5">Final result</div>
      </div>

      <div className="mt-4 text-center">
        <button onClick={addStep} className="text-xs text-blue-600 hover:text-blue-800 cursor-pointer inline-flex items-center gap-1">
          <Plus size={12} /> Add Step
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// AGENT ASSIGNMENT — PARALLEL
// ═══════════════════════════════════════════════════════════════════

function ParallelEditor({ pipeline, agents, onChange }) {
  const steps = safeSteps(pipeline.steps);
  const config = pipeline.config || {};
  const addBranch = () => onChange({ ...pipeline, steps: [...steps, { agent_id: "", agent_name: "", role: `Branch ${steps.length + 1}`, order: steps.length }] });
  const removeBranch = (i) => onChange({ ...pipeline, steps: steps.filter((_, j) => j !== i) });
  const updateBranch = (i, updates) => onChange({ ...pipeline, steps: steps.map((s, j) => j === i ? { ...s, ...updates } : s) });
  const setConfig = (k, v) => onChange({ ...pipeline, config: { ...config, [k]: v } });

  return (
    <div className="max-w-2xl mx-auto py-4">
      {/* Input */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 text-center max-w-xs mx-auto">
        <div className="text-xs font-semibold text-emerald-700 uppercase tracking-wide">Input</div>
        <div className="text-[11px] text-emerald-500 mt-0.5">Broadcast to all agents</div>
      </div>

      <div className="flex justify-center py-2"><div className="w-px h-6 bg-slate-300" /></div>

      {/* Splitter */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-2 text-center max-w-xs mx-auto">
        <div className="text-xs font-semibold text-amber-700">Splitter</div>
      </div>

      <div className="flex justify-center py-1"><div className="w-px h-4 bg-slate-300" /></div>

      {/* Parallel branches */}
      <div className="flex gap-3 justify-center flex-wrap">
        {steps.map((step, i) => (
          <div key={i} className="bg-white border border-slate-200 rounded-xl px-4 py-3 w-48 relative group">
            <button onClick={() => removeBranch(i)}
              className={cn("absolute -top-2 -right-2 w-5 h-5 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-300 hover:text-red-500 hover:border-red-300 cursor-pointer transition", steps.length <= 2 && "hidden")}>
              <X size={10} />
            </button>
            <div className="flex items-center gap-2 mb-2">
              <Layers size={12} className="text-amber-500" />
              <input value={step.role || ""} onChange={e => updateBranch(i, { role: e.target.value })}
                placeholder={`Branch ${i + 1}`}
                className="flex-1 text-xs text-slate-500 outline-none bg-transparent font-medium" />
            </div>
            <AgentDropdown value={step.agent_id} agents={agents} onChange={v => {
              const ag = agents.find(a => a.agent_id === v);
              updateBranch(i, { agent_id: v, agent_name: ag?.name || "" });
            }} />
          </div>
        ))}
        <button onClick={addBranch}
          className="w-48 border-2 border-dashed border-slate-200 rounded-xl px-4 py-6 flex flex-col items-center justify-center text-slate-400 hover:text-slate-600 hover:border-slate-300 cursor-pointer transition">
          <Plus size={16} />
          <span className="text-xs mt-1">Add Branch</span>
        </button>
      </div>

      <div className="flex justify-center py-1"><div className="w-px h-4 bg-slate-300" /></div>

      {/* Merger */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 max-w-xs mx-auto">
        <div className="text-xs font-semibold text-amber-700 text-center mb-2">Merger</div>
        <div>
          <label className="text-[11px] text-slate-500 font-semibold uppercase">Merge Strategy</label>
          <select value={config.mergeStrategy || "raw"} onChange={e => setConfig("mergeStrategy", e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs outline-none mt-0.5 cursor-pointer">
            <option value="raw">Raw Merge — JSON object with all results</option>
            <option value="summary">Summary — Use a final agent to summarize</option>
          </select>
        </div>
        {config.mergeStrategy === "summary" && (
          <div className="mt-2">
            <label className="text-[11px] text-slate-500 font-semibold uppercase">Summarizer Agent</label>
            <AgentDropdown value={config.summarizerAgentId} agents={agents} onChange={v => setConfig("summarizerAgentId", v)} placeholder="Select summarizer..." />
          </div>
        )}
      </div>

      <div className="flex justify-center py-2"><div className="w-px h-6 bg-slate-300" /></div>

      {/* Output */}
      <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-center max-w-xs mx-auto">
        <div className="text-xs font-semibold text-red-700 uppercase tracking-wide">Output</div>
        <div className="text-[11px] text-red-400 mt-0.5">Merged result</div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// AGENT ASSIGNMENT — SUPERVISOR
// ═══════════════════════════════════════════════════════════════════

function SupervisorEditor({ pipeline, agents, onChange }) {
  const steps = safeSteps(pipeline.steps);
  const config = pipeline.config || {};
  const manager = steps.find(s => s.role === "manager") || steps[0] || {};
  const workers = steps.filter(s => s.role === "worker");
  const setConfig = (k, v) => onChange({ ...pipeline, config: { ...config, [k]: v } });

  const updateManager = (updates) => {
    const newSteps = steps.map(s => s.role === "manager" || s === steps[0] ? { ...s, ...updates, role: "manager", order: 0 } : s);
    onChange({ ...pipeline, steps: newSteps });
  };

  const addWorker = () => {
    const newWorker = { agent_id: "", agent_name: "", role: "worker", label: "", order: steps.length };
    onChange({ ...pipeline, steps: [...steps, newWorker] });
  };

  const removeWorker = (idx) => {
    const workerIdx = steps.findIndex((s, i) => s.role === "worker" && workers.indexOf(s) === idx);
    if (workerIdx >= 0) onChange({ ...pipeline, steps: steps.filter((_, i) => i !== workerIdx) });
  };

  const updateWorker = (idx, updates) => {
    let wCount = -1;
    const newSteps = steps.map(s => {
      if (s.role === "worker") {
        wCount++;
        if (wCount === idx) return { ...s, ...updates };
      }
      return s;
    });
    onChange({ ...pipeline, steps: newSteps });
  };

  return (
    <div className="max-w-2xl mx-auto py-4 space-y-6">
      {/* Manager card */}
      <div className="bg-violet-50 border-2 border-violet-300 rounded-2xl p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg bg-violet-500 flex items-center justify-center text-white shadow-sm">
            <Crown size={16} />
          </div>
          <div>
            <div className="text-sm font-semibold text-violet-900">Supervisor (Manager)</div>
            <div className="text-[11px] text-violet-500">Decides which worker to call based on the query</div>
          </div>
        </div>
        <div className="space-y-3">
          <AgentDropdown value={manager.agent_id} agents={agents} onChange={v => {
            const ag = agents.find(a => a.agent_id === v);
            updateManager({ agent_id: v, agent_name: ag?.name || "" });
          }} placeholder="Select manager agent..." />
          <div>
            <label className="text-[11px] text-slate-500 font-semibold uppercase">Orchestration Logic</label>
            <textarea value={config.orchestrationLogic || ""} onChange={e => setConfig("orchestrationLogic", e.target.value)}
              rows={4} placeholder="Define routing rules in plain text, e.g.:\n- Code questions → Coder\n- Writing tasks → Writer"
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none mt-0.5 resize-none" />
          </div>
        </div>
      </div>

      {/* Connection line */}
      <div className="flex justify-center"><div className="w-px h-6 bg-violet-300" /></div>

      {/* Worker pool */}
      <div>
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Worker Pool</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {workers.map((w, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl px-4 py-3 relative group">
              <button onClick={() => removeWorker(i)}
                className={cn("absolute -top-2 -right-2 w-5 h-5 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-300 hover:text-red-500 hover:border-red-300 cursor-pointer transition", workers.length <= 1 && "hidden")}>
                <X size={10} />
              </button>
              <div className="flex items-center gap-2 mb-2">
                <Bot size={12} className="text-slate-400" />
                <input value={w.label || w.agent_name || ""} onChange={e => updateWorker(i, { label: e.target.value })}
                  placeholder={`Worker ${i + 1} role label`}
                  className="flex-1 text-xs text-slate-500 outline-none bg-transparent font-medium" />
              </div>
              <AgentDropdown value={w.agent_id} agents={agents} onChange={v => {
                const ag = agents.find(a => a.agent_id === v);
                updateWorker(i, { agent_id: v, agent_name: ag?.name || "" });
              }} />
            </div>
          ))}
          <button onClick={addWorker}
            className="border-2 border-dashed border-slate-200 rounded-xl px-4 py-6 flex flex-col items-center justify-center text-slate-400 hover:text-slate-600 hover:border-slate-300 cursor-pointer transition">
            <Plus size={16} />
            <span className="text-xs mt-1">Add Worker</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// PIPELINE EDITOR (Create/Edit — Step 2)
// ═══════════════════════════════════════════════════════════════════

function PipelineEditor({ pattern, pipeline: initialPipeline, agents, onSave, onBack }) {
  const patternMeta = PATTERNS.find(p => p.id === pattern);
  const [pipeline, setPipeline] = useState(initialPipeline || {
    name: "",
    description: "",
    pattern,
    steps: pattern === "sequential" ? [{ agent_id: "", agent_name: "", role: "Step 1", order: 0 }]
      : pattern === "parallel" ? [{ agent_id: "", agent_name: "", role: "Branch 1", order: 0 }, { agent_id: "", agent_name: "", role: "Branch 2", order: 1 }]
      : [{ agent_id: "", agent_name: "", role: "manager", order: 0 }, { agent_id: "", agent_name: "", role: "worker", label: "", order: 1 }],
    config: pattern === "supervisor" ? { orchestrationLogic: "" } : pattern === "parallel" ? { mergeStrategy: "raw" } : {},
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!pipeline.name.trim()) return;
    setSaving(true);
    try {
      const payload = { ...pipeline, pattern };
      if (pipeline.pipeline_id) {
        await apiFetch(`${API}/orchestrator/pipelines/${pipeline.pipeline_id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      } else {
        await apiFetch(`${API}/orchestrator/pipelines`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      }
    } catch (err) { console.error("Save failed", err); }
    setSaving(false);
    onSave?.(pipeline);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="h-12 bg-white border-b border-slate-200 flex items-center px-4 gap-3 flex-shrink-0">
        <button onClick={onBack} className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer">
          <ChevronLeft size={14} /> Back
        </button>
        <div className="h-5 w-px bg-slate-200" />
        <div className="w-6 h-6 rounded-md flex items-center justify-center text-white" style={{ background: patternMeta?.color }}>
          {patternMeta && <patternMeta.icon size={12} />}
        </div>
        <span className="text-xs font-medium text-slate-500">{patternMeta?.label} Pipeline</span>
        <div className="flex-1" />
        <button onClick={handleSave} disabled={saving || !pipeline.name.trim()}
          className={cn("flex items-center gap-1.5 bg-jai-primary text-white rounded-lg px-4 py-1.5 text-xs font-medium cursor-pointer", (saving || !pipeline.name.trim()) && "opacity-50 cursor-not-allowed")}>
          <Save size={12} /> {saving ? "Saving..." : "Save Pipeline"}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto bg-slate-50">
        <div className="max-w-2xl mx-auto p-6 space-y-5">
          {/* Name & description */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
            <div>
              <label className="text-[11px] text-slate-500 font-semibold uppercase">Pipeline Name</label>
              <input value={pipeline.name} onChange={e => setPipeline({ ...pipeline, name: e.target.value })}
                placeholder="e.g. Customer Support Triage"
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm font-medium outline-none mt-0.5 focus:border-slate-400" />
            </div>
            <div>
              <label className="text-[11px] text-slate-500 font-semibold uppercase">Description</label>
              <textarea value={pipeline.description || ""} onChange={e => setPipeline({ ...pipeline, description: e.target.value })}
                placeholder="What does this pipeline do?" rows={2}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none mt-0.5 resize-none focus:border-slate-400" />
            </div>
          </div>

          {/* Pattern-specific editor */}
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Agent Assignment</div>
            <div className="text-[11px] text-slate-400 mb-4">
              {pattern === "sequential" && "Assign agents to each step in the chain. Output of each step becomes input for the next."}
              {pattern === "parallel" && "Assign agents to parallel branches. All receive the same input; results are merged."}
              {pattern === "supervisor" && "Assign a manager agent and worker agents. The manager routes queries to workers."}
            </div>
            {pattern === "sequential" && <SequentialEditor pipeline={pipeline} agents={agents} onChange={setPipeline} />}
            {pattern === "parallel" && <ParallelEditor pipeline={pipeline} agents={agents} onChange={setPipeline} />}
            {pattern === "supervisor" && <SupervisorEditor pipeline={pipeline} agents={agents} onChange={setPipeline} />}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// PIPELINE DETAIL / RUN VIEW
// ═══════════════════════════════════════════════════════════════════

function PipelineDetail({ pipeline, agents, onBack, onEdit }) {
  const patternMeta = PATTERNS.find(p => p.id === pipeline.pattern);
  const [tab, setTab] = useState("overview");
  const [runInput, setRunInput] = useState("");
  const [executing, setExecuting] = useState(false);
  const [execSteps, setExecSteps] = useState([]);
  const [execResult, setExecResult] = useState(null);

  const runPipeline = async () => {
    if (!runInput.trim() || executing) return;
    setExecuting(true);
    setExecSteps([]);
    setExecResult(null);

    const steps = safeSteps(pipeline.steps);
    const results = [];

    if (pipeline.pattern === "sequential") {
      for (let i = 0; i < steps.length; i++) {
        setExecSteps(prev => [...prev, { name: steps[i].agent_name || `Step ${i + 1}`, status: "running" }]);
        await new Promise(r => setTimeout(r, 600 + Math.random() * 800));
        const output = `[Mock] ${steps[i].agent_name || "Agent"} processed: "${runInput.slice(0, 40)}..."`;
        results.push({ step: i + 1, agent: steps[i].agent_name, output });
        setExecSteps(prev => prev.map((s, j) => j === i ? { ...s, status: "success", output } : s));
      }
    } else if (pipeline.pattern === "parallel") {
      // All branches start simultaneously
      const branchSteps = steps.map((s, i) => ({ name: s.agent_name || `Branch ${i + 1}`, status: "running" }));
      setExecSteps(branchSteps);
      await new Promise(r => setTimeout(r, 800 + Math.random() * 600));
      const completed = steps.map((s, i) => {
        const output = `[Mock] ${s.agent_name || "Agent"} analyzed: "${runInput.slice(0, 30)}..."`;
        results.push({ branch: i + 1, agent: s.agent_name, output });
        return { name: s.agent_name || `Branch ${i + 1}`, status: "success", output };
      });
      setExecSteps(completed);
      // Merger step
      await new Promise(r => setTimeout(r, 400));
      setExecSteps(prev => [...prev, { name: "Merger", status: "running" }]);
      await new Promise(r => setTimeout(r, 500));
      setExecSteps(prev => prev.map(s => s.name === "Merger" ? { ...s, status: "success", output: "All branches merged" } : s));
    } else if (pipeline.pattern === "supervisor") {
      const workers = steps.filter(s => s.role === "worker");
      // Manager decides
      setExecSteps([{ name: "Supervisor", status: "running" }]);
      await new Promise(r => setTimeout(r, 700));
      const chosen = workers[Math.floor(Math.random() * workers.length)];
      setExecSteps(prev => prev.map(s => s.name === "Supervisor" ? { ...s, status: "success", output: `Routing to ${chosen?.agent_name || "worker"}` } : s));
      // Worker executes
      await new Promise(r => setTimeout(r, 300));
      setExecSteps(prev => [...prev, { name: chosen?.agent_name || "Worker", status: "running" }]);
      await new Promise(r => setTimeout(r, 800));
      const wOutput = `[Mock] ${chosen?.agent_name || "Worker"} responded to: "${runInput.slice(0, 30)}..."`;
      results.push({ agent: chosen?.agent_name, output: wOutput });
      setExecSteps(prev => prev.map(s => s.status === "running" ? { ...s, status: "success", output: wOutput } : s));
      // Manager final
      await new Promise(r => setTimeout(r, 400));
      setExecSteps(prev => [...prev, { name: "Supervisor (final)", status: "running" }]);
      await new Promise(r => setTimeout(r, 500));
      setExecSteps(prev => prev.map(s => s.name === "Supervisor (final)" ? { ...s, status: "success", output: "Final answer compiled" } : s));
    }

    setExecResult({ status: "completed", steps: results.length, output: results });
    setExecuting(false);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4 flex-shrink-0">
        <button onClick={onBack} className="text-slate-400 hover:text-slate-900 cursor-pointer"><ChevronLeft size={18} /></button>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white" style={{ background: patternMeta?.color }}>
          {patternMeta && <patternMeta.icon size={16} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-base font-semibold text-slate-900">{pipeline.name}</div>
          <div className="text-xs text-slate-500 mt-0.5">{pipeline.description}</div>
        </div>
        <Badge color={patternMeta?.color}>{patternMeta?.label}</Badge>
        <button onClick={() => onEdit(pipeline)} className="flex items-center gap-1 text-xs text-slate-600 border border-slate-200 rounded-lg px-3 py-1.5 cursor-pointer hover:bg-slate-50">
          <Edit3 size={12} /> Edit
        </button>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-slate-200 px-6 flex gap-4">
        {["overview", "run", "history"].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={cn("py-2.5 text-xs font-medium border-b-2 cursor-pointer transition capitalize",
              tab === t ? "border-jai-primary text-slate-900" : "border-transparent text-slate-400 hover:text-slate-600")}>
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto bg-slate-50 p-6">
        {tab === "overview" && (
          <div className="max-w-2xl mx-auto space-y-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Pipeline Configuration</div>
              <div className="space-y-2">
                {safeSteps(pipeline.steps).map((s, i) => (
                  <div key={i} className="flex items-center gap-3 px-3 py-2 bg-slate-50 rounded-lg">
                    {pipeline.pattern === "supervisor" ? (
                      s.role === "manager"
                        ? <Crown size={14} className="text-violet-500 shrink-0" />
                        : <Bot size={14} className="text-slate-400 shrink-0" />
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center text-[11px] font-bold text-white shrink-0">{i + 1}</div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-800">{s.agent_name || "Unassigned"}</div>
                      <div className="text-[11px] text-slate-400">{s.role}</div>
                    </div>
                  </div>
                ))}
              </div>
              {pipeline.config?.orchestrationLogic && (
                <div className="mt-4">
                  <div className="text-[11px] text-slate-500 font-semibold uppercase mb-1">Orchestration Logic</div>
                  <pre className="text-xs text-slate-600 bg-slate-50 border border-slate-100 rounded-lg p-3 whitespace-pre-wrap">{pipeline.config.orchestrationLogic}</pre>
                </div>
              )}
              {pipeline.config?.mergeStrategy && (
                <div className="mt-4 text-xs text-slate-500">
                  <strong>Merge Strategy:</strong> {pipeline.config.mergeStrategy === "raw" ? "Raw JSON merge" : "Summary via agent"}
                </div>
              )}
            </div>
          </div>
        )}

        {tab === "run" && (
          <div className="max-w-2xl mx-auto space-y-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Run Pipeline</div>
              <textarea value={runInput} onChange={e => setRunInput(e.target.value)} rows={3}
                placeholder="Enter the input prompt for this pipeline..."
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none resize-none focus:border-slate-400" />
              <div className="mt-3 flex justify-end">
                <button onClick={runPipeline} disabled={executing || !runInput.trim()}
                  className={cn("flex items-center gap-1.5 bg-emerald-600 text-white rounded-lg px-4 py-2 text-xs font-medium cursor-pointer hover:bg-emerald-700 transition",
                    (executing || !runInput.trim()) && "opacity-50 cursor-not-allowed")}>
                  {executing ? <><RefreshCw size={12} className="animate-spin" /> Running...</> : <><Play size={12} /> Run Pipeline</>}
                </button>
              </div>
            </div>

            {/* Execution trace */}
            {execSteps.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Execution Trace</div>
                <div className="space-y-2">
                  {execSteps.map((s, i) => (
                    <div key={i} className={cn("rounded-lg border px-4 py-2.5 transition",
                      s.status === "success" ? "bg-emerald-50 border-emerald-200" :
                      s.status === "running" ? "bg-amber-50 border-amber-200 animate-pulse" :
                      "bg-slate-50 border-slate-200")}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {s.status === "success" ? <CheckCircle2 size={13} className="text-emerald-500" /> :
                           s.status === "running" ? <RefreshCw size={12} className="text-amber-500 animate-spin" /> :
                           <Clock size={12} className="text-slate-400" />}
                          <span className="text-sm font-medium text-slate-800">{s.name}</span>
                        </div>
                        <span className={cn("text-[11px] font-semibold uppercase",
                          s.status === "success" ? "text-emerald-600" : s.status === "running" ? "text-amber-600" : "text-slate-400"
                        )}>{s.status}</span>
                      </div>
                      {s.output && (
                        <div className="mt-1.5 text-xs text-slate-500 bg-white border border-slate-100 rounded px-2.5 py-1.5">{s.output}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Final result */}
            {execResult && (
              <div className="bg-white border border-emerald-200 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 size={14} className="text-emerald-500" />
                  <span className="text-sm font-semibold text-emerald-700">Pipeline Complete</span>
                  <span className="text-[11px] text-slate-400">{execResult.steps} steps executed</span>
                </div>
                <pre className="text-xs font-mono text-slate-600 bg-slate-50 border border-slate-100 rounded-lg p-3 max-h-48 overflow-auto whitespace-pre-wrap">
                  {JSON.stringify(execResult.output, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {tab === "history" && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white border border-slate-200 rounded-xl p-5 text-center text-sm text-slate-400 py-12">
              <Clock size={24} className="mx-auto text-slate-300 mb-2" />
              Run history will appear here after executing the pipeline.
              <br />
              <span className="text-[11px]">{pipeline.runs_count ? `${pipeline.runs_count} historical runs (mock data)` : "No runs yet"}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// PIPELINE LIST
// ═══════════════════════════════════════════════════════════════════

const STATUS_OPTIONS = [
  { id: "all", label: "All" },
  { id: "active", label: "Active", color: "#10b981" },
  { id: "draft", label: "Draft", color: "#f59e0b" },
  { id: "inactive", label: "Inactive", color: "#94a3b8" },
];

const SORT_OPTIONS = [
  { id: "name", label: "Name" },
  { id: "created", label: "Date created" },
  { id: "last_run", label: "Last run" },
  { id: "runs", label: "Most runs" },
];

function StatusBadge({ status }) {
  const s = STATUS_OPTIONS.find(o => o.id === status) || STATUS_OPTIONS[3];
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase px-1.5 py-0.5 rounded-md"
      style={{ background: `${s.color}18`, color: s.color }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.color }} />
      {s.label}
    </span>
  );
}

function formatRelativeDate(iso) {
  if (!iso) return "Never";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now - d;
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function plToast(msg, type = "success") {
  if (typeof window !== "undefined" && window.__jaiToast) { window.__jaiToast(msg, type); return; }
  console.log(`[${type}] ${msg}`);
}
function plConfirm({ title, message, confirmLabel = "Delete" }) {
  return new Promise(resolve => {
    if (typeof window !== "undefined" && window.__jaiConfirm) { window.__jaiConfirm({ title, message, confirmLabel, resolve }); return; }
    resolve(window.confirm(`${title}\n\n${message}`));
  });
}

function PipelineList({ pipelines, onSelect, onCreate, onDelete, onClone }) {
  const currentEnv = useEnvStore(s => s.currentEnv);
  const canEditEnv = useEnvStore(s => s.canEdit);
  const [search, setSearch] = useState("");
  const [patternFilter, setPatternFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("last_run");
  const [sortDir, setSortDir] = useState("desc");
  const [viewMode, setViewMode] = useState("list");
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [cloneTarget, setCloneTarget] = useState(null);
  const [cloneName, setCloneName] = useState("");
  const cloneRef = useRef(null);

  const openCloneDialog = (p) => { setCloneTarget(p); setCloneName(p.name + " (Copy)"); setTimeout(() => cloneRef.current?.select(), 50); };
  const doClone = async () => {
    if (!cloneTarget || !cloneName.trim()) return;
    try {
      await apiFetch(`${API}/orchestrator/pipelines`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: cloneName.trim(), description: cloneTarget.description || "", pattern: cloneTarget.pattern, steps: Array.isArray(cloneTarget.steps) ? cloneTarget.steps : [], tags: cloneTarget.tags || [] }),
      });
      plToast(`Cloned as "${cloneName.trim()}"`);
      setCloneTarget(null); onClone?.();
    } catch { plToast("Clone failed", "error"); }
  };
  const confirmDelete = async (p) => {
    const ok = await plConfirm({ title: "Delete Pipeline", message: `Permanently delete "${p.name}"? This will remove all run history. This cannot be undone.`, confirmLabel: "Delete Pipeline" });
    if (!ok) return;
    onDelete(p.pipeline_id);
    plToast(`Pipeline "${p.name}" deleted`);
  };
  const exportPipeline = (p) => {
    const blob = new Blob([JSON.stringify(p, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = `${p.name.replace(/\s+/g, "_").toLowerCase()}_pipeline.json`; a.click(); URL.revokeObjectURL(url);
    plToast("Pipeline exported");
  };

  const filtered = useMemo(() => {
    let result = pipelines.filter(p => {
      if (patternFilter !== "all" && p.pattern !== patternFilter) return false;
      if (statusFilter !== "all" && p.status !== statusFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        if (!p.name.toLowerCase().includes(q) && !(p.description || "").toLowerCase().includes(q)) return false;
      }
      return true;
    });
    result.sort((a, b) => {
      let cmp = 0;
      if (sortBy === "name") cmp = a.name.localeCompare(b.name);
      else if (sortBy === "created") cmp = (a.created_at || "").localeCompare(b.created_at || "");
      else if (sortBy === "last_run") cmp = (a.last_run || "").localeCompare(b.last_run || "");
      else if (sortBy === "runs") cmp = (a.runs_count || 0) - (b.runs_count || 0);
      return sortDir === "desc" ? -cmp : cmp;
    });
    return result;
  }, [pipelines, patternFilter, statusFilter, search, sortBy, sortDir]);

  const countByPattern = (id) => pipelines.filter(p => p.pattern === id).length;
  const countByStatus = (id) => pipelines.filter(p => p.status === id).length;
  const toggleSort = (id) => {
    if (sortBy === id) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortBy(id); setSortDir("desc"); }
    setShowSortMenu(false);
  };
  const activeFilters = (patternFilter !== "all" ? 1 : 0) + (statusFilter !== "all" ? 1 : 0);
  const clearFilters = () => { setPatternFilter("all"); setStatusFilter("all"); setSearch(""); };

  const PatternIcon = ({ pattern, size = 14 }) => {
    const pm = PATTERNS.find(pt => pt.id === pattern);
    if (!pm) return <GitFork size={size} />;
    const Icon = pm.icon;
    return <Icon size={size} />;
  };

  return (
    <div className="h-full flex flex-col">
      {/* Sticky header */}
      <div className="p-6 pb-0 max-w-6xl w-full mx-auto flex-shrink-0 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-xl font-semibold text-slate-900">Pipelines</h1>
              <p className="text-sm text-slate-500 mt-1">Compose agents into structured orchestration patterns</p>
            </div>
            <EnvBadge envId={currentEnv} size="md" />
          </div>
          {canEditEnv() && <button onClick={onCreate} className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover transition">
            <Plus size={14} /> Create Pipeline
          </button>}
        </div>

        {/* Pattern filter cards */}
        <div className="grid grid-cols-3 gap-3">
          {PATTERNS.map(p => (
            <div key={p.id} onClick={() => setPatternFilter(patternFilter === p.id ? "all" : p.id)}
              className={cn("bg-white border-2 rounded-xl p-3.5 cursor-pointer transition",
                patternFilter === p.id ? "shadow-sm" : "border-slate-200 hover:border-slate-300")}
              style={patternFilter === p.id ? { borderColor: p.color, background: `${p.color}08` } : {}}>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0" style={{ background: p.color }}>
                  <p.icon size={16} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-slate-900">{p.label}</div>
                  <div className="text-[11px] text-slate-400">{p.tagline}</div>
                </div>
                <span className="text-lg font-semibold text-slate-300">{countByPattern(p.id)}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Toolbar: search, status filter, sort, view toggle */}
        {pipelines.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search pipelines..."
                className="w-full bg-white border border-slate-200 rounded-lg py-2 pl-8 pr-3 text-sm outline-none focus:border-slate-400 transition" />
            </div>

            {/* Status filter pills */}
            <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg p-0.5">
              {STATUS_OPTIONS.map(s => (
                <button key={s.id} onClick={() => setStatusFilter(s.id)}
                  className={cn("px-2.5 py-1 text-[11px] font-medium rounded-md cursor-pointer transition",
                    statusFilter === s.id ? "bg-slate-100 text-slate-900" : "text-slate-400 hover:text-slate-600")}>
                  {s.id !== "all" && <span className="inline-block w-1.5 h-1.5 rounded-full mr-1" style={{ background: s.color }} />}
                  {s.label}
                  {s.id !== "all" && <span className="ml-1 text-slate-300">{countByStatus(s.id)}</span>}
                </button>
              ))}
            </div>

            {/* Sort dropdown */}
            <div className="relative">
              <button onClick={() => setShowSortMenu(!showSortMenu)}
                className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-lg px-2.5 py-[7px] text-[11px] text-slate-500 cursor-pointer hover:bg-slate-50 transition">
                <ArrowUpDown size={12} />
                {SORT_OPTIONS.find(s => s.id === sortBy)?.label}
                <span className="text-slate-300">{sortDir === "desc" ? "↓" : "↑"}</span>
              </button>
              {showSortMenu && (
                <div className="absolute right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-20 min-w-[140px]">
                  {SORT_OPTIONS.map(s => (
                    <button key={s.id} onClick={() => toggleSort(s.id)}
                      className={cn("w-full text-left px-3 py-1.5 text-xs cursor-pointer hover:bg-slate-50",
                        sortBy === s.id ? "text-slate-900 font-medium" : "text-slate-500")}>
                      {s.label} {sortBy === s.id && (sortDir === "desc" ? "↓" : "↑")}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* View mode toggle */}
            <div className="flex items-center gap-0 bg-white border border-slate-200 rounded-lg p-0.5">
              <button onClick={() => setViewMode("list")}
                className={cn("p-1.5 rounded-md cursor-pointer transition", viewMode === "list" ? "bg-slate-100 text-slate-700" : "text-slate-300 hover:text-slate-500")}>
                <List size={14} />
              </button>
              <button onClick={() => setViewMode("grid")}
                className={cn("p-1.5 rounded-md cursor-pointer transition", viewMode === "grid" ? "bg-slate-100 text-slate-700" : "text-slate-300 hover:text-slate-500")}>
                <LayoutGrid size={14} />
              </button>
            </div>

            {/* Results count + clear */}
            <div className="flex items-center gap-2 ml-auto">
              <span className="text-[11px] text-slate-400">{filtered.length} of {pipelines.length}</span>
              {activeFilters > 0 && (
                <button onClick={clearFilters} className="text-[11px] text-blue-500 hover:text-blue-700 cursor-pointer">
                  Clear filters
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Scrollable list body */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        <div className="max-w-6xl mx-auto">
          {pipelines.length === 0 ? (
            <div className="text-center py-16 border-2 border-dashed border-slate-200 rounded-xl mt-5">
              <GitFork size={40} className="mx-auto text-slate-300 mb-3" />
              <div className="text-base font-medium text-slate-500">No pipelines yet</div>
              <div className="text-sm text-slate-400 mt-1 mb-4">Create a pipeline to compose agents into structured execution patterns.</div>
              <button onClick={onCreate} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer">
                <Plus size={14} className="inline mr-1" /> Create Pipeline
              </button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12 mt-5">
              <Search size={24} className="mx-auto text-slate-300 mb-2" />
              <div className="text-sm text-slate-500">No pipelines match your filters</div>
              <button onClick={clearFilters} className="text-xs text-blue-500 hover:text-blue-700 cursor-pointer mt-2">Clear all filters</button>
            </div>
          ) : viewMode === "list" ? (
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 mt-5">
              {filtered.map(p => {
                const pm = PATTERNS.find(pt => pt.id === p.pattern);
                const Icon = pm?.icon || GitFork;
                return (
                  <div key={p.pipeline_id} onClick={() => onSelect(p)}
                    className="flex items-center gap-4 px-5 py-3.5 hover:bg-slate-50 transition cursor-pointer group">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0" style={{ background: pm?.color || "#94a3b8" }}>
                      <Icon size={14} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-900">{p.name}</div>
                      {p.description && <div className="text-[11px] text-slate-400 mt-0.5 truncate">{p.description}</div>}
                    </div>
                    <EnvBadge envId={currentEnv} size="xs" />
                    <Badge color={pm?.color}>{pm?.label || p.pattern}</Badge>
                    <StatusBadge status={p.status} />
                    <span className="text-[11px] text-slate-400 whitespace-nowrap">{safeSteps(p.steps).length} agents</span>
                    <span className="text-[11px] text-slate-400 whitespace-nowrap">{p.runs_count || 0} runs</span>
                    <span className="text-[11px] text-slate-400 whitespace-nowrap">{formatRelativeDate(p.last_run)}</span>
                    <button onClick={e => { e.stopPropagation(); openCloneDialog(p); }} className="text-slate-400 hover:text-slate-900 cursor-pointer opacity-0 group-hover:opacity-100 transition p-1" title="Clone"><Copy size={13} /></button>
                    <button onClick={e => { e.stopPropagation(); exportPipeline(p); }} className="text-slate-400 hover:text-slate-900 cursor-pointer opacity-0 group-hover:opacity-100 transition p-1" title="Export JSON"><Braces size={13} /></button>
                    {canEditEnv() && <button onClick={e => { e.stopPropagation(); confirmDelete(p); }}
                      className="text-slate-300 hover:text-red-500 cursor-pointer opacity-0 group-hover:opacity-100 transition p-1">
                      <Trash2 size={13} />
                    </button>}
                  </div>
                );
              })}
            </div>
          ) : (
            /* Grid view */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-5">
              {filtered.map(p => {
                const pm = PATTERNS.find(pt => pt.id === p.pattern);
                const Icon = pm?.icon || GitFork;
                return (
                  <div key={p.pipeline_id} onClick={() => onSelect(p)}
                    className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-md hover:border-slate-300 transition cursor-pointer group">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0" style={{ background: pm?.color || "#94a3b8" }}>
                        <Icon size={14} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-slate-900 truncate">{p.name}</div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <Badge color={pm?.color}>{pm?.label}</Badge>
                          <StatusBadge status={p.status} />
                        </div>
                      </div>
                      <button onClick={e => { e.stopPropagation(); openCloneDialog(p); }} className="text-slate-400 hover:text-slate-900 cursor-pointer opacity-0 group-hover:opacity-100 transition p-1 self-start" title="Clone"><Copy size={12} /></button>
                      {canEditEnv() && <button onClick={e => { e.stopPropagation(); confirmDelete(p); }}
                        className="text-slate-300 hover:text-red-500 cursor-pointer opacity-0 group-hover:opacity-100 transition p-1 self-start">
                        <Trash2 size={13} />
                      </button>}
                    </div>
                    {p.description && <div className="text-xs text-slate-400 leading-relaxed mb-3 line-clamp-2">{p.description}</div>}
                    <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                      <EnvBadge envId={currentEnv} size="xs" />
                      <span className="flex items-center gap-1"><Bot size={10} /> {safeSteps(p.steps).length} agents</span>
                      <span className="flex items-center gap-1"><Play size={10} /> {p.runs_count || 0} runs</span>
                      <button onClick={e => { e.stopPropagation(); exportPipeline(p); }} className="text-slate-400 hover:text-slate-600 cursor-pointer" title="Export"><Braces size={10} /></button>
                      <span className="ml-auto flex items-center gap-1"><Clock size={10} /> {formatRelativeDate(p.last_run)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Clone Pipeline Dialog */}
      {cloneTarget && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setCloneTarget(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6" onClick={e => e.stopPropagation()}>
            <h3 className="text-base font-semibold text-slate-900">Clone Pipeline</h3>
            <p className="text-sm text-slate-500 mt-1">Create a copy of <span className="font-medium text-slate-700">{cloneTarget.name}</span> with a new name.</p>
            <div className="mt-4">
              <label className="text-xs font-medium text-slate-500 block mb-1">New Pipeline Name</label>
              <input ref={cloneRef} value={cloneName} onChange={e => setCloneName(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") doClone(); if (e.key === "Escape") setCloneTarget(null); }}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 transition"
                placeholder="Enter a name for the cloned pipeline..." autoFocus />
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setCloneTarget(null)} className="px-4 py-2 text-sm font-medium text-slate-600 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50 transition">Cancel</button>
              <button onClick={doClone} disabled={!cloneName.trim()} className={cn("px-4 py-2 text-sm font-medium text-white bg-slate-800 rounded-lg cursor-pointer hover:bg-slate-900 transition", !cloneName.trim() && "opacity-50 cursor-not-allowed")}>
                <Copy size={13} className="inline mr-1.5 -mt-0.5" />Clone Pipeline
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// MAIN EXPORT: PipelinesPage
// ═══════════════════════════════════════════════════════════════════

export default function PipelinesPage() {
  const [screen, setScreen] = useState("list");         // list | select-pattern | build | detail
  const [selectedPattern, setSelectedPattern] = useState(null);
  const [editingPipeline, setEditingPipeline] = useState(null);
  const [viewingPipeline, setViewingPipeline] = useState(null);
  const [pipelines, setPipelines] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiFetch(`${API}/orchestrator/pipelines`).then(r => r.json()).catch(() => ({ pipelines: [] })),
      apiFetch(`${API}/agents`).then(r => r.json()).catch(() => ({ agents: [] })),
      apiFetch(`${API}/langgraph/assistants`).then(r => r.json()).catch(() => ({ assistants: [] })),
    ]).then(([pl, ag, lg]) => {
      const apiPipelines = (pl.pipelines || []).map(p => ({
        ...p,
        // API may return steps as an integer count — normalise to array
        steps: Array.isArray(p.steps) ? p.steps : [],
        config: (p.config && typeof p.config === "object") ? p.config : {},
        status: p.status || "active",
      }));
      // Merge: use sample data when API returns nothing usable
      setPipelines(apiPipelines.length > 0 ? apiPipelines : SAMPLE_PIPELINES);
      const localAgents = (ag.agents || []).map(a => ({ ...a, source: "local" }));
      const lgAgents = (lg.assistants || []).map(a => ({
        agent_id: a.assistant_id, assistant_id: a.assistant_id, name: a.name,
        description: a.description, model: a.model, status: "active", source: "langgraph",
      }));
      setAgents([...localAgents, ...lgAgents]);
      setLoading(false);
    });
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = () => setScreen("select-pattern");

  const handleSelectPattern = (patternId) => {
    setSelectedPattern(patternId);
    setEditingPipeline(null);
    setScreen("build");
  };

  const handleEdit = (pipeline) => {
    setSelectedPattern(pipeline.pattern);
    setEditingPipeline(pipeline);
    setScreen("build");
  };

  const handleSave = () => {
    setScreen("list");
    load();
  };

  const handleView = (pipeline) => {
    setViewingPipeline(pipeline);
    setScreen("detail");
  };

  const handleDelete = async (id) => {
    try { await apiFetch(`${API}/orchestrator/pipelines/${id}`, { method: "DELETE" }); } catch {}
    setPipelines(prev => prev.filter(p => p.pipeline_id !== id));
  };

  // Wrap everything in a height-constrained container so h-full works in child screens
  return (
    <div className="h-full flex flex-col overflow-hidden">
      {loading ? (
        <div className="p-6 text-slate-400 text-sm">Loading pipelines...</div>
      ) : screen === "select-pattern" ? (
        <div className="flex-1 overflow-y-auto">
          <PatternPicker onSelect={handleSelectPattern} onBack={() => setScreen("list")} />
        </div>
      ) : screen === "build" ? (
        <PipelineEditor
          pattern={selectedPattern}
          pipeline={editingPipeline}
          agents={agents}
          onSave={handleSave}
          onBack={() => setScreen(editingPipeline ? "detail" : "select-pattern")}
        />
      ) : screen === "detail" && viewingPipeline ? (
        <PipelineDetail
          pipeline={viewingPipeline}
          agents={agents}
          onBack={() => setScreen("list")}
          onEdit={handleEdit}
        />
      ) : (
        <PipelineList
          pipelines={pipelines}
          onSelect={handleView}
          onCreate={handleCreate}
          onDelete={handleDelete}
          onClone={load}
        />
      )}
    </div>
  );
}
