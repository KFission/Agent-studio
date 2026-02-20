"use client";
import { useState, useEffect } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, Tabs, toast } from "../shared/StudioUI";
import {
  Settings as SettingsIcon, Save, Eye, EyeOff, Check, Plus, Trash2,
  RefreshCw, AlertTriangle, Box, Shield, Cloud, Database, KeyRound,
  ExternalLink, X, Copy,
} from "lucide-react";
import { PromotionPanel } from "../EnvironmentSwitcher";

export default function SettingsPage() {
  const [info, setInfo] = useState(null);
  const [monitoringStatus, setMonitoringStatus] = useState(null);
  const [tab, setTab] = useState("API Tokens");
  const [tokens, setTokens] = useState([]);
  const [newTokenName, setNewTokenName] = useState("");
  const [createdToken, setCreatedToken] = useState(null);
  const [tokenCopied, setTokenCopied] = useState(false);
  const [saved, setSaved] = useState(false);
  const [registeredModels, setRegisteredModels] = useState([]);

  // General settings state
  const [generalSettings, setGeneralSettings] = useState({
    platformName: "JAI Agent OS",
    defaultModel: "gemini-2.5-flash",
    maxAgentsPerUser: 25,
    maxWorkflowsPerUser: 50,
    sessionTimeoutMinutes: 480,
    enableAuditLog: true,
    auditRetentionDays: 90,
  });

  // Usage limits state
  const [limits, setLimits] = useState({
    globalRateLimitRPM: 120,
    perAgentRateLimitRPM: 60,
    maxTokensPerRequest: 16384,
    monthlyTokenBudget: 10000000,
    monthlyCostAlertUSD: 500,
    enableCostAlerts: true,
  });

  // Notification defaults state
  const [notifSettings, setNotifSettings] = useState({
    emailEnabled: true,
    emailFrom: "jai-platform@jaggaer.com",
    smtpHost: "",
    webhookDefaultTimeout: 30,
    slackWebhookUrl: "",
    teamsWebhookUrl: "",
    alertOnAgentError: true,
    alertOnBudgetThreshold: true,
    alertOnHumanReviewPending: true,
  });

  useEffect(() => {
    apiFetch(`${API}/info`).then(r => r.json()).then(setInfo).catch(() => {});
    apiFetch(`${API}/monitoring/status`).then(r => r.json()).then(setMonitoringStatus).catch(() => setMonitoringStatus({ status: "disconnected" }));
    apiFetch(`${API}/models`).then(r => r.json()).then(d => setRegisteredModels(d.models || [])).catch(() => {});
  }, []);
  const loadTokens = () => apiFetch(`${API}/api-tokens`).then(r => r.json()).then(d => setTokens(d.tokens || [])).catch(() => {});
  useEffect(() => { loadTokens(); }, []);

  const createToken = async () => {
    if (!newTokenName.trim()) return;
    const r = await apiFetch(`${API}/api-tokens`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newTokenName }) });
    const d = await r.json();
    setCreatedToken(d.token); setNewTokenName(""); loadTokens();
  };
  const revokeToken = async (id) => { await apiFetch(`${API}/api-tokens/${id}`, { method: "DELETE" }); loadTokens(); };
  const copyToken = (t) => { navigator.clipboard.writeText(t); setTokenCopied(true); setTimeout(() => setTokenCopied(false), 2000); };
  const showSaved = () => { setSaved(true); setTimeout(() => setSaved(false), 2000); };

  const SettingRow = ({ label, desc, children }) => (
    <div className="flex items-start justify-between gap-4 py-3 border-b border-slate-100 last:border-0">
      <div className="min-w-0">
        <div className="text-sm font-medium text-slate-800">{label}</div>
        {desc && <div className="text-xs text-slate-400 mt-0.5">{desc}</div>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );

  const Toggle = ({ checked, onChange }) => (
    <button onClick={() => onChange(!checked)} className={cn("w-9 h-5 rounded-full transition cursor-pointer relative", checked ? "bg-jai-primary" : "bg-slate-200")}>
      <div className={cn("absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all", checked ? "left-[18px]" : "left-0.5")} />
    </button>
  );

  return (
    <div className="p-6 animate-fade-up max-w-3xl mx-auto space-y-5">
      <div className="flex items-center gap-2"><SettingsIcon size={20} className="text-slate-500" /><h1 className="text-xl font-semibold text-slate-900">Settings</h1></div>
      <hr className="border-slate-200" />
      <Tabs tabs={["API Tokens", "General", "Usage Limits", "Notifications", "Environments", "Platform"]} active={tab} onChange={setTab} />

      {/* ── API TOKENS ── */}
      {tab === "API Tokens" && (
        <div className="space-y-4 mt-4">
          <div><h2 className="text-sm font-semibold text-slate-900">API Tokens</h2><p className="text-sm text-slate-500 mt-1">Create tokens to authenticate Agent & Workflow API calls. Tokens use <span className="font-mono text-[11px]">Bearer jai-tk-...</span> format.</p></div>

          {createdToken && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <div className="text-sm font-semibold text-amber-800 mb-1">Token created — copy it now!</div>
              <div className="text-xs text-amber-600 mb-2">This token will not be shown again.</div>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-white border border-amber-300 rounded-lg px-3 py-2 text-xs font-mono text-slate-900 select-all">{createdToken}</code>
                <button onClick={() => copyToken(createdToken)} className="bg-amber-600 text-white rounded-lg px-3 py-2 text-xs font-medium cursor-pointer flex items-center gap-1">
                  {tokenCopied ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
                </button>
              </div>
              <button onClick={() => setCreatedToken(null)} className="text-xs text-amber-600 hover:text-amber-800 mt-2 cursor-pointer">Dismiss</button>
            </div>
          )}

          <div className="flex items-center gap-2">
            <input value={newTokenName} onChange={e => setNewTokenName(e.target.value)} placeholder="Token name (e.g. CI/CD Pipeline)" className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" onKeyDown={e => e.key === "Enter" && createToken()} />
            <button onClick={createToken} disabled={!newTokenName.trim()} className={cn("bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer flex items-center gap-1", !newTokenName.trim() && "opacity-50")}>
              <Plus size={14} /> Create Token
            </button>
          </div>

          {tokens.length === 0 ? (
            <div className="text-sm text-slate-400 text-center py-6">No API tokens yet. Create one above.</div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-slate-200">{["Name", "Token", "Created", "Last Used", "Status", ""].map(h => <th key={h} className="text-left px-4 py-2.5 text-[11px] font-semibold text-slate-500 uppercase">{h}</th>)}</tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {tokens.map(t => (
                    <tr key={t.token_id}>
                      <td className="px-4 py-3 font-medium text-slate-900">{t.name}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">{t.token_prefix}</td>
                      <td className="px-4 py-3 text-xs text-slate-400">{t.created_at?.slice(0, 10)}</td>
                      <td className="px-4 py-3 text-xs text-slate-400">{t.last_used ? t.last_used.slice(0, 10) : "Never"}</td>
                      <td className="px-4 py-3"><Badge variant={t.status === "active" ? "success" : "danger"}>{t.status}</Badge></td>
                      <td className="px-4 py-3 text-right">
                        {t.status === "active" && <button onClick={() => revokeToken(t.token_id)} className="text-xs text-red-500 hover:text-red-700 cursor-pointer">Revoke</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── GENERAL ── */}
      {tab === "General" && (
        <div className="mt-4 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl px-5 py-1">
            <SettingRow label="Platform Name" desc="Displayed in the sidebar header">
              <input value={generalSettings.platformName} onChange={e => setGeneralSettings(p => ({ ...p, platformName: e.target.value }))} className="w-48 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right" />
            </SettingRow>
            <SettingRow label="Default Model" desc="Used when no model is explicitly selected">
              <select value={generalSettings.defaultModel} onChange={e => setGeneralSettings(p => ({ ...p, defaultModel: e.target.value }))} className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none">
                {registeredModels.length > 0 ? registeredModels.map(m => (
                  <option key={m.model_id} value={m.model_id}>{m.display_name}</option>
                )) : <option value="">No models registered</option>}
              </select>
            </SettingRow>
            <SettingRow label="Max Agents per User" desc="Limit how many agents a single user can create">
              <input type="number" min={1} max={200} value={generalSettings.maxAgentsPerUser} onChange={e => setGeneralSettings(p => ({ ...p, maxAgentsPerUser: parseInt(e.target.value) || 25 }))} className="w-20 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
            </SettingRow>
            <SettingRow label="Max Workflows per User" desc="Limit how many workflows a single user can create">
              <input type="number" min={1} max={500} value={generalSettings.maxWorkflowsPerUser} onChange={e => setGeneralSettings(p => ({ ...p, maxWorkflowsPerUser: parseInt(e.target.value) || 50 }))} className="w-20 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
            </SettingRow>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl px-5 py-1">
            <div className="py-2 mb-1"><h3 className="text-xs font-semibold text-slate-500 uppercase">Security</h3></div>
            <SettingRow label="Session Timeout" desc="Auto-logout after inactivity (minutes)">
              <input type="number" min={15} max={1440} value={generalSettings.sessionTimeoutMinutes} onChange={e => setGeneralSettings(p => ({ ...p, sessionTimeoutMinutes: parseInt(e.target.value) || 480 }))} className="w-20 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
            </SettingRow>
            <SettingRow label="Audit Logging" desc="Record all user actions and API calls">
              <Toggle checked={generalSettings.enableAuditLog} onChange={v => setGeneralSettings(p => ({ ...p, enableAuditLog: v }))} />
            </SettingRow>
            <SettingRow label="Audit Log Retention" desc="Days to keep audit records">
              <input type="number" min={7} max={365} value={generalSettings.auditRetentionDays} onChange={e => setGeneralSettings(p => ({ ...p, auditRetentionDays: parseInt(e.target.value) || 90 }))} className="w-20 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
            </SettingRow>
          </div>

          <button onClick={showSaved} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer flex items-center gap-1.5">
            <Save size={14} /> Save General Settings
            {saved && <span className="text-emerald-200 text-xs ml-2">Saved!</span>}
          </button>
        </div>
      )}

      {/* ── USAGE LIMITS ── */}
      {tab === "Usage Limits" && (
        <div className="mt-4 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl px-5 py-1">
            <div className="py-2 mb-1"><h3 className="text-xs font-semibold text-slate-500 uppercase">Rate Limiting</h3></div>
            <SettingRow label="Global Rate Limit" desc="Max requests per minute (platform-wide)">
              <div className="flex items-center gap-1.5">
                <input type="number" min={10} max={10000} value={limits.globalRateLimitRPM} onChange={e => setLimits(p => ({ ...p, globalRateLimitRPM: parseInt(e.target.value) || 120 }))} className="w-20 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
                <span className="text-[11px] text-slate-400">RPM</span>
              </div>
            </SettingRow>
            <SettingRow label="Per-Agent Rate Limit" desc="Max requests per minute for a single agent">
              <div className="flex items-center gap-1.5">
                <input type="number" min={1} max={1000} value={limits.perAgentRateLimitRPM} onChange={e => setLimits(p => ({ ...p, perAgentRateLimitRPM: parseInt(e.target.value) || 60 }))} className="w-20 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
                <span className="text-[11px] text-slate-400">RPM</span>
              </div>
            </SettingRow>
            <SettingRow label="Max Tokens per Request" desc="Maximum output tokens allowed in a single LLM call">
              <input type="number" min={256} max={128000} step={256} value={limits.maxTokensPerRequest} onChange={e => setLimits(p => ({ ...p, maxTokensPerRequest: parseInt(e.target.value) || 16384 }))} className="w-24 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
            </SettingRow>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl px-5 py-1">
            <div className="py-2 mb-1"><h3 className="text-xs font-semibold text-slate-500 uppercase">Budget Controls</h3></div>
            <SettingRow label="Monthly Token Budget" desc="Total tokens across all models (soft limit)">
              <div className="flex items-center gap-1.5">
                <input type="number" min={0} step={1000000} value={limits.monthlyTokenBudget} onChange={e => setLimits(p => ({ ...p, monthlyTokenBudget: parseInt(e.target.value) || 0 }))} className="w-32 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
                <span className="text-[11px] text-slate-400">tokens</span>
              </div>
            </SettingRow>
            <SettingRow label="Cost Alert Threshold" desc="Send alert when monthly spend exceeds this amount">
              <div className="flex items-center gap-1.5">
                <span className="text-sm text-slate-400">$</span>
                <input type="number" min={0} step={50} value={limits.monthlyCostAlertUSD} onChange={e => setLimits(p => ({ ...p, monthlyCostAlertUSD: parseInt(e.target.value) || 0 }))} className="w-24 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
              </div>
            </SettingRow>
            <SettingRow label="Enable Cost Alerts" desc="Notify admins when budget thresholds are hit">
              <Toggle checked={limits.enableCostAlerts} onChange={v => setLimits(p => ({ ...p, enableCostAlerts: v }))} />
            </SettingRow>
          </div>

          <button onClick={showSaved} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer flex items-center gap-1.5">
            <Save size={14} /> Save Usage Limits
            {saved && <span className="text-emerald-200 text-xs ml-2">Saved!</span>}
          </button>
        </div>
      )}

      {/* ── NOTIFICATIONS ── */}
      {tab === "Notifications" && (
        <div className="mt-4 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl px-5 py-1">
            <div className="py-2 mb-1"><h3 className="text-xs font-semibold text-slate-500 uppercase">Email</h3></div>
            <SettingRow label="Email Notifications" desc="Enable outbound email for alerts and approvals">
              <Toggle checked={notifSettings.emailEnabled} onChange={v => setNotifSettings(p => ({ ...p, emailEnabled: v }))} />
            </SettingRow>
            <SettingRow label="From Address" desc="Sender address for platform emails">
              <input value={notifSettings.emailFrom} onChange={e => setNotifSettings(p => ({ ...p, emailFrom: e.target.value }))} className="w-56 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" placeholder="noreply@company.com" />
            </SettingRow>
            <SettingRow label="SMTP Host" desc="Mail server hostname (leave blank for default)">
              <input value={notifSettings.smtpHost} onChange={e => setNotifSettings(p => ({ ...p, smtpHost: e.target.value }))} className="w-56 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" placeholder="smtp.company.com" />
            </SettingRow>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl px-5 py-1">
            <div className="py-2 mb-1"><h3 className="text-xs font-semibold text-slate-500 uppercase">Integrations</h3></div>
            <SettingRow label="Slack Webhook URL" desc="Send alerts to a Slack channel">
              <input value={notifSettings.slackWebhookUrl} onChange={e => setNotifSettings(p => ({ ...p, slackWebhookUrl: e.target.value }))} className="w-56 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" placeholder="https://hooks.slack.com/..." />
            </SettingRow>
            <SettingRow label="Teams Webhook URL" desc="Send alerts to a Microsoft Teams channel">
              <input value={notifSettings.teamsWebhookUrl} onChange={e => setNotifSettings(p => ({ ...p, teamsWebhookUrl: e.target.value }))} className="w-56 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" placeholder="https://outlook.office.com/..." />
            </SettingRow>
            <SettingRow label="Webhook Timeout" desc="Default timeout for webhook calls (seconds)">
              <input type="number" min={5} max={120} value={notifSettings.webhookDefaultTimeout} onChange={e => setNotifSettings(p => ({ ...p, webhookDefaultTimeout: parseInt(e.target.value) || 30 }))} className="w-20 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none text-right font-mono" />
            </SettingRow>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl px-5 py-1">
            <div className="py-2 mb-1"><h3 className="text-xs font-semibold text-slate-500 uppercase">Alert Triggers</h3></div>
            <SettingRow label="Agent Errors" desc="Alert when an agent execution fails">
              <Toggle checked={notifSettings.alertOnAgentError} onChange={v => setNotifSettings(p => ({ ...p, alertOnAgentError: v }))} />
            </SettingRow>
            <SettingRow label="Budget Threshold" desc="Alert when monthly spend hits the cost alert limit">
              <Toggle checked={notifSettings.alertOnBudgetThreshold} onChange={v => setNotifSettings(p => ({ ...p, alertOnBudgetThreshold: v }))} />
            </SettingRow>
            <SettingRow label="Human Review Pending" desc="Alert when a workflow is waiting for human approval">
              <Toggle checked={notifSettings.alertOnHumanReviewPending} onChange={v => setNotifSettings(p => ({ ...p, alertOnHumanReviewPending: v }))} />
            </SettingRow>
          </div>

          <button onClick={showSaved} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer flex items-center gap-1.5">
            <Save size={14} /> Save Notification Settings
            {saved && <span className="text-emerald-200 text-xs ml-2">Saved!</span>}
          </button>
        </div>
      )}

      {/* ── PLATFORM ── */}
      {tab === "Platform" && (
        <div className="mt-4 space-y-4">
          {/* Version & Status */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase">Platform Info</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {info && Object.entries(info).filter(([k]) => !["providers", "configured_providers", "available_tools", "available_models", "models", "prompt_templates", "webhooks", "websocket_connections"].includes(k)).map(([k, v]) => (
                <div key={k} className="bg-slate-50 rounded-lg px-3 py-2.5">
                  <div className="text-[11px] text-slate-400 uppercase font-semibold">{k.replace(/_/g, " ")}</div>
                  <div className="text-sm font-medium text-slate-800 mt-0.5">{typeof v === "boolean" ? (v ? "Yes" : "No") : typeof v === "object" ? JSON.stringify(v) : String(v)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Resource counts */}
          {info && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
              <h3 className="text-xs font-semibold text-slate-500 uppercase">Resources</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                  { label: "Models", value: info.models ?? registeredModels.length },
                  { label: "Prompts", value: info.prompt_templates ?? "—" },
                  { label: "Webhooks", value: info.webhooks ?? 0 },
                  { label: "WS Connections", value: info.websocket_connections ?? 0 },
                  { label: "API Tokens", value: tokens.length },
                ].map(s => (
                  <div key={s.label} className="bg-slate-50 rounded-lg px-3 py-2.5 text-center">
                    <div className="text-lg font-bold text-slate-800">{s.value}</div>
                    <div className="text-[11px] text-slate-400 uppercase font-semibold">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Infrastructure health */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase">Infrastructure</h3>
            <div className="space-y-2">
              {[
                { name: "Backend API", endpoint: API, status: info ? "connected" : "checking" },
                { name: "Monitoring (Langfuse)", endpoint: monitoringStatus?.host || "Internal", status: monitoringStatus?.connected ? "connected" : monitoringStatus?.enabled ? "checking" : "disconnected" },
                { name: "Redis (Memory)", endpoint: "localhost:6379", status: info ? "connected" : "unknown" },
                { name: "Vector Store (RAG)", endpoint: "ChromaDB", status: info ? "connected" : "unknown" },
              ].map(svc => (
                <div key={svc.name} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                  <div className="flex items-center gap-2.5">
                    <div className={cn("w-2 h-2 rounded-full", svc.status === "connected" ? "bg-emerald-500" : svc.status === "checking" ? "bg-amber-400 animate-pulse" : "bg-slate-300")} />
                    <div>
                      <div className="text-sm font-medium text-slate-800">{svc.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{svc.endpoint}</div>
                    </div>
                  </div>
                  <Badge variant={svc.status === "connected" ? "success" : svc.status === "checking" ? "warning" : "outline"}>{svc.status}</Badge>
                </div>
              ))}
            </div>
          </div>

          {/* AI Providers */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase">AI Providers</h3>
            {(() => {
              const provList = info?.providers || info?.configured_providers || [];
              const provArr = Array.isArray(provList) ? provList : [];
              const provMeta = {
                google: { label: "Google Gemini", color: "bg-blue-600" },
                openai: { label: "OpenAI", color: "bg-emerald-600" },
                anthropic: { label: "Anthropic", color: "bg-violet-600" },
                ollama: { label: "Ollama (Local)", color: "bg-amber-600" },
              };
              return provArr.length === 0 ? (
                <div className="text-sm text-slate-400 py-2">No AI providers configured. Go to <span className="font-medium text-slate-600">Model Library → Add Provider</span> to connect one.</div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {provArr.map(p => {
                    const meta = provMeta[p] || { label: p, color: "bg-slate-500" };
                    return (
                      <div key={p} className="flex items-center gap-3 bg-slate-50 rounded-lg px-4 py-3">
                        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold shrink-0", meta.color)}>
                          {meta.label[0]}
                        </div>
                        <div>
                          <div className="text-sm font-medium text-slate-800">{meta.label}</div>
                          <div className="text-[11px] text-slate-400 font-mono">{p}</div>
                        </div>
                        <Badge variant="success" className="ml-auto">active</Badge>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        </div>
      )}
      {/* ── ENVIRONMENTS ── */}
      {tab === "Environments" && (
        <div className="space-y-4 mt-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Environment Promotion & Management</h2>
            <p className="text-sm text-slate-500 mt-1">Approve or reject promotions, compare environments, and manage locks.</p>
          </div>
          <PromotionPanel />
        </div>
      )}
    </div>
  );
}
