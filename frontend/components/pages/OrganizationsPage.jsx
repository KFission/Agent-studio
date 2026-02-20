"use client";
import { useState, useEffect } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, SearchInput, EmptyState, StatCard, toast, confirmAction } from "../shared/StudioUI";
import {
  Building2, Plus, ChevronRight, Users as UsersIcon, Bot, Zap, Gauge, Trash2,
} from "lucide-react";

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState([]); const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [form, setForm] = useState({ name: "", owner_email: "", tier: "pro", domain: "" });

  const load = (retry = true) => { setLoading(true); apiFetch(`${API}/tenants`).then(r => r.json()).then(d => { setOrgs(d.tenants || []); setLoading(false); }).catch(() => { if (retry) { setTimeout(() => load(false), 1500); } else { setLoading(false); } }); };
  useEffect(load, []);

  const TIER_COLORS = { free: "outline", pro: "info", enterprise: "purple" };
  const TIER_LIMITS = { free: { agents: 5, users: 10, rpm: 60 }, pro: { agents: 50, users: 100, rpm: 600 }, enterprise: { agents: "Unlimited", users: "Unlimited", rpm: "10,000" } };

  const createOrg = async () => {
    try {
      await apiFetch(`${API}/tenants`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
      setShowCreate(false); setForm({ name: "", owner_email: "", tier: "pro", domain: "" }); load();
      toast.success(`Organization "${form.name}" created`);
    } catch (e) { toast.error("Failed to create organization"); }
  };

  const deleteOrg = async (id) => {
    const ok = await confirmAction({ title: "Delete Organization", message: "This will permanently delete this organization and all its data. This cannot be undone.", confirmLabel: "Delete Organization" });
    if (!ok) return;
    await apiFetch(`${API}/tenants/${id}`, { method: "DELETE" }); load(); toast.success("Organization deleted");
    if (selectedOrg?.tenant_id === id) setSelectedOrg(null);
  };

  if (selectedOrg) {
    const limits = TIER_LIMITS[selectedOrg.tier] || TIER_LIMITS.free;
    return (
      <div className="p-6 animate-fade-up max-w-5xl mx-auto space-y-5">
        <button onClick={() => setSelectedOrg(null)} className="text-sm text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer">
          <ChevronRight size={14} className="rotate-180" /> Back to Organizations
        </button>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-jai-primary to-jai-primary/60 flex items-center justify-center text-xl font-bold text-white">{selectedOrg.name?.charAt(0)}</div>
            <div>
              <h1 className="text-xl font-semibold text-slate-900">{selectedOrg.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant={TIER_COLORS[selectedOrg.tier] || "outline"}>{selectedOrg.tier?.toUpperCase()}</Badge>
                <span className="text-xs text-slate-400">{selectedOrg.slug} · {selectedOrg.domain || "No domain"}</span>
              </div>
            </div>
          </div>
          <button onClick={() => deleteOrg(selectedOrg.tenant_id)} className="text-xs text-red-400 hover:text-red-600 border border-red-200 rounded-lg px-3 py-1.5 cursor-pointer hover:bg-red-50 transition">Delete Org</button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Members" value={selectedOrg.current_users ?? 0} icon={UsersIcon} />
          <StatCard label="Active Agents" value={selectedOrg.current_agents ?? 0} icon={Bot} />
          <StatCard label="LLM Requests Today" value={selectedOrg.llm_requests_today ?? 0} icon={Zap} />
          <StatCard label="Rate Limit" value={`${limits.rpm} RPM`} icon={Gauge} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-900">Organization Settings</h3>
            <div className="space-y-3 text-sm">
              <div><label className="text-xs text-slate-500">Name</label><input value={selectedOrg.name} readOnly className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none mt-1" /></div>
              <div><label className="text-xs text-slate-500">Owner Email</label><input value={selectedOrg.owner_email || ""} readOnly className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none mt-1" /></div>
              <div><label className="text-xs text-slate-500">Domain</label><input value={selectedOrg.domain || ""} readOnly className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none mt-1" /></div>
              <div><label className="text-xs text-slate-500">Tier</label>
                <div className="flex gap-2 mt-1">
                  {["free", "pro", "enterprise"].map(t => (
                    <button key={t} className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition cursor-pointer",
                      selectedOrg.tier === t ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50")}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-900">Quotas & Limits</h3>
            <div className="space-y-3">
              {[
                { label: "Max Agents", value: limits.agents, current: selectedOrg.current_agents || 0 },
                { label: "Max Users", value: limits.users, current: selectedOrg.current_users || 0 },
                { label: "Requests / Minute", value: limits.rpm, current: "—" },
              ].map(q => (
                <div key={q.label} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
                  <span className="text-sm text-slate-600">{q.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">{q.current} /</span>
                    <span className="text-sm font-medium text-slate-900">{q.value}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="pt-2">
              <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">API Keys</h4>
              <button className="flex items-center gap-2 text-xs text-jai-primary font-medium cursor-pointer hover:underline"><Plus size={12} /> Generate Org API Key</button>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Members</h3>
          <div className="text-xs text-slate-400">Member management coming soon — assign users to this organization via Users & Roles page.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div><h1 className="text-xl font-semibold text-slate-900">Organizations</h1><p className="text-sm text-slate-500 mt-1">Multi-tenant org management — isolate teams, models, and budgets</p></div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} /> New Organization</button>
      </div>

      {showCreate && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
          <h3 className="text-base font-semibold text-slate-900">Create Organization</h3>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs text-slate-500">Name</label><input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 mt-1" placeholder="Procurement Division" /></div>
            <div><label className="text-xs text-slate-500">Owner Email</label><input value={form.owner_email} onChange={e => setForm(p => ({ ...p, owner_email: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 mt-1" placeholder="admin@company.com" /></div>
            <div><label className="text-xs text-slate-500">Domain</label><input value={form.domain} onChange={e => setForm(p => ({ ...p, domain: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 mt-1" placeholder="company.com" /></div>
            <div><label className="text-xs text-slate-500">Tier</label>
              <select value={form.tier} onChange={e => setForm(p => ({ ...p, tier: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 mt-1">
                <option value="free">Free</option><option value="pro">Pro</option><option value="enterprise">Enterprise</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2 justify-end pt-1">
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer hover:bg-slate-50">Cancel</button>
            <button onClick={createOrg} disabled={!form.name} className={cn("bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer", !form.name && "opacity-50")}>Create</button>
          </div>
        </div>
      )}

      {loading ? <div className="text-slate-400 text-sm">Loading organizations...</div> : orgs.length === 0 ? (
        <EmptyState icon={<Building2 size={24} />} illustration="start" title="No organizations yet" description="Create your first organization to enable multi-tenant isolation." action={<button onClick={() => setShowCreate(true)} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} className="inline mr-1" />Create Organization</button>} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {orgs.map(o => (
            <div key={o.tenant_id} onClick={() => setSelectedOrg(o)} className="bg-white border border-slate-200/80 rounded-xl p-5 hover:shadow-lg hover:-translate-y-0.5 hover:border-slate-300 transition-all duration-200 cursor-pointer">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-jai-primary to-jai-primary/60 flex items-center justify-center text-sm font-bold text-white">{o.name?.charAt(0)}</div>
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{o.name}</div>
                    <div className="text-xs text-slate-400">{o.slug}</div>
                  </div>
                </div>
                <Badge variant={TIER_COLORS[o.tier] || "outline"}>{o.tier}</Badge>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center pt-3 border-t border-slate-100">
                <div><div className="text-sm font-semibold text-slate-900">{o.current_users ?? 0}</div><div className="text-[11px] text-slate-400">Users</div></div>
                <div><div className="text-sm font-semibold text-slate-900">{o.current_agents ?? 0}</div><div className="text-[11px] text-slate-400">Agents</div></div>
                <div><div className="text-sm font-semibold text-slate-900">{o.llm_requests_today ?? 0}</div><div className="text-[11px] text-slate-400">Req/day</div></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
