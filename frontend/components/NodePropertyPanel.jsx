"use client";
import { useState, useMemo, useCallback } from "react";
import { cn } from "../lib/cn";
import {
  getNodeDef, validateNodeConfig, shouldShowField, RETRY_POLICY_SCHEMA,
  NODE_CATEGORIES,
} from "../stores/nodeRegistry";
import {
  Settings, Trash2, ChevronDown, ChevronRight, AlertCircle, AlertTriangle,
  X, Plus, Info, Copy, Braces,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════
// ICON MAP — resolve string icon names from registry to Lucide components
// ═══════════════════════════════════════════════════════════════════
import {
  PlayCircle, Globe, CalendarClock, GitBranch, Shuffle, Repeat, GitFork,
  Merge, Clock, ShieldAlert, ArrowRightLeft, Code2, ShieldCheck, Plug,
  Bell, MessageSquare, Brain, Bot, Shield, UserCheck, Ticket, LogOut,
  FileText,
} from "lucide-react";

const ICON_MAP = {
  PlayCircle, Globe, CalendarClock, GitBranch, Shuffle, Repeat, GitFork,
  Merge, Clock, ShieldAlert, ArrowRightLeft, Code2, ShieldCheck, Plug,
  Bell, MessageSquare, Brain, Bot, Shield, UserCheck, Ticket, LogOut,
  FileText, Settings,
};

export function resolveIcon(iconName) {
  return ICON_MAP[iconName] || Settings;
}

// ═══════════════════════════════════════════════════════════════════
// FIELD RENDERERS — one per field type
// ═══════════════════════════════════════════════════════════════════

function FieldLabel({ field }) {
  return (
    <div className="flex items-center gap-1 mb-0.5">
      <label className="text-[11px] text-slate-500 font-semibold uppercase tracking-wide">{field.label}</label>
      {field.required && <span className="text-red-400 text-[11px]">*</span>}
      {field.desc && (
        <span className="group relative ml-0.5">
          <Info size={9} className="text-slate-300 cursor-help" />
          <span className="absolute bottom-full left-0 mb-1 hidden group-hover:block bg-slate-800 text-white text-[11px] px-2 py-1 rounded shadow-lg whitespace-nowrap z-50 max-w-[240px] leading-tight">{field.desc}</span>
        </span>
      )}
    </div>
  );
}

function TextField({ field, value, onChange }) {
  return (
    <div>
      <FieldLabel field={field} />
      <input
        value={value ?? field.default ?? ""}
        onChange={e => onChange(e.target.value)}
        placeholder={field.placeholder || ""}
        readOnly={field.readonly}
        className={cn(
          "w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none transition",
          field.readonly ? "bg-slate-50 text-slate-400" : "bg-white focus:border-slate-400",
          field.templated && "font-mono text-[11px]"
        )}
      />
    </div>
  );
}

function NumberField({ field, value, onChange }) {
  return (
    <div>
      <FieldLabel field={field} />
      <input
        type="number"
        value={value ?? field.default ?? 0}
        onChange={e => onChange(parseFloat(e.target.value) || 0)}
        min={field.min}
        max={field.max}
        step={field.step || 1}
        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-slate-400 transition"
      />
    </div>
  );
}

function RangeField({ field, value, onChange }) {
  const v = value ?? field.default ?? field.min ?? 0;
  return (
    <div>
      <div className="flex items-center justify-between mb-0.5">
        <FieldLabel field={field} />
        <span className="text-[11px] text-slate-500 font-mono tabular-nums">{v}</span>
      </div>
      <input
        type="range"
        value={v}
        onChange={e => onChange(parseFloat(e.target.value))}
        min={field.min ?? 0}
        max={field.max ?? 1}
        step={field.step ?? 0.1}
        className="w-full accent-jai-primary"
      />
    </div>
  );
}

function BooleanField({ field, value, onChange }) {
  const checked = value ?? field.default ?? false;
  return (
    <label className="flex items-center gap-2.5 py-1 cursor-pointer group">
      <div
        onClick={() => onChange(!checked)}
        className={cn(
          "w-8 h-[18px] rounded-full relative transition-colors cursor-pointer",
          checked ? "bg-jai-primary" : "bg-slate-200"
        )}
      >
        <div className={cn("absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white shadow transition-all", checked ? "left-[17px]" : "left-0.5")} />
      </div>
      <span className="text-xs text-slate-700 group-hover:text-slate-900">{field.label}</span>
      {field.desc && (
        <span className="group/tip relative ml-0.5">
          <Info size={9} className="text-slate-300 cursor-help" />
          <span className="absolute bottom-full left-0 mb-1 hidden group-hover/tip:block bg-slate-800 text-white text-[11px] px-2 py-1 rounded shadow-lg whitespace-nowrap z-50 max-w-[240px]">{field.desc}</span>
        </span>
      )}
    </label>
  );
}

function EnumField({ field, value, onChange }) {
  return (
    <div>
      <FieldLabel field={field} />
      <select
        value={value ?? field.default ?? ""}
        onChange={e => onChange(e.target.value)}
        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-slate-400 transition"
      >
        {field.required && <option value="">Select...</option>}
        {(field.options || []).map(o => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </div>
  );
}

function TextareaField({ field, value, onChange }) {
  return (
    <div>
      <FieldLabel field={field} />
      <textarea
        value={value ?? field.default ?? ""}
        onChange={e => onChange(e.target.value)}
        rows={field.rows || 3}
        placeholder={field.placeholder || ""}
        className={cn(
          "w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none resize-y focus:border-slate-400 transition",
          field.templated && "font-mono text-[11px]"
        )}
      />
    </div>
  );
}

function CodeField({ field, value, onChange }) {
  return (
    <div>
      <FieldLabel field={field} />
      <textarea
        value={value ?? field.default ?? ""}
        onChange={e => onChange(e.target.value)}
        rows={field.rows || 8}
        spellCheck={false}
        className="w-full bg-[#1e293b] text-emerald-300 border border-slate-600 rounded-lg px-3 py-2 text-[11px] outline-none resize-y font-mono leading-relaxed"
      />
    </div>
  );
}

function JsonField({ field, value, onChange }) {
  const [error, setError] = useState(null);
  const handleChange = (v) => {
    onChange(v);
    try {
      if (v.trim()) JSON.parse(v);
      setError(null);
    } catch (e) {
      setError("Invalid JSON");
    }
  };
  return (
    <div>
      <FieldLabel field={field} />
      <textarea
        value={value ?? (typeof field.default === "string" ? field.default : JSON.stringify(field.default, null, 2)) ?? ""}
        onChange={e => handleChange(e.target.value)}
        rows={field.rows || 4}
        readOnly={field.readonly}
        spellCheck={false}
        className={cn(
          "w-full border rounded-lg px-3 py-1.5 text-[11px] outline-none resize-y font-mono",
          error ? "border-red-300 bg-red-50/30" : "border-slate-200 bg-slate-50",
          field.readonly && "text-slate-400"
        )}
      />
      {error && <div className="text-[11px] text-red-400 mt-0.5">{error}</div>}
    </div>
  );
}

function TagsField({ field, value, onChange }) {
  const [input, setInput] = useState("");
  const tags = Array.isArray(value) ? value : (field.default || []);

  const addTag = () => {
    const trimmed = input.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
    }
    setInput("");
  };

  const removeTag = (t) => onChange(tags.filter(x => x !== t));

  return (
    <div>
      <FieldLabel field={field} />
      <div className="flex flex-wrap gap-1 mb-1">
        {tags.map(t => (
          <span key={t} className="inline-flex items-center gap-0.5 bg-slate-100 text-slate-700 text-[11px] px-2 py-0.5 rounded-full">
            {t}
            <button onClick={() => removeTag(t)} className="text-slate-400 hover:text-red-500 cursor-pointer"><X size={8} /></button>
          </span>
        ))}
      </div>
      {field.options ? (
        <select
          value=""
          onChange={e => { if (e.target.value && !tags.includes(e.target.value)) onChange([...tags, e.target.value]); }}
          className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none"
        >
          <option value="">Add...</option>
          {field.options.filter(o => !tags.includes(o)).map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <div className="flex gap-1">
          <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addTag())}
            placeholder="Type and press Enter" className="flex-1 bg-white border border-slate-200 rounded-lg px-2 py-1 text-[11px] outline-none" />
          <button onClick={addTag} className="text-[11px] bg-slate-100 text-slate-600 rounded-lg px-2 py-1 hover:bg-slate-200 cursor-pointer"><Plus size={10} /></button>
        </div>
      )}
    </div>
  );
}

function KeyValueField({ field, value, onChange }) {
  const pairs = useMemo(() => {
    if (typeof value === "object" && value && !Array.isArray(value)) return Object.entries(value);
    return [];
  }, [value]);

  const update = (newPairs) => {
    const obj = {};
    newPairs.forEach(([k, v]) => { if (k) obj[k] = v; });
    onChange(obj);
  };

  const addPair = () => update([...pairs, ["", ""]]);
  const removePair = (idx) => update(pairs.filter((_, i) => i !== idx));
  const setPair = (idx, key, val) => {
    const np = [...pairs];
    np[idx] = [key, val];
    update(np);
  };

  return (
    <div>
      <FieldLabel field={field} />
      <div className="space-y-1">
        {pairs.map(([k, v], i) => (
          <div key={i} className="flex gap-1">
            <input value={k} onChange={e => setPair(i, e.target.value, v)} placeholder="key" className="flex-1 bg-white border border-slate-200 rounded px-2 py-1 text-[11px] outline-none font-mono" />
            <input value={v} onChange={e => setPair(i, k, e.target.value)} placeholder="value" className="flex-1 bg-white border border-slate-200 rounded px-2 py-1 text-[11px] outline-none font-mono" />
            <button onClick={() => removePair(i)} className="text-slate-300 hover:text-red-400 cursor-pointer"><X size={12} /></button>
          </div>
        ))}
      </div>
      <button onClick={addPair} className="mt-1 text-[11px] text-slate-500 hover:text-slate-700 flex items-center gap-0.5 cursor-pointer"><Plus size={10} /> Add pair</button>
    </div>
  );
}

function DatetimeField({ field, value, onChange }) {
  return (
    <div>
      <FieldLabel field={field} />
      <input
        type="datetime-local"
        value={value ?? ""}
        onChange={e => onChange(e.target.value)}
        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-slate-400 transition"
      />
    </div>
  );
}

function RetryPolicyField({ field, value, onChange }) {
  const [expanded, setExpanded] = useState(false);
  const policy = typeof value === "object" && value ? value : {};
  const set = (k, v) => onChange({ ...policy, [k]: v });

  return (
    <div>
      <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-1.5 text-[11px] text-slate-500 font-semibold uppercase tracking-wide cursor-pointer hover:text-slate-700">
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        {field.label}
      </button>
      {expanded && (
        <div className="mt-1.5 ml-2 pl-2 border-l-2 border-slate-100 space-y-2">
          {RETRY_POLICY_SCHEMA.map(f => (
            <div key={f.key}>
              {f.type === "number" && <NumberField field={f} value={policy[f.key]} onChange={v => set(f.key, v)} />}
              {f.type === "enum" && <EnumField field={f} value={policy[f.key]} onChange={v => set(f.key, v)} />}
              {f.type === "boolean" && <BooleanField field={f} value={policy[f.key]} onChange={v => set(f.key, v)} />}
              {f.type === "tags" && <TagsField field={f} value={policy[f.key]} onChange={v => set(f.key, v)} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// FIELD DISPATCHER — maps field.type to the correct renderer
// ═══════════════════════════════════════════════════════════════════

function FieldRenderer({ field, value, onChange, config }) {
  if (!shouldShowField(field, config)) return null;

  const props = { field, value, onChange };
  switch (field.type) {
    case "text": return <TextField {...props} />;
    case "number": return <NumberField {...props} />;
    case "range": return <RangeField {...props} />;
    case "boolean": return <BooleanField {...props} />;
    case "enum": return <EnumField {...props} />;
    case "textarea": return <TextareaField {...props} />;
    case "code": return <CodeField {...props} />;
    case "json": return <JsonField {...props} />;
    case "tags": return <TagsField {...props} />;
    case "keyvalue": return <KeyValueField {...props} />;
    case "datetime": return <DatetimeField {...props} />;
    case "retryPolicy": return <RetryPolicyField {...props} />;
    default: return <TextField {...props} />;
  }
}

// ═══════════════════════════════════════════════════════════════════
// MAIN PANEL COMPONENT
// ═══════════════════════════════════════════════════════════════════

export default function NodePropertyPanel({ node, onUpdate, onDelete, agents, tools, knowledgeBases }) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  if (!node) {
    return (
      <div className="w-80 bg-white border-l border-slate-200 flex flex-col items-center justify-center p-6 text-center flex-shrink-0">
        <Settings size={24} className="text-slate-300 mb-2" />
        <div className="text-sm text-slate-400">Select a node to configure</div>
        <div className="text-[11px] text-slate-300 mt-1">Click a node on the canvas to view and edit its properties</div>
      </div>
    );
  }

  const def = getNodeDef(node.type);
  if (!def) {
    return (
      <div className="w-80 bg-white border-l border-slate-200 flex flex-col items-center justify-center p-6 text-center flex-shrink-0">
        <AlertCircle size={24} className="text-amber-400 mb-2" />
        <div className="text-sm text-slate-500">Unknown node type: {node.type}</div>
      </div>
    );
  }

  const config = node.data?.config || {};
  const Icon = resolveIcon(def.icon);
  const catDef = NODE_CATEGORIES.find(c => c.id === def.category);

  const setConfig = (key, val) => {
    onUpdate(node.id, {
      ...node.data,
      config: { ...config, [key]: val },
    });
  };

  const setLabel = (val) => {
    onUpdate(node.id, { ...node.data, label: val });
  };

  const validation = validateNodeConfig(node.type, config);
  const hasErrors = validation.errors.length > 0;
  const hasWarnings = validation.warnings.length > 0;

  const mainFields = def.fields.filter(f => !f.advanced);
  const advancedFields = def.fields.filter(f => f.advanced);

  // Inject dynamic options for agent/KB fields
  const patchField = (field) => {
    if (field.dynamic && field.key === "agentId" && agents?.length) {
      return { ...field, options: agents.map(a => a.agent_id || a.name), type: "enum" };
    }
    if (field.dynamic && field.key === "knowledgeBase" && knowledgeBases?.length) {
      return { ...field, options: knowledgeBases.map(k => k.kb_id || k.name), type: "enum" };
    }
    return field;
  };

  return (
    <div className="w-80 bg-white border-l border-slate-200 flex flex-col flex-shrink-0 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white shadow-sm flex-shrink-0" style={{ background: def.color }}>
            <Icon size={14} />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-slate-900 truncate">{def.label}</div>
            <div className="text-[11px] uppercase tracking-wide font-medium" style={{ color: catDef?.color || "#64748b" }}>{catDef?.label || def.category}</div>
          </div>
        </div>
        <button onClick={() => onDelete(node.id)} className="text-slate-300 hover:text-red-500 cursor-pointer p-1 rounded hover:bg-red-50 transition"><Trash2 size={14} /></button>
      </div>

      {/* Validation badges */}
      {(hasErrors || hasWarnings) && (
        <div className="px-4 py-2 border-b border-slate-100 space-y-1 flex-shrink-0">
          {validation.errors.map((e, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[11px] text-red-600 bg-red-50 rounded px-2 py-1">
              <AlertCircle size={10} className="shrink-0" /> {e.message}
            </div>
          ))}
          {validation.warnings.map((w, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[11px] text-amber-600 bg-amber-50 rounded px-2 py-1">
              <AlertTriangle size={10} className="shrink-0" /> {w.message}
            </div>
          ))}
        </div>
      )}

      {/* Scrollable form */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* Label field — always present */}
        <div>
          <label className="text-[11px] text-slate-500 font-semibold uppercase tracking-wide">Label</label>
          <input
            value={node.data?.label || ""}
            onChange={e => setLabel(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-slate-400 transition mt-0.5"
          />
        </div>

        {/* Main fields */}
        {mainFields.map(f => {
          const pf = patchField(f);
          return (
            <FieldRenderer
              key={pf.key}
              field={pf}
              value={config[pf.key]}
              onChange={v => setConfig(pf.key, v)}
              config={config}
            />
          );
        })}

        {/* Advanced accordion */}
        {advancedFields.length > 0 && (
          <div className="border-t border-slate-100 pt-2">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-1.5 text-[11px] text-slate-400 font-semibold uppercase tracking-wide cursor-pointer hover:text-slate-600 w-full"
            >
              {showAdvanced ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
              Advanced ({advancedFields.length})
            </button>
            {showAdvanced && (
              <div className="mt-2 space-y-3">
                {advancedFields.map(f => {
                  const pf = patchField(f);
                  return (
                    <FieldRenderer
                      key={pf.key}
                      field={pf}
                      value={config[pf.key]}
                      onChange={v => setConfig(pf.key, v)}
                      config={config}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Notes — always at bottom if not already in fields */}
        {!def.fields.find(f => f.key === "notes") && (
          <div>
            <label className="text-[11px] text-slate-500 font-semibold uppercase tracking-wide">Notes</label>
            <textarea
              value={node.data?.notes || ""}
              onChange={e => onUpdate(node.id, { ...node.data, notes: e.target.value })}
              rows={2}
              placeholder="Optional notes..."
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none resize-none focus:border-slate-400 transition mt-0.5"
            />
          </div>
        )}

        {/* Output data preview */}
        {node.data?._outputData && Object.keys(node.data._outputData).length > 0 && (
          <div className="border-t border-slate-100 pt-2">
            <label className="text-[11px] text-slate-500 font-semibold uppercase tracking-wide flex items-center gap-1">
              <Braces size={10} /> Output Data
            </label>
            <pre className="mt-1 text-[11px] font-mono text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-2 max-h-32 overflow-auto whitespace-pre-wrap">
              {JSON.stringify(node.data._outputData, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
