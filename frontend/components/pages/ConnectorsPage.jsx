"use client";
import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, SearchInput, EmptyState } from "../shared/StudioUI";
import { Link2 } from "lucide-react";

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState([]); const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const load = (retry = true) => { setLoading(true); apiFetch(`${API}/connectors`).then(r => r.json()).then(d => { setConnectors(d.connectors || []); setLoading(false); }).catch(() => { if (retry) { setTimeout(() => load(false), 1500); } else { setLoading(false); } }); };
  useEffect(() => { load(); }, []);
  const filtered = connectors.filter(c => c.name?.toLowerCase().includes(search.toLowerCase()));
  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div><h1 className="text-xl font-semibold text-slate-900">Connectors</h1><p className="text-sm text-slate-500 mt-1">Connect to external systems — SAP, Salesforce, ServiceNow, Jira, Slack, and more</p></div>
      <SearchInput value={search} onChange={setSearch} placeholder="Search connectors..." />
      {loading ? <div className="text-slate-400 text-sm">Loading connectors...</div> : filtered.length === 0 ? (
        <EmptyState icon={<Link2 size={24} />} illustration="process" title="No connectors found" description="Enterprise connectors will be listed here." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(c => (
            <div key={c.connector_id} className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md transition cursor-pointer">
              <div className="text-sm font-semibold text-slate-900 mb-1">{c.name}</div>
              <div className="text-xs text-slate-500 line-clamp-2 mb-3">{c.description}</div>
              <div className="flex gap-1"><Badge variant="outline">{c.category}</Badge><Badge variant="outline">{(c.actions || []).length} actions</Badge></div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
