"use client";
import { useState, useEffect } from "react";
import apiFetch from "../lib/apiFetch";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, FunnelChart, Funnel, LabelList, Cell,
} from "recharts";
import { cn } from "../lib/cn";
import {
  DollarSign, TrendingUp, Shield, Zap, Users, Clock, Info, RefreshCw,
  AlertTriangle, CheckCircle2, BarChart3, ArrowUpRight, Layers,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

const COLORS = { platform: "#DF4F77", navy: "#1B2A4A", teal: "#0EA5E9", emerald: "#059669", amber: "#F59E0B", analytics: "#CF825B", reporting: "#E44E50", admin: "#993555" };
const LOB_COLORS = { Procurement: "#DF4F77", Sourcing: "#CF825B", AP: "#059669", ESG: "#993555" };
const FUNNEL_COLORS = ["#DF4F77", "#CF825B", "#E44E50", "#059669", "#993555"];

function InfoTip({ text }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-flex">
      <Info size={13} className="text-slate-400 cursor-help ml-1" onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)} />
      {show && (
        <span className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-56 bg-slate-900 text-white text-[11px] leading-tight rounded-lg px-3 py-2 shadow-lg pointer-events-none">
          {text}
        </span>
      )}
    </span>
  );
}

function KpiCard({ label, value, sub, icon: Icon, color, bg, tooltip }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 relative overflow-hidden">
      <div className="flex items-start justify-between mb-3">
        <div>
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide flex items-center">
            {label}
            {tooltip && <InfoTip text={tooltip} />}
          </span>
        </div>
        <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center", bg)}>
          <Icon size={18} className={color} />
        </div>
      </div>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

const fmtUsd = (v) => v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${v.toFixed(0)}`;

export default function ExecutiveDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    apiFetch(`${API}/executive/dashboard`).then(r => r.json()).then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
  };
  useEffect(load, []);

  if (loading || !data) {
    return (
      <div className="p-6 max-w-[1400px] mx-auto space-y-5 animate-fade-up">
        <div className="flex items-center justify-between">
          <div className="space-y-2"><div className="animate-pulse rounded-lg bg-slate-100 h-5 w-40" /><div className="animate-pulse rounded-lg bg-slate-100 h-3 w-64" /></div>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 space-y-3"><div className="animate-pulse rounded-lg bg-slate-100 h-3 w-24" /><div className="animate-pulse rounded-lg bg-slate-100 h-7 w-16" /><div className="animate-pulse rounded-lg bg-slate-100 h-3 w-32" /></div>)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {[1,2].map(i => <div key={i} className="bg-white border border-slate-200 rounded-xl h-[340px]"><div className="px-5 py-3 border-b border-slate-100"><div className="animate-pulse rounded-lg bg-slate-100 h-4 w-40" /></div></div>)}
        </div>
      </div>
    );
  }

  const { kpis, roi_by_lob, hitl_latency, guardrail_violations, agent_lifecycle_funnel, cross_lob_tool_reuse } = data;
  const violationsLast14 = (guardrail_violations || []).slice(0, 14).reverse();
  const hasSpend = kpis.total_ai_spend > 0;
  const hasViolations = violationsLast14.some(d => d.pii_blocked > 0 || d.toxic_blocked > 0 || d.hallucination_flagged > 0);
  const isNewPlatform = kpis.total_active_agents === 0 && !hasSpend;

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6 animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">Platform performance, savings, and business impact</p>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 cursor-pointer bg-white transition">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* Onboarding Quick Actions — shown when platform is fresh */}
      {isNewPlatform && (
        <div className="bg-gradient-to-br from-jai-primary-light via-white to-sky-50 border border-jai-primary-border/50 rounded-2xl p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Welcome to JAI Agent OS</h2>
            <p className="text-sm text-slate-500 mt-0.5">Get started by setting up your first AI agent in 3 steps</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { step: "1", title: "Connect a Model", desc: "Add your Google, OpenAI, or Anthropic API key", icon: Layers, color: "bg-violet-50 text-violet-600" },
              { step: "2", title: "Create an Agent", desc: "Choose a template or build from scratch", icon: Zap, color: "bg-emerald-50 text-emerald-600" },
              { step: "3", title: "Test in Playground", desc: "Chat with your agent and iterate", icon: ArrowUpRight, color: "bg-sky-50 text-sky-600" },
            ].map(s => (
              <div key={s.step} className="bg-white border border-slate-200 rounded-xl p-4 flex items-start gap-3 hover:shadow-md hover:shadow-slate-200/50 hover:border-slate-300 transition-all duration-200 cursor-pointer group">
                <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center shrink-0", s.color)}>
                  <s.icon size={18} />
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-900 group-hover:text-jai-primary transition">{s.title}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{s.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KPI Ribbon */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="AI Spend vs. Savings"
          value={hasSpend ? fmtUsd(kpis.estimated_manual_savings) : "—"}
          sub={hasSpend ? `${fmtUsd(kpis.total_ai_spend)} spent → ${kpis.roi_multiplier}x ROI` : "No usage data yet"}
          icon={DollarSign} color="text-emerald-600" bg="bg-emerald-50"
          tooltip="Total estimated manual labor savings from AI agents vs. actual token costs. ROI = Savings ÷ AI Spend."
        />
        <KpiCard
          label="Avg Grounding Score"
          value={kpis.avg_grounding_score > 0 ? `${(kpis.avg_grounding_score * 100).toFixed(0)}%` : "—"}
          sub={kpis.avg_grounding_score > 0 ? (kpis.avg_grounding_score >= 0.85 ? "Healthy — within target" : "Below target (85%)") : "No evaluation data yet"}
          icon={Shield} color="text-jai-reporting" bg="bg-jai-reporting-light"
          tooltip="Average faithfulness/accuracy score across all agents. Measures how well agents stay grounded in source data vs. hallucinating. Target: ≥85%."
        />
        <KpiCard
          label="Active Agents"
          value={kpis.total_active_agents}
          sub={Object.keys(kpis.active_agents_by_lob || {}).length > 0 ? Object.entries(kpis.active_agents_by_lob).map(([k, v]) => `${k}: ${v}`).join(" · ") : "No agents deployed yet"}
          icon={Zap} color="text-violet-600" bg="bg-violet-50"
          tooltip="Count of deployed, production-ready agents across all Lines of Business."
        />
        <KpiCard
          label="Avg Time-to-Value"
          value={data.avg_time_to_value_days > 0 ? `${data.avg_time_to_value_days} days` : "—"}
          sub={data.avg_time_to_value_days > 0 ? "From creation to first production run" : "No production runs yet"}
          icon={Clock} color="text-sky-600" bg="bg-sky-50"
          tooltip="Average number of days from when an agent is created to when it completes its first production invocation."
        />
      </div>

      {/* 2x2 Chart Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Chart A: ROI by LoB */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 flex items-center">
                Token Cost vs. Savings
                <InfoTip text="Token cost vs. estimated manual labor savings per Line of Business. Identify which department achieves the highest return on AI investment." />
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">Token Cost vs. Savings per LoB</p>
            </div>
            <DollarSign size={16} className="text-slate-300" />
          </div>
          <div className="p-4" style={{ height: 280 }}>
            {(roi_by_lob || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={roi_by_lob} barGap={4}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="lob" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={v => fmtUsd(v)} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(v) => `$${v.toLocaleString()}`} contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="token_cost" name="Token Cost" fill={COLORS.navy} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="savings" name="Est. Savings" fill={COLORS.emerald} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-slate-400">No usage data by department yet</div>
            )}
          </div>
        </div>

        {/* Chart B: HITL Latency */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 flex items-center">
                Approval Wait Times
                <InfoTip text="Average time agent-generated tasks spend waiting for human approval. High latency indicates process bottlenecks that need attention." />
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">HITL Approval Latency by LoB</p>
            </div>
            <Clock size={16} className="text-slate-300" />
          </div>
          <div className="p-4" style={{ height: 280 }}>
            {(hitl_latency || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={hitl_latency} layout="vertical" barSize={18}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 10 }} unit="h" />
                  <YAxis type="category" dataKey="lob" tick={{ fontSize: 11 }} width={90} />
                  <Tooltip formatter={(v) => `${v} hours`} contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="avg_hours" name="Avg" fill={COLORS.teal} radius={[0, 4, 4, 0]} />
                  <Bar dataKey="p95_hours" name="P95" fill={COLORS.amber} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-slate-400">No human-in-the-loop data yet</div>
            )}
          </div>
        </div>

        {/* Chart C: Guardrail Violations */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 flex items-center">
                Trust & Safety
                <InfoTip text="Guardrail violations over the past 14 days. PII blocked, toxic output prevented, and hallucination flags raised by the platform." />
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">Guardrail Violations (14 days)</p>
            </div>
            <AlertTriangle size={16} className="text-slate-300" />
          </div>
          <div className="p-4" style={{ height: 280 }}>
            {hasViolations ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={violationsLast14}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 9 }} tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="pii_blocked" name="PII Blocked" stroke={COLORS.reporting} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="toxic_blocked" name="Toxic Blocked" stroke={COLORS.amber} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="hallucination_flagged" name="Hallucination" stroke={COLORS.admin} strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-sm text-slate-400 gap-1">
                <CheckCircle2 size={20} className="text-emerald-400" />
                <span>No guardrail violations recorded</span>
              </div>
            )}
          </div>
        </div>

        {/* Chart D: Agent Lifecycle Funnel */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 flex items-center">
                Platform Velocity
                <InfoTip text="Agent lifecycle funnel from Idea to Deployed. Shows how efficiently agents move through stages. Time-to-Value measures speed to production." />
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">Agent Lifecycle Funnel</p>
            </div>
            <TrendingUp size={16} className="text-slate-300" />
          </div>
          <div className="p-4" style={{ height: 280 }}>
            <div className="flex flex-col gap-2 h-full justify-center">
              {(agent_lifecycle_funnel || []).length === 0 || agent_lifecycle_funnel.every(s => s.count === 0) ? (
                <div className="flex items-center justify-center h-full text-sm text-slate-400">No agents created yet</div>
              ) : agent_lifecycle_funnel.map((step, i) => {
                const maxCount = Math.max(agent_lifecycle_funnel[0].count, 1);
                const pct = Math.round((step.count / maxCount) * 100);
                return (
                  <div key={step.stage} className="flex items-center gap-3">
                    <span className="text-xs font-medium text-slate-600 w-20 text-right">{step.stage}</span>
                    <div className="flex-1 h-8 bg-slate-50 rounded-lg overflow-hidden relative">
                      <div
                        className="h-full rounded-lg flex items-center justify-end pr-3 transition-all duration-500"
                        style={{ width: `${pct}%`, backgroundColor: FUNNEL_COLORS[i] }}
                      >
                        <span className="text-xs font-bold text-white">{step.count}</span>
                      </div>
                    </div>
                    <span className="text-[11px] text-slate-400 w-10">{pct}%</span>
                  </div>
                );
              })}
              {data.avg_time_to_value_days > 0 && (
                <div className="text-center mt-2">
                  <span className="text-xs text-slate-500">Avg Time-to-Value: </span>
                  <span className="text-xs font-bold text-jai-primary">{data.avg_time_to_value_days} days</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Cross-LoB Tool Reuse Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 flex items-center">
              Cross-LoB Tool Reuse
              <InfoTip text="Shared tools used by agents across multiple Lines of Business. High reuse proves platform value — building shared infrastructure, not silos." />
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">Proving platform value — shared tools across departments</p>
          </div>
          <Layers size={16} className="text-slate-300" />
        </div>
        {(cross_lob_tool_reuse || []).length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-400">No cross-team tool usage yet. Tools will appear here once agents start using shared tools.</div>
        ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left px-5 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">Tool</th>
              <th className="text-left px-5 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">Agents Using</th>
              <th className="text-left px-5 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">LoBs</th>
              <th className="text-left px-5 py-2.5 font-semibold text-slate-500 uppercase text-[11px]">Reuse Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cross_lob_tool_reuse.sort((a, b) => b.agents_using - a.agents_using).map(t => (
              <tr key={t.tool_id} className="hover:bg-slate-50">
                <td className="px-5 py-2.5 font-medium text-slate-800">{t.tool_name}</td>
                <td className="px-5 py-2.5 text-slate-600">
                  <span className="inline-flex items-center gap-1">
                    <Zap size={11} className="text-amber-500" />
                    {t.agents_using} agents
                  </span>
                </td>
                <td className="px-5 py-2.5">
                  <div className="flex gap-1 flex-wrap">
                    {t.lobs_using.map(l => (
                      <span key={l} className="text-[11px] px-1.5 py-0.5 rounded-full font-medium" style={{ backgroundColor: LOB_COLORS[l] + "18", color: LOB_COLORS[l] }}>
                        {l}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-5 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-jai-primary" style={{ width: `${Math.min(100, (t.agents_using / 18) * 100)}%` }} />
                    </div>
                    <span className="text-slate-500">{t.lobs_using.length}/4 LoBs</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        )}
      </div>
    </div>
  );
}
