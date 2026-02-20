"use client";
import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import apiFetch from "../../lib/apiFetch";
import useAuthStore from "../../stores/authStore";
import { cn } from "../../lib/cn";
import { API, Badge, toast } from "../shared/StudioUI";
import { Bot, MessageSquare, Settings as SettingsIcon, ChevronDown, Plus, Send, Brain, Wrench, Sparkles, Paperclip, Mic } from "lucide-react";
import ReactMarkdown from "react-markdown";

function TypingIndicator({ agentName }) {
  return (
    <div className="flex gap-3 flex-row animate-fade-up">
      <div className="w-8 h-8 rounded-full bg-jai-primary-light flex items-center justify-center shrink-0">
        <Bot size={14} className="text-jai-primary" />
      </div>
      <div className="bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 flex items-center gap-1.5">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
        <span className="text-xs text-slate-400 ml-2">{agentName} is thinking...</span>
      </div>
    </div>
  );
}

export default function ChatPage({ initialAgent }) {
  const { user } = useAuthStore();
  const [agents, setAgents] = useState([]);
  const [selAgent, setSelAgent] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  const [threads, setThreads] = useState([{ id: "t-1", title: "New conversation", time: "Just now" }]);
  const [activeThread, setActiveThread] = useState("t-1");
  const [agentPickerOpen, setAgentPickerOpen] = useState(false);
  const lgThreadIdRef = useRef(null);   // LangGraph thread_id for context-aware chat
  const lgAssistantIdRef = useRef(null); // LangGraph assistant_id for the selected agent
  const [chatConfig, setChatConfig] = useState({ model: "gemini-2.5-flash", systemPrompt: "", temperature: 0.1, ragEnabled: false, memoryEnabled: true });
  const endRef = useRef(null);
  const inputRef = useRef(null);

  const userInitials = useMemo(() => {
    const name = user?.displayName || user?.email || "U";
    return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  }, [user]);

  useEffect(() => {
    // Fetch both local agents and LangGraph assistants
    Promise.all([
      apiFetch(`${API}/agents`).then(r => r.json()).catch(() => ({ agents: [] })),
      apiFetch(`${API}/langgraph/assistants`).then(r => r.json()).catch(() => ({ assistants: [] })),
    ]).then(([localData, lgData]) => {
      const localAgents = (localData.agents || []).map(a => ({ ...a, source: "local" }));
      const lgAssistants = (lgData.assistants || []).map(a => ({
        agent_id: a.assistant_id,
        assistant_id: a.assistant_id,
        name: a.name,
        description: a.description,
        model: a.model,
        source: "langgraph",
      }));
      // Merge: local agents first, then LangGraph-only assistants
      const localIds = new Set(localAgents.map(a => a.name?.toLowerCase()));
      const uniqueLg = lgAssistants.filter(a => !localIds.has(a.name?.toLowerCase()));
      const merged = [...localAgents, ...uniqueLg];
      setAgents(merged);
      if (initialAgent) { const found = merged.find(x => x.agent_id === initialAgent); if (found) setSelAgent(found); }
      else if (merged.length && !selAgent) setSelAgent(merged[0]);
    });
  }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, isTyping]);

  // Pre-configure chat from agent's settings when agent changes
  useEffect(() => {
    if (selAgent) {
      setChatConfig(prev => ({
        ...prev,
        model: selAgent.model || prev.model,
        systemPrompt: selAgent.context || prev.systemPrompt,
        ragEnabled: selAgent.rag_enabled ?? prev.ragEnabled,
        temperature: selAgent.temperature ?? prev.temperature,
      }));
      // Reset LangGraph thread when agent changes (new conversation context)
      lgThreadIdRef.current = null;
      // Resolve LangGraph assistant_id for this agent
      if (selAgent.assistant_id) {
        lgAssistantIdRef.current = selAgent.assistant_id;
      } else {
        // Look up by name from LangGraph server
        lgAssistantIdRef.current = null;
        apiFetch(`${API}/langgraph/assistants`).then(r => r.json()).then(d => {
          const match = (d.assistants || []).find(
            a => a.name?.toLowerCase() === selAgent.name?.toLowerCase()
          );
          if (match) lgAssistantIdRef.current = match.assistant_id;
        }).catch(() => {});
      }
    }
  }, [selAgent?.agent_id]);

  const send = useCallback(() => {
    if (!input.trim() || isTyping) return;
    const userMsg = input.trim();
    setMessages(p => [...p, { role: "user", content: userMsg }]);
    setInput("");
    setIsTyping(true);

    const assistantId = lgAssistantIdRef.current;
    if (!assistantId && !selAgent?.agent_id) {
      setTimeout(() => {
        setMessages(p => [...p, { role: "assistant", content: "Please select an agent first to start a conversation." }]);
        setIsTyping(false);
      }, 400);
      return;
    }

    const doChat = async () => {
      try {
        // If we have a LangGraph assistant_id, use context-aware LangGraph chat
        let resolvedAssistantId = assistantId;

        // If no assistant_id yet, try to create one on the fly
        if (!resolvedAssistantId && selAgent) {
          try {
            const createRes = await apiFetch(`${API}/langgraph/assistants`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                name: selAgent.name || "Agent",
                description: selAgent.description || "",
                system_prompt: selAgent.context || chatConfig.systemPrompt || "You are a helpful assistant.",
                model_id: selAgent.model || chatConfig.model || "gemini-2.5-flash",
              }),
            });
            if (createRes.ok) {
              const createData = await createRes.json();
              resolvedAssistantId = createData.assistant_id;
              lgAssistantIdRef.current = resolvedAssistantId;
            }
          } catch (e) { console.warn("Failed to create LangGraph assistant:", e); }
        }

        if (!resolvedAssistantId) throw new Error("Could not resolve LangGraph assistant for this agent.");

        // Send via LangGraph chat (context-aware via thread_id)
        const r = await apiFetch(`${API}/langgraph/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: userMsg,
            assistant_id: resolvedAssistantId,
            thread_id: lgThreadIdRef.current || undefined,
          }),
        });

        if (!r.ok) {
          const errData = await r.json().catch(() => ({}));
          throw new Error(errData.detail || `Chat failed (${r.status})`);
        }

        const data = await r.json();

        // Store thread_id for subsequent messages (context continuity)
        if (data.thread_id) {
          lgThreadIdRef.current = data.thread_id;
        }

        const response = data.response || "No response from agent.";
        setMessages(p => [...p, { role: "assistant", content: response, latency_ms: data.latency_ms }]);
        setIsTyping(false);
      } catch (e) {
        console.error("Chat error:", e);
        setMessages(p => [...p, { role: "assistant", content: `Error: ${e.message}` }]);
        setIsTyping(false);
      }
    };
    doChat();
  }, [input, isTyping, selAgent, chatConfig]);

  const newThread = () => {
    const id = `t-${Date.now()}`;
    setThreads(p => [{ id, title: "New conversation", time: "Just now" }, ...p]);
    setActiveThread(id);
    setMessages([]);
    lgThreadIdRef.current = null; // Reset LangGraph thread for fresh context
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Persistent thread list */}
      <div className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col">
        <div className="p-3 border-b border-slate-100">
          <button onClick={newThread} className="w-full flex items-center justify-center gap-2 bg-jai-primary text-white rounded-lg py-2 text-sm font-medium hover:bg-jai-primary-hover transition cursor-pointer shadow-sm shadow-jai-primary/20">
            <Plus size={14} /> New Thread
          </button>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-1">
          {threads.map(t => (
            <div key={t.id} onClick={() => setActiveThread(t.id)}
              className={cn("p-2.5 rounded-lg cursor-pointer transition-all duration-150",
                activeThread === t.id ? "bg-jai-primary-light border border-jai-primary-border" : "hover:bg-slate-50 border border-transparent")}>
              <div className="text-sm font-medium text-slate-900 truncate">{t.title}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">{t.time}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {/* Header with rich agent picker */}
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <div className="relative">
            <button onClick={() => setAgentPickerOpen(!agentPickerOpen)}
              className="flex items-center gap-3 px-3 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 hover:border-slate-300 transition cursor-pointer min-w-[240px]">
              <div className="w-8 h-8 rounded-lg bg-jai-primary-light flex items-center justify-center shrink-0">
                <Bot size={16} className="text-jai-primary" />
              </div>
              <div className="text-left flex-1">
                <div className="text-sm font-medium text-slate-900">{selAgent?.name || "Select Agent"}</div>
                {selAgent?.description && <div className="text-[11px] text-slate-500 truncate max-w-[180px]">{selAgent.description}</div>}
              </div>
              <ChevronDown size={14} className={cn("text-slate-400 transition-transform duration-150", agentPickerOpen && "rotate-180")} />
            </button>
            {agentPickerOpen && (
              <div className="absolute top-full left-0 mt-1 w-80 bg-white border border-slate-200 rounded-xl shadow-lg z-50 max-h-80 overflow-y-auto animate-scale-in">
                {agents.map(a => (
                  <div key={a.agent_id} onClick={() => { setSelAgent(a); setAgentPickerOpen(false); }}
                    className={cn("px-4 py-3 cursor-pointer hover:bg-slate-50 border-b border-slate-100 last:border-0 transition",
                      selAgent?.agent_id === a.agent_id && "bg-jai-primary-light")}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-900">{a.name}</span>
                      <div className="flex gap-1">
                        {a.rag_enabled && <Badge variant="brand">RAG</Badge>}
                        {a.tools_count > 0 && <Badge variant="info">Tools</Badge>}
                      </div>
                    </div>
                    {a.description && <div className="text-xs text-slate-500 mt-1 truncate">{a.description}</div>}
                  </div>
                ))}
                {agents.length === 0 && <div className="p-4 text-sm text-slate-400 text-center">No agents available</div>}
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <button onClick={() => setConfigOpen(!configOpen)}
              className={cn("p-2 rounded-lg border text-slate-500 hover:bg-slate-50 transition cursor-pointer",
                configOpen ? "border-jai-primary bg-jai-primary-light text-jai-primary" : "border-slate-200")}>
              <SettingsIcon size={16} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-8 py-6 space-y-5 scrollbar-thin">
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 h-full animate-fade-up">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-jai-primary/10 to-jai-primary/5 flex items-center justify-center">
                <Sparkles size={28} className="text-jai-primary" />
              </div>
              <div className="text-lg font-semibold text-slate-900">Start a conversation</div>
              <div className="text-sm text-slate-500 max-w-md text-center">
                {selAgent ? `Chat with ${selAgent.name} — ask anything.` : "Select an agent from the dropdown above to begin."}
              </div>
              {selAgent && (
                <div className="flex flex-wrap gap-2 mt-1 max-w-lg justify-center">
                  {["What can you help me with?", "Show me recent contracts", "Create a new RFQ", "Summarize supplier performance"].map(s => (
                    <button key={s} onClick={() => { setInput(s); inputRef.current?.focus(); }}
                      className="px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-full text-slate-600 hover:bg-slate-50 hover:border-slate-300 transition cursor-pointer shadow-sm">{s}</button>
                  ))}
                </div>
              )}
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={cn("flex gap-3 animate-fade-up", m.role === "user" ? "flex-row-reverse" : "flex-row")}>
              {m.role === "user" ? (
                <div className="w-8 h-8 rounded-full bg-jai-navy flex items-center justify-center text-[11px] font-bold text-white shrink-0">
                  {userInitials}
                </div>
              ) : (
                <div className="w-8 h-8 rounded-full bg-jai-primary-light flex items-center justify-center shrink-0">
                  <Bot size={14} className="text-jai-primary" />
                </div>
              )}
              <div className={cn("max-w-[70%] px-4 py-3 rounded-2xl text-sm leading-relaxed",
                m.role === "user"
                  ? "bg-jai-navy text-white rounded-br-md whitespace-pre-wrap"
                  : "bg-slate-50 text-slate-800 border border-slate-100 rounded-bl-md")}>
                {m.role === "assistant" ? (
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                      em: ({ children }) => <em className="italic">{children}</em>,
                      ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                      li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                      h1: ({ children }) => <h1 className="text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-base font-bold mb-2 mt-3 first:mt-0">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-sm font-bold mb-1.5 mt-2 first:mt-0">{children}</h3>,
                      code: ({ inline, children }) => inline
                        ? <code className="bg-slate-200/60 text-slate-800 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
                        : <pre className="bg-slate-900 text-slate-100 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono"><code>{children}</code></pre>,
                      blockquote: ({ children }) => <blockquote className="border-l-2 border-slate-300 pl-3 italic text-slate-600 my-2">{children}</blockquote>,
                      a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-jai-primary underline hover:text-jai-primary-hover">{children}</a>,
                      hr: () => <hr className="border-slate-200 my-3" />,
                      table: ({ children }) => <div className="overflow-x-auto my-2"><table className="min-w-full text-xs border border-slate-200 rounded">{children}</table></div>,
                      th: ({ children }) => <th className="bg-slate-100 px-3 py-1.5 text-left font-semibold border-b border-slate-200">{children}</th>,
                      td: ({ children }) => <td className="px-3 py-1.5 border-b border-slate-100">{children}</td>,
                    }}
                  >{m.content}</ReactMarkdown>
                ) : m.content}
              </div>
            </div>
          ))}
          {isTyping && <TypingIndicator agentName={selAgent?.name || "Agent"} />}
          <div ref={endRef} />
        </div>

        {/* Input */}
        <div className="px-8 py-4 border-t border-slate-100 bg-white">
          <div className="flex gap-2 max-w-3xl mx-auto items-end">
            <textarea value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder={`Message ${selAgent?.name || "agent"}...`}
              rows={1}
              disabled={isTyping}
              className="flex-1 bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-jai-primary focus:ring-2 focus:ring-jai-primary/10 transition resize-none overflow-hidden disabled:opacity-50"
              style={{ maxHeight: "120px" }}
              ref={el => { inputRef.current = el; if (el) { el.style.height = "auto"; el.style.height = Math.min(el.scrollHeight, 120) + "px"; } }} />
            <button
              onClick={() => {}}
              title="Attach file"
              className="flex items-center justify-center w-10 h-10 rounded-xl text-slate-400 hover:text-jai-primary hover:bg-jai-primary/5 cursor-pointer transition-all duration-150 shrink-0 active:scale-95">
              <Paperclip size={18} />
            </button>
            <button
              onClick={() => {}}
              title="Voice input"
              className="flex items-center justify-center w-10 h-10 rounded-xl text-slate-400 hover:text-jai-primary hover:bg-jai-primary/5 cursor-pointer transition-all duration-150 shrink-0 active:scale-95">
              <Mic size={18} />
            </button>
            <button onClick={send} disabled={!input.trim() || isTyping}
              className={cn("flex items-center justify-center w-10 h-10 bg-jai-primary text-white rounded-xl cursor-pointer hover:bg-jai-primary-hover transition-all duration-150 shrink-0 shadow-sm shadow-jai-primary/20 active:scale-95",
                (!input.trim() || isTyping) && "opacity-40 cursor-not-allowed")}>
              <Send size={16} />
            </button>
          </div>
          <div className="text-[11px] text-slate-300 text-center mt-1.5">Press Enter to send · Shift+Enter for new line</div>
        </div>
      </div>

      {/* Config Sidebar — with slide-in animation */}
      {configOpen && (
        <div className="w-[360px] border-l border-slate-200 bg-white overflow-y-auto p-5 shrink-0 space-y-4 animate-slide-in-left">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-slate-900">Configuration</h3>
            <button onClick={() => setConfigOpen(false)} className="text-slate-400 hover:text-slate-700 cursor-pointer transition">✕</button>
          </div>
          {selAgent && <>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1.5">Model</label>
              <select value={chatConfig.model} onChange={e => setChatConfig(p => ({ ...p, model: e.target.value }))}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-jai-primary focus:ring-2 focus:ring-jai-primary/10 transition">
                <option value="gemini-2.5-flash">gemini-2.5-flash</option><option value="gemini-2.5-pro">gemini-2.5-pro</option><option value="claude-sonnet-4">claude-sonnet-4</option><option value="gpt-4o">gpt-4o</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1.5">System Prompt</label>
              <textarea value={chatConfig.systemPrompt} onChange={e => setChatConfig(p => ({ ...p, systemPrompt: e.target.value }))}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2.5 text-sm font-mono text-slate-900 outline-none h-24 resize-y focus:border-jai-primary focus:ring-2 focus:ring-jai-primary/10 transition"
                placeholder="You are a helpful assistant..." />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-slate-600">Temperature</label>
                <span className="text-xs font-mono text-jai-primary font-semibold">{chatConfig.temperature}</span>
              </div>
              <input type="range" min="0" max="1" step="0.05" value={chatConfig.temperature}
                onChange={e => setChatConfig(p => ({ ...p, temperature: parseFloat(e.target.value) }))} className="w-full accent-jai-primary" />
            </div>
            <hr className="border-slate-100" />
            <div className="space-y-3">
              <label className="flex items-center gap-2.5 text-sm text-slate-700 cursor-pointer">
                <input type="checkbox" checked={chatConfig.ragEnabled} onChange={e => setChatConfig(p => ({ ...p, ragEnabled: e.target.checked }))} className="w-4 h-4 rounded accent-jai-primary" />
                <div><div className="font-medium">RAG Retrieval</div><div className="text-[11px] text-slate-400">Ground responses in knowledge base</div></div>
              </label>
              <label className="flex items-center gap-2.5 text-sm text-slate-700 cursor-pointer">
                <input type="checkbox" checked={chatConfig.memoryEnabled} onChange={e => setChatConfig(p => ({ ...p, memoryEnabled: e.target.checked }))} className="w-4 h-4 rounded accent-jai-primary" />
                <div><div className="font-medium">Short-term Memory</div><div className="text-[11px] text-slate-400">Remember context within session</div></div>
              </label>
            </div>
            <button onClick={() => { toast.success("Configuration saved"); setConfigOpen(false); }}
              className="w-full bg-jai-primary text-white rounded-xl px-4 py-2.5 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover transition shadow-sm shadow-jai-primary/20">Save Configuration</button>
          </>}
        </div>
      )}
    </div>
  );
}
