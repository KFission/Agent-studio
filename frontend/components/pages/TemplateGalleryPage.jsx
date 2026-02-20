"use client";
import { useState, useEffect } from "react";
import apiFetch from "../../lib/apiFetch";
import { cn } from "../../lib/cn";
import { API, Badge, SearchInput, EmptyState, toast } from "../shared/StudioUI";
import {
  LayoutGrid, Plus, Bot, Search, Zap, ArrowRight, DollarSign, BarChart3,
  MessageCircle, Workflow, Eye, X, Download, Star, Upload, Globe, Users,
  TrendingUp, Shield, Briefcase, Monitor, Scale, ChevronDown, Loader2,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════
// PAGE: Agent Marketplace & Templates
// ═══════════════════════════════════════════════════════════════════

const TEMPLATE_CATEGORIES = [
  { id: "procurement", label: "Procurement", icon: DollarSign, color: "bg-emerald-50 text-emerald-600" },
  { id: "data", label: "Data & Analytics", icon: BarChart3, color: "bg-blue-50 text-blue-600" },
  { id: "support", label: "Customer Support", icon: MessageCircle, color: "bg-violet-50 text-violet-600" },
  { id: "automation", label: "Automation", icon: Workflow, color: "bg-amber-50 text-amber-600" },
  { id: "finance", label: "Finance", icon: DollarSign, color: "bg-teal-50 text-teal-600" },
  { id: "hr", label: "HR", icon: Users, color: "bg-pink-50 text-pink-600" },
  { id: "legal", label: "Legal", icon: Scale, color: "bg-indigo-50 text-indigo-600" },
  { id: "it_ops", label: "IT Ops", icon: Monitor, color: "bg-orange-50 text-orange-600" },
  { id: "custom", label: "Custom", icon: Bot, color: "bg-slate-100 text-slate-600" },
];

const AGENT_TEMPLATES = [
  { id: "tpl-bid-analyzer", name: "Bid Analyzer", description: "Score and compare supplier bids across evaluation criteria with a 15-step workflow.", category: "procurement", complexity: "advanced", tools: ["Jaggaer RFQ API", "LLM Scoring"], tags: ["sourcing", "award-decision"] },
  { id: "tpl-supplier-risk", name: "Supplier Risk Monitor", description: "Continuously assess supplier risk using financial data, news, and compliance records.", category: "procurement", complexity: "intermediate", tools: ["Web Search", "Database Query"], tags: ["risk", "compliance"] },
  { id: "tpl-rfq-summarizer", name: "RFQ Summarizer", description: "Extract key requirements, deadlines, and evaluation criteria from RFQ documents.", category: "procurement", complexity: "basic", tools: ["Document Parser", "LLM"], tags: ["rfq", "summarization"] },
  { id: "tpl-invoice-processor", name: "Invoice Processor", description: "Automate 3-way matching: PO → Receipt → Invoice. Flag discrepancies for human review.", category: "procurement", complexity: "advanced", tools: ["Jaggaer AP API", "OCR"], tags: ["ap", "invoice"] },
  { id: "tpl-data-analyst", name: "Data Analyst", description: "Query databases, generate charts, and summarize insights in natural language.", category: "data", complexity: "intermediate", tools: ["SQL Query", "Chart Gen"], tags: ["analytics", "reporting"] },
  { id: "tpl-report-builder", name: "Report Builder", description: "Generate weekly/monthly reports from multiple data sources with executive summaries.", category: "data", complexity: "basic", tools: ["Database Query", "Template Engine"], tags: ["reporting"] },
  { id: "tpl-ticket-handler", name: "Ticket Handler", description: "Classify, route, and draft responses for incoming support tickets.", category: "support", complexity: "intermediate", tools: ["Ticket API", "LLM Classification"], tags: ["support", "routing"] },
  { id: "tpl-faq-bot", name: "FAQ Bot", description: "RAG-powered Q&A agent grounded on your knowledge base documents.", category: "support", complexity: "basic", tools: ["RAG Retrieval"], tags: ["faq", "knowledge-base"] },
  { id: "tpl-doc-workflow", name: "Document Workflow", description: "Route documents through review → approve → sign → archive pipeline.", category: "automation", complexity: "advanced", tools: ["Document API", "Approval Queue"], tags: ["workflow", "documents"] },
  { id: "tpl-email-responder", name: "Email Auto-Responder", description: "Classify incoming emails and draft contextual responses for human review.", category: "automation", complexity: "intermediate", tools: ["Email API", "LLM"], tags: ["email", "automation"] },
];

const COMPLEXITY_COLORS = { basic: "success", intermediate: "info", advanced: "warning" };

function StarRating({ rating, size = 12 }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <Star key={i} size={size} className={i <= Math.round(rating) ? "text-amber-400 fill-amber-400" : "text-slate-200"} />
      ))}
    </div>
  );
}

function StarInput({ value, onChange }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map(i => (
        <button key={i} type="button" onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(0)}
          onClick={() => onChange(i)} className="cursor-pointer">
          <Star size={18} className={i <= (hover || value) ? "text-amber-400 fill-amber-400" : "text-slate-300"} />
        </button>
      ))}
    </div>
  );
}

export default function TemplateGalleryPage({ setPage, setEditAgent }) {
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("all");
  const [preview, setPreview] = useState(null);
  const [sortBy, setSortBy] = useState("popular");

  // Marketplace state
  const [listings, setListings] = useState([]);
  const [loadingListings, setLoadingListings] = useState(false);
  const [mktStats, setMktStats] = useState(null);
  const [detailListing, setDetailListing] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [installing, setInstalling] = useState(null);

  // Publish modal
  const [showPublish, setShowPublish] = useState(false);
  const [agents, setAgents] = useState([]);
  const [publishForm, setPublishForm] = useState({ agent_id: "", category: "custom", long_description: "", complexity: "intermediate", tags: "", publisher_name: "" });
  const [publishing, setPublishing] = useState(false);

  // Review modal
  const [showReview, setShowReview] = useState(null);
  const [reviewForm, setReviewForm] = useState({ rating: 5, comment: "" });
  const [submittingReview, setSubmittingReview] = useState(false);

  // Load marketplace data — always load on mount
  const fetchListings = () => {
    setLoadingListings(true);
    const params = new URLSearchParams();
    if (catFilter !== "all") params.set("category", catFilter);
    if (search) params.set("search", search);
    params.set("sort_by", sortBy);
    apiFetch(`${API}/marketplace/listings?${params}`)
      .then(r => r.json()).then(d => setListings(d.listings || []))
      .catch(() => {}).finally(() => setLoadingListings(false));
  };

  useEffect(() => {
    fetchListings();
    apiFetch(`${API}/marketplace/stats`).then(r => r.json()).then(setMktStats).catch(() => {});
  }, []);

  useEffect(() => {
    fetchListings();
  }, [catFilter, search, sortBy]);

  // Load agents for publish modal
  useEffect(() => {
    if (showPublish) {
      apiFetch(`${API}/agents`).then(r => r.json()).then(d => setAgents(d.agents || [])).catch(() => {});
    }
  }, [showPublish]);

  // Templates filter
  const filteredTemplates = AGENT_TEMPLATES.filter(t => {
    if (catFilter !== "all" && t.category !== catFilter) return false;
    if (search && !t.name.toLowerCase().includes(search.toLowerCase()) && !t.description.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const useTemplate = (tpl) => {
    toast.success(`Creating agent from "${tpl.name}" template`);
    setPage("AgentBuilder");
  };

  const installListing = async (listing) => {
    setInstalling(listing.listing_id);
    try {
      const r = await apiFetch(`${API}/marketplace/listings/${listing.listing_id}/install`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "current-user", tenant_id: "current-tenant" }),
      });
      const data = await r.json();
      toast.success(`Installed "${listing.name}" as agent ${data.agent_id}`);
      fetchListings();
    } catch (e) {
      toast.error("Install failed: " + e.message);
    }
    setInstalling(null);
  };

  const publishAgent = async () => {
    if (!publishForm.agent_id) return;
    setPublishing(true);
    try {
      const r = await apiFetch(`${API}/marketplace/publish`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...publishForm,
          tags: publishForm.tags ? publishForm.tags.split(",").map(t => t.trim()).filter(Boolean) : [],
        }),
      });
      const data = await r.json();
      toast.success(`Published "${data.name}" to marketplace`);
      setShowPublish(false);
      setPublishForm({ agent_id: "", category: "custom", long_description: "", complexity: "intermediate", tags: "", publisher_name: "" });
      fetchListings();
    } catch (e) {
      toast.error("Publish failed: " + e.message);
    }
    setPublishing(false);
  };

  const submitReview = async () => {
    if (!showReview) return;
    setSubmittingReview(true);
    try {
      await apiFetch(`${API}/marketplace/listings/${showReview}/review`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "current-user", user_name: "You", ...reviewForm }),
      });
      toast.success("Review submitted");
      setShowReview(null);
      setReviewForm({ rating: 5, comment: "" });
      fetchListings();
      if (detailListing?.listing_id === showReview) loadDetail(showReview);
    } catch (e) {
      toast.error("Review failed");
    }
    setSubmittingReview(false);
  };

  const loadDetail = async (id) => {
    setLoadingDetail(true);
    try {
      const r = await apiFetch(`${API}/marketplace/listings/${id}`);
      setDetailListing(await r.json());
    } catch { setDetailListing(null); }
    setLoadingDetail(false);
  };

  const catForId = (id) => TEMPLATE_CATEGORIES.find(c => c.id === id);

  return (
    <div className="p-6 animate-fade-up max-w-6xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Agent Marketplace</h1>
          <p className="text-sm text-slate-500 mt-0.5">Browse starter templates, discover community agents, and publish your own</p>
        </div>
        <button onClick={() => setShowPublish(true)}
          className="flex items-center gap-2 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer hover:bg-jai-primary-hover transition">
          <Upload size={14} /> Publish Agent
        </button>
      </div>

      {/* Stats bar */}
      {mktStats && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Published", value: mktStats.published || 0, icon: Globe },
            { label: "Featured", value: mktStats.featured || 0, icon: Star },
            { label: "Total Installs", value: mktStats.total_installs || 0, icon: Download },
            { label: "Reviews", value: mktStats.total_reviews || 0, icon: MessageCircle },
          ].map(s => (
            <div key={s.label} className="bg-white border border-slate-200 rounded-xl px-4 py-3 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center"><s.icon size={14} className="text-slate-400" /></div>
              <div><div className="text-lg font-bold text-slate-900">{s.value}</div><div className="text-[11px] text-slate-400 uppercase">{s.label}</div></div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => setCatFilter("all")}
          className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition cursor-pointer",
            catFilter === "all" ? "bg-jai-primary text-white border-jai-primary" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50")}>
          All
        </button>
        {TEMPLATE_CATEGORIES.map(c => (
          <button key={c.id} onClick={() => setCatFilter(c.id)}
            className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition cursor-pointer flex items-center gap-1.5",
              catFilter === c.id ? "bg-jai-primary text-white border-jai-primary" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50")}>
            <c.icon size={12} /> {c.label}
          </button>
        ))}

        <div className="flex-1" />

        <select value={sortBy} onChange={e => setSortBy(e.target.value)}
          className="border border-slate-200 rounded-lg px-2 py-1.5 text-xs text-slate-600 outline-none bg-white cursor-pointer">
          <option value="popular">Most Popular</option>
          <option value="newest">Newest</option>
          <option value="rating">Highest Rated</option>
          <option value="name">A-Z</option>
        </select>
        <SearchInput value={search} onChange={setSearch} placeholder="Search agents & templates..." />
      </div>

      {/* ═══════ STARTER TEMPLATES ═══════ */}
      {filteredTemplates.length > 0 && (
        <>
          <div className="flex items-center gap-2 mt-1">
            <LayoutGrid size={14} className="text-slate-400" />
            <h2 className="text-sm font-semibold text-slate-700">Starter Templates</h2>
            <span className="text-[11px] text-slate-400">{filteredTemplates.length} templates</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTemplates.map(tpl => {
              const cat = catForId(tpl.category);
              return (
                <div key={tpl.id} className="bg-white border border-slate-200/80 rounded-xl overflow-hidden hover:shadow-lg hover:-translate-y-0.5 hover:border-slate-300 transition-all duration-200">
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center shrink-0", cat?.color || "bg-slate-100 text-slate-600")}>
                        {cat ? <cat.icon size={18} /> : <Bot size={18} />}
                      </div>
                      <Badge variant={COMPLEXITY_COLORS[tpl.complexity]}>{tpl.complexity}</Badge>
                    </div>
                    <h3 className="text-sm font-semibold text-slate-900">{tpl.name}</h3>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{tpl.description}</p>
                    <div className="flex flex-wrap gap-1 mt-3">
                      {tpl.tools.map(t => <span key={t} className="text-[11px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{t}</span>)}
                    </div>
                  </div>
                  <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
                    <button onClick={() => setPreview(tpl)} className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer"><Eye size={12} /> Preview</button>
                    <button onClick={() => useTemplate(tpl)} className="text-xs text-white bg-jai-primary rounded-lg px-3 py-1.5 font-medium cursor-pointer flex items-center gap-1"><Plus size={12} /> Use Template</button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ═══════ COMMUNITY AGENTS ═══════ */}
      <div className="flex items-center gap-2 mt-1">
        <Globe size={14} className="text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-700">Community Agents</h2>
        {listings.length > 0 && <span className="text-[11px] text-slate-400">{listings.length} published</span>}
      </div>
      {loadingListings ? (
        <div className="flex items-center justify-center py-12"><Loader2 size={24} className="animate-spin text-slate-400" /></div>
      ) : listings.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {listings.map(l => {
                const cat = catForId(l.category);
                return (
                  <div key={l.listing_id} className="bg-white border border-slate-200/80 rounded-xl overflow-hidden hover:shadow-lg hover:-translate-y-0.5 hover:border-slate-300 transition-all duration-200">
                    {l.featured && (
                      <div className="bg-gradient-to-r from-amber-400 to-amber-500 px-4 py-1 text-[11px] font-bold text-white uppercase tracking-wider flex items-center gap-1">
                        <Star size={10} className="fill-white" /> Featured
                      </div>
                    )}
                    <div className="p-5">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center shrink-0", cat?.color || "bg-slate-100 text-slate-600")}>
                          {cat ? <cat.icon size={18} /> : <Bot size={18} />}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Badge variant={COMPLEXITY_COLORS[l.complexity] || "info"}>{l.complexity}</Badge>
                        </div>
                      </div>
                      <h3 className="text-sm font-semibold text-slate-900">{l.name}</h3>
                      <p className="text-xs text-slate-500 mt-1 line-clamp-2">{l.description}</p>
                      {/* Rating + stats */}
                      <div className="flex items-center gap-3 mt-3">
                        {l.avg_rating > 0 && (
                          <div className="flex items-center gap-1">
                            <StarRating rating={l.avg_rating} size={10} />
                            <span className="text-[11px] text-slate-500">{l.avg_rating}</span>
                          </div>
                        )}
                        <div className="flex items-center gap-1 text-[11px] text-slate-400">
                          <Download size={10} /> {l.install_count}
                        </div>
                        {l.review_count > 0 && (
                          <div className="flex items-center gap-1 text-[11px] text-slate-400">
                            <MessageCircle size={10} /> {l.review_count}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {l.tools_used?.slice(0, 3).map(t => <span key={t} className="text-[11px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{t}</span>)}
                        {l.tags?.slice(0, 2).map(t => <span key={t} className="text-[11px] bg-violet-50 text-violet-500 px-1.5 py-0.5 rounded">{t}</span>)}
                      </div>
                      <div className="flex items-center gap-2 mt-2 text-[11px] text-slate-400">
                        <span>by <strong className="text-slate-600">{l.publisher_name || "Anonymous"}</strong></span>
                        {l.model_id && <span className="bg-slate-100 px-1.5 py-0.5 rounded">{l.model_id}</span>}
                      </div>
                    </div>
                    <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
                      <button onClick={() => loadDetail(l.listing_id)} className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 cursor-pointer"><Eye size={12} /> Details</button>
                      <div className="flex items-center gap-2">
                        <button onClick={() => { setShowReview(l.listing_id); setReviewForm({ rating: 5, comment: "" }); }}
                          className="text-xs text-slate-400 hover:text-amber-500 cursor-pointer"><Star size={12} /></button>
                        <button onClick={() => installListing(l)} disabled={installing === l.listing_id}
                          className={cn("text-xs text-white bg-jai-primary rounded-lg px-3 py-1.5 font-medium cursor-pointer flex items-center gap-1",
                            installing === l.listing_id && "opacity-50 cursor-not-allowed")}>
                          {installing === l.listing_id ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />} Install
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
        </div>
      ) : (
        <EmptyState icon={<Globe size={24} />} illustration="search" title="No community agents yet"
          description="Be the first to publish an agent! Click 'Publish Agent' above to share with the community." />
      )}

      {filteredTemplates.length === 0 && listings.length === 0 && !loadingListings && (
        <EmptyState icon={<LayoutGrid size={24} />} illustration="search" title="No results found" description="Try adjusting your search or category filter." />
      )}

      {/* ═══════ TEMPLATE PREVIEW MODAL ═══════ */}
      {preview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setPreview(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">{preview.name}</h3>
                <div className="flex gap-2 mt-1"><Badge variant={COMPLEXITY_COLORS[preview.complexity]}>{preview.complexity}</Badge><Badge variant="outline">{preview.category}</Badge></div>
              </div>
              <button onClick={() => setPreview(null)} className="text-slate-400 hover:text-slate-900 cursor-pointer"><X size={16} /></button>
            </div>
            <p className="text-sm text-slate-600 mb-4">{preview.description}</p>
            <div className="space-y-3">
              <div><h4 className="text-xs font-semibold text-slate-500 uppercase mb-1">Tools Required</h4><div className="flex flex-wrap gap-1">{preview.tools.map(t => <Badge key={t} variant="outline">{t}</Badge>)}</div></div>
              <div><h4 className="text-xs font-semibold text-slate-500 uppercase mb-1">Tags</h4><div className="flex flex-wrap gap-1">{preview.tags.map(t => <Badge key={t} variant="info">{t}</Badge>)}</div></div>
            </div>
            <div className="flex gap-2 mt-6">
              <button onClick={() => setPreview(null)} className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer hover:bg-slate-50">Close</button>
              <button onClick={() => { setPreview(null); useTemplate(preview); }} className="flex-1 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer">Use This Template</button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════ MARKETPLACE DETAIL MODAL ═══════ */}
      {detailListing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setDetailListing(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            {detailListing.featured && (
              <div className="bg-gradient-to-r from-amber-400 to-amber-500 px-6 py-1.5 text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1 rounded-t-2xl">
                <Star size={12} className="fill-white" /> Featured Agent
              </div>
            )}
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{detailListing.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant={COMPLEXITY_COLORS[detailListing.complexity]}>{detailListing.complexity}</Badge>
                    <Badge variant="outline">{detailListing.category}</Badge>
                    {detailListing.avg_rating > 0 && (
                      <div className="flex items-center gap-1"><StarRating rating={detailListing.avg_rating} size={11} /><span className="text-xs text-slate-500">{detailListing.avg_rating} ({detailListing.review_count})</span></div>
                    )}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    by <strong className="text-slate-600">{detailListing.publisher_name}</strong> &middot; v{detailListing.version} &middot; {detailListing.install_count} installs
                  </div>
                </div>
                <button onClick={() => setDetailListing(null)} className="text-slate-400 hover:text-slate-900 cursor-pointer"><X size={16} /></button>
              </div>
              <p className="text-sm text-slate-600 mb-4">{detailListing.long_description || detailListing.description}</p>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div><h4 className="text-xs font-semibold text-slate-500 uppercase mb-1">Tools</h4><div className="flex flex-wrap gap-1">{(detailListing.tools_used || []).map(t => <Badge key={t} variant="outline">{t}</Badge>)}</div></div>
                <div><h4 className="text-xs font-semibold text-slate-500 uppercase mb-1">Tags</h4><div className="flex flex-wrap gap-1">{(detailListing.tags || []).map(t => <Badge key={t} variant="info">{t}</Badge>)}</div></div>
                <div><h4 className="text-xs font-semibold text-slate-500 uppercase mb-1">Model</h4><span className="text-xs text-slate-700">{detailListing.model_id || "—"}</span></div>
                <div><h4 className="text-xs font-semibold text-slate-500 uppercase mb-1">RAG</h4><span className="text-xs text-slate-700">{detailListing.rag_enabled ? "Enabled" : "Disabled"}</span></div>
              </div>
              {detailListing.requires_api_keys?.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 mb-4">
                  <div className="text-xs font-semibold text-amber-700 mb-1">Requires API Keys</div>
                  <div className="flex gap-1">{detailListing.requires_api_keys.map(k => <Badge key={k} variant="warning">{k}</Badge>)}</div>
                </div>
              )}
              {/* Reviews */}
              {detailListing.reviews?.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Reviews</h4>
                  <div className="space-y-2">
                    {detailListing.reviews.map(r => (
                      <div key={r.review_id} className="bg-slate-50 rounded-lg px-3 py-2">
                        <div className="flex items-center gap-2 mb-0.5">
                          <StarRating rating={r.rating} size={10} />
                          <span className="text-xs font-medium text-slate-700">{r.user_name || "User"}</span>
                        </div>
                        {r.comment && <p className="text-xs text-slate-500">{r.comment}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex gap-2 mt-6">
                <button onClick={() => setDetailListing(null)} className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer hover:bg-slate-50">Close</button>
                <button onClick={() => { setShowReview(detailListing.listing_id); setReviewForm({ rating: 5, comment: "" }); }}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer hover:bg-slate-50 flex items-center gap-1"><Star size={12} /> Review</button>
                <button onClick={() => { setDetailListing(null); installListing(detailListing); }}
                  className="flex-1 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer flex items-center justify-center gap-1"><Download size={14} /> Install Agent</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═══════ PUBLISH MODAL ═══════ */}
      {showPublish && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowPublish(false)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900">Publish to Marketplace</h3>
              <button onClick={() => setShowPublish(false)} className="text-slate-400 hover:text-slate-900 cursor-pointer"><X size={16} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Select Agent</label>
                <select value={publishForm.agent_id} onChange={e => setPublishForm(p => ({ ...p, agent_id: e.target.value }))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300">
                  <option value="">Choose an agent...</option>
                  {agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.name} (v{a.version})</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Publisher Name</label>
                <input value={publishForm.publisher_name} onChange={e => setPublishForm(p => ({ ...p, publisher_name: e.target.value }))}
                  placeholder="Your name or team name" className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Category</label>
                  <select value={publishForm.category} onChange={e => setPublishForm(p => ({ ...p, category: e.target.value }))}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300">
                    {TEMPLATE_CATEGORIES.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Complexity</label>
                  <select value={publishForm.complexity} onChange={e => setPublishForm(p => ({ ...p, complexity: e.target.value }))}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300">
                    <option value="basic">Basic</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Description</label>
                <textarea value={publishForm.long_description} onChange={e => setPublishForm(p => ({ ...p, long_description: e.target.value }))}
                  placeholder="Detailed description for marketplace listing..." rows={3}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300 resize-none" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Tags (comma-separated)</label>
                <input value={publishForm.tags} onChange={e => setPublishForm(p => ({ ...p, tags: e.target.value }))}
                  placeholder="procurement, sourcing, analysis" className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300" />
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button onClick={() => setShowPublish(false)} className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer hover:bg-slate-50">Cancel</button>
              <button onClick={publishAgent} disabled={!publishForm.agent_id || publishing}
                className={cn("flex-1 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer flex items-center justify-center gap-1",
                  (!publishForm.agent_id || publishing) && "opacity-50 cursor-not-allowed")}>
                {publishing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                {publishing ? "Publishing..." : "Publish"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════ REVIEW MODAL ═══════ */}
      {showReview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowReview(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-slate-900">Rate & Review</h3>
              <button onClick={() => setShowReview(null)} className="text-slate-400 hover:text-slate-900 cursor-pointer"><X size={16} /></button>
            </div>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500">Rating:</span>
                <StarInput value={reviewForm.rating} onChange={r => setReviewForm(p => ({ ...p, rating: r }))} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Comment (optional)</label>
                <textarea value={reviewForm.comment} onChange={e => setReviewForm(p => ({ ...p, comment: e.target.value }))}
                  placeholder="Share your experience..." rows={3}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-300 resize-none" />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowReview(null)} className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer hover:bg-slate-50">Cancel</button>
              <button onClick={submitReview} disabled={submittingReview}
                className={cn("flex-1 bg-jai-primary text-white rounded-lg px-4 py-2 text-sm font-medium cursor-pointer",
                  submittingReview && "opacity-50 cursor-not-allowed")}>
                {submittingReview ? "Submitting..." : "Submit Review"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
