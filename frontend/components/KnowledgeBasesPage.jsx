"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import apiFetch from "../lib/apiFetch";
import useEnvStore from "../stores/envStore";
import { EnvBadge, EnvVersionMeta } from "./EnvironmentSwitcher";
import { cn } from "../lib/cn";
import {
  Brain, Plus, Upload, Play, Beaker, Trash2, RefreshCw, FileText, Search,
  Database, ChevronRight, X, Check, AlertCircle, BarChart3, Sparkles,
  Settings, Zap, Edit3, Target, FileUp, Loader2, File, DownloadCloud,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

const DEFAULT_PROMPTS = {
  answerGeneration: `Given the following context chunks from a knowledge base, generate a comprehensive and accurate answer to the user's question.

## Context
{chunks}

## Question
{question}

## Instructions
- Only use information from the provided context
- If the context doesn't contain enough information, say so
- Cite specific chunks when possible
- Be concise but thorough`,
  testCaseGeneration: `You are a QA test case generator for a RAG knowledge base. Given a set of document chunks, generate diverse question-answer pairs that test different aspects of the content.

## Document Content
{document_content}

## Instructions
- Generate {num_questions} question-answer pairs
- Cover different topics, detail levels, and question types
- Include factual, inferential, and comparison questions
- Each answer should be directly supported by the document content
- Format as JSON array: [{"question": "...", "expected_answer": "...", "category": "..."}]`,
  evaluation: `You are an expert evaluator for a RAG (Retrieval-Augmented Generation) system. Score the following response on multiple dimensions.

## Question
{question}

## Expected Answer
{expected_answer}

## Generated Answer
{generated_answer}

## Retrieved Context
{context}

## Evaluation Criteria
Score each from 0.0 to 1.0:
- **Faithfulness**: Is the answer grounded in the provided context?
- **Relevance**: Does the answer address the question?
- **Context Precision**: Were the right chunks retrieved?
- **Context Recall**: Were all needed chunks retrieved?
- **Answer Correctness**: Does the answer match the expected answer?
- **Accuracy**: Is the answer factually correct based on source docs?

Respond with JSON: {"faithfulness": 0.0, "relevance": 0.0, "context_precision": 0.0, "context_recall": 0.0, "answer_correctness": 0.0, "accuracy": 0.0}`,
};

function StatPill({ label, value, color = "text-slate-700" }) {
  return (
    <div className="bg-slate-50 rounded-lg px-3 py-2 text-center">
      <div className={cn("text-lg font-bold", color)}>{value}</div>
      <div className="text-[11px] text-slate-400 uppercase tracking-wide">{label}</div>
    </div>
  );
}

function EvalGauge({ label, value }) {
  const pct = Math.round(value * 100);
  const color = pct >= 85 ? "text-emerald-600" : pct >= 70 ? "text-amber-600" : "text-red-600";
  const bg = pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-slate-500 w-28 truncate">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", bg)} style={{ width: `${pct}%` }} />
      </div>
      <span className={cn("text-xs font-bold w-10 text-right", color)}>{pct}%</span>
    </div>
  );
}

function PromptEditorModal({ title, value, onChange, onClose, onAiImprove, improving }) {
  const [draft, setDraft] = useState(value);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between shrink-0">
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { onAiImprove(draft, (improved) => setDraft(improved)); }}
              disabled={improving}
              className="flex items-center gap-1 text-xs text-jai-primary hover:text-[#C73D65] cursor-pointer bg-[#FDF1F5] px-2.5 py-1 rounded-lg font-medium disabled:opacity-40"
            >
              <Zap size={11} /> {improving ? "Improving..." : "AI Improve"}
            </button>
            <button onClick={onClose} className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-900 hover:bg-slate-100 cursor-pointer"><X size={14} /></button>
          </div>
        </div>
        <div className="p-5 flex-1 overflow-y-auto">
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            rows={16}
            className="w-full border border-slate-200 rounded-lg px-4 py-3 text-sm font-mono outline-none resize-none focus:border-jai-primary leading-relaxed"
          />
          <div className="text-[11px] text-slate-400 mt-1.5">
            Variables: <code className="bg-slate-100 px-1 rounded">{"{chunks}"}</code> <code className="bg-slate-100 px-1 rounded">{"{question}"}</code> <code className="bg-slate-100 px-1 rounded">{"{document_content}"}</code> <code className="bg-slate-100 px-1 rounded">{"{expected_answer}"}</code> <code className="bg-slate-100 px-1 rounded">{"{generated_answer}"}</code> <code className="bg-slate-100 px-1 rounded">{"{context}"}</code>
          </div>
        </div>
        <div className="px-6 py-3 border-t border-slate-200 flex justify-end gap-2 shrink-0">
          <button onClick={onClose} className="px-4 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer">Cancel</button>
          <button onClick={() => { onChange(draft); onClose(); }} className="bg-jai-primary text-white rounded-lg px-4 py-1.5 text-xs font-medium cursor-pointer hover:bg-jai-primary-hover flex items-center gap-1.5"><Check size={12} /> Save</button>
        </div>
      </div>
    </div>
  );
}

export default function KnowledgeBasesPage() {
  const currentEnv = useEnvStore(s => s.currentEnv);
  const [kbs, setKbs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name: "", description: "", chunk_size: 512, overlap: 64 });
  const [testQuery, setTestQuery] = useState("");
  const [testResults, setTestResults] = useState(null);
  const [testData, setTestData] = useState(null);
  const [evalResults, setEvalResults] = useState(null);
  const [actionLoading, setActionLoading] = useState("");
  const [models, setModels] = useState([]);
  const [evalModel, setEvalModel] = useState("gemini-2.5-flash");
  const [topK, setTopK] = useState(5);
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [prompts, setPrompts] = useState({ ...DEFAULT_PROMPTS });
  const [improving, setImproving] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null); // { current, total, fileName }
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const load = useCallback(() => {
    setLoading(true);
    apiFetch(`${API}/knowledge-bases`).then(r => r.json()).then(d => {
      setKbs(d.knowledge_bases || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    apiFetch(`${API}/models`).then(r => r.json()).then(d => setModels(d.models || [])).catch(() => {});
  }, []);

  // Load files when a KB is selected
  const loadFiles = useCallback((kbId) => {
    apiFetch(`${API}/knowledge-bases/${kbId}/files`).then(r => r.json()).then(files => {
      setUploadedFiles(Array.isArray(files) ? files : []);
    }).catch(() => setUploadedFiles([]));
  }, []);

  useEffect(() => {
    if (selected?.kb_id) loadFiles(selected.kb_id);
    else setUploadedFiles([]);
  }, [selected?.kb_id, loadFiles]);

  // Auto-poll file list while any file is syncing
  useEffect(() => {
    const hasSyncing = uploadedFiles.some(f => f.status === "syncing");
    if (!hasSyncing || !selected?.kb_id) return;
    const interval = setInterval(() => {
      loadFiles(selected.kb_id);
      load(); // also refresh KB list to update doc counts
    }, 5000);
    return () => clearInterval(interval);
  }, [uploadedFiles, selected?.kb_id, loadFiles, load]);

  const createKb = async () => {
    setActionLoading("create");
    try {
      const r = await apiFetch(`${API}/knowledge-bases`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(createForm) });
      const kb = await r.json();
      setKbs(prev => [...prev, kb]);
      setShowCreate(false);
      setCreateForm({ name: "", description: "", chunk_size: 512, overlap: 64 });
      setSelected(kb);
    } catch (e) { console.error("Create KB failed:", e); }
    setActionLoading("");
  };

  // Real file upload — multipart FormData to GCS via backend
  const uploadFiles = async (kbId, files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadProgress({ current: 0, total: files.length, fileName: "" });
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgress({ current: i + 1, total: files.length, fileName: file.name });
        const formData = new FormData();
        formData.append("file", file);
        await apiFetch(`${API}/knowledge-bases/${kbId}/upload`, {
          method: "POST",
          body: formData,
          // Do NOT set Content-Type — browser sets it with boundary for multipart
        });
      }
      // Refresh file list and KB data
      loadFiles(kbId);
      load();
    } catch (e) { console.error("Upload failed:", e); }
    setUploading(false);
    setUploadProgress(null);
  };

  const handleFileSelect = (e) => {
    const files = e.target.files;
    if (files && selected?.kb_id) uploadFiles(selected.kb_id, Array.from(files));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files && selected?.kb_id) uploadFiles(selected.kb_id, Array.from(files));
  };

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);

  // Trigger Discovery Engine indexing
  const triggerIndex = async (kbId) => {
    setActionLoading("index");
    try {
      await apiFetch(`${API}/knowledge-bases/${kbId}/index`, { method: "POST" });
      loadFiles(kbId);
      load();
    } catch (e) { console.error("Index failed:", e); }
    setActionLoading("");
  };

  // Delete a single file
  const deleteFile = async (kbId, fileId) => {
    try {
      await apiFetch(`${API}/knowledge-bases/${kbId}/files/${fileId}`, { method: "DELETE" });
      loadFiles(kbId);
      load();
    } catch (e) { console.error("Delete file failed:", e); }
  };

  const runTest = async (kbId) => {
    if (!testQuery.trim()) return;
    setActionLoading("test");
    const r = await apiFetch(`${API}/knowledge-bases/${kbId}/test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: testQuery, top_k: topK }) });
    setTestResults(await r.json());
    setActionLoading("");
  };

  const generateTestData = async (kbId) => {
    setActionLoading("generate");
    const r = await apiFetch(`${API}/knowledge-bases/${kbId}/generate-test-data`, { method: "POST" });
    setTestData(await r.json());
    setActionLoading("");
  };

  const evaluate = async (kbId) => {
    setActionLoading("evaluate");
    const r = await apiFetch(`${API}/knowledge-bases/${kbId}/evaluate`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_id: evalModel, top_k: topK }),
    });
    setEvalResults(await r.json());
    setActionLoading("");
  };

  const deleteKb = async (kbId) => {
    await apiFetch(`${API}/knowledge-bases/${kbId}`, { method: "DELETE" });
    if (selected?.kb_id === kbId) { setSelected(null); setTestResults(null); setTestData(null); setEvalResults(null); }
    load();
  };

  const aiImprovePrompt = async (content, callback) => {
    setImproving(true);
    try {
      const r = await apiFetch(`${API}/prompts/improve`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, goal: "Improve this RAG prompt for better accuracy, clarity, and groundedness", model_id: evalModel }),
      });
      const data = await r.json();
      if (data.status === "success" && data.improved) {
        callback(data.improved);
      }
    } catch (e) { console.error("AI improve failed:", e); }
    setImproving(false);
  };

  if (loading) return <div className="p-6 text-slate-400 text-sm">Loading knowledge bases...</div>;

  return (
    <div className="flex h-full">
      {/* Left: KB List */}
      <div className="w-80 border-r border-slate-200 bg-white flex flex-col shrink-0">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Knowledge Bases</h2>
          <div className="flex items-center gap-1">
            <button onClick={load} className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer"><RefreshCw size={13} /></button>
            <button onClick={() => setShowCreate(true)} className="w-7 h-7 flex items-center justify-center rounded-lg bg-jai-primary text-white cursor-pointer hover:bg-jai-primary-hover"><Plus size={13} /></button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {kbs.map(kb => (
            <div
              key={kb.kb_id}
              onClick={() => { setSelected(kb); setTestResults(null); setTestData(null); setEvalResults(null); }}
              className={cn(
                "p-3 rounded-lg cursor-pointer transition border",
                selected?.kb_id === kb.kb_id ? "bg-[#FDF1F5] border-[#F2B3C6]" : "border-transparent hover:bg-slate-50"
              )}
            >
              <div className="flex items-center gap-2">
                <Database size={14} className="text-jai-primary shrink-0" />
                <span className="text-sm font-medium text-slate-800 truncate">{kb.name}</span>
                <div className={cn("w-1.5 h-1.5 rounded-full ml-auto shrink-0", kb.status === "active" ? "bg-emerald-500" : "bg-amber-500")} />
              </div>
              <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{kb.description}</p>
              <div className="flex gap-3 mt-1.5 text-[11px] text-slate-500">
                <EnvBadge envId={currentEnv} size="xs" />
                <span>{kb.documents} docs</span>
                <span>{kb.chunks} chunks</span>
              </div>
            </div>
          ))}
          {kbs.length === 0 && (
            <div className="text-center py-8 text-sm text-slate-400">
              <Brain size={24} className="mx-auto mb-2 text-slate-300" />
              No knowledge bases yet
            </div>
          )}
        </div>
      </div>

      {/* Right: Detail Panel */}
      <div className="flex-1 overflow-y-auto bg-slate-50">
        {!selected ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center">
              <Database size={36} className="mx-auto mb-3 text-slate-300" />
              <div className="text-sm">Select a knowledge base or create a new one</div>
            </div>
          </div>
        ) : (
          <div className="p-6 animate-fade-up max-w-4xl mx-auto space-y-5">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-lg font-semibold text-slate-900">{selected.name}</h1>
                <p className="text-sm text-slate-500 mt-0.5">{selected.description}</p>
                <div className="flex items-center gap-2 mt-2">
                  <EnvBadge envId={currentEnv} />
                  <EnvVersionMeta assetId={selected.kb_id} />
                </div>
              </div>
              <button onClick={() => deleteKb(selected.kb_id)} className="text-slate-400 hover:text-red-500 cursor-pointer p-1"><Trash2 size={16} /></button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-3">
              <StatPill label="Documents" value={selected.documents} color="text-slate-800" />
              <StatPill label="Chunks" value={selected.chunks} color="text-jai-primary" />
              <StatPill label="Embedding" value={selected.embedding_model?.replace("text-embedding-", "v")} color="text-sky-600" />
              <StatPill label="Dimension" value={selected.dimension} color="text-violet-600" />
            </div>

            {/* Config */}
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">Vertex AI Discovery Engine Config</h3>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                <div><span className="text-slate-400">Provider:</span> Google Vertex AI</div>
                <div><span className="text-slate-400">Index ID:</span> <span className="font-mono">{selected.index_id}</span></div>
                <div><span className="text-slate-400">Chunk Size:</span> {selected.metadata?.avg_chunk_size || 512} tokens</div>
                <div><span className="text-slate-400">Overlap:</span> {selected.metadata?.overlap || 64} tokens</div>
                <div><span className="text-slate-400">Created:</span> {selected.created_at ? new Date(selected.created_at).toLocaleDateString() : "—"}</div>
                <div><span className="text-slate-400">Last Synced:</span> {selected.last_synced ? new Date(selected.last_synced).toLocaleDateString() : "Never"}</div>
              </div>
            </div>

            {/* RAG Configuration */}
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-slate-500 uppercase">RAG Configuration</h3>
                <Settings size={13} className="text-slate-400" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase block mb-1">Evaluation Model</label>
                  <select
                    value={evalModel}
                    onChange={e => setEvalModel(e.target.value)}
                    className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none bg-white"
                  >
                    {models.length > 0 ? models.map(m => (
                      <option key={m.model_id} value={m.model_id}>{m.name || m.model_id}</option>
                    )) : (
                      <>
                        <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                        <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-4o-mini">GPT-4o Mini</option>
                        <option value="claude-sonnet-4">Claude Sonnet 4</option>
                      </>
                    )}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase block mb-1">Chunks to Retrieve (Top K)</label>
                  <input
                    type="number" min={1} max={20} value={topK}
                    onChange={e => setTopK(Math.max(1, Math.min(20, parseInt(e.target.value) || 5)))}
                    className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none"
                  />
                </div>
              </div>
              <div className="mt-3 space-y-2">
                {[
                  { key: "answerGeneration", label: "Answer Generation Prompt", desc: "How answers are generated from retrieved chunks" },
                  { key: "testCaseGeneration", label: "Test Case Generation Prompt", desc: "How test Q&A pairs are generated from documents" },
                  { key: "evaluation", label: "Evaluation Prompt", desc: "How the LLM-as-judge evaluates RAG quality" },
                ].map(p => (
                  <div key={p.key} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2">
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-slate-700">{p.label}</div>
                      <div className="text-[11px] text-slate-400 truncate">{p.desc}</div>
                    </div>
                    <button
                      onClick={() => setEditingPrompt(p.key)}
                      className="flex items-center gap-1 text-[11px] text-jai-primary hover:text-[#C73D65] cursor-pointer bg-white border border-slate-200 px-2 py-1 rounded-lg font-medium shrink-0 ml-3"
                    >
                      <Edit3 size={10} /> Edit
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Upload Documents */}
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-slate-500 uppercase">Upload Documents</h3>
                <div className="flex items-center gap-2">
                  {uploadedFiles.length > 0 && (
                    <button
                      onClick={() => triggerIndex(selected.kb_id)}
                      disabled={actionLoading === "index" || uploading}
                      className="flex items-center gap-1.5 text-xs font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg px-3 py-1.5 cursor-pointer disabled:opacity-40 transition"
                    >
                      {actionLoading === "index" ? <Loader2 size={12} className="animate-spin" /> : <DownloadCloud size={12} />}
                      {actionLoading === "index" ? "Indexing..." : "Index All"}
                    </button>
                  )}
                </div>
              </div>

              {/* Hidden file input — use sr-only instead of hidden so .click() works */}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.doc,.txt,.md,.html,.csv,.json,.pptx,.xlsx"
                onChange={handleFileSelect}
                className="absolute w-0 h-0 overflow-hidden opacity-0"
                tabIndex={-1}
              />

              {/* Drag-and-drop zone */}
              <div
                className={cn(
                  "border-2 border-dashed rounded-lg p-6 text-center transition cursor-pointer",
                  dragOver ? "border-jai-primary bg-[#FDF1F5]/40" : "border-slate-200 hover:border-jai-primary hover:bg-[#FDF1F5]/20",
                  uploading && "pointer-events-none opacity-60"
                )}
                onClick={() => !uploading && fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                {uploading ? (
                  <>
                    <Loader2 size={24} className="mx-auto text-jai-primary mb-2 animate-spin" />
                    <p className="text-sm text-jai-primary font-medium">
                      Uploading {uploadProgress?.current}/{uploadProgress?.total}...
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1 truncate">{uploadProgress?.fileName}</p>
                  </>
                ) : (
                  <>
                    <FileUp size={24} className="mx-auto text-slate-400 mb-2" />
                    <p className="text-sm text-slate-600">
                      {dragOver ? "Drop files here" : "Click or drag files to upload"}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1">PDF, DOCX, TXT, MD, HTML, CSV, JSON, PPTX, XLSX</p>
                  </>
                )}
              </div>

              {/* Uploaded files list */}
              {uploadedFiles.length > 0 && (
                <div className="mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase">{uploadedFiles.length} File{uploadedFiles.length !== 1 ? "s" : ""}</span>
                  </div>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {uploadedFiles.map(f => (
                      <div key={f.id} className="flex items-center gap-2.5 bg-slate-50 rounded-lg px-3 py-2 group">
                        <File size={14} className="text-slate-400 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-medium text-slate-700 truncate">{f.file_name}</div>
                          <div className="text-[11px] text-slate-400">
                            {f.file_size_bytes ? `${(f.file_size_bytes / 1024).toFixed(1)} KB` : "—"}
                            {f.file_type ? ` · ${f.file_type.toUpperCase()}` : ""}
                          </div>
                        </div>
                        <span className={cn(
                          "text-[11px] font-medium px-2 py-0.5 rounded-full shrink-0",
                          f.status === "indexed" ? "bg-emerald-50 text-emerald-600" :
                          f.status === "syncing" ? "bg-blue-50 text-blue-600" :
                          f.status === "uploaded" ? "bg-amber-50 text-amber-600" :
                          f.status === "failed" ? "bg-red-50 text-red-600" :
                          "bg-slate-100 text-slate-500"
                        )}>
                          {f.status === "indexed" ? "Indexed" : f.status === "syncing" ? "Syncing..." : f.status === "uploaded" ? "Pending Index" : f.status}
                        </span>
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteFile(selected.kb_id, f.id); }}
                          className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 cursor-pointer transition p-0.5"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Test Query */}
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-slate-500 uppercase">Test Retrieval</h3>
                <span className="text-[11px] text-slate-400">Top K: {topK} chunks · Model: {evalModel}</span>
              </div>
              <div className="flex gap-2">
                <input
                  value={testQuery}
                  onChange={e => setTestQuery(e.target.value)}
                  placeholder="Ask a question about your documents..."
                  className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-jai-primary"
                  onKeyDown={e => e.key === "Enter" && runTest(selected.kb_id)}
                />
                <button
                  onClick={() => runTest(selected.kb_id)}
                  disabled={actionLoading === "test" || !testQuery.trim()}
                  className="bg-jai-primary text-white rounded-lg px-4 py-2 text-xs font-medium cursor-pointer hover:bg-jai-primary-hover disabled:opacity-40 flex items-center gap-1.5"
                >
                  <Search size={12} /> Test
                </button>
              </div>
              {testResults && (
                <div className="mt-3 space-y-2">
                  <div className="text-[11px] text-slate-400">Latency: {testResults.latency_ms}ms · {testResults.results?.length || 0} results</div>
                  {testResults.results?.map((r, i) => (
                    <div key={i} className="bg-slate-50 border border-slate-100 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] font-medium text-slate-500">{r.document} — Page {r.page}</span>
                        <span className={cn("text-[11px] font-bold", r.score >= 0.8 ? "text-emerald-600" : r.score >= 0.65 ? "text-amber-600" : "text-red-600")}>
                          Score: {r.score}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">{r.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Generate Test Data + Evaluate */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white border border-slate-200 rounded-xl p-4">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-xs font-semibold text-slate-500 uppercase">Generate Test Data</h3>
                  <button onClick={() => setEditingPrompt("testCaseGeneration")} className="text-[11px] text-slate-400 hover:text-jai-primary cursor-pointer flex items-center gap-0.5"><Edit3 size={9} /> Prompt</button>
                </div>
                <p className="text-[11px] text-slate-400 mb-3">Auto-generate Q&A pairs from your documents to test retrieval quality.</p>
                <button
                  onClick={() => generateTestData(selected.kb_id)}
                  disabled={actionLoading === "generate"}
                  className="w-full bg-slate-900 text-white rounded-lg px-3 py-2 text-xs font-medium cursor-pointer hover:bg-slate-800 flex items-center justify-center gap-1.5 disabled:opacity-40"
                >
                  <Sparkles size={12} /> {actionLoading === "generate" ? "Generating..." : "Generate Test Questions"}
                </button>
                {testData && (
                  <div className="mt-3 space-y-1.5">
                    {testData.test_data?.map((q, i) => (
                      <div key={i} className="bg-slate-50 rounded-lg px-3 py-2 text-xs">
                        <div className="text-slate-700 font-medium">{q.question}</div>
                        <div className="text-slate-400 text-[11px] mt-0.5">Expected: {q.expected_answer}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-4">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-xs font-semibold text-slate-500 uppercase">Evaluate RAG Quality</h3>
                  <button onClick={() => setEditingPrompt("evaluation")} className="text-[11px] text-slate-400 hover:text-jai-primary cursor-pointer flex items-center gap-0.5"><Edit3 size={9} /> Prompt</button>
                </div>
                <p className="text-[11px] text-slate-400 mb-2">LLM-as-judge evaluation for retrieval and answer quality.</p>
                <div className="flex items-center gap-2 mb-3">
                  <select value={evalModel} onChange={e => setEvalModel(e.target.value)} className="flex-1 border border-slate-200 rounded-lg px-2 py-1 text-[11px] outline-none bg-white">
                    {models.length > 0 ? models.map(m => (
                      <option key={m.model_id} value={m.model_id}>{m.name || m.model_id}</option>
                    )) : (
                      <>
                        <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                        <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-4o-mini">GPT-4o Mini</option>
                        <option value="claude-sonnet-4">Claude Sonnet 4</option>
                      </>
                    )}
                  </select>
                </div>
                <button
                  onClick={() => evaluate(selected.kb_id)}
                  disabled={actionLoading === "evaluate"}
                  className="w-full bg-jai-primary text-white rounded-lg px-3 py-2 text-xs font-medium cursor-pointer hover:bg-jai-primary-hover flex items-center justify-center gap-1.5 disabled:opacity-40"
                >
                  <BarChart3 size={12} /> {actionLoading === "evaluate" ? "Evaluating..." : "Run Evaluation"}
                </button>
                {evalResults && (
                  <div className="mt-3 space-y-2">
                    <div className="text-center mb-2">
                      <span className="text-2xl font-bold text-jai-primary">{Math.round(evalResults.evaluation.overall_score * 100)}%</span>
                      <span className="text-xs text-slate-400 ml-1">overall</span>
                    </div>
                    <EvalGauge label="Faithfulness" value={evalResults.evaluation.faithfulness} />
                    <EvalGauge label="Relevance" value={evalResults.evaluation.relevance} />
                    <EvalGauge label="Context Precision" value={evalResults.evaluation.context_precision} />
                    <EvalGauge label="Context Recall" value={evalResults.evaluation.context_recall} />
                    <EvalGauge label="Answer Correctness" value={evalResults.evaluation.answer_correctness} />
                    {evalResults.evaluation.accuracy != null && <EvalGauge label="Accuracy" value={evalResults.evaluation.accuracy} />}
                    <div className="text-[11px] text-slate-400 text-center mt-1">
                      {evalResults.questions_evaluated} questions · Model: {evalResults.model_used} · Top K: {topK}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create KB Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">Create Knowledge Base</h3>
              <button onClick={() => setShowCreate(false)} className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-900 hover:bg-slate-100 cursor-pointer"><X size={16} /></button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase block mb-1">Name</label>
                <input value={createForm.name} onChange={e => setCreateForm(p => ({ ...p, name: e.target.value }))} className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" placeholder="Contract Repository" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase block mb-1">Description</label>
                <textarea value={createForm.description} onChange={e => setCreateForm(p => ({ ...p, description: e.target.value }))} rows={2} className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none resize-none" placeholder="What documents will this contain?" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase block mb-1">Chunk Size (tokens)</label>
                  <input type="number" value={createForm.chunk_size} onChange={e => setCreateForm(p => ({ ...p, chunk_size: parseInt(e.target.value) || 512 }))} className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase block mb-1">Overlap (tokens)</label>
                  <input type="number" value={createForm.overlap} onChange={e => setCreateForm(p => ({ ...p, overlap: parseInt(e.target.value) || 64 }))} className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" />
                </div>
              </div>
              <div className="bg-slate-50 border border-slate-100 rounded-lg p-3">
                <div className="text-[11px] font-semibold text-slate-400 uppercase mb-1">Provider</div>
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <Database size={14} className="text-sky-500" />
                  Google Vertex AI Vector Search
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Embedding model: text-embedding-004 (768d)</div>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer">Cancel</button>
              <button
                onClick={createKb}
                disabled={!createForm.name.trim() || actionLoading === "create"}
                className="bg-jai-primary text-white rounded-lg px-4 py-2 text-xs font-medium cursor-pointer hover:bg-jai-primary-hover disabled:opacity-40 flex items-center gap-1.5"
              >
                <Plus size={12} /> {actionLoading === "create" ? "Creating..." : "Create Knowledge Base"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Prompt Editor Modal */}
      {editingPrompt && (
        <PromptEditorModal
          title={
            editingPrompt === "answerGeneration" ? "Answer Generation Prompt" :
            editingPrompt === "testCaseGeneration" ? "Test Case Generation Prompt" :
            "Evaluation Prompt"
          }
          value={prompts[editingPrompt]}
          onChange={(v) => setPrompts(prev => ({ ...prev, [editingPrompt]: v }))}
          onClose={() => setEditingPrompt(null)}
          onAiImprove={aiImprovePrompt}
          improving={improving}
        />
      )}
    </div>
  );
}
