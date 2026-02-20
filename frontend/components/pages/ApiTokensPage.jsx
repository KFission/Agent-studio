"use client";
import { useState, useEffect } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, EmptyState, toast, confirmAction, relativeTime } from "../shared/StudioUI";
import { KeyRound, Plus, Copy, Trash2, Check, Eye, EyeOff } from "lucide-react";

export default function ApiTokensPage() {
  const [tokens, setTokens] = useState([
    { id: "tok-1", name: "Production CI/CD", prefix: "jai-pk-...a3f2", created_at: new Date(Date.now() - 86400000 * 30).toISOString(), last_used: new Date(Date.now() - 3600000).toISOString(), scope: "full", status: "active" },
    { id: "tok-2", name: "Staging Environment", prefix: "jai-sk-...b7e1", created_at: new Date(Date.now() - 86400000 * 14).toISOString(), last_used: new Date(Date.now() - 86400000).toISOString(), scope: "read", status: "active" },
    { id: "tok-3", name: "Mobile App Integration", prefix: "jai-mk-...c9d4", created_at: new Date(Date.now() - 86400000 * 7).toISOString(), last_used: null, scope: "agents_only", status: "active" },
  ]);
  const [showCreate, setShowCreate] = useState(false);
  const [newToken, setNewToken] = useState(null);
  const [form, setForm] = useState({ name: "", scope: "full" });

  const SCOPE_LABELS = { full: "Full Access", read: "Read Only", agents_only: "Agents Only" };
  const SCOPE_COLORS = { full: "danger", read: "info", agents_only: "warning" };

  const createToken = () => {
    const token = `jai-${form.scope === "full" ? "pk" : form.scope === "read" ? "sk" : "mk"}-${crypto.randomUUID().replace(/-/g, "").slice(0, 32)}`;
    const entry = { id: `tok-${Date.now()}`, name: form.name, prefix: token.slice(0, 7) + "..." + token.slice(-4), created_at: new Date().toISOString(), last_used: null, scope: form.scope, status: "active" };
    setTokens(prev => [entry, ...prev]);
    setNewToken(token);
    setShowCreate(false);
    setForm({ name: "", scope: "full" });
    toast.success("API token created — copy it now, you won't see it again");
  };

  const revokeToken = async (id) => {
    const ok = await confirmAction({ title: "Revoke API Token", message: "Any applications using this token will immediately lose access. This cannot be undone.", confirmLabel: "Revoke Token" });
    if (!ok) return;
    setTokens(prev => prev.filter(t => t.id !== id));
    toast.success("Token revoked");
  };

  return (
    <div className="p-6 animate-fade-up max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div><h1 className="text-xl font-semibold text-slate-900">API Tokens</h1><p className="text-sm text-slate-500 mt-1">Manage API keys for agent-as-a-service endpoints</p></div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} /> New Token</button>
      </div>

      {newToken && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2"><Check size={14} className="text-emerald-600" /><span className="text-sm font-semibold text-emerald-800">Token Created — Copy Now</span></div>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-white border border-emerald-200 rounded-lg px-3 py-2 text-sm font-mono text-slate-900 select-all">{newToken}</code>
            <button onClick={() => { navigator.clipboard.writeText(newToken); toast.success("Token copied"); }} className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium cursor-pointer flex items-center gap-1"><Copy size={13} /> Copy</button>
          </div>
          <div className="text-xs text-emerald-600 mt-2">This token won't be shown again. Store it securely.</div>
          <button onClick={() => setNewToken(null)} className="text-xs text-emerald-500 hover:underline mt-1 cursor-pointer">Dismiss</button>
        </div>
      )}

      {showCreate && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
          <h3 className="text-base font-semibold text-slate-900">Generate API Token</h3>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs text-slate-500">Token Name</label><input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 mt-1" placeholder="e.g. CI/CD Pipeline" /></div>
            <div><label className="text-xs text-slate-500">Scope</label>
              <select value={form.scope} onChange={e => setForm(p => ({ ...p, scope: e.target.value }))} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300 focus:ring-1 focus:ring-slate-200 mt-1">
                <option value="full">Full Access — read, write, execute</option>
                <option value="read">Read Only — list and inspect</option>
                <option value="agents_only">Agents Only — chat completions</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2 justify-end pt-1">
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer hover:bg-slate-50">Cancel</button>
            <button onClick={createToken} disabled={!form.name} className={cn("bg-slate-800 text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-slate-900", !form.name && "opacity-50")}>Generate Token</button>
          </div>
        </div>
      )}

      {tokens.length === 0 ? (
        <EmptyState icon={<KeyRound size={24} />} illustration="locked" title="No API tokens" description="Generate tokens to integrate agents into your applications via the OpenAI-compatible API." />
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="divide-y divide-slate-50">
            {tokens.map(t => (
              <div key={t.id} className="flex items-center gap-4 px-5 py-4">
                <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center shrink-0"><KeyRound size={16} className="text-slate-500" /></div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-900">{t.name}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <code className="text-xs text-slate-400 font-mono">{t.prefix}</code>
                    <Badge variant={SCOPE_COLORS[t.scope]}>{SCOPE_LABELS[t.scope]}</Badge>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs text-slate-500">Created {relativeTime(t.created_at)}</div>
                  <div className="text-[11px] text-slate-300">{t.last_used ? `Last used ${relativeTime(t.last_used)}` : "Never used"}</div>
                </div>
                <button onClick={() => revokeToken(t.id)} className="text-xs text-red-400 hover:text-red-600 border border-red-200 rounded-lg px-2.5 py-1 cursor-pointer hover:bg-red-50 transition">Revoke</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Usage Example</h3>
        <pre className="text-xs font-mono text-slate-500 bg-white border border-slate-200 rounded-lg p-3 overflow-x-auto">{`curl -X POST ${API.replace("localhost:8080", "your-domain.com")}/v1/chat/completions \\
  -H "Authorization: Bearer jai-pk-your-token-here" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "Hello"}]}'`}</pre>
      </div>
    </div>
  );
}
