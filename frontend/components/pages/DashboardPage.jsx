"use client";
import { useState, useEffect } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, StatCard } from "../shared/StudioUI";
import {
  Bot, Workflow, Link2, ArrowRight, Activity, DollarSign, Check, Clock,
  Users as UsersIcon, Inbox as InboxIcon, TrendingUp, Gauge,
} from "lucide-react";

const CHART_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#f97316", "#ec4899"];

function DonutChart({ data, size = 120 }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;
  const cx = size / 2, cy = size / 2, r = size * 0.38, stroke = size * 0.15;
  let cumAngle = -90;
  const slices = data.map((d, i) => {
    const angle = (d.value / total) * 360;
    const startRad = (cumAngle * Math.PI) / 180;
    const endRad = ((cumAngle + angle) * Math.PI) / 180;
    const x1 = cx + r * Math.cos(startRad), y1 = cy + r * Math.sin(startRad);
    const x2 = cx + r * Math.cos(endRad), y2 = cy + r * Math.sin(endRad);
    const largeArc = angle > 180 ? 1 : 0;
    cumAngle += angle;
    return { path: `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`, color: CHART_COLORS[i % CHART_COLORS.length], label: d.label, value: d.value, pct: ((d.value / total) * 100).toFixed(1) };
  });
  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {slices.map((s, i) => <path key={i} d={s.path} fill="none" stroke={s.color} strokeWidth={stroke} strokeLinecap="round" />)}
        <text x={cx} y={cy - 4} textAnchor="middle" className="fill-slate-900 text-[11px] font-semibold">${total.toFixed(2)}</text>
        <text x={cx} y={cy + 10} textAnchor="middle" className="fill-slate-400 text-[8px]">total</text>
      </svg>
      <div className="space-y-1">
        {slices.slice(0, 6).map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: s.color }} />
            <span className="text-slate-700 truncate max-w-[100px]">{s.label || "\u2014"}</span>
            <span className="text-slate-400 ml-auto">{s.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AreaChart({ data, width = 500, height = 100 }) {
  if (!data.length) return null;
  const maxVal = Math.max(...data.map(d => d.value), 0.0001);
  const padding = { top: 8, right: 8, bottom: 20, left: 8 };
  const w = width - padding.left - padding.right;
  const h = height - padding.top - padding.bottom;
  const points = data.map((d, i) => ({
    x: padding.left + (i / Math.max(data.length - 1, 1)) * w,
    y: padding.top + h - (d.value / maxVal) * h,
    ...d,
  }));
  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const areaPath = linePath + ` L ${points[points.length - 1].x} ${padding.top + h} L ${points[0].x} ${padding.top + h} Z`;
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="overflow-visible">
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#6366f1" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#6366f1" stopOpacity="0.01" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#areaGrad)" />
      <path d={linePath} fill="none" stroke="#6366f1" strokeWidth="2" strokeLinejoin="round" />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="3" fill="#6366f1" className="opacity-0 hover:opacity-100 transition-opacity" />
          <title>{p.label}: ${p.value.toFixed(4)} \u00b7 {p.extra} req</title>
        </g>
      ))}
      {points.filter((_, i) => i % Math.max(Math.floor(data.length / 5), 1) === 0 || i === data.length - 1).map((p, i) => (
        <text key={i} x={p.x} y={padding.top + h + 14} textAnchor="middle" className="fill-slate-400 text-[8px]">{p.shortLabel}</text>
      ))}
    </svg>
  );
}

function MeteringWidget() {
  const [dimension, setDimension] = useState("lob");
  const [period, setPeriod] = useState(30);
  const [data, setData] = useState([]);
  const [summary, setSummary] = useState(null);
  const [trend, setTrend] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [fetched, setFetched] = useState(false);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      apiFetch(`${API}/metering/by-${dimension}?period_days=${period}`).then(r => r.json()).catch(() => ({ data: [] })),
      apiFetch(`${API}/metering/summary?period_days=${period}`).then(r => r.json()).catch(() => null),
      apiFetch(`${API}/metering/trend?period_days=${period}`).then(r => r.json()).catch(() => ({ trend: [] })),
    ]).then(([dimData, sumData, trendData]) => {
      setData(dimData.data || []);
      setSummary(sumData);
      setTrend(trendData.trend || []);
      setLoading(false);
      setFetched(true);
    });
  };

  useEffect(() => { if (expanded) fetchData(); }, [dimension, period, expanded]);

  const maxCost = Math.max(...data.map(d => d.total_cost_usd), 0.001);
  const donutData = data.slice(0, 8).map(d => ({ label: d.dimension_value || "\u2014", value: d.total_cost_usd }));
  const areaData = trend.map(t => ({ label: t.date, shortLabel: t.date.slice(5), value: t.cost_usd, extra: t.requests }));

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between flex-wrap gap-2 cursor-pointer select-none" onClick={() => setExpanded(e => !e)}>
        <div className="flex items-center gap-2">
          <Gauge size={16} className="text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-900">Cost & Usage Metering</h2>
          {!expanded && <span className="text-[11px] text-slate-400 ml-1">Click to expand</span>}
        </div>
        <div className="flex items-center gap-2">
          {expanded && (
            <>
              <select value={dimension} onChange={e => { e.stopPropagation(); setDimension(e.target.value); }} className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-xs outline-none">
                <option value="lob">By LoB</option><option value="group">By Group</option><option value="agent">By Agent</option><option value="model">By Model</option><option value="user">By User</option>
              </select>
              <select value={period} onChange={e => { e.stopPropagation(); setPeriod(Number(e.target.value)); }} className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-xs outline-none">
                <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option>
              </select>
            </>
          )}
          <TrendingUp size={14} className={cn("text-slate-400 transition-transform", expanded && "rotate-180")} />
        </div>
      </div>
      {expanded && summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-slate-100">
          {[
            { label: "Total Requests", value: summary.total_requests },
            { label: "Total Tokens", value: summary.total_tokens?.toLocaleString() },
            { label: "Total Cost", value: `$${summary.total_cost_usd?.toFixed(4)}` },
            { label: "Avg Latency", value: `${summary.avg_latency_ms}ms` },
            { label: "Success Rate", value: `${summary.success_rate}%` },
          ].map(k => (
            <div key={k.label} className="bg-white px-4 py-3">
              <div className="text-[11px] text-slate-400 uppercase font-semibold">{k.label}</div>
              <div className="text-lg font-semibold text-slate-900 mt-0.5">{k.value || "\u2014"}</div>
            </div>
          ))}
        </div>
      )}
      {!expanded ? null : loading ? <div className="py-8 text-sm text-slate-400 text-center">Loading metering data...</div> : data.length === 0 && trend.length === 0 ? (
        <div className="py-8 text-sm text-slate-400 text-center">No usage data for this period.</div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
            {data.length > 0 && (
              <div className="px-5 py-4">
                <div className="text-[11px] text-slate-400 uppercase font-semibold mb-3">Cost Breakdown ({dimension})</div>
                <DonutChart data={donutData} />
              </div>
            )}
            {trend.length > 1 && (
              <div className="px-5 py-4">
                <div className="text-[11px] text-slate-400 uppercase font-semibold mb-3">Daily Cost Trend</div>
                <AreaChart data={areaData} height={120} />
              </div>
            )}
          </div>
          {data.length > 0 && (
            <div className="px-5 py-3 border-t border-slate-100">
              <div className="space-y-2">
                {data.map((d, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                    <div className="w-28 text-sm font-medium text-slate-900 truncate" title={d.dimension_value}>{d.dimension_value || "\u2014"}</div>
                    <div className="flex-1 bg-slate-100 rounded-full h-3 relative overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${Math.max((d.total_cost_usd / maxCost) * 100, 2)}%`, background: CHART_COLORS[i % CHART_COLORS.length] }} />
                    </div>
                    <div className="w-20 text-right text-xs font-mono text-slate-600">${d.total_cost_usd.toFixed(4)}</div>
                    <div className="w-16 text-right text-xs text-slate-400">{d.total_requests} req</div>
                    <div className="w-20 text-right text-xs text-slate-400">{d.total_tokens.toLocaleString()} tok</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5 animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="h-3 bg-slate-100 rounded w-16 mb-3" />
            <div className="h-6 bg-slate-100 rounded w-12" />
          </div>
        ))}
      </div>
      <div className="h-36 bg-white border border-slate-200 rounded-2xl" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="h-48 bg-white border border-slate-200 rounded-xl" />
        <div className="h-48 bg-white border border-slate-200 rounded-xl" />
      </div>
    </div>
  );
}

export default function DashboardPage({ setPage }) {
  const [m, setM] = useState(null);
  const [inboxItems, setInboxItems] = useState([]);
  const [period, setPeriod] = useState(30);
  const [dashLoading, setDashLoading] = useState(true);
  const [collapsed, setCollapsed] = useState({});
  const toggleSection = (key) => setCollapsed(prev => ({ ...prev, [key]: !prev[key] }));

  useEffect(() => {
    setDashLoading(true);
    Promise.all([
      apiFetch(`${API}/dashboard/metrics?period_days=${period}`).then(r => r.json()).catch(() => null),
      apiFetch(`${API}/inbox?status=pending`).then(r => r.json()).catch(() => ({ items: [] })),
    ]).then(([metrics, inbox]) => {
      if (metrics) setM(metrics);
      setInboxItems((inbox?.items || []).slice(0, 4));
      setDashLoading(false);
    });
  }, [period]);

  const kpi = m?.kpis || {};
  const trendSign = (v) => v > 0 ? `+${v}%` : v < 0 ? `${v}%` : "\u2014";
  const maxAgentCalls = Math.max(...(m?.top_agents || []).map(a => a.calls), 1);
  const areaData = (m?.daily_trend || []).map(t => ({ label: t.date, shortLabel: t.date.slice(5), value: t.cost_usd, extra: t.calls }));

  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">Platform intelligence & operations overview</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={period} onChange={e => setPeriod(Number(e.target.value))} className="bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs outline-none font-medium text-slate-600">
            <option value={7}>7 days</option><option value={30}>30 days</option><option value={90}>90 days</option>
          </select>
        </div>
      </div>

      {dashLoading && !m && <DashboardSkeleton />}

      {!dashLoading && !m && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: Bot, label: "Create an Agent", desc: "Build an AI agent with tools, RAG, and guardrails", page: "AgentBuilder", color: "bg-violet-50 text-violet-600" },
            { icon: Workflow, label: "Build a Workflow", desc: "Visual drag-and-drop automation builder", page: "Workflows", color: "bg-emerald-50 text-emerald-600" },
            { icon: Link2, label: "Connect a Provider", desc: "Add OpenAI, Google, or Anthropic API keys", page: "Integrations", color: "bg-sky-50 text-sky-600" },
          ].map(card => (
            <button key={card.page} onClick={() => setPage(card.page)}
              className="flex items-center gap-4 bg-white border border-slate-200/80 rounded-xl p-5 text-left hover:shadow-lg hover:-translate-y-0.5 hover:border-slate-300 transition-all duration-200 cursor-pointer">
              <div className={cn("w-11 h-11 rounded-xl flex items-center justify-center shrink-0", card.color)}><card.icon size={20} /></div>
              <div>
                <div className="text-sm font-semibold text-slate-900">{card.label}</div>
                <div className="text-xs text-slate-500 mt-0.5">{card.desc}</div>
              </div>
              <ArrowRight size={14} className="text-slate-300 shrink-0 ml-auto" />
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="API Calls" value={kpi.total_calls?.toLocaleString() ?? "\u2014"} icon={Activity} trend={trendSign(kpi.calls_trend_pct)} />
        <StatCard label="Total Cost" value={kpi.total_cost_usd ? `$${kpi.total_cost_usd.toFixed(2)}` : "\u2014"} icon={DollarSign} trend={trendSign(kpi.cost_trend_pct)} />
        <StatCard label="Success Rate" value={kpi.success_rate ? `${kpi.success_rate}%` : "\u2014"} icon={Check} trend={kpi.success_rate >= 95 ? "healthy" : kpi.success_rate >= 85 ? "acceptable" : "needs attention"} />
        <StatCard label="Avg Latency" value={kpi.avg_latency_ms ? `${kpi.avg_latency_ms}ms` : "\u2014"} icon={Clock} />
        <StatCard label="Active Users" value={kpi.active_users ?? "\u2014"} icon={UsersIcon} />
        <StatCard label="Pending Approvals" value={inboxItems.length} icon={InboxIcon} />
      </div>

      {m?.roi && (
        <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 text-white relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-jai-primary/10 via-transparent to-jai-primary/5" />
          <div className="relative">
            <div className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-4">Automation ROI \u2014 {period} Days</div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
              <div><div className="text-2xl font-bold tracking-tight">{m.roi.active_agents}</div><div className="text-xs text-slate-400 mt-1">Active Agents</div></div>
              <div><div className="text-2xl font-bold tracking-tight">{m.roi.active_workflows}</div><div className="text-xs text-slate-400 mt-1">Active Workflows</div></div>
              <div><div className="text-2xl font-bold tracking-tight">{m.roi.automated_decisions?.toLocaleString()}</div><div className="text-xs text-slate-400 mt-1">Automated Decisions</div></div>
              <div><div className="text-2xl font-bold tracking-tight">{Math.round(m.roi.estimated_time_saved_min / 60)}h</div><div className="text-xs text-slate-400 mt-1">Est. Time Saved</div></div>
              <div><div className="text-2xl font-bold tracking-tight">${m.roi.cost_per_decision?.toFixed(4)}</div><div className="text-xs text-slate-400 mt-1">Cost per Decision</div></div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between cursor-pointer" onClick={() => toggleSection("agents")}>
            <h2 className="text-sm font-semibold text-slate-900">Top Agents by Usage</h2>
            <button onClick={() => setPage("Agents")} className="text-xs text-emerald-600 font-medium hover:underline flex items-center gap-1">All agents <ArrowRight size={12} /></button>
          </div>
          {(m?.top_agents || []).length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-400">No agent usage data</div>
          ) : (
            <div className="divide-y divide-slate-50">
              {(m?.top_agents || []).slice(0, 6).map((a, i) => (
                <div key={a.agent_id} className="px-5 py-2.5 flex items-center gap-3">
                  <div className="w-5 text-center text-[11px] font-bold text-slate-400">#{i + 1}</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900 truncate">{a.agent_name}</div>
                    <div className="flex items-center gap-3 mt-1">
                      <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                        <div className="h-full rounded-full bg-jai-primary" style={{ width: `${(a.calls / maxAgentCalls) * 100}%` }} />
                      </div>
                      <span className="text-[11px] text-slate-500 w-14 text-right">{a.calls} calls</span>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-xs font-mono text-slate-600">${a.cost_usd.toFixed(3)}</div>
                    <div className="text-[11px] text-slate-400">{a.success_rate}% ok</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between cursor-pointer" onClick={() => toggleSection("models")}>
            <h2 className="text-sm font-semibold text-slate-900">LLM Models by Spend</h2>
            <button onClick={() => setPage("Models")} className="text-xs text-emerald-600 font-medium hover:underline flex items-center gap-1">All models <ArrowRight size={12} /></button>
          </div>
          {(m?.top_models || []).length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-400">No model usage data</div>
          ) : (
            <div className="px-5 py-3">
              <div className="flex items-center gap-4 mb-4">
                <DonutChart data={(m?.top_models || []).slice(0, 6).map(d => ({ label: d.model, value: d.cost_usd }))} size={100} />
              </div>
              <div className="space-y-2">
                {(m?.top_models || []).slice(0, 5).map((d, i) => (
                  <div key={d.model} className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                    <span className="text-xs font-medium text-slate-800 flex-1 truncate">{d.model}</span>
                    <span className="text-xs font-mono text-slate-500">${d.cost_usd.toFixed(3)}</span>
                    <span className="text-[11px] text-slate-400 w-16 text-right">{d.calls} calls</span>
                    <span className="text-[11px] text-slate-400 w-16 text-right">{(d.tokens / 1000).toFixed(0)}K tok</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
            <TrendingUp size={14} className="text-slate-500" />
            <h2 className="text-sm font-semibold text-slate-900">Daily Cost Trend</h2>
          </div>
          <div className="px-5 py-4">
            {areaData.length > 1 ? <AreaChart data={areaData} height={130} /> : <div className="text-sm text-slate-400 text-center py-6">Not enough data for trend</div>}
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Spend by Team</h2>
            <button onClick={() => setPage("Groups")} className="text-xs text-emerald-600 font-medium hover:underline flex items-center gap-1">Groups <ArrowRight size={12} /></button>
          </div>
          {(m?.cost_by_group || []).length === 0 ? (
            <div className="p-6 text-center text-sm text-slate-400">No group data</div>
          ) : (
            <div className="divide-y divide-slate-50">
              {(m?.cost_by_group || []).slice(0, 5).map(g => (
                <div key={g.group_id} className="px-5 py-2.5">
                  <div className="flex items-center justify-between">
                    <div><div className="text-sm font-medium text-slate-900">{g.group_name}</div><div className="text-[11px] text-slate-400">{g.lob}</div></div>
                    <div className="text-right"><div className="text-sm font-mono font-semibold text-slate-900">${g.cost_usd.toFixed(2)}</div><div className="text-[11px] text-slate-400">{g.calls} calls</div></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {inboxItems.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-900">Pending Approvals</h2>
            <button onClick={() => setPage("Inbox")} className="text-xs text-emerald-600 font-medium hover:underline flex items-center gap-1">View all <ArrowRight size={12} /></button>
          </div>
          <div className="divide-y divide-slate-100">
            {inboxItems.map(item => (
              <div key={item.item_id} className="px-5 py-2.5 flex items-center justify-between">
                <div><div className="text-sm font-medium text-slate-900">{item.title || "Interrupt"}</div><div className="text-xs text-slate-500 mt-0.5">Agent: {item.agent_id}</div></div>
                <Badge variant="warning">{item.interrupt_type || "approval"}</Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Usage & Metering widget */}
      <MeteringWidget />
    </div>
  );
}
