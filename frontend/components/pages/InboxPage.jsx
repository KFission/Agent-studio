"use client";
import { useState, useEffect, useMemo } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, EmptyState, relativeTime } from "../shared/StudioUI";
import { Inbox as InboxIcon, Bot, Clock, Check, X, Edit3 } from "lucide-react";

function SLACountdown({ createdAt, slaHours = 4 }) {
  const [remaining, setRemaining] = useState("");
  const [isUrgent, setIsUrgent] = useState(false);
  useEffect(() => {
    const update = () => {
      const deadline = new Date(createdAt).getTime() + slaHours * 3600 * 1000;
      const diff = deadline - Date.now();
      if (diff <= 0) { setRemaining("Overdue"); setIsUrgent(true); return; }
      const hrs = Math.floor(diff / 3600000);
      const mins = Math.floor((diff % 3600000) / 60000);
      setRemaining(`${hrs}h ${mins}m left`);
      setIsUrgent(diff < 3600000);
    };
    update();
    const interval = setInterval(update, 60000);
    return () => clearInterval(interval);
  }, [createdAt, slaHours]);
  return (
    <span className={cn("text-xs font-medium flex items-center gap-1", isUrgent ? "text-red-600 animate-sla-pulse" : "text-amber-600")}>
      <Clock size={12} /> {remaining}
    </span>
  );
}

export default function InboxPage({ onCountUpdate }) {
  const [items, setItems] = useState([]); const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null); const [filter, setFilter] = useState("all");

  const load = (retry = true) => {
    setLoading(true);
    const url = filter === "all" ? `${API}/inbox` : `${API}/inbox?status=${filter}`;
    fetch(url).then(r => r.json()).then(d => { const arr = d.items || []; setItems(arr); setLoading(false); if (onCountUpdate) onCountUpdate(arr.filter(i => i.status === "pending").length); })
      .catch(() => { if (retry) { setTimeout(() => load(false), 1500); } else { setLoading(false); } });
    apiFetch(`${API}/inbox/stats/summary`).then(r => r.json()).then(setStats).catch(() => {});
  };
  useEffect(() => { load(); }, [filter]);

  const resolve = async (itemId, action) => {
    await apiFetch(`${API}/inbox/${itemId}/resolve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, resolved_by: "admin" }) });
    load();
  };

  const grouped = useMemo(() => {
    const map = {};
    items.forEach(item => { const key = item.agent_id || "unknown"; if (!map[key]) map[key] = []; map[key].push(item); });
    return Object.entries(map);
  }, [items]);

  return (
    <div className="p-6 animate-fade-up max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div><h1 className="text-xl font-semibold text-slate-900">Approvals</h1><p className="text-sm text-slate-500 mt-1">Human-in-the-loop review queue — approve, reject, or escalate agent decisions</p></div>
        {stats && (
          <div className="flex gap-3">
            <div className="bg-white border border-slate-200 rounded-xl px-4 py-2 text-center"><div className="text-xl font-bold text-amber-500">{stats.pending}</div><div className="text-[11px] text-slate-500">Pending</div></div>
            <div className="bg-white border border-slate-200 rounded-xl px-4 py-2 text-center"><div className="text-xl font-bold text-slate-900">{stats.total}</div><div className="text-[11px] text-slate-500">Total</div></div>
          </div>
        )}
      </div>
      <hr className="border-slate-200" />
      <div className="flex gap-2">
        {["all", "pending", "approved", "rejected"].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={cn("px-3.5 py-1.5 rounded-lg text-xs font-medium cursor-pointer border capitalize transition",
              filter === f ? "bg-emerald-50 border-emerald-300 text-emerald-700" : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50")}>
            {f}
          </button>
        ))}
      </div>
      {loading ? <div className="text-slate-400 text-sm">Loading inbox...</div> : items.length === 0 ? (
        <EmptyState icon={<InboxIcon size={24} />} illustration="empty" title="Inbox is empty" description="No interrupts requiring attention." />
      ) : (
        <div className="space-y-6">
          {grouped.map(([agentId, agentItems]) => (
            <div key={agentId}>
              <div className="flex items-center gap-2 mb-3">
                <Bot size={16} className="text-slate-400" />
                <h3 className="text-sm font-semibold text-slate-700">Agent: {agentId}</h3>
                <Badge variant="outline">{agentItems.length}</Badge>
              </div>
              <div className="space-y-3 ml-6">
                {agentItems.map(item => (
                  <div key={item.item_id} className="bg-white border border-slate-200 rounded-xl p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="text-sm font-semibold text-slate-900">{item.title || "Interrupt"}</div>
                        <div className="text-xs text-slate-500 mt-0.5">{item.description || `Thread: ${item.thread_title || item.thread_id}`}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        {item.status === "pending" && item.created_at && <SLACountdown createdAt={item.created_at} />}
                        <Badge variant={item.status === "pending" ? "warning" : item.status === "approved" ? "success" : item.status === "rejected" ? "danger" : "outline"}>{item.status}</Badge>
                        <Badge variant="outline">{item.interrupt_type}</Badge>
                      </div>
                    </div>
                    <div className="text-xs text-slate-400 mb-3">Created: {relativeTime(item.created_at)}</div>
                    {item.status === "pending" && (
                      <div className="flex gap-2">
                        <button onClick={() => resolve(item.item_id, "approve")} className="flex items-center gap-1.5 bg-emerald-500 text-white rounded-lg px-3 py-1.5 text-xs font-medium cursor-pointer"><Check size={12} /> Approve</button>
                        <button onClick={() => resolve(item.item_id, "reject")} className="flex items-center gap-1.5 border border-red-300 text-red-600 rounded-lg px-3 py-1.5 text-xs font-medium cursor-pointer hover:bg-red-50"><X size={12} /> Reject</button>
                        <button onClick={() => resolve(item.item_id, "edit")} className="flex items-center gap-1.5 border border-slate-200 text-slate-600 rounded-lg px-3 py-1.5 text-xs font-medium cursor-pointer hover:bg-slate-50"><Edit3 size={12} /> Edit & Approve</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
