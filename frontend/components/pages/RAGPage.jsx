"use client";
import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, EmptyState } from "../shared/StudioUI";
import { Brain, Plus, Upload, Trash2, Database } from "lucide-react";

export default function RAGPage() {
  const [collections, setCollections] = useState([]); const [docs, setDocs] = useState([]);
  const [selCol, setSelCol] = useState(null); const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false); const [newName, setNewName] = useState(""); const [newDesc, setNewDesc] = useState("");
  const loadCols = (retry = true) => { setLoading(true); apiFetch(`${API}/rag/collections`).then(r => r.json()).then(d => { setCollections(d.collections || []); setLoading(false); }).catch(() => { if (retry) { setTimeout(() => loadCols(false), 1500); } else { setLoading(false); } }); };
  useEffect(() => { loadCols(); }, []);
  const selectCol = async (col) => { setSelCol(col); const r = await apiFetch(`${API}/rag/collections/${col.collection_id}/documents`); const d = await r.json(); setDocs(d.documents || []); };
  const createCol = async () => { await apiFetch(`${API}/rag/collections`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newName, description: newDesc }) }); setShowCreate(false); setNewName(""); setNewDesc(""); loadCols(); };
  if (loading) return <div className="p-6 text-slate-400 text-sm">Loading RAG collections...</div>;
  if (!collections.length && !showCreate) return <div className="p-6 animate-fade-up max-w-5xl mx-auto"><EmptyState icon={<Brain size={24} />} illustration="upload" title="No RAG collections" description="Create a collection and upload documents." action={<button onClick={() => setShowCreate(true)} className="bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer"><Plus size={14} className="inline mr-1" />Create Collection</button>} /></div>;
  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto grid grid-cols-3 gap-6 items-start">
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="p-4 flex justify-between items-center border-b border-slate-100"><h2 className="text-sm font-semibold text-slate-900">Collections</h2><button onClick={() => setShowCreate(true)} className="p-1.5 border border-slate-200 rounded-lg text-slate-500 cursor-pointer hover:bg-slate-50"><Plus size={14} /></button></div>
        {showCreate && <div className="p-4 space-y-2 border-b border-slate-100">
          <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Collection name" className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" />
          <input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Description" className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none" />
          <div className="flex gap-2"><button onClick={createCol} disabled={!newName} className="bg-jai-primary text-white rounded-lg px-3 py-1.5 text-xs font-medium cursor-pointer">Create</button><button onClick={() => setShowCreate(false)} className="border border-slate-200 rounded-lg px-3 py-1.5 text-xs cursor-pointer">Cancel</button></div>
        </div>}
        <div className="p-2 space-y-1">
          {collections.map(c => (
            <div key={c.collection_id} onClick={() => selectCol(c)} className={cn("px-3 py-2.5 rounded-lg cursor-pointer transition", selCol?.collection_id === c.collection_id ? "bg-slate-100 border border-emerald-300" : "hover:bg-slate-50 border border-transparent")}>
              <div className="text-sm font-medium text-slate-900">{c.name}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">{c.document_count} documents</div>
            </div>
          ))}
        </div>
      </div>
      <div className="col-span-2 bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="p-4 flex justify-between items-center border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-900">{selCol ? `Documents — ${selCol.name}` : "Select a collection"}</h2>
          {selCol && <button className="text-sm text-slate-600 flex items-center gap-1 cursor-pointer hover:text-slate-900"><Upload size={14} /> Upload</button>}
        </div>
        {!selCol ? <div className="p-10 text-center text-sm text-slate-400">Select a collection to view documents</div> : docs.length === 0 ? (
          <div className="p-10 text-center"><div className="text-sm text-slate-400 mb-3">No documents in this collection</div><button className="text-sm text-slate-600 flex items-center gap-1 mx-auto cursor-pointer"><Upload size={14} /> Upload Documents</button></div>
        ) : (
          <div className="p-4 space-y-2">
            {docs.map(d => (
              <div key={d.doc_id} className="flex justify-between items-start py-3 border-b border-slate-100 last:border-0">
                <div><div className="text-sm text-slate-900">{d.content.slice(0, 120)}...</div><div className="text-[11px] text-slate-400 mt-1">{d.token_count} tokens · {d.doc_id}</div></div>
                <button className="p-1.5 text-red-400 hover:text-red-600 cursor-pointer"><Trash2 size={14} /></button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
