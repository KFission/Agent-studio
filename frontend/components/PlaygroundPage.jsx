"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import {
  Play, Save, RotateCcw, ChevronDown, ExternalLink, Zap, Clock, Hash,
  Loader2, Copy, Plus, X, Settings2, GripVertical, MoreVertical, FileText
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

function apiFetch(url, opts = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("jai_token") : null;
  return fetch(url, { ...opts, headers: { ...opts.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) } });
}

function cn(...c) { return c.filter(Boolean).join(" "); }

/* ── helpers ── */
const extractVars = (messages) => {
  const all = messages.map(m => m.content).join(" ");
  return [...new Set((all.match(/\{\{(\w+)\}\}/g) || []).map(v => v.slice(2, -2)))];
};

const makeDefaultWindow = (id) => ({
  id,
  modelId: "",
  messages: [
    { role: "system", content: "You are a helpful assistant.", _id: `${id}-s` },
    { role: "user", content: "", _id: `${id}-u` },
  ],
  temperature: 0.7,
  maxTokens: 1024,
  output: null,
  running: false,
  error: null,
});

/* ════════════════════════════════════════════════════════════════════════
   PlaygroundPage — Langfuse-style multi-window playground
   ════════════════════════════════════════════════════════════════════════ */
export default function PlaygroundPage() {
  const [windows, setWindows] = useState([makeDefaultWindow(1)]);
  const [models, setModels] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [showPromptPicker, setShowPromptPicker] = useState(null); // windowId or null
  const [showSave, setShowSave] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [saveTags, setSaveTags] = useState("");
  const nextIdRef = useRef(2);

  /* ── load models + prompts ── */
  useEffect(() => {
    apiFetch(`${API}/models`).then(r => r.json()).then(d => setModels(d.models || [])).catch(() => {});
    apiFetch(`${API}/prompts?limit=100`).then(r => r.json()).then(d => setPrompts(d.data || [])).catch(() => {});
  }, []);

  /* ── pick up prompt from PromptsPage via localStorage ── */
  useEffect(() => {
    try {
      const raw = localStorage.getItem("jai_playground_prompt");
      if (!raw) return;
      localStorage.removeItem("jai_playground_prompt");
      const data = JSON.parse(raw);
      const msgs = [];
      if (data.type === "chat" && Array.isArray(data.prompt)) {
        data.prompt.forEach((m, i) => msgs.push({ role: m.role, content: m.content, _id: `loaded-${i}` }));
      } else {
        msgs.push({ role: "system", content: typeof data.prompt === "string" ? data.prompt : JSON.stringify(data.prompt), _id: "loaded-0" });
        msgs.push({ role: "user", content: "", _id: "loaded-1" });
      }
      setWindows(prev => {
        const w = { ...prev[0], messages: msgs };
        if (data.config?.model) w.modelId = data.config.model;
        if (data.config?.temperature !== undefined) w.temperature = data.config.temperature;
        return [w, ...prev.slice(1)];
      });
    } catch {}
  }, []);

  /* ── set default model once models load ── */
  useEffect(() => {
    if (models.length > 0) {
      setWindows(prev => prev.map(w => w.modelId ? w : { ...w, modelId: models[0].model_id }));
    }
  }, [models]);

  /* ── window CRUD ── */
  const addWindow = () => {
    if (windows.length >= 3) return;
    const id = nextIdRef.current++;
    setWindows(prev => [...prev, { ...makeDefaultWindow(id), modelId: models[0]?.model_id || "" }]);
  };

  const removeWindow = (id) => {
    if (windows.length <= 1) return;
    setWindows(prev => prev.filter(w => w.id !== id));
  };

  const updateWindow = (id, patch) => setWindows(prev => prev.map(w => w.id === id ? { ...w, ...patch } : w));

  const updateMessage = (winId, msgIdx, content) => {
    setWindows(prev => prev.map(w => {
      if (w.id !== winId) return w;
      const msgs = [...w.messages];
      msgs[msgIdx] = { ...msgs[msgIdx], content };
      return { ...w, messages: msgs };
    }));
  };

  const addMessage = (winId) => {
    setWindows(prev => prev.map(w => {
      if (w.id !== winId) return w;
      return { ...w, messages: [...w.messages, { role: "user", content: "", _id: `${winId}-${Date.now()}` }] };
    }));
  };

  const addPlaceholder = (winId) => {
    setWindows(prev => prev.map(w => {
      if (w.id !== winId) return w;
      return { ...w, messages: [...w.messages, { role: "user", content: "{{placeholder}}", _id: `${winId}-ph-${Date.now()}` }] };
    }));
  };

  const removeMessage = (winId, msgIdx) => {
    setWindows(prev => prev.map(w => {
      if (w.id !== winId) return w;
      return { ...w, messages: w.messages.filter((_, i) => i !== msgIdx) };
    }));
  };

  const changeRole = (winId, msgIdx, role) => {
    setWindows(prev => prev.map(w => {
      if (w.id !== winId) return w;
      const msgs = [...w.messages];
      msgs[msgIdx] = { ...msgs[msgIdx], role };
      return { ...w, messages: msgs };
    }));
  };

  /* ── run a single window ── */
  const runWindow = async (win) => {
    updateWindow(win.id, { running: true, output: null, error: null });
    try {
      const body = {
        prompt_content: win.messages.map(({ _id, ...m }) => m),
        prompt_type: "chat",
        model_id: win.modelId,
        temperature: win.temperature,
        max_tokens: win.maxTokens,
        variables: {},
      };
      // extract and substitute variables
      const vars = extractVars(win.messages);
      if (vars.length > 0) {
        body.variables = {};
        vars.forEach(v => { body.variables[v] = `[${v}]`; });
      }
      const r = await apiFetch(`${API}/playground/run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.ok) {
        updateWindow(win.id, { running: false, output: await r.json() });
      } else {
        const err = await r.json().catch(() => ({ detail: "Request failed" }));
        updateWindow(win.id, { running: false, error: err.detail || JSON.stringify(err) });
      }
    } catch (e) {
      updateWindow(win.id, { running: false, error: e.message });
    }
  };

  /* ── run all windows ── */
  const runAll = () => { windows.forEach(w => runWindow(w)); };

  /* ── reset playground ── */
  const resetPlayground = () => {
    nextIdRef.current = 2;
    setWindows([makeDefaultWindow(1)]);
  };

  /* ── load prompt into a window ── */
  const loadPromptIntoWindow = async (winId, promptName) => {
    setShowPromptPicker(null);
    try {
      const r = await apiFetch(`${API}/prompts/${encodeURIComponent(promptName)}`);
      if (!r.ok) return;
      const d = await r.json();
      const msgs = [];
      if (d.type === "chat" && Array.isArray(d.prompt)) {
        d.prompt.forEach((m, i) => msgs.push({ role: m.role, content: m.content, _id: `lp-${i}` }));
      } else {
        const content = typeof d.prompt === "string" ? d.prompt : JSON.stringify(d.prompt);
        msgs.push({ role: "system", content, _id: "lp-0" });
        msgs.push({ role: "user", content: "", _id: "lp-1" });
      }
      const patch = { messages: msgs };
      if (d.config?.model) patch.modelId = d.config.model;
      if (d.config?.temperature !== undefined) patch.temperature = d.config.temperature;
      updateWindow(winId, patch);
    } catch {}
  };

  /* ── save to prompt management ── */
  const saveToPrompts = async () => {
    if (!saveName.trim() || windows.length === 0) return;
    const w = windows[0];
    try {
      const prompt = w.messages.map(({ _id, ...m }) => m);
      const tags = saveTags.split(",").map(t => t.trim()).filter(Boolean);
      await apiFetch(`${API}/prompts`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: saveName, prompt, type: "chat", config: { model: w.modelId, temperature: w.temperature }, labels: ["latest"], tags }),
      });
      setShowSave(false);
      setSaveName("");
      setSaveTags("");
    } catch {}
  };

  const modelDisplay = (modelId) => {
    const m = models.find(x => x.model_id === modelId);
    if (m) return m.display_name || m.model_id;
    return modelId || "Select model";
  };

  /* ══════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════ */
  return (
    <div className="h-[calc(100vh-48px)] flex flex-col overflow-hidden bg-white">
      {/* ── Header bar ── */}
      <div className="px-5 py-2.5 border-b border-slate-200 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-slate-900">Playground</h1>
          <span className="w-2 h-2 rounded-full bg-slate-300" />
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">{windows.length} window{windows.length !== 1 ? "s" : ""}</span>
          <button onClick={runAll}
            className="flex items-center gap-1.5 bg-slate-900 text-white rounded-lg px-3.5 py-1.5 text-xs font-medium cursor-pointer hover:bg-slate-800">
            <Play size={12} /> Run All <span className="text-slate-400 ml-1 text-[11px]">(Ctrl+Enter)</span>
          </button>
          <button onClick={resetPlayground}
            className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-600 cursor-pointer hover:bg-slate-50 bg-white">
            <RotateCcw size={12} /> Reset playground
          </button>
        </div>
      </div>

      {/* ── Windows area ── */}
      <div className="flex-1 flex overflow-hidden">
        {windows.map((w) => (
          <div key={w.id} className={cn("flex flex-col border-r border-slate-200 last:border-r-0 overflow-hidden",
            windows.length === 1 ? "flex-1" : windows.length === 2 ? "w-1/2" : "w-1/3")}>

            {/* Window header: model selector + actions */}
            <div className="px-3 py-2 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <select value={w.modelId} onChange={e => updateWindow(w.id, { modelId: e.target.value })}
                  className="text-xs font-medium bg-transparent outline-none cursor-pointer text-slate-700 truncate max-w-[200px] border border-slate-200 rounded-lg px-2 py-1.5 bg-white">
                  {models.map(m => <option key={m.model_id} value={m.model_id}>{m.display_name || m.model_id}</option>)}
                  {models.length === 0 && <option value="">No models</option>}
                </select>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={() => setShowPromptPicker(showPromptPicker === w.id ? null : w.id)} title="Load prompt"
                  className="text-slate-400 hover:text-slate-600 cursor-pointer p-1"><FileText size={14} /></button>
                <button onClick={() => { const txt = JSON.stringify(w.messages.map(({_id,...m})=>m), null, 2); try{navigator.clipboard?.writeText(txt)}catch{} }} title="Copy messages"
                  className="text-slate-400 hover:text-slate-600 cursor-pointer p-1"><Copy size={14} /></button>
                {windows.length > 1 && (
                  <button onClick={() => removeWindow(w.id)} title="Close window"
                    className="text-slate-400 hover:text-red-500 cursor-pointer p-1"><X size={14} /></button>
                )}
              </div>
            </div>

            {/* Prompt picker dropdown */}
            {showPromptPicker === w.id && (
              <div className="bg-white border-b border-slate-200 shadow-inner max-h-48 overflow-y-auto">
                <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase bg-slate-50">Load from Prompt Management</div>
                {prompts.map(p => (
                  <button key={p.name} onClick={() => loadPromptIntoWindow(w.id, p.name)}
                    className="w-full text-left px-3 py-2 hover:bg-slate-50 text-xs cursor-pointer border-b border-slate-50 last:border-0">
                    <div className="font-medium text-slate-800">{p.name}</div>
                    <div className="text-[11px] text-slate-400">{(p.labels || []).join(", ")}</div>
                  </button>
                ))}
                {prompts.length === 0 && <div className="p-3 text-xs text-slate-400">No prompts</div>}
              </div>
            )}

            {/* Toolbar row: settings icons */}
            <div className="px-3 py-1.5 bg-white border-b border-slate-100 flex items-center gap-2 shrink-0">
              <div className="flex items-center gap-1 text-[11px] text-slate-500">
                <Settings2 size={11} />
                <span>temp: </span>
                <input type="number" step="0.1" min="0" max="2" value={w.temperature}
                  onChange={e => updateWindow(w.id, { temperature: parseFloat(e.target.value) || 0 })}
                  className="w-10 border border-slate-200 rounded px-1 py-0.5 text-[11px] outline-none bg-white" />
              </div>
              <div className="flex items-center gap-1 text-[11px] text-slate-500">
                <span>max: </span>
                <input type="number" step="128" min="1" max="32768" value={w.maxTokens}
                  onChange={e => updateWindow(w.id, { maxTokens: parseInt(e.target.value) || 1024 })}
                  className="w-14 border border-slate-200 rounded px-1 py-0.5 text-[11px] outline-none bg-white" />
              </div>
            </div>

            {/* Messages + output area (scrollable) */}
            <div className="flex-1 overflow-y-auto flex flex-col">
              {/* Messages */}
              <div className="flex-1 p-3 space-y-2">
                {w.messages.map((m, i) => (
                  <div key={m._id || i} className="flex items-start gap-1.5 group">
                    <div className="pt-2 text-slate-300 opacity-0 group-hover:opacity-100 cursor-grab"><GripVertical size={12} /></div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <select value={m.role} onChange={e => changeRole(w.id, i, e.target.value)}
                          className="text-xs font-semibold text-slate-700 bg-transparent outline-none cursor-pointer capitalize">
                          <option value="system">System</option><option value="user">User</option><option value="assistant">Assistant</option>
                        </select>
                        <textarea value={m.content} onChange={e => updateMessage(w.id, i, e.target.value)}
                          className="flex-1 text-xs text-slate-800 bg-white border border-slate-200 rounded-lg px-3 py-2 outline-none resize-none min-h-[36px] font-mono"
                          rows={Math.max(1, (m.content.match(/\n/g) || []).length + 1)}
                          placeholder={m.role === "system" ? "You are a helpful assistant." : "Enter message..."} />
                      </div>
                    </div>
                    <button onClick={() => removeMessage(w.id, i)}
                      className="pt-2 text-slate-300 opacity-0 group-hover:opacity-100 hover:text-red-400 cursor-pointer"><X size={12} /></button>
                  </div>
                ))}
                {/* Add message / placeholder buttons */}
                <div className="flex items-center gap-2 pt-1">
                  <button onClick={() => addMessage(w.id)}
                    className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 cursor-pointer border border-dashed border-slate-300 rounded-lg px-2.5 py-1.5 hover:bg-slate-50">
                    <Plus size={11} /> Message
                  </button>
                  <button onClick={() => addPlaceholder(w.id)}
                    className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 cursor-pointer border border-dashed border-slate-300 rounded-lg px-2.5 py-1.5 hover:bg-slate-50">
                    <Plus size={11} /> Placeholder
                  </button>
                </div>
              </div>

              {/* Output section */}
              <div className="border-t border-slate-200 bg-white shrink-0">
                <div className="px-3 py-1.5 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-600">Output</span>
                    {w.output && (
                      <>
                        <button className="text-slate-400 hover:text-slate-600 cursor-pointer"><code className="text-[11px]">{"{}"}</code></button>
                        <button className="text-slate-400 hover:text-slate-600 cursor-pointer text-[11px]">◎</button>
                      </>
                    )}
                  </div>
                  {w.output && (
                    <button onClick={() => {
                      addMessage(w.id);
                      setTimeout(() => {
                        setWindows(prev => prev.map(win => {
                          if (win.id !== w.id) return win;
                          const msgs = [...win.messages];
                          msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], role: "assistant", content: w.output.output || "" };
                          return { ...win, messages: msgs };
                        }));
                      }, 50);
                    }} className="text-[11px] text-blue-500 hover:underline cursor-pointer">
                      + Add to messages
                    </button>
                  )}
                </div>
                <div className="px-3 py-3 min-h-[80px] max-h-[200px] overflow-y-auto">
                  {w.running && <div className="flex items-center gap-2 text-xs text-slate-400"><Loader2 size={12} className="animate-spin" /> Generating...</div>}
                  {w.error && <div className="text-xs text-red-600 bg-red-50 rounded-lg p-2">{w.error}</div>}
                  {w.output && (
                    <div>
                      <div className="text-xs text-slate-800 whitespace-pre-wrap leading-relaxed">{w.output.output}</div>
                      {(w.output.total_tokens || w.output.latency_ms) && (
                        <div className="mt-2 flex items-center gap-3 text-[11px] text-slate-400 border-t border-slate-100 pt-2">
                          {w.output.latency_ms && <span className="flex items-center gap-0.5"><Clock size={9} />{w.output.latency_ms.toFixed(0)}ms</span>}
                          {w.output.total_tokens && <span className="flex items-center gap-0.5"><Hash size={9} />{w.output.total_tokens} tok</span>}
                          {w.output.trace_id && <span className="font-mono text-blue-400">{w.output.trace_id.slice(0, 8)}…</span>}
                        </div>
                      )}
                    </div>
                  )}
                  {!w.running && !w.output && !w.error && <div className="text-xs text-slate-300 italic">Press Submit to generate</div>}
                </div>
              </div>

              {/* Submit button */}
              <div className="p-3 bg-white shrink-0 flex items-center gap-2">
                <button onClick={() => runWindow(w)} disabled={w.running || !w.modelId}
                  className={cn("flex-1 py-2.5 rounded-lg text-sm font-medium cursor-pointer transition",
                    w.running ? "bg-slate-300 text-slate-500" : "bg-slate-900 text-white hover:bg-slate-800")}>
                  {w.running ? "Generating..." : "Submit"}
                </button>
                <button className="text-slate-400 hover:text-slate-600 cursor-pointer p-1.5 border border-slate-200 rounded-lg"><Settings2 size={14} /></button>
              </div>
            </div>
          </div>
        ))}

        {/* Add window button */}
        {windows.length < 3 && (
          <button onClick={addWindow}
            className="w-12 flex items-center justify-center border-l border-slate-200 bg-slate-50 hover:bg-slate-100 cursor-pointer transition shrink-0"
            title="Add window">
            <Plus size={16} className="text-slate-400" />
          </button>
        )}
      </div>

      {/* ── Keyboard shortcut ── */}
      <KeyboardHandler onRunAll={runAll} />

      {/* ── Save dialog ── */}
      {showSave && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center" onClick={() => setShowSave(false)}>
          <div className="bg-white border border-slate-200 rounded-xl p-5 w-96 space-y-3 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-slate-900">Save to Prompt Management</h3>
            <div><label className="text-xs font-medium text-slate-500 block mb-1">Prompt Name</label>
              <input value={saveName} onChange={e => setSaveName(e.target.value)} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="my-prompt" /></div>
            <div><label className="text-xs font-medium text-slate-500 block mb-1">Tags (comma-separated)</label>
              <input value={saveTags} onChange={e => setSaveTags(e.target.value)} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="agent, classification" /></div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowSave(false)} className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs text-slate-600 cursor-pointer hover:bg-slate-50">Cancel</button>
              <button onClick={saveToPrompts} disabled={!saveName.trim()}
                className={cn("bg-slate-900 text-white rounded-lg px-4 py-1.5 text-xs font-medium cursor-pointer", !saveName.trim() && "opacity-50")}>Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* Keyboard handler for Ctrl+Enter → Run All */
function KeyboardHandler({ onRunAll }) {
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); onRunAll(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onRunAll]);
  return null;
}
