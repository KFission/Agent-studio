"""
JAI Agent OS — Seed Templates
Pre-built agent templates, tool definitions, and configurations
extracted from Agents_GP (Jaggaer Direct Sourcing) and ChatwithData
(Procurement Intelligence) codebases.

Provides ready-to-use templates so users see real examples on first load.
"""

import uuid
from datetime import datetime


def _id(prefix="tpl"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT TEMPLATES — from Agents_GP/jaggaer_agents + ChatwithData
# ═══════════════════════════════════════════════════════════════════════════════

SEED_AGENTS = [
    # ── Agents_GP: Direct Sourcing Agents ──────────────────────────────────
    {
        "agent_id": "agent-bid-analyzer",
        "name": "Bid Analyzer Agent",
        "description": "Score and compare supplier bids across defined evaluation criteria. "
                       "Implements a 15-step LangGraph workflow: capture bids → validate completeness → "
                       "autoscore non-price → load cost breakdown → calculate cost score → retrieve risk → "
                       "evaluate compliance → aggregate scores → flag exceptions → build award scenarios → "
                       "compare → select preferred → determine split award → route approval → finalize.",
        "category": "procurement",
        "graph_type": "langgraph",
        "status": "active",
        "tags": ["sourcing", "bid-analysis", "award-decision", "direct-sourcing"],
        "config": {
            "llm_model": "gemini-2.5-flash",
            "temperature": 0.3,
            "max_tokens": 2000,
            "cost_weight": 0.50,
            "quality_weight": 0.20,
            "delivery_weight": 0.15,
            "risk_weight": 0.10,
            "compliance_weight": 0.05,
            "hitl_approval_threshold": 10000.0,
            "hitl_risk_threshold": 0.7,
        },
        "tools": ["jaggaer-rfq-api", "jaggaer-supplier-api", "jaggaer-document-api", "llm-scoring"],
        "workflow_steps": [
            "capture_bid_submissions", "validate_bid_completeness", "autoscore_non_price",
            "load_cost_breakdown", "calculate_cost_score", "retrieve_risk_score",
            "evaluate_compliance", "aggregate_bid_scores", "flag_bid_exceptions",
            "build_award_scenarios", "compare_scenarios", "select_preferred_scenario",
            "determine_split_award", "route_award_for_approval", "finalize_award_decision"
        ],
        "metrics": {"decision_speed": "30% faster award decisions", "fairness": "improved bid fairness"},
        "api_readiness": "90%",
    },
    {
        "agent_id": "agent-supplier-data-change",
        "name": "Supplier Data Change Agent",
        "description": "Validate, process, and track updates to supplier master data records. "
                       "14-step workflow: capture request → classify change → verify mandatory data → "
                       "validate bank account → collect documents → score risk → determine approval → "
                       "approve profile → select update method → update master → bulk import → "
                       "sync via API → notify stakeholders → close request.",
        "category": "procurement",
        "graph_type": "langgraph",
        "status": "active",
        "tags": ["supplier-management", "master-data", "data-quality", "direct-sourcing"],
        "config": {
            "llm_model": "gemini-2.5-flash",
            "temperature": 0.3,
            "max_tokens": 2000,
            "confidence_threshold": 0.8,
            "max_retries": 3,
        },
        "tools": ["jaggaer-supplier-api", "jaggaer-document-api", "jaggaer-action-api", "llm-classification"],
        "workflow_steps": [
            "capture_update_request", "classify_change_type", "verify_mandatory_data",
            "validate_bank_account", "collect_supporting_documents", "score_change_risk",
            "determine_approval_workflow", "approve_supplier_profile", "select_update_method",
            "update_supplier_master", "bulk_import_supplier_data", "sync_supplier_master_via_api",
            "notify_stakeholders", "close_change_request"
        ],
        "metrics": {"accuracy": "90% master data accuracy", "errors": "fewer AP errors"},
        "api_readiness": "100%",
    },
    {
        "agent_id": "agent-workflow-approval",
        "name": "Workflow Approval Agent",
        "description": "Route purchase requests for approval based on rules and org structure. "
                       "15-step workflow: capture PR → validate data → classify spend → verify budget → "
                       "assess thresholds → determine path → identify approvers → resolve delegations → "
                       "create tasks → route approval → capture decision → handle rejection → "
                       "escalate delays → finalize outcome → update PR status.",
        "category": "procurement",
        "graph_type": "langgraph",
        "status": "active",
        "tags": ["approval", "purchase-request", "workflow", "direct-sourcing"],
        "config": {
            "llm_model": "gemini-2.5-flash",
            "temperature": 0.3,
            "max_tokens": 2000,
            "policy_tiers": {
                "tier_1": {"max_amount": 1000, "approvers": ["manager"]},
                "tier_2": {"max_amount": 10000, "approvers": ["manager", "director"]},
                "tier_3": {"max_amount": 50000, "approvers": ["manager", "director", "vp"]},
                "tier_4": {"max_amount": 999999999, "approvers": ["manager", "director", "vp", "cfo"]},
            },
        },
        "tools": ["jaggaer-action-api", "jaggaer-user-api", "llm-classification"],
        "workflow_steps": [
            "capture_pr_submission", "validate_pr_data", "classify_spend",
            "verify_budget", "assess_policy_thresholds", "determine_approval_path",
            "identify_approvers", "resolve_delegations", "create_workflow_tasks",
            "route_for_approval", "capture_approver_decision", "handle_rejection",
            "escalate_delays", "finalize_approval_outcome", "update_pr_status"
        ],
        "metrics": {"speed": "60% faster approvals", "integrity": "maintained policy integrity"},
        "api_readiness": "86%",
    },
    {
        "agent_id": "agent-supplier-collaboration",
        "name": "Supplier Collaboration Agent",
        "description": "Facilitate communication, task updates, and document sharing with suppliers. "
                       "13-step workflow: grant portal access → compile worklist → publish → "
                       "request compliance docs → receive docs → track expiry → send notifications → "
                       "create corrective action → assign tasks → monitor progress → "
                       "update scorecard → initiate improvement plan → archive cycle.",
        "category": "procurement",
        "graph_type": "langgraph",
        "status": "active",
        "tags": ["supplier-collaboration", "compliance", "scorecard", "direct-sourcing"],
        "config": {
            "llm_model": "gemini-2.5-flash",
            "temperature": 0.3,
            "max_tokens": 2000,
            "required_doc_types": ["certificate", "insurance", "nda", "quality_cert", "iso_cert"],
            "expiry_warning_days": [60, 30, 7],
        },
        "tools": ["jaggaer-supplier-api", "jaggaer-document-api", "jaggaer-action-api", "llm-scoring"],
        "workflow_steps": [
            "grant_portal_access", "compile_task_worklist", "publish_worklist",
            "request_compliance_documents", "receive_supplier_documents", "track_document_expiry",
            "send_expiry_notifications", "create_corrective_action", "assign_corrective_tasks",
            "monitor_task_progress", "update_supplier_scorecard", "initiate_improvement_plan",
            "archive_collaboration_cycle"
        ],
        "metrics": {"scorecard": "15% improvement in supplier scorecards"},
        "api_readiness": "86%",
    },

    # ── ChatwithData: Procurement Intelligence Agents ──────────────────────
    {
        "agent_id": "agent-procurement-supervisor",
        "name": "Procurement Intelligence Supervisor",
        "description": "LangGraph supervisor that orchestrates the full text-to-SQL pipeline for "
                       "procurement analytics. Classifies intent, routes to domain agents, coordinates "
                       "cross-domain queries, manages human-in-the-loop review, and formats responses. "
                       "Supports 8 intent domains: spend analysis, contract query, sourcing events, "
                       "supplier lookup, savings tracking, purchase ops, category strategy, cross-domain.",
        "category": "analytics",
        "graph_type": "langgraph",
        "status": "active",
        "tags": ["analytics", "text-to-sql", "procurement-intelligence", "supervisor"],
        "config": {
            "claude_model": "claude-sonnet-4-20250514",
            "claude_max_tokens": 8192,
            "gemini_pro_model": "gemini-2.5-flash",
            "gemini_flash_model": "gemini-2.0-flash-exp",
            "enable_human_review": True,
            "sql_max_rows": 10000,
            "sql_timeout_seconds": 60,
        },
        "tools": ["snowflake-query", "schema-vectorizer", "few-shot-store", "llm-sql-generation"],
        "workflow_steps": [
            "intent_classifier", "router", "domain_agent", "human_review",
            "query_executor", "insight_generator", "response_formatter"
        ],
        "intent_domains": {
            "spend_analysis": "Spend analytics and category breakdown",
            "contract_query": "Contract intelligence and compliance",
            "sourcing_event": "Sourcing events and RFx management",
            "supplier_lookup": "Supplier management and performance",
            "savings_tracking": "Value and savings tracking",
            "purchase_ops": "Purchase operations and PO management",
            "category_strategy": "Category strategy and market analysis",
            "cross_domain": "Cross-domain savings and analytics",
        },
    },
    {
        "agent_id": "agent-domain-spend",
        "name": "Spend Analytics Domain Agent",
        "description": "Domain-specific agent for spend analysis queries. Implements a 7-step "
                       "text-to-SQL pipeline: load semantic model → build schema context (vector retrieval) → "
                       "enrich query (entity resolution) → generate SQL → validate SQL → explain SQL → return.",
        "category": "analytics",
        "graph_type": "langgraph",
        "status": "active",
        "tags": ["analytics", "spend-analysis", "text-to-sql", "domain-agent"],
        "config": {
            "domain": "spend",
            "semantic_model_name": "spend_analytics",
            "schema_retrieval_top_k": 10,
        },
        "tools": ["snowflake-query", "schema-vectorizer", "llm-sql-generation"],
        "workflow_steps": [
            "load_semantic_model", "build_schema_context", "enrich_query",
            "generate_sql", "validate_sql", "explain_sql", "return_result"
        ],
    },
    {
        "agent_id": "agent-domain-contract",
        "name": "Contract Intelligence Domain Agent",
        "description": "Domain-specific agent for contract queries and compliance analysis. "
                       "Same 7-step pipeline as spend agent but with contract-specific semantic model.",
        "category": "analytics",
        "graph_type": "langgraph",
        "status": "active",
        "tags": ["analytics", "contract", "text-to-sql", "domain-agent"],
        "config": {
            "domain": "contract",
            "semantic_model_name": "contract_intelligence",
        },
        "tools": ["snowflake-query", "schema-vectorizer", "llm-sql-generation"],
        "workflow_steps": [
            "load_semantic_model", "build_schema_context", "enrich_query",
            "generate_sql", "validate_sql", "explain_sql", "return_result"
        ],
    },
    {
        "agent_id": "agent-domain-supplier",
        "name": "Supplier Management Domain Agent",
        "description": "Domain-specific agent for supplier lookup, performance, and risk queries.",
        "category": "analytics",
        "graph_type": "langgraph",
        "status": "active",
        "tags": ["analytics", "supplier", "text-to-sql", "domain-agent"],
        "config": {
            "domain": "supplier",
            "semantic_model_name": "supplier_management",
        },
        "tools": ["snowflake-query", "schema-vectorizer", "llm-sql-generation"],
        "workflow_steps": [
            "load_semantic_model", "build_schema_context", "enrich_query",
            "generate_sql", "validate_sql", "explain_sql", "return_result"
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL TEMPLATES — from Agents_GP API client + ChatwithData tools
# ═══════════════════════════════════════════════════════════════════════════════

SEED_TOOLS = [
    # ── Jaggaer Direct Sourcing API Tools ──────────────────────────────────
    {
        "tool_id": "jaggaer-supplier-api",
        "name": "Jaggaer Supplier API",
        "description": "CRUD operations on Jaggaer Direct Sourcing supplier records. "
                       "List, get, import, update suppliers and contacts.",
        "type": "api",
        "category": "enterprise-connector",
        "tags": ["jaggaer", "supplier", "api", "direct-sourcing"],
        "config": {
            "base_url": "https://premajor.app11.jaggaer.com/arc/api",
            "auth_type": "bearer",
            "headers": {"X-TENANT-ID": "${JAGGAER_TENANT_ID}", "X-JAGGAER-ORIGINATION": "agentic-ai"},
            "timeout_seconds": 60,
            "rate_limit_per_minute": 60,
            "retry_attempts": 3,
        },
        "endpoints": [
            {"method": "GET", "path": "/direct-suppliers", "description": "List suppliers"},
            {"method": "GET", "path": "/direct-suppliers/{id}", "description": "Get supplier by ID"},
            {"method": "GET", "path": "/direct-suppliers/count", "description": "Get supplier count"},
            {"method": "POST", "path": "/suppliers/import", "description": "Import suppliers"},
            {"method": "POST", "path": "/suppliers/company", "description": "Import supplier company"},
            {"method": "POST", "path": "/suppliers/contact", "description": "Import supplier contact"},
            {"method": "POST", "path": "/suppliers/user", "description": "Import supplier user"},
            {"method": "POST", "path": "/suppliers/user/{id}/status", "description": "Update user status"},
        ],
    },
    {
        "tool_id": "jaggaer-rfq-api",
        "name": "Jaggaer RFQ API",
        "description": "Manage Direct RFQs — list, get details, documents, items, quotations, and suppliers.",
        "type": "api",
        "category": "enterprise-connector",
        "tags": ["jaggaer", "rfq", "sourcing", "api"],
        "config": {
            "base_url": "https://premajor.app11.jaggaer.com/arc/api",
            "auth_type": "bearer",
            "headers": {"X-TENANT-ID": "${JAGGAER_TENANT_ID}", "X-JAGGAER-ORIGINATION": "agentic-ai"},
        },
        "endpoints": [
            {"method": "GET", "path": "/direct-rfqs", "description": "List Direct RFQs"},
            {"method": "GET", "path": "/direct-rfqs/{id}", "description": "Get RFQ by ID"},
            {"method": "GET", "path": "/direct-rfqs/{id}/documents", "description": "List RFQ documents"},
            {"method": "GET", "path": "/direct-rfqs/{id}/items", "description": "List RFQ items"},
            {"method": "GET", "path": "/direct-rfqs/{id}/quotations", "description": "List RFQ quotations"},
            {"method": "GET", "path": "/direct-rfqs/{id}/suppliers", "description": "List RFQ suppliers"},
            {"method": "GET", "path": "/direct-rfqs/count", "description": "Get RFQ count"},
        ],
    },
    {
        "tool_id": "jaggaer-action-api",
        "name": "Jaggaer Action API",
        "description": "Create, list, update actions and manage action files in Jaggaer platform.",
        "type": "api",
        "category": "enterprise-connector",
        "tags": ["jaggaer", "action", "workflow", "api"],
        "config": {
            "base_url": "https://premajor.app11.jaggaer.com/arc/api",
            "auth_type": "bearer",
            "headers": {"X-TENANT-ID": "${JAGGAER_TENANT_ID}", "X-JAGGAER-ORIGINATION": "agentic-ai"},
        },
        "endpoints": [
            {"method": "POST", "path": "/actions", "description": "Create action"},
            {"method": "GET", "path": "/actions", "description": "List actions"},
            {"method": "GET", "path": "/actions/{id}", "description": "Get action by ID"},
            {"method": "PATCH", "path": "/actions/{id}", "description": "Update action"},
            {"method": "POST", "path": "/actions/{id}/files", "description": "Add action files"},
            {"method": "GET", "path": "/actions/{id}/files", "description": "List action files"},
        ],
    },
    {
        "tool_id": "jaggaer-document-api",
        "name": "Jaggaer Document API",
        "description": "Document management — create, list, get documents and manage file attachments.",
        "type": "api",
        "category": "enterprise-connector",
        "tags": ["jaggaer", "document", "file", "api"],
        "config": {
            "base_url": "https://premajor.app11.jaggaer.com/arc/api",
            "auth_type": "bearer",
            "headers": {"X-TENANT-ID": "${JAGGAER_TENANT_ID}", "X-JAGGAER-ORIGINATION": "agentic-ai"},
        },
        "endpoints": [
            {"method": "GET", "path": "/documents", "description": "List documents"},
            {"method": "GET", "path": "/documents/{id}", "description": "Get document by ID"},
            {"method": "POST", "path": "/documents", "description": "Create document"},
            {"method": "POST", "path": "/documents/{id}/files", "description": "Add document files"},
            {"method": "GET", "path": "/documents/{id}/files", "description": "List document files"},
        ],
    },
    {
        "tool_id": "jaggaer-commodity-api",
        "name": "Jaggaer Commodity API",
        "description": "Commodity management — clusters, commodities, and commodity-supplier mappings.",
        "type": "api",
        "category": "enterprise-connector",
        "tags": ["jaggaer", "commodity", "category", "api"],
        "config": {
            "base_url": "https://premajor.app11.jaggaer.com/arc/api",
            "auth_type": "bearer",
        },
        "endpoints": [
            {"method": "GET", "path": "/commodities/clusters", "description": "List commodity clusters"},
            {"method": "GET", "path": "/commodities/clusters/{id}", "description": "Get cluster by ID"},
            {"method": "GET", "path": "/commodities", "description": "List commodities"},
            {"method": "GET", "path": "/commodities/{id}", "description": "Get commodity by ID"},
            {"method": "GET", "path": "/commodities/{id}/suppliers", "description": "List commodity suppliers"},
        ],
    },
    {
        "tool_id": "jaggaer-bom-api",
        "name": "Jaggaer BOM API",
        "description": "Bill of Materials management — list, get, create BOMs and manage BOM items.",
        "type": "api",
        "category": "enterprise-connector",
        "tags": ["jaggaer", "bom", "materials", "api"],
        "config": {
            "base_url": "https://premajor.app11.jaggaer.com/arc/api",
            "auth_type": "bearer",
        },
        "endpoints": [
            {"method": "GET", "path": "/boms", "description": "List BOM headers"},
            {"method": "GET", "path": "/boms/{id}", "description": "Get BOM header"},
            {"method": "GET", "path": "/boms/{id}/items", "description": "Get BOM with items"},
            {"method": "POST", "path": "/boms", "description": "Create BOM"},
            {"method": "POST", "path": "/boms/{id}/items", "description": "Add BOM item"},
            {"method": "PATCH", "path": "/boms/{id}/activate", "description": "Activate BOM"},
        ],
    },
    {
        "tool_id": "jaggaer-material-api",
        "name": "Jaggaer Material API",
        "description": "Direct material management — list, get, create, update materials.",
        "type": "api",
        "category": "enterprise-connector",
        "tags": ["jaggaer", "material", "api"],
        "config": {
            "base_url": "https://premajor.app11.jaggaer.com/arc/api",
            "auth_type": "bearer",
        },
        "endpoints": [
            {"method": "GET", "path": "/materials", "description": "List materials"},
            {"method": "GET", "path": "/materials/{id}", "description": "Get material by ID"},
            {"method": "POST", "path": "/materials", "description": "Create material"},
            {"method": "PATCH", "path": "/materials/{id}", "description": "Update material"},
        ],
    },
    {
        "tool_id": "jaggaer-user-api",
        "name": "Jaggaer User & Group API",
        "description": "Buyer user management and group listing for approval routing.",
        "type": "api",
        "category": "enterprise-connector",
        "tags": ["jaggaer", "user", "group", "api"],
        "config": {
            "base_url": "https://premajor.app11.jaggaer.com/arc/api",
            "auth_type": "bearer",
        },
        "endpoints": [
            {"method": "GET", "path": "/direct-users", "description": "List buyer users"},
            {"method": "GET", "path": "/direct-users/{id}", "description": "Get buyer user by ID"},
            {"method": "GET", "path": "/groups", "description": "List groups"},
        ],
    },
    {
        "tool_id": "jaggaer-idoc-api",
        "name": "Jaggaer IDoc / ERP Integration",
        "description": "SAP IDoc import and monitoring for ERP integration.",
        "type": "api",
        "category": "enterprise-connector",
        "tags": ["jaggaer", "idoc", "sap", "erp", "api"],
        "config": {
            "base_url": "https://premajor.app11.jaggaer.com/arc/api",
            "auth_type": "bearer",
        },
        "endpoints": [
            {"method": "POST", "path": "/idocs", "description": "Import IDoc"},
            {"method": "GET", "path": "/idoc-monitoring-logs", "description": "List IDoc monitoring logs"},
        ],
    },

    # ── ChatwithData: Analytics Tools ──────────────────────────────────────
    {
        "tool_id": "snowflake-query",
        "name": "Snowflake SQL Query",
        "description": "Execute validated SQL queries against Snowflake data warehouse. "
                       "Supports JAGGAER_DW database with 803 views across 6 procurement domains.",
        "type": "db",
        "category": "data-connector",
        "tags": ["snowflake", "sql", "analytics", "data-warehouse"],
        "config": {
            "warehouse": "COMPUTE_WH",
            "database": "JAGGAER_DW",
            "schema": "ANALYTICS",
            "role": "ANALYST_ROLE",
            "max_rows": 10000,
            "timeout_seconds": 60,
            "auth_methods": ["password", "key-pair", "sso"],
        },
    },
    {
        "tool_id": "schema-vectorizer",
        "name": "Schema Vectorizer",
        "description": "ChromaDB-backed vector store for schema retrieval. Embeds 803 Snowflake views "
                       "for semantic search during SQL generation. Returns top-K relevant schemas.",
        "type": "rag",
        "category": "data-connector",
        "tags": ["chromadb", "vector-search", "schema", "embedding"],
        "config": {
            "persist_dir": "./chroma_db",
            "collection_name": "jaggaer_schema",
            "top_k": 10,
        },
    },
    {
        "tool_id": "few-shot-store",
        "name": "Few-Shot Example Store",
        "description": "Curated library of question→SQL examples per procurement domain. "
                       "Used for in-context learning during SQL generation.",
        "type": "rag",
        "category": "data-connector",
        "tags": ["few-shot", "examples", "sql", "in-context-learning"],
    },
    {
        "tool_id": "llm-sql-generation",
        "name": "LLM SQL Generator",
        "description": "Dual-LLM SQL generation: Claude for complex reasoning, Gemini for validation. "
                       "Includes SQL guardrails, error correction, and explanation generation.",
        "type": "llm",
        "category": "ai-tool",
        "tags": ["sql-generation", "text-to-sql", "dual-llm"],
        "config": {
            "primary_model": "claude-sonnet-4-20250514",
            "validation_model": "gemini-2.0-flash-exp",
            "max_retries": 3,
        },
    },
    {
        "tool_id": "llm-classification",
        "name": "LLM Intent Classifier",
        "description": "Fast intent classification using Gemini Flash. Routes queries to the correct "
                       "domain agent based on procurement intent.",
        "type": "llm",
        "category": "ai-tool",
        "tags": ["classification", "intent", "routing"],
        "config": {
            "model": "gemini-2.5-flash",
            "temperature": 0.0,
            "max_tokens": 200,
        },
    },
    {
        "tool_id": "llm-scoring",
        "name": "LLM Scoring Engine",
        "description": "AI-powered scoring for bids, risk assessment, compliance evaluation, "
                       "and supplier scorecards using structured output.",
        "type": "llm",
        "category": "ai-tool",
        "tags": ["scoring", "risk", "compliance", "evaluation"],
        "config": {
            "model": "gemini-2.5-flash",
            "temperature": 0.3,
            "structured_output": True,
        },
    },
    # ── Platform Built-in Tools (shipped to all devs automatically) ─────────
    {
        "tool_id": "platform-ocr",
        "name": "OCR – Document Text Extraction",
        "description": "Extract text from scanned PDFs, images (PNG/JPG/TIFF), and photos of documents "
                       "using Google Cloud Vision API. Supports handwriting, tables, and multi-language.",
        "type": "api",
        "category": "platform-builtin",
        "tags": ["ocr", "vision", "pdf", "image", "extraction", "platform"],
        "config": {
            "provider": "google-cloud-vision",
            "supported_formats": ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"],
            "max_file_size_mb": 20,
            "languages": ["en", "de", "fr", "es", "it", "pt", "ja", "zh"],
            "features": ["TEXT_DETECTION", "DOCUMENT_TEXT_DETECTION", "TABLE_DETECTION"],
        },
        "is_platform_tool": True,
    },
    {
        "tool_id": "platform-calculator",
        "name": "Calculator – Math & Financial Expressions",
        "description": "Evaluate mathematical and financial expressions safely. Supports arithmetic, "
                       "percentages, currency conversion, NPV, IRR, amortization, and unit conversions.",
        "type": "python",
        "category": "platform-builtin",
        "tags": ["calculator", "math", "finance", "currency", "platform"],
        "config": {
            "safe_mode": True,
            "supported_operations": ["arithmetic", "percentages", "currency_conversion",
                                     "npv", "irr", "amortization", "unit_conversion"],
            "max_precision": 15,
        },
        "is_platform_tool": True,
    },
    {
        "tool_id": "platform-translator",
        "name": "Translator – Multi-Language Translation",
        "description": "Translate text between 100+ languages using Google Cloud Translation API. "
                       "Supports auto-detection, glossary terms, and batch translation.",
        "type": "api",
        "category": "platform-builtin",
        "tags": ["translator", "language", "i18n", "localization", "platform"],
        "config": {
            "provider": "google-cloud-translate",
            "default_target": "en",
            "max_chars": 50000,
            "glossary_support": True,
        },
        "is_platform_tool": True,
    },
    {
        "tool_id": "platform-summarizer",
        "name": "Summarizer – Document & Text Summarization",
        "description": "Summarize long documents, emails, meeting notes, and contracts into concise "
                       "bullet points or executive summaries. Configurable length and style.",
        "type": "llm",
        "category": "platform-builtin",
        "tags": ["summarizer", "text", "document", "extraction", "platform"],
        "config": {
            "model": "gemini-2.5-flash",
            "styles": ["bullets", "executive", "technical", "one-liner"],
            "max_input_tokens": 128000,
            "default_max_output": 500,
        },
        "is_platform_tool": True,
    },
    {
        "tool_id": "platform-sentiment",
        "name": "Sentiment Analyzer",
        "description": "Analyze sentiment and emotion in text — supplier communications, survey responses, "
                       "feedback forms. Returns polarity, magnitude, and emotion labels.",
        "type": "llm",
        "category": "platform-builtin",
        "tags": ["sentiment", "nlp", "analysis", "emotion", "platform"],
        "config": {
            "model": "gemini-2.5-flash",
            "output_format": "json",
            "emotions": ["positive", "negative", "neutral", "anger", "satisfaction", "urgency"],
        },
        "is_platform_tool": True,
    },
    {
        "tool_id": "platform-entity-extractor",
        "name": "Entity Extractor – NER & Key Info",
        "description": "Extract named entities (companies, people, dates, amounts, contract terms) "
                       "from unstructured text using LLM-powered NER.",
        "type": "llm",
        "category": "platform-builtin",
        "tags": ["ner", "entity", "extraction", "nlp", "platform"],
        "config": {
            "model": "gemini-2.5-flash",
            "entity_types": ["PERSON", "ORG", "DATE", "MONEY", "PERCENT",
                             "CONTRACT_TERM", "PRODUCT", "LOCATION"],
        },
        "is_platform_tool": True,
    },
    {
        "tool_id": "platform-email-composer",
        "name": "Email Composer – Smart Drafting",
        "description": "Draft professional procurement emails — RFQ follow-ups, supplier notifications, "
                       "approval requests, escalation notices. Tone and template configurable.",
        "type": "llm",
        "category": "platform-builtin",
        "tags": ["email", "drafting", "communication", "template", "platform"],
        "config": {
            "model": "gemini-2.5-flash",
            "tones": ["formal", "friendly", "urgent", "neutral"],
            "templates": ["rfq_followup", "supplier_notification", "approval_request",
                          "escalation", "thank_you", "rejection_notice"],
        },
        "is_platform_tool": True,
    },
    {
        "tool_id": "platform-web-search",
        "name": "Web Search – Real-time Information",
        "description": "Search the web for real-time supplier news, market prices, regulatory updates, "
                       "and company information using Google Custom Search API.",
        "type": "api",
        "category": "platform-builtin",
        "tags": ["search", "web", "news", "market", "platform"],
        "config": {
            "provider": "google-custom-search",
            "max_results": 10,
            "safe_search": True,
        },
        "is_platform_tool": True,
    },
    {
        "tool_id": "platform-pdf-generator",
        "name": "PDF Generator – Report & Doc Creation",
        "description": "Generate formatted PDF reports from structured data — bid comparisons, "
                       "scorecards, audit trails, executive summaries.",
        "type": "python",
        "category": "platform-builtin",
        "tags": ["pdf", "report", "document", "generation", "platform"],
        "config": {
            "templates": ["bid_comparison", "supplier_scorecard", "audit_trail",
                          "executive_summary", "contract_summary"],
            "max_pages": 50,
            "branding": "jaggaer",
        },
        "is_platform_tool": True,
    },
    {
        "tool_id": "platform-data-validator",
        "name": "Data Validator – Schema & Format Checks",
        "description": "Validate data against schemas, check formats (email, phone, DUNS, VAT), "
                       "detect duplicates, and ensure referential integrity.",
        "type": "python",
        "category": "platform-builtin",
        "tags": ["validation", "data-quality", "schema", "format", "platform"],
        "config": {
            "validators": ["email", "phone", "duns", "vat", "iban", "swift",
                           "iso_country", "currency_code", "date_format"],
            "duplicate_detection": True,
        },
        "is_platform_tool": True,
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# WORKATO CONNECTOR TEMPLATES — Enterprise Integration Platform
# ═══════════════════════════════════════════════════════════════════════════════

WORKATO_CONNECTORS = [
    {
        "connector_id": "workato-sap",
        "name": "SAP S/4HANA (via Workato)",
        "description": "Connect to SAP S/4HANA for purchase orders, material masters, vendor masters, "
                       "and financial postings. Supports IDoc, BAPI, and OData interfaces.",
        "type": "workato",
        "category": "erp",
        "icon": "sap",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["sap", "erp", "purchase-order", "vendor", "material"],
        "actions": [
            {"name": "Get Purchase Order", "method": "GET", "path": "/sap/po/{id}"},
            {"name": "Create Purchase Order", "method": "POST", "path": "/sap/po"},
            {"name": "Get Vendor Master", "method": "GET", "path": "/sap/vendor/{id}"},
            {"name": "Post Goods Receipt", "method": "POST", "path": "/sap/gr"},
            {"name": "Get Material Master", "method": "GET", "path": "/sap/material/{id}"},
            {"name": "Create Invoice", "method": "POST", "path": "/sap/invoice"},
        ],
        "triggers": [
            {"name": "New Purchase Order", "event": "po.created"},
            {"name": "PO Status Changed", "event": "po.status_changed"},
            {"name": "Goods Receipt Posted", "event": "gr.posted"},
            {"name": "Invoice Received", "event": "invoice.received"},
        ],
        "workato_config": {
            "connection_type": "on_prem_agent",
            "recipe_template": "sap_procurement_sync",
        },
    },
    {
        "connector_id": "workato-salesforce",
        "name": "Salesforce CRM (via Workato)",
        "description": "Sync supplier and contract data with Salesforce. Manage accounts, opportunities, "
                       "and custom procurement objects.",
        "type": "workato",
        "category": "crm",
        "icon": "salesforce",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["salesforce", "crm", "supplier", "contract"],
        "actions": [
            {"name": "Get Account", "method": "GET", "path": "/sf/account/{id}"},
            {"name": "Create Account", "method": "POST", "path": "/sf/account"},
            {"name": "Update Account", "method": "PATCH", "path": "/sf/account/{id}"},
            {"name": "Search Accounts", "method": "GET", "path": "/sf/account/search"},
            {"name": "Get Opportunity", "method": "GET", "path": "/sf/opportunity/{id}"},
            {"name": "Create Contract", "method": "POST", "path": "/sf/contract"},
        ],
        "triggers": [
            {"name": "New Account", "event": "account.created"},
            {"name": "Account Updated", "event": "account.updated"},
            {"name": "Opportunity Won", "event": "opportunity.won"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "sf_supplier_sync",
        },
    },
    {
        "connector_id": "workato-servicenow",
        "name": "ServiceNow ITSM (via Workato)",
        "description": "Integrate with ServiceNow for IT procurement workflows, change management, "
                       "and asset management.",
        "type": "workato",
        "category": "itsm",
        "icon": "servicenow",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["servicenow", "itsm", "change-management", "asset"],
        "actions": [
            {"name": "Create Incident", "method": "POST", "path": "/snow/incident"},
            {"name": "Get Change Request", "method": "GET", "path": "/snow/change/{id}"},
            {"name": "Create Change Request", "method": "POST", "path": "/snow/change"},
            {"name": "Get Asset", "method": "GET", "path": "/snow/asset/{id}"},
            {"name": "Update CMDB", "method": "PATCH", "path": "/snow/cmdb/{id}"},
        ],
        "triggers": [
            {"name": "New Incident", "event": "incident.created"},
            {"name": "Change Approved", "event": "change.approved"},
            {"name": "Asset Retired", "event": "asset.retired"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "snow_procurement_integration",
        },
    },
    {
        "connector_id": "workato-coupa",
        "name": "Coupa Procurement (via Workato)",
        "description": "Connect to Coupa for requisitions, purchase orders, invoices, and supplier management.",
        "type": "workato",
        "category": "procurement",
        "icon": "coupa",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["coupa", "procurement", "requisition", "invoice"],
        "actions": [
            {"name": "Get Requisition", "method": "GET", "path": "/coupa/requisition/{id}"},
            {"name": "Create Requisition", "method": "POST", "path": "/coupa/requisition"},
            {"name": "Get Purchase Order", "method": "GET", "path": "/coupa/po/{id}"},
            {"name": "Get Invoice", "method": "GET", "path": "/coupa/invoice/{id}"},
            {"name": "Approve Invoice", "method": "POST", "path": "/coupa/invoice/{id}/approve"},
            {"name": "Get Supplier", "method": "GET", "path": "/coupa/supplier/{id}"},
        ],
        "triggers": [
            {"name": "New Requisition", "event": "requisition.created"},
            {"name": "PO Approved", "event": "po.approved"},
            {"name": "Invoice Submitted", "event": "invoice.submitted"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "coupa_jaggaer_sync",
        },
    },
    {
        "connector_id": "workato-oracle",
        "name": "Oracle ERP Cloud (via Workato)",
        "description": "Connect to Oracle ERP Cloud for procurement, payables, and supplier management.",
        "type": "workato",
        "category": "erp",
        "icon": "oracle",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["oracle", "erp", "procurement", "payables"],
        "actions": [
            {"name": "Get Purchase Order", "method": "GET", "path": "/oracle/po/{id}"},
            {"name": "Create Requisition", "method": "POST", "path": "/oracle/requisition"},
            {"name": "Get Supplier", "method": "GET", "path": "/oracle/supplier/{id}"},
            {"name": "Create Invoice", "method": "POST", "path": "/oracle/invoice"},
            {"name": "Get Receipt", "method": "GET", "path": "/oracle/receipt/{id}"},
        ],
        "triggers": [
            {"name": "PO Created", "event": "po.created"},
            {"name": "Invoice Approved", "event": "invoice.approved"},
            {"name": "Supplier Updated", "event": "supplier.updated"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "oracle_procurement_sync",
        },
    },
    {
        "connector_id": "workato-netsuite",
        "name": "NetSuite ERP (via Workato)",
        "description": "Connect to NetSuite for vendor bills, purchase orders, and item management.",
        "type": "workato",
        "category": "erp",
        "icon": "netsuite",
        "status": "available",
        "auth_type": "token",
        "tags": ["netsuite", "erp", "vendor", "purchase-order"],
        "actions": [
            {"name": "Get Vendor Bill", "method": "GET", "path": "/ns/vendorbill/{id}"},
            {"name": "Create Purchase Order", "method": "POST", "path": "/ns/purchaseorder"},
            {"name": "Get Vendor", "method": "GET", "path": "/ns/vendor/{id}"},
            {"name": "Search Items", "method": "GET", "path": "/ns/item/search"},
        ],
        "triggers": [
            {"name": "New Vendor Bill", "event": "vendorbill.created"},
            {"name": "PO Approved", "event": "purchaseorder.approved"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "netsuite_procurement_sync",
        },
    },
    {
        "connector_id": "workato-slack",
        "name": "Slack Notifications (via Workato)",
        "description": "Send procurement notifications, approval requests, and alerts to Slack channels.",
        "type": "workato",
        "category": "collaboration",
        "icon": "slack",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["slack", "notification", "collaboration", "approval"],
        "actions": [
            {"name": "Send Message", "method": "POST", "path": "/slack/message"},
            {"name": "Send Approval Request", "method": "POST", "path": "/slack/approval"},
            {"name": "Update Message", "method": "PATCH", "path": "/slack/message/{ts}"},
            {"name": "Upload File", "method": "POST", "path": "/slack/file"},
        ],
        "triggers": [
            {"name": "Message Received", "event": "message.received"},
            {"name": "Approval Response", "event": "approval.responded"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "slack_procurement_alerts",
        },
    },
    {
        "connector_id": "workato-teams",
        "name": "Microsoft Teams (via Workato)",
        "description": "Send procurement notifications and approval requests to Microsoft Teams channels.",
        "type": "workato",
        "category": "collaboration",
        "icon": "teams",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["teams", "microsoft", "notification", "collaboration"],
        "actions": [
            {"name": "Send Message", "method": "POST", "path": "/teams/message"},
            {"name": "Create Adaptive Card", "method": "POST", "path": "/teams/card"},
            {"name": "Send Approval", "method": "POST", "path": "/teams/approval"},
        ],
        "triggers": [
            {"name": "Message Received", "event": "message.received"},
            {"name": "Approval Completed", "event": "approval.completed"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "teams_procurement_alerts",
        },
    },
    {
        "connector_id": "workato-jira",
        "name": "Jira (via Workato)",
        "description": "Create and track procurement-related issues, tasks, and projects in Jira.",
        "type": "workato",
        "category": "project-management",
        "icon": "jira",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["jira", "project-management", "task", "issue"],
        "actions": [
            {"name": "Create Issue", "method": "POST", "path": "/jira/issue"},
            {"name": "Update Issue", "method": "PATCH", "path": "/jira/issue/{id}"},
            {"name": "Get Issue", "method": "GET", "path": "/jira/issue/{id}"},
            {"name": "Add Comment", "method": "POST", "path": "/jira/issue/{id}/comment"},
            {"name": "Transition Issue", "method": "POST", "path": "/jira/issue/{id}/transition"},
        ],
        "triggers": [
            {"name": "Issue Created", "event": "issue.created"},
            {"name": "Issue Updated", "event": "issue.updated"},
            {"name": "Issue Transitioned", "event": "issue.transitioned"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "jira_procurement_tasks",
        },
    },
    {
        "connector_id": "workato-docusign",
        "name": "DocuSign (via Workato)",
        "description": "Send contracts and procurement documents for electronic signature via DocuSign.",
        "type": "workato",
        "category": "document-management",
        "icon": "docusign",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["docusign", "e-signature", "contract", "document"],
        "actions": [
            {"name": "Send Envelope", "method": "POST", "path": "/docusign/envelope"},
            {"name": "Get Envelope Status", "method": "GET", "path": "/docusign/envelope/{id}"},
            {"name": "Download Document", "method": "GET", "path": "/docusign/envelope/{id}/document"},
            {"name": "Void Envelope", "method": "POST", "path": "/docusign/envelope/{id}/void"},
        ],
        "triggers": [
            {"name": "Envelope Completed", "event": "envelope.completed"},
            {"name": "Envelope Declined", "event": "envelope.declined"},
            {"name": "Envelope Sent", "event": "envelope.sent"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "docusign_contract_signing",
        },
    },
    {
        "connector_id": "workato-sharepoint",
        "name": "SharePoint (via Workato)",
        "description": "Store and retrieve procurement documents, contracts, and compliance files in SharePoint.",
        "type": "workato",
        "category": "document-management",
        "icon": "sharepoint",
        "status": "available",
        "auth_type": "oauth2",
        "tags": ["sharepoint", "document", "storage", "microsoft"],
        "actions": [
            {"name": "Upload File", "method": "POST", "path": "/sharepoint/file"},
            {"name": "Get File", "method": "GET", "path": "/sharepoint/file/{id}"},
            {"name": "List Files", "method": "GET", "path": "/sharepoint/files"},
            {"name": "Create Folder", "method": "POST", "path": "/sharepoint/folder"},
        ],
        "triggers": [
            {"name": "File Uploaded", "event": "file.uploaded"},
            {"name": "File Modified", "event": "file.modified"},
        ],
        "workato_config": {
            "connection_type": "cloud",
            "recipe_template": "sharepoint_document_sync",
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR PIPELINE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

SEED_PIPELINES = [
    {
        "pipeline_id": "pipeline-jd-orchestrator",
        "name": "Jaggaer Direct Sourcing Orchestrator",
        "description": "Hub-and-spoke orchestrator coordinating all 4 direct sourcing agents. "
                       "Routes requests by agent type, supports parallel batch execution.",
        "pattern": "supervisor",
        "steps": 4,
        "agents": [
            "agent-bid-analyzer",
            "agent-supplier-data-change",
            "agent-workflow-approval",
            "agent-supplier-collaboration",
        ],
        "config": {
            "parallel_execution": True,
            "max_concurrent": 4,
            "timeout_seconds": 120,
        },
    },
    {
        "pipeline_id": "pipeline-procurement-intelligence",
        "name": "Procurement Intelligence Pipeline",
        "description": "Supervisor → Domain Agent → Human Review → Query Execution → Insight Generation. "
                       "Supports 8 procurement domains with text-to-SQL.",
        "pattern": "supervisor",
        "steps": 7,
        "agents": [
            "agent-procurement-supervisor",
            "agent-domain-spend",
            "agent-domain-contract",
            "agent-domain-supplier",
        ],
        "config": {
            "enable_human_review": True,
            "sql_max_rows": 10000,
        },
    },
    {
        "pipeline_id": "pipeline-supplier-onboarding",
        "name": "Supplier Onboarding Pipeline",
        "description": "End-to-end supplier onboarding: data change → compliance docs → "
                       "approval workflow → ERP sync via Workato SAP connector.",
        "pattern": "sequential",
        "steps": 4,
        "agents": [
            "agent-supplier-data-change",
            "agent-supplier-collaboration",
            "agent-workflow-approval",
        ],
        "connectors": ["workato-sap", "workato-docusign"],
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES — from both codebases
# ═══════════════════════════════════════════════════════════════════════════════

SEED_PROMPTS = [
    {
        "template_id": "prompt-intent-classification",
        "name": "Intent Classification",
        "description": "Classify user query into procurement domain intent for routing.",
        "category": "classification",
        "content": (
            "You are a procurement intelligence classifier. Analyze the user's question and classify "
            "it into exactly ONE of these intents:\n"
            "- spend_analysis: Questions about spending, budgets, cost breakdowns\n"
            "- contract_query: Questions about contracts, terms, compliance\n"
            "- sourcing_event: Questions about RFQs, RFPs, sourcing events\n"
            "- supplier_lookup: Questions about suppliers, vendor performance\n"
            "- savings_tracking: Questions about savings, cost avoidance\n"
            "- purchase_ops: Questions about POs, requisitions, receipts\n"
            "- category_strategy: Questions about category management\n"
            "- cross_domain: Questions spanning multiple domains\n\n"
            "User question: {question}\n\n"
            "Respond with JSON: {{\"intent\": \"<intent>\", \"confidence\": <0.0-1.0>, \"reasoning\": \"<brief>\"}}"
        ),
    },
    {
        "template_id": "prompt-sql-generation",
        "name": "Text-to-SQL Generation",
        "description": "Generate Snowflake SQL from natural language with schema context.",
        "category": "sql-generation",
        "content": (
            "You are an expert Snowflake SQL analyst for procurement data.\n\n"
            "SCHEMA CONTEXT:\n{schema_context}\n\n"
            "SEMANTIC MODEL:\n{semantic_model}\n\n"
            "FEW-SHOT EXAMPLES:\n{few_shot_examples}\n\n"
            "RULES:\n"
            "- Use only views and columns from the schema context\n"
            "- Always include LIMIT {max_rows}\n"
            "- Use proper Snowflake SQL syntax\n"
            "- Include helpful column aliases\n"
            "- Add ORDER BY for meaningful results\n\n"
            "User question: {question}\n\n"
            "Generate the SQL query:"
        ),
    },
    {
        "template_id": "prompt-bid-scoring",
        "name": "Bid Scoring Prompt",
        "description": "AI-powered bid evaluation across cost, quality, delivery, risk, compliance.",
        "category": "evaluation",
        "content": (
            "You are a procurement bid evaluation expert. Score this supplier bid.\n\n"
            "BID DATA:\n{bid_data}\n\n"
            "EVALUATION CRITERIA:\n"
            "- Cost (50%): Price competitiveness vs. market benchmarks\n"
            "- Quality (20%): Technical capability, certifications, past performance\n"
            "- Delivery (15%): Lead time, reliability, logistics capability\n"
            "- Risk (10%): Financial stability, geopolitical risk, single-source risk\n"
            "- Compliance (5%): Regulatory, environmental, social compliance\n\n"
            "Respond with JSON: {{\"cost_score\": <0-100>, \"quality_score\": <0-100>, "
            "\"delivery_score\": <0-100>, \"risk_score\": <0-100>, \"compliance_score\": <0-100>, "
            "\"weighted_total\": <0-100>, \"recommendation\": \"<award/reject/review>\", "
            "\"justification\": \"<brief>\"}}"
        ),
    },
    {
        "template_id": "prompt-change-risk",
        "name": "Supplier Change Risk Assessment",
        "description": "Assess risk level of supplier data changes for approval routing.",
        "category": "risk-assessment",
        "content": (
            "You are a supplier master data risk assessor.\n\n"
            "CHANGE REQUEST:\n{change_data}\n\n"
            "Assess the risk of this change considering:\n"
            "- Bank account changes (HIGH risk)\n"
            "- Address/contact changes (MEDIUM risk)\n"
            "- Classification changes (LOW risk)\n"
            "- Volume of changes in single request\n"
            "- Supplier criticality tier\n\n"
            "Respond with JSON: {{\"risk_score\": <0.0-1.0>, \"risk_level\": \"low|medium|high|critical\", "
            "\"requires_approval\": <true/false>, \"approval_tier\": \"<tier>\", "
            "\"risk_factors\": [\"<factor1>\", ...]}}"
        ),
    },
    {
        "template_id": "prompt-approval-routing",
        "name": "PR Approval Routing",
        "description": "Determine approval path for purchase requests based on amount and policy.",
        "category": "workflow",
        "content": (
            "You are a procurement approval routing engine.\n\n"
            "PURCHASE REQUEST:\n{pr_data}\n\n"
            "POLICY TIERS:\n"
            "- Tier 1 (≤$1,000): Manager only\n"
            "- Tier 2 (≤$10,000): Manager + Director\n"
            "- Tier 3 (≤$50,000): Manager + Director + VP\n"
            "- Tier 4 (>$50,000): Manager + Director + VP + CFO\n\n"
            "Determine the approval path and respond with JSON: "
            "{{\"tier\": \"<tier>\", \"approvers\": [\"<role1>\", ...], "
            "\"estimated_days\": <int>, \"auto_approve\": <true/false>, "
            "\"escalation_after_days\": <int>}}"
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SETTINGS — merged from both .env.example files
# ═══════════════════════════════════════════════════════════════════════════════

SEED_SETTINGS = {
    "gcp": {
        "project_id": "gcp-jai-platform-dev",
        "environment": "dev",
        "region": "us-central1",
    },
    "jaggaer_api": {
        "base_url": "https://premajor.app11.jaggaer.com/arc/api",
        "tenant_id": "${JAGGAER_TENANT_ID}",
        "origination": "agentic-ai",
        "auth_type": "bearer",
    },
    "llm_models": {
        "agent": {"model": "gemini-2.5-flash", "temperature": 0.3, "max_tokens": 2000},
        "router": {"model": "gemini-2.5-flash", "temperature": 0.0, "max_tokens": 200},
        "supervisor": {"model": "gemini-2.0-flash-exp", "temperature": 0.0, "max_tokens": 200},
        "sql_generation": {"model": "claude-sonnet-4-20250514", "temperature": 0.0, "max_tokens": 8192},
        "validation": {"model": "gemini-2.0-flash-exp", "temperature": 0.0, "max_tokens": 2048},
    },
    "snowflake": {
        "warehouse": "COMPUTE_WH",
        "database": "JAGGAER_DW",
        "schema": "ANALYTICS",
        "role": "ANALYST_ROLE",
        "max_rows": 10000,
        "timeout_seconds": 60,
    },
    "agent_defaults": {
        "max_retries": 3,
        "retry_delay_seconds": 2,
        "timeout_seconds": 60,
        "confidence_threshold": 0.8,
        "hitl_approval_threshold": 10000.0,
        "hitl_risk_threshold": 0.7,
        "rate_limit_per_minute": 60,
    },
    "langsmith": {
        "tracing_v2": True,
        "endpoint": "https://api.smith.langchain.com",
        "project": "jai-agent-os",
    },
    "workato": {
        "base_url": "${WORKATO_BASE_URL}",
        "api_token": "${WORKATO_API_TOKEN}",
        "workspace_id": "${WORKATO_WORKSPACE_ID}",
        "recipe_prefix": "jai_agent_os",
    },
}
