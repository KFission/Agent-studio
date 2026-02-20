"use client";
import { useState, useEffect } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, SearchInput, EmptyState, Tabs, toast, confirmAction } from "../shared/StudioUI";
import {
  Users as UsersIcon, Plus, Trash2, Edit3, Check, X, Shield, Eye,
  UserPlus, ChevronDown, ChevronRight, Save, RefreshCw,
} from "lucide-react";

// Platform modules for role-based access control
const PLATFORM_MODULES = [
  { section: "Build", modules: [
    { id: "Agents", label: "Agents", desc: "Create, configure, and deploy AI agents" },
    { id: "Workflows", label: "Workflows", desc: "Visual drag-and-drop workflow builder" },
    { id: "Orchestrator", label: "Pipelines", desc: "Chain agents into multi-step pipelines" },
    { id: "Tools", label: "Tool Registry", desc: "API tools and functions available to agents" },
    { id: "Guardrails", label: "Guardrails", desc: "Safety rules, content filters, and compliance" },
    { id: "KnowledgeBases", label: "Knowledge Bases", desc: "RAG document collections for grounded responses" },
    { id: "Prompts", label: "Prompts", desc: "Langfuse-backed prompt management with versioning & labels" },
  ]},
  { section: "Run & Test", modules: [
    { id: "Chat", label: "Chat", desc: "Test and interact with agents in real time" },
    { id: "LLMPlayground", label: "LLM Playground", desc: "Test prompts against LLMs with variable substitution" },
    { id: "Inbox", label: "Approvals", desc: "Human-in-the-loop review queue" },
    { id: "Eval", label: "Eval Studio", desc: "Side-by-side LLM benchmarking across models" },
  ]},
  { section: "Operate", modules: [
    { id: "UsageMetering", label: "Usage & Metering", desc: "Token consumption, cost tracking, and trends" },
    { id: "Models", label: "Model Library", desc: "Browse, register, and manage LLM models" },
    { id: "LLMLogs", label: "Logs", desc: "LLM request/response logs and diagnostics" },
    { id: "Monitoring", label: "Monitoring", desc: "Live traces, generations, and cost analytics" },
    { id: "Connectors", label: "Connectors", desc: "Connect to Slack, Jira, SAP, and more" },
  ]},
  { section: "Admin", modules: [
    { id: "Groups", label: "Teams", desc: "Organize users with shared model and agent access" },
    { id: "NotificationChannels", label: "Notifications", desc: "Alert channels \u2014 email, Slack, Teams, webhooks" },
    { id: "Users", label: "Users & Roles", desc: "User accounts and custom role permissions" },
    { id: "Settings", label: "Settings", desc: "Platform config, API tokens, and usage limits" },
  ]},
];

const ACCESS_LEVELS = [
  { value: "write", label: "Write", color: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  { value: "read", label: "Read", color: "bg-sky-100 text-sky-700 border-sky-200" },
  { value: "none", label: "No Access", color: "bg-slate-100 text-slate-400 border-slate-200" },
];

const DEFAULT_SYSTEM_ROLES = [
  { name: "Platform Admin", is_system: true, description: "Full access to all modules", permissions: PLATFORM_MODULES.flatMap(s => s.modules).reduce((acc, m) => ({ ...acc, [m.id]: "write" }), {}) },
  { name: "Agent Developer", is_system: true, description: "Build and test agents, workflows, tools", permissions: { Agents: "write", Workflows: "write", Orchestrator: "write", Tools: "write", Guardrails: "write", KnowledgeBases: "write", Prompts: "write", Chat: "write", Inbox: "write", Eval: "write", UsageMetering: "read", Models: "read", LLMLogs: "read", Monitoring: "read", Connectors: "none", Groups: "none", Integrations: "none", NotificationChannels: "none", Users: "none", Settings: "none" } },
  { name: "Viewer", is_system: true, description: "Read-only access to all modules", permissions: PLATFORM_MODULES.flatMap(s => s.modules).reduce((acc, m) => ({ ...acc, [m.id]: "read" }), {}) },
];

export default function UsersPage() {
  const [users, setUsers] = useState([]); const [apiRoles, setApiRoles] = useState([]); const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("Users");
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [newUser, setNewUser] = useState({ username: "", email: "", password: "", first_name: "", last_name: "", roles: ["viewer"] });
  const [createUserError, setCreateUserError] = useState("");
  const [creatingUser, setCreatingUser] = useState(false);
  const [customRoles, setCustomRoles] = useState([]);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [roleName, setRoleName] = useState("");
  const [roleDesc, setRoleDesc] = useState("");
  const [rolePerms, setRolePerms] = useState(() => PLATFORM_MODULES.flatMap(s => s.modules).reduce((acc, m) => ({ ...acc, [m.id]: "read" }), {}));

  const loadData = (retry = true) => {
    setLoading(true);
    Promise.all([
      apiFetch(`${API}/users`).then(r => r.json()),
      apiFetch(`${API}/roles`).then(r => r.json()).catch(() => ({ roles: [] })),
    ]).then(([u, r]) => { setUsers(u.users || []); setApiRoles(r.roles || []); setLoading(false); })
      .catch(() => { if (retry) { setTimeout(() => loadData(false), 1500); } else { setLoading(false); } });
  };
  useEffect(() => { loadData(); }, []);

  const handleCreateUser = async () => {
    setCreateUserError(""); setCreatingUser(true);
    try {
      const res = await apiFetch(`${API}/users`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newUser) });
      if (!res.ok) { const body = await res.json().catch(() => ({})); throw new Error(body.detail || "Failed to create user"); }
      await res.json();
      toast.success("User created successfully");
      loadData();
      setShowCreateUser(false);
      setNewUser({ username: "", email: "", password: "", first_name: "", last_name: "", roles: ["viewer"] });
    } catch (e) { setCreateUserError(e.message); }
    setCreatingUser(false);
  };

  const allRoles = [...DEFAULT_SYSTEM_ROLES, ...customRoles];

  const openCreateRole = () => {
    setRoleName(""); setRoleDesc("");
    setRolePerms(PLATFORM_MODULES.flatMap(s => s.modules).reduce((acc, m) => ({ ...acc, [m.id]: "read" }), {}));
    setEditingRole(null); setShowCreateRole(true);
  };

  const openEditRole = (role) => {
    setRoleName(role.name); setRoleDesc(role.description || "");
    setRolePerms({ ...PLATFORM_MODULES.flatMap(s => s.modules).reduce((acc, m) => ({ ...acc, [m.id]: "none" }), {}), ...role.permissions });
    setEditingRole(role.name); setShowCreateRole(true);
  };

  const saveRole = () => {
    if (!roleName.trim()) return;
    const newRole = { name: roleName.trim(), is_system: false, description: roleDesc, permissions: { ...rolePerms } };
    if (editingRole) {
      setCustomRoles(prev => prev.map(r => r.name === editingRole ? newRole : r));
    } else {
      setCustomRoles(prev => [...prev, newRole]);
    }
    setShowCreateRole(false);
  };

  const deleteRole = (name) => setCustomRoles(prev => prev.filter(r => r.name !== name));

  const setSectionAccess = (section, level) => {
    const sectionModules = PLATFORM_MODULES.find(s => s.section === section)?.modules || [];
    setRolePerms(prev => {
      const next = { ...prev };
      sectionModules.forEach(m => { next[m.id] = level; });
      return next;
    });
  };

  const permCounts = (perms) => {
    const vals = Object.values(perms || {});
    return { write: vals.filter(v => v === "write").length, read: vals.filter(v => v === "read").length, none: vals.filter(v => v === "none").length };
  };

  if (loading) return <div className="p-6 text-slate-400 text-sm">Loading...</div>;
  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      <div><h1 className="text-xl font-semibold text-slate-900">Users & Roles</h1><p className="text-sm text-slate-500 mt-1">Manage user accounts and define custom roles with module-level permissions</p></div>
      <Tabs tabs={["Users", "Roles"]} active={tab} onChange={setTab} />

      {/* ── USERS TAB ── */}
      {tab === "Users" && (
        <>
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-500">{users.length} user{users.length !== 1 ? "s" : ""}</div>
            <button onClick={() => { setShowCreateUser(true); setCreateUserError(""); }} className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover">
              <UserPlus size={14} /> Add User
            </button>
          </div>

          {/* Create User Modal */}
          {showCreateUser && (
            <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowCreateUser(false)}>
              <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4" onClick={e => e.stopPropagation()}>
                <div><h2 className="text-lg font-semibold text-slate-900">Create New User</h2><p className="text-sm text-slate-500 mt-0.5">This user will be able to log in with their email and password</p></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="block text-xs font-medium text-slate-600 mb-1">First Name</label><input value={newUser.first_name} onChange={e => setNewUser(p => ({ ...p, first_name: e.target.value }))} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-jai-primary" placeholder="John" /></div>
                  <div><label className="block text-xs font-medium text-slate-600 mb-1">Last Name</label><input value={newUser.last_name} onChange={e => setNewUser(p => ({ ...p, last_name: e.target.value }))} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-jai-primary" placeholder="Doe" /></div>
                </div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Username <span className="text-red-400">*</span></label><input value={newUser.username} onChange={e => setNewUser(p => ({ ...p, username: e.target.value }))} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-jai-primary" placeholder="johndoe" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Email <span className="text-red-400">*</span></label><input type="email" value={newUser.email} onChange={e => setNewUser(p => ({ ...p, email: e.target.value }))} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-jai-primary" placeholder="john@jaggaer.com" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Password <span className="text-red-400">*</span></label><input type="password" value={newUser.password} onChange={e => setNewUser(p => ({ ...p, password: e.target.value }))} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-jai-primary" placeholder="Min 6 characters" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
                  <select value={newUser.roles[0]} onChange={e => setNewUser(p => ({ ...p, roles: [e.target.value] }))} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-jai-primary">
                    <option value="viewer">Viewer</option><option value="agent_developer">Agent Developer</option><option value="platform_admin">Platform Admin</option>
                  </select>
                </div>
                {createUserError && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{createUserError}</p>}
                <div className="flex justify-end gap-2 pt-2">
                  <button onClick={() => setShowCreateUser(false)} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 cursor-pointer">Cancel</button>
                  <button onClick={handleCreateUser} disabled={creatingUser || !newUser.username || !newUser.email || !newUser.password} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover disabled:opacity-40 disabled:cursor-not-allowed">
                    {creatingUser ? "Creating..." : "Create User"}
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200">{["User", "Email", "Roles", "Status", ""].map(h => <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">{h}</th>)}</tr></thead>
              <tbody className="divide-y divide-slate-100">{users.map(u => (
                <tr key={u.user_id}>
                  <td className="px-4 py-3"><div className="flex items-center gap-2.5"><div className="w-8 h-8 rounded-lg bg-[#FDF1F5] flex items-center justify-center text-xs font-semibold text-jai-primary">{(u.display_name || u.username || "?").slice(0, 2).toUpperCase()}</div><div><div className="font-medium text-slate-900">{u.display_name || u.username}</div><div className="text-[11px] text-slate-400 font-mono">{u.user_id}</div></div></div></td>
                  <td className="px-4 py-3 text-slate-500">{u.email}</td>
                  <td className="px-4 py-3"><div className="flex gap-1 flex-wrap">{(u.roles || []).map(r => <Badge key={r} variant={r === "platform_admin" ? "brand" : "outline"}>{r}</Badge>)}</div></td>
                  <td className="px-4 py-3"><Badge variant={u.is_active ? "success" : "danger"}>{u.is_active ? "Active" : "Inactive"}</Badge></td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={async () => {
                      const ok = await confirmAction({ title: "Delete User", message: `Delete user "${u.display_name || u.username}"? This cannot be undone.` });
                      if (!ok) return;
                      try { await apiFetch(`${API}/users/${u.user_id}`, { method: "DELETE" }); toast.success("User deleted"); loadData(); } catch { toast.error("Failed to delete user"); }
                    }} className="text-slate-300 hover:text-red-500 cursor-pointer transition"><Trash2 size={14} /></button>
                  </td>
                </tr>
              ))}</tbody>
            </table>
            {users.length === 0 && <div className="text-sm text-slate-400 py-8 text-center">No users yet. Click "Add User" to create one.</div>}
          </div>
        </>
      )}

      {/* ── ROLES TAB ── */}
      {tab === "Roles" && !showCreateRole && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-500">{allRoles.length} roles ({DEFAULT_SYSTEM_ROLES.length} system · {customRoles.length} custom)</div>
            <button onClick={openCreateRole} className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover">
              <Plus size={14} /> Create Role
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {allRoles.map(role => {
              const counts = permCounts(role.permissions);
              return (
                <div key={role.name} className={cn("bg-white border rounded-xl p-4 transition", role.is_system ? "border-slate-200" : "border-slate-200 hover:border-slate-300")}>
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-slate-900">{role.name}</h3>
                        {role.is_system && <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500 font-medium">System</span>}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">{role.description}</div>
                    </div>
                    {!role.is_system && (
                      <div className="flex gap-1 shrink-0">
                        <button onClick={() => openEditRole(role)} className="text-slate-400 hover:text-slate-700 cursor-pointer p-1"><Edit3 size={12} /></button>
                        <button onClick={() => deleteRole(role.name)} className="text-slate-400 hover:text-red-500 cursor-pointer p-1"><Trash2 size={12} /></button>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 mt-3">
                    {counts.write > 0 && <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 font-medium">{counts.write} write</span>}
                    {counts.read > 0 && <span className="text-[11px] px-2 py-0.5 rounded-full bg-sky-50 text-sky-600 font-medium">{counts.read} read</span>}
                    {counts.none > 0 && <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-50 text-slate-400 font-medium">{counts.none} hidden</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── CREATE / EDIT ROLE ── */}
      {tab === "Roles" && showCreateRole && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <button onClick={() => setShowCreateRole(false)} className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer">
              <ChevronRight size={14} className="rotate-180" /> Back to Roles
            </button>
            <h2 className="text-sm font-semibold text-slate-900">{editingRole ? `Edit Role: ${editingRole}` : "Create Custom Role"}</h2>
          </div>

          {/* Role identity */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] text-slate-500 font-semibold uppercase block mb-1">Role Name *</label>
                <input value={roleName} onChange={e => setRoleName(e.target.value)} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="e.g. QA, Analyst, Manager" />
              </div>
              <div>
                <label className="text-[11px] text-slate-500 font-semibold uppercase block mb-1">Description</label>
                <input value={roleDesc} onChange={e => setRoleDesc(e.target.value)} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="What this role is for..." />
              </div>
            </div>
          </div>

          {/* Module permissions grid */}
          {PLATFORM_MODULES.map(section => {
            const sectionPerms = section.modules.map(m => rolePerms[m.id] || "none");
            const allSame = sectionPerms.every(p => p === sectionPerms[0]);
            return (
              <div key={section.section} className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-600 uppercase">{section.section}</h3>
                  <div className="flex gap-1">
                    {ACCESS_LEVELS.map(lvl => (
                      <button key={lvl.value} onClick={() => setSectionAccess(section.section, lvl.value)}
                        className={cn("text-[11px] px-2 py-0.5 rounded-full border cursor-pointer transition font-medium",
                          allSame && sectionPerms[0] === lvl.value ? lvl.color + " ring-1 ring-offset-1" : "bg-white border-slate-200 text-slate-400 hover:bg-slate-50")}>
                        All {lvl.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="divide-y divide-slate-100">
                  {section.modules.map(mod => (
                    <div key={mod.id} className="flex items-center justify-between px-4 py-2.5">
                      <div>
                        <div className="text-sm font-medium text-slate-800">{mod.label}</div>
                        <div className="text-[11px] text-slate-400">{mod.desc}</div>
                      </div>
                      <div className="flex gap-1">
                        {ACCESS_LEVELS.map(lvl => (
                          <button key={lvl.value} onClick={() => setRolePerms(prev => ({ ...prev, [mod.id]: lvl.value }))}
                            className={cn("text-[11px] px-2.5 py-1 rounded-lg border cursor-pointer transition font-medium",
                              rolePerms[mod.id] === lvl.value ? lvl.color : "bg-white border-slate-200 text-slate-400 hover:bg-slate-50")}>
                            {lvl.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Summary + Save */}
          <div className="flex items-center gap-3">
            <button onClick={saveRole} disabled={!roleName.trim()}
              className={cn("bg-jai-primary text-white rounded-lg px-5 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover flex items-center gap-1.5", !roleName.trim() && "opacity-50 cursor-not-allowed")}>
              <Save size={14} /> {editingRole ? "Update Role" : "Create Role"}
            </button>
            <button onClick={() => setShowCreateRole(false)} className="px-4 py-2 text-sm text-slate-500 hover:text-slate-700 cursor-pointer">Cancel</button>
            <div className="flex-1" />
            <div className="flex gap-2 text-[11px]">
              <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 font-medium">{Object.values(rolePerms).filter(v => v === "write").length} write</span>
              <span className="px-2 py-0.5 rounded-full bg-sky-50 text-sky-600 font-medium">{Object.values(rolePerms).filter(v => v === "read").length} read</span>
              <span className="px-2 py-0.5 rounded-full bg-slate-50 text-slate-400 font-medium">{Object.values(rolePerms).filter(v => v === "none").length} hidden</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
