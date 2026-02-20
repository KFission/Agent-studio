"use client";
import { useState, useRef, useEffect } from "react";
import useAuthStore from "../stores/authStore";
import apiFetch from "../lib/apiFetch";
import useEnvStore from "../stores/envStore";
import dynamic from "next/dynamic";
import { ProdWarningBanner, UatWarningBanner, UnsavedChangesDialog, ProdEditConfirmDialog } from "./EnvironmentSwitcher";
import { cn } from "../lib/cn";
import { PageTransition } from "./ui";
import { ToastContainer, ConfirmDialog, toast, API } from "./shared/StudioUI";
import {
  MessageSquare, Inbox as InboxIcon, Users as UsersIcon, Bot, Wrench,
  Box, BarChart3, Building2, Link2, KeyRound,
  Settings as SettingsIcon, Search, Plus, Check, X, Activity,
  ChevronRight, ChevronDown, Database,
  FolderKanban, Workflow, History,
  Bell, HelpCircle, PanelLeft, LogOut,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════
// DYNAMIC IMPORTS — each page lazy-loaded for code splitting
// ═══════════════════════════════════════════════════════════════════

const DynLoadingSkeleton = () => <div className="p-6 max-w-6xl mx-auto space-y-5"><div className="flex items-center justify-between"><div className="space-y-2"><div className="animate-pulse rounded-lg bg-slate-100 h-5 w-40" /><div className="animate-pulse rounded-lg bg-slate-100 h-3 w-64" /></div></div><div className="grid grid-cols-1 md:grid-cols-3 gap-4">{[1,2,3].map(i => <div key={i} className="bg-white border border-slate-200/80 rounded-xl p-5 space-y-3"><div className="flex items-center gap-3"><div className="animate-pulse rounded-xl bg-slate-100 w-10 h-10" /><div className="flex-1 space-y-1.5"><div className="animate-pulse rounded-lg bg-slate-100 h-4 w-2/3" /><div className="animate-pulse rounded-lg bg-slate-100 h-3 w-full" /></div></div></div>)}</div></div>;
const dyn = (loader) => dynamic(loader, { ssr: false, loading: DynLoadingSkeleton });

// Previously-extracted external components
const WorkflowsPage = dyn(() => import("./WorkflowBuilder"));
const ToolsPage = dyn(() => import("./ToolsPage"));
const ExecutiveDashboard = dyn(() => import("./ExecutiveDashboard"));
const KnowledgeBasesPage = dyn(() => import("./KnowledgeBasesPage"));
const NotificationChannelsPage = dyn(() => import("./NotificationChannelsPage"));
const PipelinesPage = dyn(() => import("./PipelineBuilder"));
const NewPromptsPage = dyn(() => import("./PromptsPage"));
const LLMPlaygroundPage = dyn(() => import("./PlaygroundPage"));
const NewMonitoringPage = dyn(() => import("./MonitoringPage"));

// Newly code-split pages (were inline)
const DashboardPage = dyn(() => import("./pages/DashboardPage"));
const ChatPage = dyn(() => import("./pages/ChatPage"));
const AgentsPage = dyn(() => import("./pages/AgentsPage"));
const AgentBuilderPage = dyn(() => import("./pages/AgentBuilderPage"));
const GuardrailsPage = dyn(() => import("./pages/GuardrailsPage"));
const InboxPage = dyn(() => import("./pages/InboxPage"));
const EvalPage = dyn(() => import("./pages/EvalPage"));
const RAGPage = dyn(() => import("./pages/RAGPage"));
const ModelsPage = dyn(() => import("./pages/ModelsPage"));
// LLMLogsPage removed — merged into MonitoringPage
const UsersPage = dyn(() => import("./pages/UsersPage"));
const SettingsPage = dyn(() => import("./pages/SettingsPage"));
const GroupsPage = dyn(() => import("./pages/GroupsPage"));
const OrganizationsPage = dyn(() => import("./pages/OrganizationsPage"));
const AuditTrailPage = dyn(() => import("./pages/AuditTrailPage"));
const ApiTokensPage = dyn(() => import("./pages/ApiTokensPage"));
const TemplateGalleryPage = dyn(() => import("./pages/TemplateGalleryPage"));
const ConnectorsPage = dyn(() => import("./pages/ConnectorsPage"));

// ═══════════════════════════════════════════════════════════════════
// COMMAND PALETTE (⌘K)
// ═══════════════════════════════════════════════════════════════════

function CommandPalette({ open, onClose, onNavigate, pages }) {
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  // Recency tracking via localStorage
  const getRecent = () => { try { return JSON.parse(localStorage.getItem("jai_cmd_recent") || "[]"); } catch { return []; } };
  const addRecent = (id) => { try { const r = getRecent().filter(x => x !== id); r.unshift(id); localStorage.setItem("jai_cmd_recent", JSON.stringify(r.slice(0, 8))); } catch {} };

  useEffect(() => { if (open) { setQuery(""); setActiveIdx(0); setTimeout(() => inputRef.current?.focus(), 50); } }, [open]);
  if (!open) return null;

  const allItems = [
    { id: "_create_agent", label: "Create New Agent", type: "action", section: "Actions" },
    { id: "_create_workflow", label: "Create New Workflow", type: "action", section: "Actions" },
    { id: "_create_pipeline", label: "Create New Pipeline", type: "action", section: "Actions" },
    ...Object.entries(pages).map(([id, label]) => ({ id, label, type: "page", section: "Pages" })),
  ];

  const recentIds = getRecent();
  const recentItems = recentIds.map(id => allItems.find(i => i.id === id)).filter(Boolean).map(i => ({ ...i, section: "Recent" }));

  let filtered;
  if (query) {
    const q = query.toLowerCase();
    filtered = allItems.filter(i => i.label.toLowerCase().includes(q));
  } else {
    // Show Recent (if any), then Actions, then Pages
    const seen = new Set(recentItems.map(i => i.id));
    filtered = [...recentItems, ...allItems.filter(i => !seen.has(i.id))];
  }

  const grouped = {};
  filtered.forEach(i => { if (!grouped[i.section]) grouped[i.section] = []; grouped[i.section].push(i); });
  const flatItems = filtered;

  const handleSelect = (item) => {
    addRecent(item.id);
    onClose();
    if (item.type === "page") onNavigate(item.id);
    else if (item.id === "_create_agent") onNavigate("AgentBuilder");
    else if (item.id === "_create_workflow") onNavigate("Workflows");
    else if (item.id === "_create_pipeline") onNavigate("Orchestrator");
  };

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActiveIdx(i => Math.min(i + 1, flatItems.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActiveIdx(i => Math.max(i - 1, 0)); }
    else if (e.key === "Enter" && flatItems[activeIdx]) { e.preventDefault(); handleSelect(flatItems[activeIdx]); }
  };

  // Scroll active item into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${activeIdx}"]`);
    if (el) el.scrollIntoView({ block: "nearest" });
  }, [activeIdx]);

  let flatIdx = -1;

  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center pt-[18vh] bg-black/30 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden border border-slate-200 animate-scale-in" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100">
          <Search size={16} className="text-slate-400 shrink-0" />
          <input ref={inputRef} value={query} onChange={e => { setQuery(e.target.value); setActiveIdx(0); }} onKeyDown={onKeyDown}
            placeholder="Search pages, actions..."
            className="flex-1 text-sm text-slate-900 outline-none bg-transparent placeholder:text-slate-400" />
          <kbd className="text-[11px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded font-mono">ESC</kbd>
        </div>
        <div className="max-h-[340px] overflow-y-auto py-2" ref={listRef}>
          {Object.entries(grouped).map(([section, items]) => (
            <div key={section}>
              <div className="px-4 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{section}</div>
              {items.map(item => {
                flatIdx++;
                const idx = flatIdx;
                return (
                  <button key={item.id + section} data-idx={idx} onClick={() => handleSelect(item)}
                    onMouseEnter={() => setActiveIdx(idx)}
                    className={cn("w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 cursor-pointer transition text-left",
                      activeIdx === idx ? "bg-jai-primary-light text-jai-primary" : "hover:bg-slate-50")}>
                    <span className="flex-1">{item.label}</span>
                    {item.type === "action" && <span className="text-[11px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">action</span>}
                    {activeIdx === idx && <span className="text-[11px] text-slate-300 font-mono">↵</span>}
                  </button>
                );
              })}
            </div>
          ))}
          {filtered.length === 0 && <div className="px-4 py-6 text-sm text-slate-400 text-center">No results for &quot;{query}&quot;</div>}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// SIDEBAR NAVIGATION CONFIG
// ═══════════════════════════════════════════════════════════════════

const NAV_SECTIONS = [
  {
    label: "Build",
    items: [
      { id: "Agents", icon: Bot, mosaicIcon: "atom", label: "Agents", tip: "Create, configure, and deploy AI agents" },
      { id: "Workflows", icon: Workflow, mosaicIcon: "network", label: "Workflows", tip: "Visual drag-and-drop workflow builder" },
      { id: "KnowledgeBases", icon: Database, mosaicIcon: "data", label: "Knowledge", tip: "RAG document collections for grounded responses" },
      { id: "Tools", icon: Wrench, mosaicIcon: "connect", label: "Tools", tip: "API tools, functions, and integrations available to agents" },
    ],
  },
  {
    label: "Test",
    items: [
      { id: "Chat", icon: MessageSquare, mosaicIcon: "chat", label: "Playground", tip: "Test and interact with your agents in real time" },
      { id: "Eval", icon: BarChart3, mosaicIcon: "assessment", label: "Eval Studio", tip: "Side-by-side LLM benchmarking across models" },
    ],
  },
  {
    label: "Operate",
    items: [
      { id: "Inbox", icon: InboxIcon, mosaicIcon: "notification", label: "Approvals", tip: "Human-in-the-loop review queue for agent decisions" },
      { id: "Monitoring", icon: Activity, mosaicIcon: "dashboard", label: "Monitoring", tip: "Logs, traces, cost analytics, and usage metering" },
      { id: "Models", icon: Box, mosaicIcon: "platform", label: "Models", tip: "Connect AI providers and manage model access" },
    ],
  },
];

// Admin sub-pages — rendered inside AdminHub
const ADMIN_PAGES = [
  { id: "Organizations", icon: Building2, label: "Organizations", tip: "Manage orgs, tenants, and multi-org settings" },
  { id: "Groups", icon: FolderKanban, label: "Teams", tip: "Organize users into teams with shared access" },
  { id: "Users", icon: UsersIcon, label: "Users & Roles", tip: "Manage user accounts and role permissions" },
  { id: "ApiTokens", icon: KeyRound, label: "API Tokens", tip: "Generate and manage API keys" },
  { id: "NotificationChannels", icon: Bell, label: "Notifications", tip: "Alert channels — email, Slack, Teams, webhooks" },
  { id: "Connectors", icon: Link2, label: "Connectors", tip: "Connect to external systems — Slack, Jira, SAP" },
  { id: "AuditTrail", icon: History, label: "Audit Trail", tip: "Immutable log of all platform actions" },
  { id: "Settings", icon: SettingsIcon, label: "Settings", tip: "Platform configuration and usage limits" },
];

// ═══════════════════════════════════════════════════════════════════
// ORG SWITCHER
// ═══════════════════════════════════════════════════════════════════

function WorkspaceContext() {
  const { currentEnv, switchEnv, permissions } = useEnvStore();
  const [orgs, setOrgs] = useState([]);
  const [activeOrg, setActiveOrg] = useState(null);
  const [open, setOpen] = useState(false);
  const triggerRef = useRef(null);
  const panelRef = useRef(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  useEffect(() => {
    apiFetch(`${API}/tenants`).then(r => r.json()).then(d => {
      const list = d.tenants || [];
      setOrgs(list);
      if (list.length && !activeOrg) setActiveOrg(list[0]);
    }).catch(() => {
      const fallback = [{ tenant_id: "org-default", name: "Default Org", slug: "default", tier: "enterprise", is_active: true }];
      setOrgs(fallback); setActiveOrg(fallback[0]);
    });
  }, []);

  // Position the portal panel next to the trigger
  useEffect(() => {
    if (open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPos({ top: rect.bottom + 6, left: rect.left });
    }
  }, [open]);

  // Close on click-outside
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target) && triggerRef.current && !triggerRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const TIER_COLORS = { free: "text-slate-500 bg-slate-100", pro: "text-blue-600 bg-blue-50", enterprise: "text-violet-600 bg-violet-50" };
  const envMeta = { dev: { label: "Dev", dot: "bg-slate-400", bg: "bg-slate-50" }, qa: { label: "QA", dot: "bg-amber-400", bg: "bg-amber-50" }, uat: { label: "UAT", dot: "bg-blue-400", bg: "bg-blue-50" }, prod: { label: "Prod", dot: "bg-emerald-500", bg: "bg-emerald-50" } };
  const env = envMeta[currentEnv] || envMeta.dev;

  return (
    <>
      {/* Compact trigger — one row showing Org + Env */}
      <button
        ref={triggerRef}
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-center gap-2 px-2.5 py-2 rounded-xl text-left cursor-pointer transition-all duration-150",
          open ? "bg-slate-100 ring-1 ring-slate-200" : "hover:bg-slate-50"
        )}
      >
        <div className="w-6 h-6 rounded-md bg-gradient-to-br from-jai-primary to-jai-primary/60 flex items-center justify-center text-[11px] font-bold text-white shrink-0">
          {activeOrg?.name?.charAt(0) || "O"}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-semibold text-slate-800 truncate leading-tight">{activeOrg?.name || "Select Org"}</div>
          <div className="flex items-center gap-1 mt-0.5">
            <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", env.dot)} />
            <span className="text-[11px] text-slate-500">{env.label}</span>
          </div>
        </div>
        <ChevronDown size={12} className={cn("text-slate-400 shrink-0 transition-transform duration-150", open && "rotate-180")} />
      </button>

      {/* Portal-based popover — renders at body level, never clipped */}
      {open && typeof document !== "undefined" && require("react-dom").createPortal(
        <div ref={panelRef} className="fixed z-[100] animate-scale-in" style={{ top: pos.top, left: pos.left, minWidth: 280 }}>
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 overflow-hidden">
            {/* ── Organization section ── */}
            <div className="px-3 pt-3 pb-1">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Organization</div>
              <div className="space-y-0.5 max-h-48 overflow-y-auto scrollbar-thin">
                {orgs.map(org => (
                  <button key={org.tenant_id} onClick={() => { setActiveOrg(org); toast.info(`Switched to ${org.name}`); }}
                    className={cn("w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left cursor-pointer transition",
                      activeOrg?.tenant_id === org.tenant_id ? "bg-jai-primary-light" : "hover:bg-slate-50")}>
                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-jai-primary to-jai-primary/60 flex items-center justify-center text-[11px] font-bold text-white shrink-0">
                      {org.name?.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-900 truncate">{org.name}</div>
                      <div className="text-[11px] text-slate-400">{org.slug}</div>
                    </div>
                    <span className={cn("text-[11px] font-semibold px-1.5 py-0.5 rounded-full uppercase", TIER_COLORS[org.tier] || TIER_COLORS.free)}>{org.tier}</span>
                    {activeOrg?.tenant_id === org.tenant_id && <Check size={12} className="text-jai-primary shrink-0" />}
                  </button>
                ))}
              </div>
              <button className="w-full flex items-center gap-2 px-2.5 py-1.5 mt-1 text-xs text-slate-400 hover:text-slate-700 hover:bg-slate-50 rounded-lg cursor-pointer transition">
                <Plus size={12} /> New Organization
              </button>
            </div>

            <div className="mx-3 my-1 h-px bg-slate-100" />

            {/* ── Environment section ── */}
            <div className="px-3 pt-1 pb-3">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Environment</div>
              <div className="grid grid-cols-4 gap-1.5">
                {Object.entries(envMeta).map(([id, meta]) => {
                  const isCurrent = currentEnv === id;
                  const perm = permissions[id];
                  const disabled = !perm?.canView;
                  return (
                    <button
                      key={id}
                      onClick={() => { if (!disabled && !isCurrent) { switchEnv(id); } }}
                      disabled={disabled}
                      className={cn(
                        "flex flex-col items-center gap-1 py-2.5 px-1 rounded-lg text-center cursor-pointer transition-all duration-150",
                        isCurrent ? "bg-slate-900 text-white shadow-sm" : disabled ? "opacity-30 cursor-not-allowed" : "hover:bg-slate-50 text-slate-600"
                      )}
                    >
                      <span className={cn("w-2 h-2 rounded-full", isCurrent ? "bg-white" : meta.dot)} />
                      <span className="text-[11px] font-semibold">{meta.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════
// TOP HEADER BAR
// ═══════════════════════════════════════════════════════════════════

function TopHeader({ page, setPage, inboxCount, onOpenCmdPalette }) {
  const { user, logout } = useAuthStore();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  return (
    <div className="h-12 bg-white border-b border-slate-200 flex items-center px-4 gap-4 shrink-0 z-30">
      {/* Left: brand */}
      <div className="flex items-center gap-2 shrink-0 cursor-pointer" onClick={() => setPage("Dashboard")}>
        <img src="https://www.jaggaer.com/wp-content/uploads/JAGGAER-Logo-Red-228x24.png" alt="JAGGAER" className="h-4 object-contain shrink-0" />
        <span className="text-[11px] font-semibold text-slate-400 tracking-wide uppercase whitespace-nowrap">JAI Agent OS</span>
      </div>

      {/* Center: global search with ⌘K hint */}
      <div className="flex-1 flex justify-center max-w-xl mx-auto">
        <button
          onClick={onOpenCmdPalette}
          className="relative w-full max-w-md flex items-center gap-2.5 bg-slate-50 border border-slate-200 rounded-lg py-1.5 pl-3 pr-3 text-sm text-slate-400 hover:border-slate-300 hover:bg-slate-100/50 transition cursor-pointer text-left"
        >
          <Search size={14} className="shrink-0" />
          <span className="flex-1">Search pages, actions...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 text-[11px] text-slate-400 bg-white border border-slate-200 px-1.5 py-0.5 rounded font-mono shadow-sm">⌘K</kbd>
        </button>
      </div>

      {/* Right: notification bell, help, user avatar */}
      <div className="flex items-center gap-1 shrink-0">
        <button onClick={() => setPage("Inbox")} className="relative w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 cursor-pointer transition">
          <Bell size={17} />
          {inboxCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 flex items-center justify-center rounded-full bg-jai-danger text-[11px] font-bold text-white">{inboxCount > 9 ? "9+" : inboxCount}</span>
          )}
        </button>
        <button onClick={() => window.open(`${API}/docs`, '_blank')} title="API Documentation (Swagger)" className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 cursor-pointer transition">
          <HelpCircle size={17} />
        </button>
        <div className="ml-1 relative">
          <button onClick={() => setUserMenuOpen(!userMenuOpen)} className="flex items-center gap-2 cursor-pointer group">
            <div className="w-8 h-8 rounded-full bg-jai-primary flex items-center justify-center text-xs font-bold text-white ring-2 ring-white group-hover:ring-slate-200 transition">
              {user?.avatar || "U"}
            </div>
          </button>
          {userMenuOpen && (
            <div className="absolute right-0 top-10 w-56 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50 animate-scale-in">
              <div className="px-4 py-2 border-b border-slate-100">
                <div className="text-sm font-semibold text-slate-900 truncate">{user?.displayName}</div>
                <div className="text-xs text-slate-500 truncate">{user?.email}</div>
              </div>
              <button onClick={() => { setUserMenuOpen(false); logout(); }} className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition cursor-pointer">
                <LogOut size={15} />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════════════════════════

function Sidebar({ page, setPage, collapsed, setCollapsed, inboxCount }) {
  const [expandedSections, setExpandedSections] = useState(["Build", "Test"]);
  const toggleSection = (label) => setExpandedSections(prev => prev.includes(label) ? prev.filter(s => s !== label) : [...prev, label]);
  const isAdminPage = ADMIN_PAGES.some(p => p.id === page);

  return (
    <div className={cn("h-full bg-white border-r border-slate-200/60 flex flex-col transition-all duration-200 overflow-hidden shrink-0", collapsed ? "w-14 min-w-14" : "w-56 min-w-56")}>
      {/* Workspace context — org + env in one compact trigger */}
      {!collapsed && (
        <div className="px-2 pt-2.5 pb-1 border-b border-slate-100 mb-1">
          <WorkspaceContext />
        </div>
      )}
      {/* Dashboard link */}
      <div className="px-2 pt-2">
        <div onClick={() => setPage("Dashboard")} title={collapsed ? "Dashboard" : undefined}
          className={cn("flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer text-sm transition",
            page === "Dashboard" ? "bg-jai-primary-light text-jai-primary font-medium" : "text-slate-500 hover:bg-slate-50 hover:text-slate-800")}>
          <img src="/icons/home.svg" alt="" width={18} height={18} className="shrink-0 opacity-70" />
          {!collapsed && <span className="truncate">Dashboard</span>}
        </div>
      </div>
      {/* Nav sections — lean: Build, Test, Operate */}
      <div className="flex-1 px-2 py-1 flex flex-col gap-0.5 overflow-y-auto scrollbar-thin">
        {NAV_SECTIONS.map(section => (
          <div key={section.label} className="mt-3 first:mt-1">
            {!collapsed && (
              <div className="flex items-center justify-between px-2.5 py-1.5 cursor-pointer group" onClick={() => toggleSection(section.label)}>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider group-hover:text-slate-500 transition">{section.label}</span>
                {expandedSections.includes(section.label) ? <ChevronDown size={12} className="text-slate-300" /> : <ChevronRight size={12} className="text-slate-300" />}
              </div>
            )}
            {(collapsed || expandedSections.includes(section.label)) && section.items.map(n => {
              const active = page === n.id;
              const IconComp = n.icon;
              return (
                <div key={n.id} onClick={() => setPage(n.id)} title={collapsed ? `${n.label} — ${n.tip || ""}` : (n.tip || n.label)}
                  className={cn("flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer text-[13px] transition-all duration-150 relative",
                    active ? "bg-jai-primary-light text-jai-primary font-medium" : "text-slate-500 hover:bg-slate-50 hover:text-slate-700")}>
                  {n.mosaicIcon ? (
                    <img src={`/icons/${n.mosaicIcon}.svg`} alt="" width={17} height={17} className="shrink-0 opacity-70" style={{ filter: active ? "none" : "grayscale(0.3)" }} />
                  ) : (
                    <IconComp size={17} className="shrink-0" />
                  )}
                  {!collapsed && <span className="truncate">{n.label}</span>}
                  {n.id === "Inbox" && inboxCount > 0 && (
                    <span className={cn("absolute flex items-center justify-center text-[11px] font-bold text-white bg-amber-500 rounded-full",
                      collapsed ? "top-0.5 right-0.5 w-4 h-4" : "ml-auto w-5 h-5 static")}>
                      {inboxCount}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      {/* Admin — single destination at bottom */}
      <div className="px-2 pb-1 shrink-0">
        <div onClick={() => setPage("AdminHub")} title={collapsed ? "Admin — Settings, Users, Tokens, Audit" : "Settings, Users, Tokens, Audit"}
          className={cn("flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer text-[13px] transition-all duration-150",
            (page === "AdminHub" || isAdminPage) ? "bg-jai-primary-light text-jai-primary font-medium" : "text-slate-500 hover:bg-slate-50 hover:text-slate-700")}>
          <SettingsIcon size={17} className="shrink-0" />
          {!collapsed && <span className="truncate">Admin</span>}
        </div>
      </div>
      {/* Collapse toggle */}
      <div className="px-3 py-2.5 border-t border-slate-100 shrink-0">
        <button onClick={() => setCollapsed(!collapsed)} className="flex items-center gap-2.5 text-slate-400 hover:text-slate-700 cursor-pointer transition w-full px-1">
          {collapsed ? <ChevronRight size={16} /> : <><PanelLeft size={16} /><span className="text-xs">Collapse</span></>}
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// MAIN APP — JAI Agent OS
// ═══════════════════════════════════════════════════════════════════

const PAGE_TITLES = {
  Dashboard: "Dashboard", AdminHub: "Admin", UsageMetering: "Usage & Metering", Chat: "Playground", Inbox: "Approvals", Agents: "Agents", AgentBuilder: "Agent Builder", Workflows: "Workflow Builder", Tools: "Tools",
  Guardrails: "Guardrails", RAG: "RAG", KnowledgeBases: "Knowledge", Orchestrator: "Pipelines", Models: "Models", Prompts: "Prompt Studio",
  Eval: "Eval Studio", Monitoring: "Monitoring", Templates: "Marketplace",
  NotificationChannels: "Notifications", Connectors: "Connectors", Users: "Users & Roles", Settings: "Settings", Groups: "Teams",
  Organizations: "Organizations", AuditTrail: "Audit Trail", ApiTokens: "API Tokens",
};

export default function AgentStudio() {
  const [page, setPage] = useState("Dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [inboxCount, setInboxCount] = useState(0);
  const [chatAgent, setChatAgent] = useState(null);
  const [editAgent, setEditAgent] = useState(null);
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false);

  const navigateTo = (p, data) => { if (p !== "AgentBuilder") setEditAgent(null); setPage(p); };

  // Fetch inbox count on mount
  useEffect(() => {
    apiFetch(`${API}/inbox?status=pending`).then(r => r.json()).then(d => setInboxCount((d.items || []).length)).catch(() => {});
  }, []);

  // Browser tab title with badge count
  useEffect(() => {
    const title = PAGE_TITLES[page] || "JAI Agent OS";
    document.title = inboxCount > 0 ? `(${inboxCount}) ${title} — JAI Agent OS` : `${title} — JAI Agent OS`;
  }, [page, inboxCount]);

  // Global keyboard shortcuts: ⌘K command palette, Esc close
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); setCmdPaletteOpen(prev => !prev); }
      if (e.key === "Escape") setCmdPaletteOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="flex flex-col w-full h-screen font-sans text-slate-900 bg-white overflow-hidden">
      {/* Top header bar — full width */}
      <TopHeader page={page} setPage={setPage} inboxCount={inboxCount} onOpenCmdPalette={() => setCmdPaletteOpen(true)} />
      {/* Environment warning banners */}
      <ProdWarningBanner />
      <UatWarningBanner />
      {/* Global dialogs */}
      <UnsavedChangesDialog />
      <ProdEditConfirmDialog />
      <ToastContainer />
      <ConfirmDialog />
      <CommandPalette open={cmdPaletteOpen} onClose={() => setCmdPaletteOpen(false)} onNavigate={navigateTo} pages={PAGE_TITLES} />
      {/* Body: sidebar + content */}
      <div className="flex flex-1 overflow-hidden min-h-0">
        <Sidebar page={page} setPage={navigateTo} collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} inboxCount={inboxCount} />
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* Page content — with animated transitions */}
          <div className={cn("flex-1 bg-jai-surface-secondary", (page === "Workflows" || page === "AgentBuilder" || page === "KnowledgeBases" || page === "Orchestrator" || page === "Chat") ? "overflow-hidden" : "overflow-auto")}>
            <PageTransition pageKey={page}>
              {page === "Dashboard" && <ExecutiveDashboard />}
              {page === "UsageMetering" && <DashboardPage setPage={setPage} />}
              {page === "Chat" && <ChatPage initialAgent={chatAgent} />}
              {page === "Inbox" && <InboxPage onCountUpdate={setInboxCount} />}
              {page === "Agents" && <AgentsPage setPage={setPage} setChatAgent={setChatAgent} setEditAgent={setEditAgent} />}
              {page === "AgentBuilder" && <AgentBuilderPage key={editAgent?.agent_id || 'new'} setPage={setPage} editAgent={editAgent} />}
              {page === "Guardrails" && <GuardrailsPage />}
              {page === "Templates" && <TemplateGalleryPage setPage={setPage} setEditAgent={setEditAgent} />}
              {page === "Tools" && <ToolsPage />}
              {page === "RAG" && <RAGPage />}
              {page === "KnowledgeBases" && <KnowledgeBasesPage />}
              {page === "Workflows" && <WorkflowsPage />}
              {page === "Orchestrator" && <PipelinesPage />}
              {page === "Models" && <ModelsPage />}
              {page === "Prompts" && <NewPromptsPage onNavigate={setPage} />}
              {page === "Eval" && <EvalPage />}
              {page === "Monitoring" && <NewMonitoringPage />}
              {/* Admin Hub — grid of admin sub-pages */}
              {page === "AdminHub" && (
                <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-up">
                  <div>
                    <h1 className="text-xl font-semibold text-slate-900">Admin</h1>
                    <p className="text-sm text-slate-500 mt-1">Platform configuration, access control, and compliance</p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {ADMIN_PAGES.map(ap => {
                      const Icon = ap.icon;
                      return (
                        <div key={ap.id} onClick={() => navigateTo(ap.id)}
                          className="flex items-center gap-3.5 bg-white border border-slate-200/80 rounded-xl p-4 hover:shadow-md hover:border-slate-300 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group">
                          <div className="w-9 h-9 rounded-lg bg-slate-50 flex items-center justify-center shrink-0 group-hover:bg-jai-primary-light transition">
                            <Icon size={17} className="text-slate-400 group-hover:text-jai-primary transition" />
                          </div>
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-slate-900">{ap.label}</div>
                            <div className="text-xs text-slate-400 mt-0.5 truncate">{ap.tip}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {page === "Organizations" && <OrganizationsPage />}
              {page === "AuditTrail" && <AuditTrailPage />}
              {page === "ApiTokens" && <ApiTokensPage />}
              {page === "Groups" && <GroupsPage />}
              {page === "NotificationChannels" && <NotificationChannelsPage />}
              {page === "Connectors" && <ConnectorsPage />}
              {page === "Users" && <UsersPage />}
              {page === "Settings" && <SettingsPage />}
            </PageTransition>
          </div>
        </div>
      </div>
    </div>
  );
}
