"use client";
import { useState, useEffect, useCallback } from "react";
import apiFetch from "../lib/apiFetch";
import { cn } from "../lib/cn";
import {
  Bell, Mail, MessageSquare, Phone, Globe, Webhook, Check, X, Settings,
  RefreshCw, Send, ToggleLeft, ToggleRight, ChevronDown, ChevronRight,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

const CHANNEL_ICONS = {
  email: Mail,
  teams: MessageSquare,
  slack: MessageSquare,
  sms: Phone,
  whatsapp: Phone,
  webhook: Webhook,
};

const CHANNEL_COLORS = {
  email: { bg: "bg-sky-50", text: "text-sky-600", border: "border-sky-200" },
  teams: { bg: "bg-violet-50", text: "text-violet-600", border: "border-violet-200" },
  slack: { bg: "bg-emerald-50", text: "text-emerald-600", border: "border-emerald-200" },
  sms: { bg: "bg-amber-50", text: "text-amber-600", border: "border-amber-200" },
  whatsapp: { bg: "bg-green-50", text: "text-green-600", border: "border-green-200" },
  webhook: { bg: "bg-slate-50", text: "text-slate-600", border: "border-slate-200" },
};

function ConfigField({ label, value, onChange, type = "text", placeholder = "" }) {
  return (
    <div>
      <label className="text-[11px] font-semibold text-slate-500 uppercase block mb-1">{label}</label>
      <input
        type={type}
        value={value || ""}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-jai-primary transition"
      />
    </div>
  );
}

const CONFIG_FIELDS = {
  email: [
    { key: "smtp_host", label: "SMTP Host", placeholder: "smtp.jaggaer.com" },
    { key: "smtp_port", label: "SMTP Port", placeholder: "587", type: "number" },
    { key: "from_address", label: "From Address", placeholder: "notifications@jaggaer.com" },
    { key: "use_tls", label: "Use TLS", type: "toggle" },
  ],
  teams: [
    { key: "webhook_url", label: "Incoming Webhook URL", placeholder: "https://outlook.office.com/webhook/..." },
    { key: "tenant_id", label: "Azure Tenant ID", placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" },
    { key: "channel_id", label: "Channel ID", placeholder: "19:xxxxxx@thread.tacv2" },
  ],
  slack: [
    { key: "webhook_url", label: "Webhook URL", placeholder: "https://hooks.slack.com/services/..." },
    { key: "channel", label: "Channel", placeholder: "#procurement-approvals" },
    { key: "bot_token", label: "Bot Token", placeholder: "xoxb-..." },
  ],
  sms: [
    { key: "account_sid", label: "Twilio Account SID", placeholder: "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
    { key: "auth_token", label: "Auth Token", placeholder: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
    { key: "from_number", label: "From Number", placeholder: "+1234567890" },
    { key: "messaging_service_sid", label: "Messaging Service SID (optional)", placeholder: "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
  ],
  whatsapp: [
    { key: "account_sid", label: "Twilio Account SID", placeholder: "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
    { key: "auth_token", label: "Auth Token", placeholder: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
    { key: "from_number", label: "WhatsApp From Number", placeholder: "whatsapp:+14155238886" },
  ],
  webhook: [
    { key: "url", label: "Webhook URL", placeholder: "https://your-service.com/webhook" },
    { key: "method", label: "HTTP Method", placeholder: "POST" },
    { key: "auth_type", label: "Auth Type", placeholder: "none / bearer / api_key" },
  ],
};

export default function NotificationChannelsPage() {
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [testResults, setTestResults] = useState({});

  const load = useCallback(() => {
    setLoading(true);
    apiFetch(`${API}/notification-channels`).then(r => r.json()).then(d => {
      setChannels(d.channels || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const toggleEnabled = async (ch) => {
    const r = await apiFetch(`${API}/notification-channels/${ch.channel_id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !ch.enabled }),
    });
    const updated = await r.json();
    setChannels(prev => prev.map(c => c.channel_id === ch.channel_id ? { ...c, enabled: updated.enabled } : c));
  };

  const updateConfig = async (channelId, key, value) => {
    setChannels(prev => prev.map(c => {
      if (c.channel_id !== channelId) return c;
      return { ...c, config: { ...c.config, [key]: value } };
    }));
  };

  const saveConfig = async (ch) => {
    await apiFetch(`${API}/notification-channels/${ch.channel_id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config: ch.config }),
    });
  };

  const testChannel = async (channelId) => {
    setTestResults(prev => ({ ...prev, [channelId]: "sending" }));
    const r = await apiFetch(`${API}/notification-channels/${channelId}/test`, { method: "POST" });
    const res = await r.json();
    setTestResults(prev => ({ ...prev, [channelId]: res.success ? "success" : "error" }));
    setTimeout(() => setTestResults(prev => ({ ...prev, [channelId]: null })), 3000);
  };

  if (loading) return <div className="p-6 text-slate-400 text-sm">Loading notification channels...</div>;

  return (
    <div className="p-6 animate-fade-up max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Notification Channels</h1>
          <p className="text-sm text-slate-500 mt-0.5">Configure how Human-in-the-Loop approval notifications are delivered</p>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 cursor-pointer bg-white">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      <div className="bg-gradient-to-r from-[#1B2A4A] to-jai-primary rounded-xl p-5 text-white">
        <div className="flex items-center gap-3 mb-2">
          <Bell size={20} />
          <h2 className="text-sm font-semibold">HITL Notification Delivery</h2>
        </div>
        <p className="text-xs text-pink-100 leading-relaxed">
          When an agent pauses for human approval (Human Review node in workflows), notifications are sent
          through enabled channels below. Developers select channels per workflow node. Multiple channels can fire simultaneously.
        </p>
      </div>

      <div className="space-y-3">
        {channels.map(ch => {
          const Icon = CHANNEL_ICONS[ch.type] || Globe;
          const colors = CHANNEL_COLORS[ch.type] || CHANNEL_COLORS.webhook;
          const fields = CONFIG_FIELDS[ch.type] || [];
          const isExpanded = expanded === ch.channel_id;

          return (
            <div key={ch.channel_id} className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div
                className="flex items-center gap-3 px-5 py-4 cursor-pointer hover:bg-slate-50/50 transition"
                onClick={() => setExpanded(isExpanded ? null : ch.channel_id)}
              >
                <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center", colors.bg)}>
                  <Icon size={16} className={colors.text} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-slate-900">{ch.name}</div>
                  <div className="text-[11px] text-slate-400">{ch.description}</div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={e => { e.stopPropagation(); toggleEnabled(ch); }}
                    className={cn("w-10 h-5 rounded-full relative transition cursor-pointer", ch.enabled ? "bg-jai-primary" : "bg-slate-200")}
                  >
                    <div className={cn("w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all shadow-sm", ch.enabled ? "left-5.5 right-0.5" : "left-0.5")}
                      style={{ left: ch.enabled ? 22 : 2 }} />
                  </button>
                  <span className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full", ch.enabled ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-400")}>
                    {ch.enabled ? "Active" : "Off"}
                  </span>
                  {isExpanded ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
                </div>
              </div>

              {isExpanded && (
                <div className="border-t border-slate-100 px-5 py-4 bg-slate-50/50">
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    {fields.map(f => {
                      if (f.type === "toggle") {
                        return (
                          <div key={f.key} className="flex items-center gap-2">
                            <label className="text-[11px] font-semibold text-slate-500 uppercase">{f.label}</label>
                            <button
                              onClick={() => updateConfig(ch.channel_id, f.key, !ch.config[f.key])}
                              className={cn("w-8 h-4 rounded-full relative transition cursor-pointer", ch.config[f.key] ? "bg-jai-primary" : "bg-slate-200")}
                            >
                              <div className="w-3 h-3 bg-white rounded-full absolute top-0.5 transition-all shadow-sm"
                                style={{ left: ch.config[f.key] ? 16 : 2 }} />
                            </button>
                          </div>
                        );
                      }
                      return (
                        <ConfigField
                          key={f.key}
                          label={f.label}
                          value={ch.config[f.key]}
                          onChange={v => updateConfig(ch.channel_id, f.key, f.type === "number" ? parseInt(v) || 0 : v)}
                          type={f.type || "text"}
                          placeholder={f.placeholder}
                        />
                      );
                    })}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => saveConfig(ch)}
                      className="bg-slate-900 text-white rounded-lg px-3 py-1.5 text-xs font-medium cursor-pointer hover:bg-slate-800 flex items-center gap-1.5"
                    >
                      <Check size={12} /> Save Config
                    </button>
                    <button
                      onClick={() => testChannel(ch.channel_id)}
                      disabled={testResults[ch.channel_id] === "sending"}
                      className="border border-slate-200 bg-white text-slate-700 rounded-lg px-3 py-1.5 text-xs font-medium cursor-pointer hover:bg-slate-50 flex items-center gap-1.5 disabled:opacity-40"
                    >
                      <Send size={12} />
                      {testResults[ch.channel_id] === "sending" ? "Sending..." :
                       testResults[ch.channel_id] === "success" ? "✓ Sent!" :
                       testResults[ch.channel_id] === "error" ? "✗ Failed" : "Send Test"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
