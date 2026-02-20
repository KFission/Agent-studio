"use client";
import { useState, useEffect } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, SearchInput, EmptyState, toast, confirmAction } from "../shared/StudioUI";
import {
  FolderKanban, Plus, Trash2, ChevronRight, Bot, Box, UserPlus, X,
  Users as UsersIcon, DollarSign,
} from "lucide-react";

export default function GroupsPage() {
  const [groups, setGroups] = useState([]); const [loading, setLoading] = useState(true);
  const [models, setModels] = useState([]); const [agents, setAgents] = useState([]); const [users, setUsers] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", lob: "", monthly_budget_usd: 0 });
  const [selected, setSelected] = useState(null);
  const [addMemberId, setAddMemberId] = useState("");
  const [search, setSearch] = useState("");

  const load = (retry = true) => {
    setLoading(true);
    apiFetch(`${API}/groups`).then(r => r.json()).then(d => { setGroups(d.groups || []); setLoading(false); })
      .catch(() => { if (retry) { setTimeout(() => load(false), 1500); } else { setLoading(false); } });
    apiFetch(`${API}/models`).then(r => r.json()).then(d => setModels(d.models || [])).catch(() => {});
    apiFetch(`${API}/agents`).then(r => r.json()).then(d => setAgents(d.agents || [])).catch(() => {});
    apiFetch(`${API}/users`).then(r => r.json()).then(d => setUsers(d.users || [])).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const createGroup = async () => {
    try {
      await apiFetch(`${API}/groups`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
      toast.success(`Group "${form.name}" created`);
      setShowCreate(false); setForm({ name: "", description: "", lob: "", monthly_budget_usd: 0 }); load();
    } catch (e) { toast.error("Failed to create group"); }
  };
  const deleteGroup = async (gid, name) => {
    const ok = await confirmAction({ title: "Delete Group", message: `Delete group "${name || gid}"? All member assignments will be lost.` });
    if (!ok) return;
    try {
      await apiFetch(`${API}/groups/${gid}`, { method: "DELETE" });
      toast.success("Group deleted");
      if (selected?.group_id === gid) setSelected(null); load();
    } catch (e) { toast.error("Failed to delete group"); }
  };
  const addMember = async (gid) => {
    if (!addMemberId) return;
    try {
      const res = await apiFetch(`${API}/groups/${gid}/members`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id: addMemberId }) });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || "Failed to add member"); }
      toast.success("Member added");
      setAddMemberId(""); load(); const r = await apiFetch(`${API}/groups/${gid}`); setSelected(await r.json());
    } catch (e) { toast.error(e.message || "Failed to add member"); }
  };
  const removeMember = async (gid, uid) => {
    try {
      await apiFetch(`${API}/groups/${gid}/members/${uid}`, { method: "DELETE" });
      toast.success("Member removed");
      load(); const r = await apiFetch(`${API}/groups/${gid}`); setSelected(await r.json());
    } catch (e) { toast.error("Failed to remove member"); }
  };
  const assignModel = async (gid, modelId) => { await apiFetch(`${API}/groups/${gid}/models`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model_ids: [modelId] }) }); load(); const r = await apiFetch(`${API}/groups/${gid}`); setSelected(await r.json()); };
  const revokeModel = async (gid, modelId) => { await apiFetch(`${API}/groups/${gid}/models`, { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model_ids: [modelId] }) }); load(); const r = await apiFetch(`${API}/groups/${gid}`); setSelected(await r.json()); };
  const assignAgent = async (gid, agentId) => { await apiFetch(`${API}/groups/${gid}/agents`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ agent_ids: [agentId] }) }); load(); const r = await apiFetch(`${API}/groups/${gid}`); setSelected(await r.json()); };

  const allRoles = ["platform_admin", "agent_developer", "agent_operator", "viewer"];

  if (selected) {
    const assignedModels = models.filter(m => (selected.allowed_model_ids || []).includes(m.model_id));
    const unassignedModels = models.filter(m => !(selected.allowed_model_ids || []).includes(m.model_id));
    const assignedAgents = agents.filter(a => (selected.allowed_agent_ids || []).includes(a.agent_id));
    const nonMembers = users.filter(u => !(selected.member_ids || []).includes(u.user_id));

    return (
      <div className="p-6 animate-fade-up max-w-5xl mx-auto space-y-5">
        <button onClick={() => setSelected(null)} className="text-sm text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer"><ChevronRight size={14} className="rotate-180" /> Back to Groups</button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">{selected.name}</h1>
            <p className="text-sm text-slate-500 mt-1">{selected.description || "No description"}</p>
            <div className="flex gap-2 mt-2">
              {selected.lob && <Badge variant="brand">{selected.lob}</Badge>}
              <Badge variant="outline">{(selected.member_ids || []).length} members</Badge>
              <Badge variant="outline">{(selected.allowed_model_ids || []).length} models</Badge>
              <Badge variant="outline">{(selected.allowed_agent_ids || []).length} agents</Badge>
              {selected.monthly_budget_usd > 0 && <Badge variant="warning">${selected.monthly_budget_usd}/mo budget</Badge>}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Members */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 flex justify-between items-center">
              <h3 className="text-sm font-semibold text-slate-900">Members</h3>
            </div>
            <div className="p-4 space-y-2">
              <div className="flex gap-2">
                {nonMembers.length > 0 ? (
                  <>
                    <select value={addMemberId} onChange={e => setAddMemberId(e.target.value)} className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none">
                      <option value="">Select user to add...</option>
                      {nonMembers.map(u => <option key={u.user_id} value={u.user_id}>{u.display_name || u.username} ({u.email})</option>)}
                    </select>
                    <button onClick={() => addMember(selected.group_id)} disabled={!addMemberId} className={cn("flex items-center gap-1 bg-jai-primary text-white rounded-lg px-3 py-1.5 text-xs font-medium cursor-pointer", !addMemberId && "opacity-50")}><UserPlus size={12} /> Add</button>
                  </>
                ) : users.length === 0 ? (
                  <div className="text-xs text-slate-400 py-2">No users in the system yet. Create users in <strong>Users &amp; Roles</strong> first.</div>
                ) : (
                  <div className="text-xs text-slate-400 py-2">All users are already members of this group.</div>
                )}
              </div>
              {(selected.member_ids || []).length === 0 ? <div className="text-sm text-slate-400 py-4 text-center">No members yet</div> : (
                <div className="divide-y divide-slate-100">
                  {(selected.member_ids || []).map(uid => {
                    const u = users.find(u => u.user_id === uid);
                    return (
                      <div key={uid} className="flex items-center justify-between py-2">
                        <div><div className="text-sm font-medium text-slate-900">{u?.display_name || uid}</div>{u?.email && <div className="text-xs text-slate-400">{u.email}</div>}</div>
                        <button onClick={() => removeMember(selected.group_id, uid)} className="text-xs text-red-500 hover:text-red-700 cursor-pointer"><Trash2 size={13} /></button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Roles */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100"><h3 className="text-sm font-semibold text-slate-900">Assigned Roles</h3></div>
            <div className="p-4 space-y-2">
              {allRoles.map(r => (
                <label key={r} className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input type="checkbox" checked={(selected.assigned_roles || []).includes(r)} onChange={async e => {
                    if (e.target.checked) { await apiFetch(`${API}/groups/${selected.group_id}/roles`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ roles: [r] }) }); }
                    const res = await apiFetch(`${API}/groups/${selected.group_id}`); setSelected(await res.json()); load();
                  }} className="accent-emerald-500" />
                  <span className="font-medium">{r}</span>
                </label>
              ))}
              <div className="text-[11px] text-slate-400 mt-2">Members inherit these roles when accessing the platform.</div>
            </div>
          </div>

          {/* Allowed Models (Admin pushes models here) */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100"><h3 className="text-sm font-semibold text-slate-900">Allowed Models</h3></div>
            <div className="p-4 space-y-2">
              <div className="text-[11px] text-slate-400 mb-2">Models pushed to this group. Members can use these without needing API keys.</div>
              {assignedModels.map(m => (
                <div key={m.model_id} className="flex items-center justify-between py-1.5">
                  <div className="flex items-center gap-2"><Box size={14} className="text-slate-400" /><span className="text-sm text-slate-900">{m.display_name}</span><Badge variant="outline">{m.provider}</Badge></div>
                  <button onClick={() => revokeModel(selected.group_id, m.model_id)} className="text-xs text-red-500 cursor-pointer"><X size={13} /></button>
                </div>
              ))}
              {unassignedModels.length > 0 && (
                <select onChange={e => { if (e.target.value) assignModel(selected.group_id, e.target.value); e.target.value = ""; }} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none mt-2">
                  <option value="">+ Add model...</option>
                  {unassignedModels.map(m => <option key={m.model_id} value={m.model_id}>{m.display_name} ({m.provider})</option>)}
                </select>
              )}
            </div>
          </div>

          {/* Allowed Agents */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100"><h3 className="text-sm font-semibold text-slate-900">Allowed Agents</h3></div>
            <div className="p-4 space-y-2">
              {assignedAgents.map(a => (
                <div key={a.agent_id} className="flex items-center justify-between py-1.5">
                  <div className="flex items-center gap-2"><Bot size={14} className="text-slate-400" /><span className="text-sm text-slate-900">{a.name}</span></div>
                </div>
              ))}
              {agents.filter(a => !(selected.allowed_agent_ids || []).includes(a.agent_id)).length > 0 && (
                <select onChange={e => { if (e.target.value) assignAgent(selected.group_id, e.target.value); e.target.value = ""; }} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none mt-2">
                  <option value="">+ Add agent...</option>
                  {agents.filter(a => !(selected.allowed_agent_ids || []).includes(a.agent_id)).map(a => <option key={a.agent_id} value={a.agent_id}>{a.name}</option>)}
                </select>
              )}
              {assignedAgents.length === 0 && <div className="text-sm text-slate-400 py-2 text-center">No agents assigned</div>}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div><h1 className="text-xl font-semibold text-slate-900">Teams</h1><p className="text-sm text-slate-500 mt-1">Organize users into teams by line of business. Assign models, agents, and roles at the team level.</p></div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} /> New Team</button>
      </div>
      {groups.length > 0 && !showCreate && (
        <div className="flex items-center gap-3">
          <SearchInput value={search} onChange={setSearch} placeholder="Search groups..." />
          <span className="text-xs text-slate-400">{groups.filter(g => !search || g.name.toLowerCase().includes(search.toLowerCase())).length} group{groups.length !== 1 ? "s" : ""}</span>
        </div>
      )}
      {showCreate && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
          <h3 className="text-base font-semibold text-slate-900">Create Group</h3>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs text-slate-500">Name</label><input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="Procurement Team" /></div>
            <div><label className="text-xs text-slate-500">Line of Business</label><input value={form.lob} onChange={e => setForm(p => ({ ...p, lob: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="procurement" /></div>
          </div>
          <div><label className="text-xs text-slate-500">Description</label><input value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="Team responsible for..." /></div>
          <div><label className="text-xs text-slate-500">Monthly Budget (USD, 0=unlimited)</label><input type="number" value={form.monthly_budget_usd} onChange={e => setForm(p => ({ ...p, monthly_budget_usd: parseFloat(e.target.value) || 0 }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" /></div>
          <div className="flex gap-2">
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 cursor-pointer hover:bg-slate-50">Cancel</button>
            <button onClick={createGroup} disabled={!form.name} className={cn("bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer", !form.name && "opacity-50")}>Create Group</button>
          </div>
        </div>
      )}
      {loading ? <div className="text-slate-400 text-sm">Loading groups...</div> : groups.length === 0 ? (
        <EmptyState icon={<FolderKanban size={24} />} illustration="empty" title="No groups yet" description="Create a group to organize users by team or Line of Business, then assign models and agents." action={<button onClick={() => setShowCreate(true)} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} className="inline mr-1" />Create Group</button>} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {groups.filter(g => !search || g.name.toLowerCase().includes(search.toLowerCase()) || (g.lob || "").toLowerCase().includes(search.toLowerCase())).map(g => (
            <div key={g.group_id} className="bg-white border border-slate-200/80 rounded-xl overflow-hidden hover:shadow-lg hover:-translate-y-0.5 hover:border-slate-300 transition-all duration-200 cursor-pointer" onClick={() => setSelected(g)}>
              <div className="p-5">
                <div className="flex items-start justify-between">
                  <div className="text-base font-semibold text-slate-900">{g.name}</div>
                  {g.lob && <Badge variant="brand">{g.lob}</Badge>}
                </div>
                {g.description && <div className="text-sm text-slate-500 mt-2 line-clamp-2">{g.description}</div>}
                <div className="flex flex-wrap gap-1.5 mt-3">
                  <Badge variant="outline"><UsersIcon size={10} className="inline" /> {(g.member_ids || []).length} members</Badge>
                  <Badge variant="info"><Box size={10} className="inline" /> {(g.allowed_model_ids || []).length} models</Badge>
                  <Badge variant="outline"><Bot size={10} className="inline" /> {(g.allowed_agent_ids || []).length} agents</Badge>
                </div>
                {g.monthly_budget_usd > 0 && <div className="text-xs text-amber-600 mt-2"><DollarSign size={10} className="inline" /> ${g.monthly_budget_usd}/mo budget</div>}
              </div>
              <div className="px-5 py-3 border-t border-slate-100 flex justify-between items-center">
                <span className="text-xs text-slate-400">{g.group_id}</span>
                <button onClick={e => { e.stopPropagation(); deleteGroup(g.group_id, g.name); }} className="text-xs text-red-400 hover:text-red-600 cursor-pointer"><Trash2 size={13} /></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
