--
-- PostgreSQL database dump
--

\restrict RBysU0OB7YSezbXARmsNGTuN4LHHChxy9KyVGabzpOaE5o5HbUKqi3d9B38Xbmv

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents (
    id character varying(64) NOT NULL,
    name character varying(256) NOT NULL,
    description text NOT NULL,
    version integer NOT NULL,
    status character varying(32) NOT NULL,
    tags jsonb NOT NULL,
    model_config_json jsonb NOT NULL,
    context text NOT NULL,
    prompt_template_id character varying(128),
    rag_config_json jsonb NOT NULL,
    memory_config_json jsonb NOT NULL,
    db_config_json jsonb NOT NULL,
    tools_json jsonb NOT NULL,
    endpoint_json jsonb NOT NULL,
    access_control_json jsonb NOT NULL,
    graph_manifest_id character varying(128),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    created_by character varying(128) NOT NULL,
    metadata_json jsonb NOT NULL,
    credential_id character varying(64)
);


--
-- Name: guardrail_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.guardrail_rules (
    id character varying(64) NOT NULL,
    name character varying(256) NOT NULL,
    description text NOT NULL,
    rule_type character varying(32) NOT NULL,
    scope character varying(32) NOT NULL,
    action character varying(32) NOT NULL,
    enabled boolean NOT NULL,
    applies_to character varying(32) NOT NULL,
    config_json jsonb NOT NULL,
    agent_ids jsonb NOT NULL,
    group_ids jsonb NOT NULL,
    is_deployed boolean NOT NULL,
    times_triggered integer NOT NULL,
    last_triggered timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    created_by character varying(128) NOT NULL
);


--
-- Name: integrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.integrations (
    id character varying(64) NOT NULL,
    name character varying(256) NOT NULL,
    provider character varying(64) NOT NULL,
    description text NOT NULL,
    api_key_encrypted text NOT NULL,
    api_key_masked character varying(64) NOT NULL,
    auth_type character varying(32) NOT NULL,
    service_account_json jsonb NOT NULL,
    endpoint_url text NOT NULL,
    project_id character varying(256) NOT NULL,
    default_model character varying(256) NOT NULL,
    allowed_models jsonb NOT NULL,
    registered_models jsonb NOT NULL,
    rate_limit_rpm integer NOT NULL,
    assigned_group_ids jsonb NOT NULL,
    status character varying(32) NOT NULL,
    last_tested timestamp without time zone,
    last_error text NOT NULL,
    created_by character varying(128) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    metadata_json jsonb NOT NULL,
    service_account_json_encrypted text DEFAULT ''::text
);


--
-- Name: prompt_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prompt_templates (
    id character varying(64) NOT NULL,
    name character varying(256) NOT NULL,
    description text NOT NULL,
    category character varying(64) NOT NULL,
    tags jsonb NOT NULL,
    content text NOT NULL,
    variables jsonb NOT NULL,
    version integer NOT NULL,
    is_builtin boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    created_by character varying(128) NOT NULL
);


--
-- Name: provider_credentials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.provider_credentials (
    id character varying(64) NOT NULL,
    name character varying(256) NOT NULL,
    provider character varying(64) NOT NULL,
    credential_blob text NOT NULL,
    display_metadata jsonb NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    created_by character varying(128) NOT NULL
);


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants (
    id character varying(64) NOT NULL,
    name character varying(256) NOT NULL,
    slug character varying(128) NOT NULL,
    tier character varying(32) NOT NULL,
    owner_email character varying(256) NOT NULL,
    domain character varying(256) NOT NULL,
    is_active boolean NOT NULL,
    settings_json jsonb NOT NULL,
    quota_json jsonb NOT NULL,
    allowed_providers jsonb NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: tools; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tools (
    id character varying(64) NOT NULL,
    name character varying(256) NOT NULL,
    description text NOT NULL,
    tool_type character varying(32) NOT NULL,
    category character varying(64) NOT NULL,
    status character varying(32) NOT NULL,
    tags jsonb NOT NULL,
    config_json jsonb NOT NULL,
    endpoints_json jsonb NOT NULL,
    is_public boolean NOT NULL,
    is_platform_tool boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    created_by character varying(128) NOT NULL,
    metadata_json jsonb NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id character varying(64) NOT NULL,
    username character varying(128) NOT NULL,
    email character varying(256) NOT NULL,
    password_hash character varying(256) NOT NULL,
    first_name character varying(128) NOT NULL,
    last_name character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    avatar_url text NOT NULL,
    tenant_id character varying(64) NOT NULL,
    roles jsonb NOT NULL,
    is_active boolean NOT NULL,
    preferences jsonb NOT NULL,
    created_at timestamp without time zone NOT NULL,
    last_login timestamp without time zone,
    metadata_json jsonb NOT NULL
);


--
-- Data for Name: agents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agents (id, name, description, version, status, tags, model_config_json, context, prompt_template_id, rag_config_json, memory_config_json, db_config_json, tools_json, endpoint_json, access_control_json, graph_manifest_id, created_at, updated_at, created_by, metadata_json, credential_id) FROM stdin;
agent-bid-analyzer	Bid Analyzer Agent	Score and compare supplier bids across defined evaluation criteria. Implements a 15-step LangGraph workflow: capture bids → validate completeness → autoscore non-price → load cost breakdown → calculate cost score → retrieve risk → evaluate compliance → aggregate scores → flag exceptions → build award scenarios → compare → select preferred → determine split award → route approval → finalize.	1	active	["sourcing", "bid-analysis", "award-decision", "direct-sourcing"]	{"model_id": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3}		\N	{}	{}	{}	[{"tool_id": "jaggaer-rfq-api", "tool_name": "jaggaer-rfq-api"}, {"tool_id": "jaggaer-supplier-api", "tool_name": "jaggaer-supplier-api"}, {"tool_id": "jaggaer-document-api", "tool_name": "jaggaer-document-api"}, {"tool_id": "llm-scoring", "tool_name": "llm-scoring"}]	{}	{}	\N	2026-02-16 23:27:19.643637	2026-02-16 23:27:19.643638	system	{"metrics": {"fairness": "improved bid fairness", "decision_speed": "30% faster award decisions"}, "category": "procurement", "graph_type": "langgraph", "seed_config": {"llm_model": "gemini-2.5-flash", "max_tokens": 2000, "cost_weight": 0.5, "risk_weight": 0.1, "temperature": 0.3, "quality_weight": 0.2, "delivery_weight": 0.15, "compliance_weight": 0.05, "hitl_risk_threshold": 0.7, "hitl_approval_threshold": 10000.0}, "api_readiness": "90%", "intent_domains": {}, "workflow_steps": ["capture_bid_submissions", "validate_bid_completeness", "autoscore_non_price", "load_cost_breakdown", "calculate_cost_score", "retrieve_risk_score", "evaluate_compliance", "aggregate_bid_scores", "flag_bid_exceptions", "build_award_scenarios", "compare_scenarios", "select_preferred_scenario", "determine_split_award", "route_award_for_approval", "finalize_award_decision"]}	\N
agent-supplier-data-change	Supplier Data Change Agent	Validate, process, and track updates to supplier master data records. 14-step workflow: capture request → classify change → verify mandatory data → validate bank account → collect documents → score risk → determine approval → approve profile → select update method → update master → bulk import → sync via API → notify stakeholders → close request.	1	active	["supplier-management", "master-data", "data-quality", "direct-sourcing"]	{"model_id": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3}		\N	{}	{}	{}	[{"tool_id": "jaggaer-supplier-api", "tool_name": "jaggaer-supplier-api"}, {"tool_id": "jaggaer-document-api", "tool_name": "jaggaer-document-api"}, {"tool_id": "jaggaer-action-api", "tool_name": "jaggaer-action-api"}, {"tool_id": "llm-classification", "tool_name": "llm-classification"}]	{}	{}	\N	2026-02-16 23:27:19.643639	2026-02-16 23:27:19.643639	system	{"metrics": {"errors": "fewer AP errors", "accuracy": "90% master data accuracy"}, "category": "procurement", "graph_type": "langgraph", "seed_config": {"llm_model": "gemini-2.5-flash", "max_tokens": 2000, "max_retries": 3, "temperature": 0.3, "confidence_threshold": 0.8}, "api_readiness": "100%", "intent_domains": {}, "workflow_steps": ["capture_update_request", "classify_change_type", "verify_mandatory_data", "validate_bank_account", "collect_supporting_documents", "score_change_risk", "determine_approval_workflow", "approve_supplier_profile", "select_update_method", "update_supplier_master", "bulk_import_supplier_data", "sync_supplier_master_via_api", "notify_stakeholders", "close_change_request"]}	\N
agent-workflow-approval	Workflow Approval Agent	Route purchase requests for approval based on rules and org structure. 15-step workflow: capture PR → validate data → classify spend → verify budget → assess thresholds → determine path → identify approvers → resolve delegations → create tasks → route approval → capture decision → handle rejection → escalate delays → finalize outcome → update PR status.	1	active	["approval", "purchase-request", "workflow", "direct-sourcing"]	{"model_id": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3}		\N	{}	{}	{}	[{"tool_id": "jaggaer-action-api", "tool_name": "jaggaer-action-api"}, {"tool_id": "jaggaer-user-api", "tool_name": "jaggaer-user-api"}, {"tool_id": "llm-classification", "tool_name": "llm-classification"}]	{}	{}	\N	2026-02-16 23:27:19.64364	2026-02-16 23:27:19.64364	system	{"metrics": {"speed": "60% faster approvals", "integrity": "maintained policy integrity"}, "category": "procurement", "graph_type": "langgraph", "seed_config": {"llm_model": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3, "policy_tiers": {"tier_1": {"approvers": ["manager"], "max_amount": 1000}, "tier_2": {"approvers": ["manager", "director"], "max_amount": 10000}, "tier_3": {"approvers": ["manager", "director", "vp"], "max_amount": 50000}, "tier_4": {"approvers": ["manager", "director", "vp", "cfo"], "max_amount": 999999999}}}, "api_readiness": "86%", "intent_domains": {}, "workflow_steps": ["capture_pr_submission", "validate_pr_data", "classify_spend", "verify_budget", "assess_policy_thresholds", "determine_approval_path", "identify_approvers", "resolve_delegations", "create_workflow_tasks", "route_for_approval", "capture_approver_decision", "handle_rejection", "escalate_delays", "finalize_approval_outcome", "update_pr_status"]}	\N
agent-supplier-collaboration	Supplier Collaboration Agent	Facilitate communication, task updates, and document sharing with suppliers. 13-step workflow: grant portal access → compile worklist → publish → request compliance docs → receive docs → track expiry → send notifications → create corrective action → assign tasks → monitor progress → update scorecard → initiate improvement plan → archive cycle.	1	active	["supplier-collaboration", "compliance", "scorecard", "direct-sourcing"]	{"model_id": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3}		\N	{}	{}	{}	[{"tool_id": "jaggaer-supplier-api", "tool_name": "jaggaer-supplier-api"}, {"tool_id": "jaggaer-document-api", "tool_name": "jaggaer-document-api"}, {"tool_id": "jaggaer-action-api", "tool_name": "jaggaer-action-api"}, {"tool_id": "llm-scoring", "tool_name": "llm-scoring"}]	{}	{}	\N	2026-02-16 23:27:19.643641	2026-02-16 23:27:19.643641	system	{"metrics": {"scorecard": "15% improvement in supplier scorecards"}, "category": "procurement", "graph_type": "langgraph", "seed_config": {"llm_model": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3, "required_doc_types": ["certificate", "insurance", "nda", "quality_cert", "iso_cert"], "expiry_warning_days": [60, 30, 7]}, "api_readiness": "86%", "intent_domains": {}, "workflow_steps": ["grant_portal_access", "compile_task_worklist", "publish_worklist", "request_compliance_documents", "receive_supplier_documents", "track_document_expiry", "send_expiry_notifications", "create_corrective_action", "assign_corrective_tasks", "monitor_task_progress", "update_supplier_scorecard", "initiate_improvement_plan", "archive_collaboration_cycle"]}	\N
agent-procurement-supervisor	Procurement Intelligence Supervisor	LangGraph supervisor that orchestrates the full text-to-SQL pipeline for procurement analytics. Classifies intent, routes to domain agents, coordinates cross-domain queries, manages human-in-the-loop review, and formats responses. Supports 8 intent domains: spend analysis, contract query, sourcing events, supplier lookup, savings tracking, purchase ops, category strategy, cross-domain.	1	active	["analytics", "text-to-sql", "procurement-intelligence", "supervisor"]	{"model_id": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3}		\N	{}	{}	{}	[{"tool_id": "snowflake-query", "tool_name": "snowflake-query"}, {"tool_id": "schema-vectorizer", "tool_name": "schema-vectorizer"}, {"tool_id": "few-shot-store", "tool_name": "few-shot-store"}, {"tool_id": "llm-sql-generation", "tool_name": "llm-sql-generation"}]	{}	{}	\N	2026-02-16 23:27:19.643642	2026-02-16 23:27:19.643642	system	{"metrics": {}, "category": "analytics", "graph_type": "langgraph", "seed_config": {"claude_model": "claude-sonnet-4-20250514", "sql_max_rows": 10000, "gemini_pro_model": "gemini-2.5-flash", "claude_max_tokens": 8192, "gemini_flash_model": "gemini-2.0-flash-exp", "enable_human_review": true, "sql_timeout_seconds": 60}, "api_readiness": "", "intent_domains": {"cross_domain": "Cross-domain savings and analytics", "purchase_ops": "Purchase operations and PO management", "contract_query": "Contract intelligence and compliance", "sourcing_event": "Sourcing events and RFx management", "spend_analysis": "Spend analytics and category breakdown", "supplier_lookup": "Supplier management and performance", "savings_tracking": "Value and savings tracking", "category_strategy": "Category strategy and market analysis"}, "workflow_steps": ["intent_classifier", "router", "domain_agent", "human_review", "query_executor", "insight_generator", "response_formatter"]}	\N
agent-domain-spend	Spend Analytics Domain Agent	Domain-specific agent for spend analysis queries. Implements a 7-step text-to-SQL pipeline: load semantic model → build schema context (vector retrieval) → enrich query (entity resolution) → generate SQL → validate SQL → explain SQL → return.	1	active	["analytics", "spend-analysis", "text-to-sql", "domain-agent"]	{"model_id": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3}		\N	{}	{}	{}	[{"tool_id": "snowflake-query", "tool_name": "snowflake-query"}, {"tool_id": "schema-vectorizer", "tool_name": "schema-vectorizer"}, {"tool_id": "llm-sql-generation", "tool_name": "llm-sql-generation"}]	{}	{}	\N	2026-02-16 23:27:19.643643	2026-02-16 23:27:19.643643	system	{"metrics": {}, "category": "analytics", "graph_type": "langgraph", "seed_config": {"domain": "spend", "semantic_model_name": "spend_analytics", "schema_retrieval_top_k": 10}, "api_readiness": "", "intent_domains": {}, "workflow_steps": ["load_semantic_model", "build_schema_context", "enrich_query", "generate_sql", "validate_sql", "explain_sql", "return_result"]}	\N
agent-domain-contract	Contract Intelligence Domain Agent	Domain-specific agent for contract queries and compliance analysis. Same 7-step pipeline as spend agent but with contract-specific semantic model.	1	active	["analytics", "contract", "text-to-sql", "domain-agent"]	{"model_id": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3}		\N	{}	{}	{}	[{"tool_id": "snowflake-query", "tool_name": "snowflake-query"}, {"tool_id": "schema-vectorizer", "tool_name": "schema-vectorizer"}, {"tool_id": "llm-sql-generation", "tool_name": "llm-sql-generation"}]	{}	{}	\N	2026-02-16 23:27:19.643644	2026-02-16 23:27:19.643644	system	{"metrics": {}, "category": "analytics", "graph_type": "langgraph", "seed_config": {"domain": "contract", "semantic_model_name": "contract_intelligence"}, "api_readiness": "", "intent_domains": {}, "workflow_steps": ["load_semantic_model", "build_schema_context", "enrich_query", "generate_sql", "validate_sql", "explain_sql", "return_result"]}	\N
agent-domain-supplier	Supplier Management Domain Agent	Domain-specific agent for supplier lookup, performance, and risk queries.	1	active	["analytics", "supplier", "text-to-sql", "domain-agent"]	{"model_id": "gemini-2.5-flash", "max_tokens": 2000, "temperature": 0.3}		\N	{}	{}	{}	[{"tool_id": "snowflake-query", "tool_name": "snowflake-query"}, {"tool_id": "schema-vectorizer", "tool_name": "schema-vectorizer"}, {"tool_id": "llm-sql-generation", "tool_name": "llm-sql-generation"}]	{}	{}	\N	2026-02-16 23:27:19.643645	2026-02-16 23:27:19.643645	system	{"metrics": {}, "category": "analytics", "graph_type": "langgraph", "seed_config": {"domain": "supplier", "semantic_model_name": "supplier_management"}, "api_readiness": "", "intent_domains": {}, "workflow_steps": ["load_semantic_model", "build_schema_context", "enrich_query", "generate_sql", "validate_sql", "explain_sql", "return_result"]}	\N
\.


--
-- Data for Name: guardrail_rules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.guardrail_rules (id, name, description, rule_type, scope, action, enabled, applies_to, config_json, agent_ids, group_ids, is_deployed, times_triggered, last_triggered, created_at, updated_at, created_by) FROM stdin;
gr-b35d7b45	PII Detection & Redaction	Detect and redact personally identifiable information (emails, phone numbers, SSN, credit cards) in agent inputs and outputs using Guardrails AI detect_pii validator	pii_detection	global	redact	t	both	{"pii_entities": ["EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "CREDIT_CARD"]}	[]	[]	f	0	\N	2026-02-17 01:15:18.69245	2026-02-17 01:15:18.692451	admin
gr-c486c485	Prompt Injection Guard	Detect and block jailbreak attempts, prompt injection, and instruction override patterns in user inputs	prompt_injection	global	block	t	input	{"additional_patterns": []}	[]	[]	f	0	\N	2026-02-17 01:15:18.692454	2026-02-17 01:15:18.692454	admin
gr-f65e2003	Profanity Guard	Ensure agent outputs are free of profanity and offensive words using Guardrails AI profanity_free validator	profanity	global	block	t	output	{}	[]	[]	f	0	\N	2026-02-17 01:15:18.692456	2026-02-17 01:15:18.692456	admin
gr-1b7ff07c	Output Length Limit	Enforce maximum and minimum character length on agent responses using Guardrails AI valid_length validator	valid_length	global	block	t	output	{"max": 10000, "min": 1}	[]	[]	f	0	\N	2026-02-17 01:15:18.692458	2026-02-17 01:15:18.692458	admin
gr-2d62a944	Reading Time Check	Ensure agent responses stay within a readable time limit using Guardrails AI reading_time validator	reading_time	global	warn	t	output	{"reading_time": 5}	[]	[]	f	0	\N	2026-02-17 01:15:18.69246	2026-02-17 01:15:18.69246	admin
gr-a6f94f6d	Sensitive Pattern Filter	Block or flag text matching sensitive regex patterns (e.g. internal codes, API keys) using Guardrails AI regex_match validator	regex_match	global	redact	t	both	{"regex": "(?i)(api[_-]?key|secret|password|CONFIDENTIAL|INTERNAL_ONLY)"}	[]	[]	f	0	\N	2026-02-17 01:15:18.692462	2026-02-17 01:18:21.271929	admin
\.


--
-- Data for Name: integrations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.integrations (id, name, provider, description, api_key_encrypted, api_key_masked, auth_type, service_account_json, endpoint_url, project_id, default_model, allowed_models, registered_models, rate_limit_rpm, assigned_group_ids, status, last_tested, last_error, created_by, created_at, updated_at, metadata_json, service_account_json_encrypted) FROM stdin;
int-3603e6f4	test	google			service-acct	service_account	{"type": "service_account", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "client_id": "113386300297143683883", "token_uri": "https://oauth2.googleapis.com/token", "project_id": "gcp-jai-assist-dev", "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQD06Z+UtUb5Ppij\\nEN4Dn9aVgg0bf0tLQQRKT9Qte9MwBk1KBZrr/E97Eu7YAJzIFVjx9Nl1ASB+CXvY\\n0pNHo7O9Hksm7YABkjX2ygucVTLU8P17nF0BtqVtQ4sohBpU85n9TAhrCvO7V+AA\\ncWdOJoyZZbMwrwraXaGfFYJkUhZ0xrgGu2Nz3EDRTfqcfmTzlKp/+YrxE70du/zS\\n5V2ySZJtpR46AJ00gG8gBtvSriOugCfm5h/fLYLgTwky/28JckWrwq6UbiwGS5+I\\n1hHg3VuZ5+rWjSZH+zR3GCCDdRA1ecSjV0x5cgghsitIRa1lO4X4uSYbOTWqzq8s\\nq9hX1969AgMBAAECggEACcNkynGV5aU+bKUP6K6USBZXY0ImPwGARDMdpv4xm3pA\\n1gOBBckjj6k1Tsnqy294bIAsNBB1BQ6Sj+tIa5nFy537ynk7egnkBKrQyYJm+fCt\\nIOKenY0fAqBSREL3PBg69QtKfElDO/PDQ66W+u6pT7XWGHR97FnBBz29BTagMQxP\\n/lrxd062kp8YO5y8huuegGS/MXQBb/+haR2IyPiRGwlGRc2XLhr6T8d53hlFzP4l\\n1ZKVOHcYtA1WpACW2MQhENTgSxZfDmwN95YDV8yshAICUUsbmYCERfSQRmPvwLIV\\nk9YRsmKpEDqG1rw3jSomAbnN4GdzDo4Z+j3ZR5OscQKBgQD8M78SQ4ulagJ0PMiC\\nTtSX4fXzIdwImsTIst3yH0RzjlSpVQwsne6P+T5PoR8+woENWRp1vQ2axaMACX1M\\n8Fe/5MU1bL/s5h9eRtKsTDhMu/6A1xxlRYU7KnYR/b+fTmqc9YOr6tb4Pd44uw+S\\nZNW4D9vJ//9Jb9QMMweItEKakQKBgQD4mcZ/sRoD7mtge0OmsU+djcftM73DMWSI\\nn4xsWXmi5m4bvBEUBzLsBRJyxl7uXjKUkTu1dmMcA8WEojKwPilX4dxVSXyJXw2z\\nr2Kn1IwSthw0dX1jcgpn4Xm0R88dsspwavoPOMp+MZad/MXIr/7u/AgUlGeUnOsN\\nrrC+x7yfbQKBgQCofcnBYe8B6/kHvzQWGqRddFDkxlJCTWP60cUF5W3N5eEZ3//q\\nLvkapuHCQVqmizu8tzK+Rje4lyF2/OABbvCw+x3lu2nd00BRs+87vRA/87jsSspl\\nvjRsesm261gCDlmb00rMqHBGGM9GB3M30rYV6kJkier8HQIFxHHcGtIEgQKBgQDi\\nzula9qlVjOBKViuSmZKZnBEbSGmI/DdMrsPe1oMzLCipBRxPuYGr87SxImrZ7vcW\\ntKpVFH23wXkjWRgF07DEjTwIU9NbQW2u0gSgOjrRl3SEJ+0OHa2AuSXgZOOBpO0t\\nQ2yBFr8oAvX3jfak8m0UfLyiigM2gzOweACpDnH4wQKBgEfoQuHE89HAxARw0kqR\\nCAJmWQENjo3RllqAejx56ZTuUQ3pKnobd4NDMFaJqmitSEWfHh9I2FHUTV46LbGQ\\n0gsAi6vF3iba6rZNQuLaRQJG8+f49yNAPWuoPIvPRnMk1Y1pEj659WjzROjosXIZ\\ngTcnYVnMxioKUl2852WX4GlH\\n-----END PRIVATE KEY-----\\n", "client_email": "806842104863-compute@developer.gserviceaccount.com", "private_key_id": "35782d2e7874aa6a0feb8dc7bd1ac4537e8644ca", "universe_domain": "googleapis.com", "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/806842104863-compute%40developer.gserviceaccount.com", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"}	us-central1	gcp-jai-assist-dev	gemini-2.5-flash	[]	["gemini-2.0-flash-001", "gemini-2.0-flash-lite-001", "gemini-2.5-computer-use-preview-10-2025", "gemini-2.5-flash", "gemini-2.5-flash-image"]	0	[]	active	\N		admin	2026-02-17 02:15:01.983801	2026-02-17 02:15:01.983804	{}	
\.


--
-- Data for Name: prompt_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.prompt_templates (id, name, description, category, tags, content, variables, version, is_builtin, created_at, updated_at, created_by) FROM stdin;
prompt-intent-classification	Intent Classification	Classify user query into procurement domain intent for routing.	classification	[]	You are a procurement intelligence classifier. Analyze the user's question and classify it into exactly ONE of these intents:\n- spend_analysis: Questions about spending, budgets, cost breakdowns\n- contract_query: Questions about contracts, terms, compliance\n- sourcing_event: Questions about RFQs, RFPs, sourcing events\n- supplier_lookup: Questions about suppliers, vendor performance\n- savings_tracking: Questions about savings, cost avoidance\n- purchase_ops: Questions about POs, requisitions, receipts\n- category_strategy: Questions about category management\n- cross_domain: Questions spanning multiple domains\n\nUser question: {question}\n\nRespond with JSON: {{"intent": "<intent>", "confidence": <0.0-1.0>, "reasoning": "<brief>"}}	[]	1	t	2026-02-16 23:27:19.649084	2026-02-16 23:27:19.649084	system
prompt-sql-generation	Text-to-SQL Generation	Generate Snowflake SQL from natural language with schema context.	sql-generation	[]	You are an expert Snowflake SQL analyst for procurement data.\n\nSCHEMA CONTEXT:\n{schema_context}\n\nSEMANTIC MODEL:\n{semantic_model}\n\nFEW-SHOT EXAMPLES:\n{few_shot_examples}\n\nRULES:\n- Use only views and columns from the schema context\n- Always include LIMIT {max_rows}\n- Use proper Snowflake SQL syntax\n- Include helpful column aliases\n- Add ORDER BY for meaningful results\n\nUser question: {question}\n\nGenerate the SQL query:	[]	1	t	2026-02-16 23:27:19.649085	2026-02-16 23:27:19.649085	system
prompt-bid-scoring	Bid Scoring Prompt	AI-powered bid evaluation across cost, quality, delivery, risk, compliance.	evaluation	[]	You are a procurement bid evaluation expert. Score this supplier bid.\n\nBID DATA:\n{bid_data}\n\nEVALUATION CRITERIA:\n- Cost (50%): Price competitiveness vs. market benchmarks\n- Quality (20%): Technical capability, certifications, past performance\n- Delivery (15%): Lead time, reliability, logistics capability\n- Risk (10%): Financial stability, geopolitical risk, single-source risk\n- Compliance (5%): Regulatory, environmental, social compliance\n\nRespond with JSON: {{"cost_score": <0-100>, "quality_score": <0-100>, "delivery_score": <0-100>, "risk_score": <0-100>, "compliance_score": <0-100>, "weighted_total": <0-100>, "recommendation": "<award/reject/review>", "justification": "<brief>"}}	[]	1	t	2026-02-16 23:27:19.649085	2026-02-16 23:27:19.649085	system
prompt-change-risk	Supplier Change Risk Assessment	Assess risk level of supplier data changes for approval routing.	risk-assessment	[]	You are a supplier master data risk assessor.\n\nCHANGE REQUEST:\n{change_data}\n\nAssess the risk of this change considering:\n- Bank account changes (HIGH risk)\n- Address/contact changes (MEDIUM risk)\n- Classification changes (LOW risk)\n- Volume of changes in single request\n- Supplier criticality tier\n\nRespond with JSON: {{"risk_score": <0.0-1.0>, "risk_level": "low|medium|high|critical", "requires_approval": <true/false>, "approval_tier": "<tier>", "risk_factors": ["<factor1>", ...]}}	[]	1	t	2026-02-16 23:27:19.649086	2026-02-16 23:27:19.649086	system
prompt-approval-routing	PR Approval Routing	Determine approval path for purchase requests based on amount and policy.	workflow	[]	You are a procurement approval routing engine.\n\nPURCHASE REQUEST:\n{pr_data}\n\nPOLICY TIERS:\n- Tier 1 (≤$1,000): Manager only\n- Tier 2 (≤$10,000): Manager + Director\n- Tier 3 (≤$50,000): Manager + Director + VP\n- Tier 4 (>$50,000): Manager + Director + VP + CFO\n\nDetermine the approval path and respond with JSON: {{"tier": "<tier>", "approvers": ["<role1>", ...], "estimated_days": <int>, "auto_approve": <true/false>, "escalation_after_days": <int>}}	[]	1	t	2026-02-16 23:27:19.649086	2026-02-16 23:27:19.649086	system
\.


--
-- Data for Name: provider_credentials; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.provider_credentials (id, name, provider, credential_blob, display_metadata, is_active, created_at, updated_at, created_by) FROM stdin;
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants (id, name, slug, tier, owner_email, domain, is_active, settings_json, quota_json, allowed_providers, created_at, updated_at) FROM stdin;
tenant-default	Jaggaer Default	default	enterprise	admin@jaggaer.com	jaggaer.com	t	{}	{"max_tools": 200, "max_users": 50, "max_agents": 100, "max_api_keys": 10, "llm_requests_per_day": 10000, "llm_requests_per_minute": 60}	["google", "anthropic", "openai", "ollama"]	2026-02-16 23:27:19.64169	2026-02-16 23:27:19.641691
\.


--
-- Data for Name: tools; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tools (id, name, description, tool_type, category, status, tags, config_json, endpoints_json, is_public, is_platform_tool, created_at, updated_at, created_by, metadata_json) FROM stdin;
jaggaer-supplier-api	Jaggaer Supplier API	CRUD operations on Jaggaer Direct Sourcing supplier records. List, get, import, update suppliers and contacts.	api	enterprise-connector	active	["jaggaer", "supplier", "api", "direct-sourcing"]	{"headers": {"X-TENANT-ID": "${JAGGAER_TENANT_ID}", "X-JAGGAER-ORIGINATION": "agentic-ai"}, "base_url": "https://premajor.app11.jaggaer.com/arc/api", "auth_type": "bearer", "retry_attempts": 3, "timeout_seconds": 60, "rate_limit_per_minute": 60}	[{"path": "/direct-suppliers", "method": "GET", "description": "List suppliers"}, {"path": "/direct-suppliers/{id}", "method": "GET", "description": "Get supplier by ID"}, {"path": "/direct-suppliers/count", "method": "GET", "description": "Get supplier count"}, {"path": "/suppliers/import", "method": "POST", "description": "Import suppliers"}, {"path": "/suppliers/company", "method": "POST", "description": "Import supplier company"}, {"path": "/suppliers/contact", "method": "POST", "description": "Import supplier contact"}, {"path": "/suppliers/user", "method": "POST", "description": "Import supplier user"}, {"path": "/suppliers/user/{id}/status", "method": "POST", "description": "Update user status"}]	t	f	2026-02-16 23:27:19.64623	2026-02-16 23:27:19.646231	system	{}
jaggaer-rfq-api	Jaggaer RFQ API	Manage Direct RFQs — list, get details, documents, items, quotations, and suppliers.	api	enterprise-connector	active	["jaggaer", "rfq", "sourcing", "api"]	{"headers": {"X-TENANT-ID": "${JAGGAER_TENANT_ID}", "X-JAGGAER-ORIGINATION": "agentic-ai"}, "base_url": "https://premajor.app11.jaggaer.com/arc/api", "auth_type": "bearer"}	[{"path": "/direct-rfqs", "method": "GET", "description": "List Direct RFQs"}, {"path": "/direct-rfqs/{id}", "method": "GET", "description": "Get RFQ by ID"}, {"path": "/direct-rfqs/{id}/documents", "method": "GET", "description": "List RFQ documents"}, {"path": "/direct-rfqs/{id}/items", "method": "GET", "description": "List RFQ items"}, {"path": "/direct-rfqs/{id}/quotations", "method": "GET", "description": "List RFQ quotations"}, {"path": "/direct-rfqs/{id}/suppliers", "method": "GET", "description": "List RFQ suppliers"}, {"path": "/direct-rfqs/count", "method": "GET", "description": "Get RFQ count"}]	t	f	2026-02-16 23:27:19.646231	2026-02-16 23:27:19.646231	system	{}
jaggaer-action-api	Jaggaer Action API	Create, list, update actions and manage action files in Jaggaer platform.	api	enterprise-connector	active	["jaggaer", "action", "workflow", "api"]	{"headers": {"X-TENANT-ID": "${JAGGAER_TENANT_ID}", "X-JAGGAER-ORIGINATION": "agentic-ai"}, "base_url": "https://premajor.app11.jaggaer.com/arc/api", "auth_type": "bearer"}	[{"path": "/actions", "method": "POST", "description": "Create action"}, {"path": "/actions", "method": "GET", "description": "List actions"}, {"path": "/actions/{id}", "method": "GET", "description": "Get action by ID"}, {"path": "/actions/{id}", "method": "PATCH", "description": "Update action"}, {"path": "/actions/{id}/files", "method": "POST", "description": "Add action files"}, {"path": "/actions/{id}/files", "method": "GET", "description": "List action files"}]	t	f	2026-02-16 23:27:19.646231	2026-02-16 23:27:19.646232	system	{}
jaggaer-document-api	Jaggaer Document API	Document management — create, list, get documents and manage file attachments.	api	enterprise-connector	active	["jaggaer", "document", "file", "api"]	{"headers": {"X-TENANT-ID": "${JAGGAER_TENANT_ID}", "X-JAGGAER-ORIGINATION": "agentic-ai"}, "base_url": "https://premajor.app11.jaggaer.com/arc/api", "auth_type": "bearer"}	[{"path": "/documents", "method": "GET", "description": "List documents"}, {"path": "/documents/{id}", "method": "GET", "description": "Get document by ID"}, {"path": "/documents", "method": "POST", "description": "Create document"}, {"path": "/documents/{id}/files", "method": "POST", "description": "Add document files"}, {"path": "/documents/{id}/files", "method": "GET", "description": "List document files"}]	t	f	2026-02-16 23:27:19.646232	2026-02-16 23:27:19.646232	system	{}
jaggaer-commodity-api	Jaggaer Commodity API	Commodity management — clusters, commodities, and commodity-supplier mappings.	api	enterprise-connector	active	["jaggaer", "commodity", "category", "api"]	{"base_url": "https://premajor.app11.jaggaer.com/arc/api", "auth_type": "bearer"}	[{"path": "/commodities/clusters", "method": "GET", "description": "List commodity clusters"}, {"path": "/commodities/clusters/{id}", "method": "GET", "description": "Get cluster by ID"}, {"path": "/commodities", "method": "GET", "description": "List commodities"}, {"path": "/commodities/{id}", "method": "GET", "description": "Get commodity by ID"}, {"path": "/commodities/{id}/suppliers", "method": "GET", "description": "List commodity suppliers"}]	t	f	2026-02-16 23:27:19.646232	2026-02-16 23:27:19.646232	system	{}
jaggaer-bom-api	Jaggaer BOM API	Bill of Materials management — list, get, create BOMs and manage BOM items.	api	enterprise-connector	active	["jaggaer", "bom", "materials", "api"]	{"base_url": "https://premajor.app11.jaggaer.com/arc/api", "auth_type": "bearer"}	[{"path": "/boms", "method": "GET", "description": "List BOM headers"}, {"path": "/boms/{id}", "method": "GET", "description": "Get BOM header"}, {"path": "/boms/{id}/items", "method": "GET", "description": "Get BOM with items"}, {"path": "/boms", "method": "POST", "description": "Create BOM"}, {"path": "/boms/{id}/items", "method": "POST", "description": "Add BOM item"}, {"path": "/boms/{id}/activate", "method": "PATCH", "description": "Activate BOM"}]	t	f	2026-02-16 23:27:19.646233	2026-02-16 23:27:19.646233	system	{}
jaggaer-material-api	Jaggaer Material API	Direct material management — list, get, create, update materials.	api	enterprise-connector	active	["jaggaer", "material", "api"]	{"base_url": "https://premajor.app11.jaggaer.com/arc/api", "auth_type": "bearer"}	[{"path": "/materials", "method": "GET", "description": "List materials"}, {"path": "/materials/{id}", "method": "GET", "description": "Get material by ID"}, {"path": "/materials", "method": "POST", "description": "Create material"}, {"path": "/materials/{id}", "method": "PATCH", "description": "Update material"}]	t	f	2026-02-16 23:27:19.646233	2026-02-16 23:27:19.646233	system	{}
jaggaer-user-api	Jaggaer User & Group API	Buyer user management and group listing for approval routing.	api	enterprise-connector	active	["jaggaer", "user", "group", "api"]	{"base_url": "https://premajor.app11.jaggaer.com/arc/api", "auth_type": "bearer"}	[{"path": "/direct-users", "method": "GET", "description": "List buyer users"}, {"path": "/direct-users/{id}", "method": "GET", "description": "Get buyer user by ID"}, {"path": "/groups", "method": "GET", "description": "List groups"}]	t	f	2026-02-16 23:27:19.646233	2026-02-16 23:27:19.646233	system	{}
jaggaer-idoc-api	Jaggaer IDoc / ERP Integration	SAP IDoc import and monitoring for ERP integration.	api	enterprise-connector	active	["jaggaer", "idoc", "sap", "erp", "api"]	{"base_url": "https://premajor.app11.jaggaer.com/arc/api", "auth_type": "bearer"}	[{"path": "/idocs", "method": "POST", "description": "Import IDoc"}, {"path": "/idoc-monitoring-logs", "method": "GET", "description": "List IDoc monitoring logs"}]	t	f	2026-02-16 23:27:19.646234	2026-02-16 23:27:19.646234	system	{}
snowflake-query	Snowflake SQL Query	Execute validated SQL queries against Snowflake data warehouse. Supports JAGGAER_DW database with 803 views across 6 procurement domains.	db	data-connector	active	["snowflake", "sql", "analytics", "data-warehouse"]	{"role": "ANALYST_ROLE", "schema": "ANALYTICS", "database": "JAGGAER_DW", "max_rows": 10000, "warehouse": "COMPUTE_WH", "auth_methods": ["password", "key-pair", "sso"], "timeout_seconds": 60}	[]	t	f	2026-02-16 23:27:19.646234	2026-02-16 23:27:19.646234	system	{}
schema-vectorizer	Schema Vectorizer	ChromaDB-backed vector store for schema retrieval. Embeds 803 Snowflake views for semantic search during SQL generation. Returns top-K relevant schemas.	rag	data-connector	active	["chromadb", "vector-search", "schema", "embedding"]	{"top_k": 10, "persist_dir": "./chroma_db", "collection_name": "jaggaer_schema"}	[]	t	f	2026-02-16 23:27:19.646234	2026-02-16 23:27:19.646235	system	{}
few-shot-store	Few-Shot Example Store	Curated library of question→SQL examples per procurement domain. Used for in-context learning during SQL generation.	rag	data-connector	active	["few-shot", "examples", "sql", "in-context-learning"]	{}	[]	t	f	2026-02-16 23:27:19.646235	2026-02-16 23:27:19.646235	system	{}
llm-sql-generation	LLM SQL Generator	Dual-LLM SQL generation: Claude for complex reasoning, Gemini for validation. Includes SQL guardrails, error correction, and explanation generation.	llm	ai-tool	active	["sql-generation", "text-to-sql", "dual-llm"]	{"max_retries": 3, "primary_model": "claude-sonnet-4-20250514", "validation_model": "gemini-2.0-flash-exp"}	[]	t	f	2026-02-16 23:27:19.646235	2026-02-16 23:27:19.646235	system	{}
llm-classification	LLM Intent Classifier	Fast intent classification using Gemini Flash. Routes queries to the correct domain agent based on procurement intent.	llm	ai-tool	active	["classification", "intent", "routing"]	{"model": "gemini-2.5-flash", "max_tokens": 200, "temperature": 0.0}	[]	t	f	2026-02-16 23:27:19.646235	2026-02-16 23:27:19.646236	system	{}
llm-scoring	LLM Scoring Engine	AI-powered scoring for bids, risk assessment, compliance evaluation, and supplier scorecards using structured output.	llm	ai-tool	active	["scoring", "risk", "compliance", "evaluation"]	{"model": "gemini-2.5-flash", "temperature": 0.3, "structured_output": true}	[]	t	f	2026-02-16 23:27:19.646236	2026-02-16 23:27:19.646236	system	{}
platform-ocr	OCR – Document Text Extraction	Extract text from scanned PDFs, images (PNG/JPG/TIFF), and photos of documents using Google Cloud Vision API. Supports handwriting, tables, and multi-language.	api	platform-builtin	active	["ocr", "vision", "pdf", "image", "extraction", "platform"]	{"features": ["TEXT_DETECTION", "DOCUMENT_TEXT_DETECTION", "TABLE_DETECTION"], "provider": "google-cloud-vision", "languages": ["en", "de", "fr", "es", "it", "pt", "ja", "zh"], "max_file_size_mb": 20, "supported_formats": ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"]}	[]	t	t	2026-02-16 23:27:19.646236	2026-02-16 23:27:19.646236	system	{}
platform-calculator	Calculator – Math & Financial Expressions	Evaluate mathematical and financial expressions safely. Supports arithmetic, percentages, currency conversion, NPV, IRR, amortization, and unit conversions.	python	platform-builtin	active	["calculator", "math", "finance", "currency", "platform"]	{"safe_mode": true, "max_precision": 15, "supported_operations": ["arithmetic", "percentages", "currency_conversion", "npv", "irr", "amortization", "unit_conversion"]}	[]	t	t	2026-02-16 23:27:19.646236	2026-02-16 23:27:19.646237	system	{}
platform-translator	Translator – Multi-Language Translation	Translate text between 100+ languages using Google Cloud Translation API. Supports auto-detection, glossary terms, and batch translation.	api	platform-builtin	active	["translator", "language", "i18n", "localization", "platform"]	{"provider": "google-cloud-translate", "max_chars": 50000, "default_target": "en", "glossary_support": true}	[]	t	t	2026-02-16 23:27:19.646237	2026-02-16 23:27:19.646237	system	{}
platform-summarizer	Summarizer – Document & Text Summarization	Summarize long documents, emails, meeting notes, and contracts into concise bullet points or executive summaries. Configurable length and style.	llm	platform-builtin	active	["summarizer", "text", "document", "extraction", "platform"]	{"model": "gemini-2.5-flash", "styles": ["bullets", "executive", "technical", "one-liner"], "max_input_tokens": 128000, "default_max_output": 500}	[]	t	t	2026-02-16 23:27:19.646237	2026-02-16 23:27:19.646237	system	{}
platform-sentiment	Sentiment Analyzer	Analyze sentiment and emotion in text — supplier communications, survey responses, feedback forms. Returns polarity, magnitude, and emotion labels.	llm	platform-builtin	active	["sentiment", "nlp", "analysis", "emotion", "platform"]	{"model": "gemini-2.5-flash", "emotions": ["positive", "negative", "neutral", "anger", "satisfaction", "urgency"], "output_format": "json"}	[]	t	t	2026-02-16 23:27:19.646237	2026-02-16 23:27:19.646238	system	{}
platform-entity-extractor	Entity Extractor – NER & Key Info	Extract named entities (companies, people, dates, amounts, contract terms) from unstructured text using LLM-powered NER.	llm	platform-builtin	active	["ner", "entity", "extraction", "nlp", "platform"]	{"model": "gemini-2.5-flash", "entity_types": ["PERSON", "ORG", "DATE", "MONEY", "PERCENT", "CONTRACT_TERM", "PRODUCT", "LOCATION"]}	[]	t	t	2026-02-16 23:27:19.646238	2026-02-16 23:27:19.646238	system	{}
platform-email-composer	Email Composer – Smart Drafting	Draft professional procurement emails — RFQ follow-ups, supplier notifications, approval requests, escalation notices. Tone and template configurable.	llm	platform-builtin	active	["email", "drafting", "communication", "template", "platform"]	{"model": "gemini-2.5-flash", "tones": ["formal", "friendly", "urgent", "neutral"], "templates": ["rfq_followup", "supplier_notification", "approval_request", "escalation", "thank_you", "rejection_notice"]}	[]	t	t	2026-02-16 23:27:19.646238	2026-02-16 23:27:19.646238	system	{}
platform-web-search	Web Search – Real-time Information	Search the web for real-time supplier news, market prices, regulatory updates, and company information using Google Custom Search API.	api	platform-builtin	active	["search", "web", "news", "market", "platform"]	{"provider": "google-custom-search", "max_results": 10, "safe_search": true}	[]	t	t	2026-02-16 23:27:19.646239	2026-02-16 23:27:19.646239	system	{}
platform-pdf-generator	PDF Generator – Report & Doc Creation	Generate formatted PDF reports from structured data — bid comparisons, scorecards, audit trails, executive summaries.	python	platform-builtin	active	["pdf", "report", "document", "generation", "platform"]	{"branding": "jaggaer", "max_pages": 50, "templates": ["bid_comparison", "supplier_scorecard", "audit_trail", "executive_summary", "contract_summary"]}	[]	t	t	2026-02-16 23:27:19.646239	2026-02-16 23:27:19.646239	system	{}
platform-data-validator	Data Validator – Schema & Format Checks	Validate data against schemas, check formats (email, phone, DUNS, VAT), detect duplicates, and ensure referential integrity.	python	platform-builtin	active	["validation", "data-quality", "schema", "format", "platform"]	{"validators": ["email", "phone", "duns", "vat", "iban", "swift", "iso_country", "currency_code", "date_format"], "duplicate_detection": true}	[]	t	t	2026-02-16 23:27:19.646239	2026-02-16 23:27:19.646239	system	{}
workato-sap	SAP S/4HANA (via Workato)	Connect to SAP S/4HANA for purchase orders, material masters, vendor masters, and financial postings. Supports IDoc, BAPI, and OData interfaces.	workato	erp	active	["sap", "erp", "purchase-order", "vendor", "material"]	{"icon": "sap", "actions": [{"name": "Get Purchase Order", "path": "/sap/po/{id}", "method": "GET"}, {"name": "Create Purchase Order", "path": "/sap/po", "method": "POST"}, {"name": "Get Vendor Master", "path": "/sap/vendor/{id}", "method": "GET"}, {"name": "Post Goods Receipt", "path": "/sap/gr", "method": "POST"}, {"name": "Get Material Master", "path": "/sap/material/{id}", "method": "GET"}, {"name": "Create Invoice", "path": "/sap/invoice", "method": "POST"}], "triggers": [{"name": "New Purchase Order", "event": "po.created"}, {"name": "PO Status Changed", "event": "po.status_changed"}, {"name": "Goods Receipt Posted", "event": "gr.posted"}, {"name": "Invoice Received", "event": "invoice.received"}], "auth_type": "oauth2", "workato_config": {"connection_type": "on_prem_agent", "recipe_template": "sap_procurement_sync"}}	[]	t	f	2026-02-16 23:27:19.647432	2026-02-16 23:27:19.647432	system	{"source": "workato"}
workato-salesforce	Salesforce CRM (via Workato)	Sync supplier and contract data with Salesforce. Manage accounts, opportunities, and custom procurement objects.	workato	crm	active	["salesforce", "crm", "supplier", "contract"]	{"icon": "salesforce", "actions": [{"name": "Get Account", "path": "/sf/account/{id}", "method": "GET"}, {"name": "Create Account", "path": "/sf/account", "method": "POST"}, {"name": "Update Account", "path": "/sf/account/{id}", "method": "PATCH"}, {"name": "Search Accounts", "path": "/sf/account/search", "method": "GET"}, {"name": "Get Opportunity", "path": "/sf/opportunity/{id}", "method": "GET"}, {"name": "Create Contract", "path": "/sf/contract", "method": "POST"}], "triggers": [{"name": "New Account", "event": "account.created"}, {"name": "Account Updated", "event": "account.updated"}, {"name": "Opportunity Won", "event": "opportunity.won"}], "auth_type": "oauth2", "workato_config": {"connection_type": "cloud", "recipe_template": "sf_supplier_sync"}}	[]	t	f	2026-02-16 23:27:19.647432	2026-02-16 23:27:19.647433	system	{"source": "workato"}
workato-servicenow	ServiceNow ITSM (via Workato)	Integrate with ServiceNow for IT procurement workflows, change management, and asset management.	workato	itsm	active	["servicenow", "itsm", "change-management", "asset"]	{"icon": "servicenow", "actions": [{"name": "Create Incident", "path": "/snow/incident", "method": "POST"}, {"name": "Get Change Request", "path": "/snow/change/{id}", "method": "GET"}, {"name": "Create Change Request", "path": "/snow/change", "method": "POST"}, {"name": "Get Asset", "path": "/snow/asset/{id}", "method": "GET"}, {"name": "Update CMDB", "path": "/snow/cmdb/{id}", "method": "PATCH"}], "triggers": [{"name": "New Incident", "event": "incident.created"}, {"name": "Change Approved", "event": "change.approved"}, {"name": "Asset Retired", "event": "asset.retired"}], "auth_type": "oauth2", "workato_config": {"connection_type": "cloud", "recipe_template": "snow_procurement_integration"}}	[]	t	f	2026-02-16 23:27:19.647433	2026-02-16 23:27:19.647433	system	{"source": "workato"}
workato-coupa	Coupa Procurement (via Workato)	Connect to Coupa for requisitions, purchase orders, invoices, and supplier management.	workato	procurement	active	["coupa", "procurement", "requisition", "invoice"]	{"icon": "coupa", "actions": [{"name": "Get Requisition", "path": "/coupa/requisition/{id}", "method": "GET"}, {"name": "Create Requisition", "path": "/coupa/requisition", "method": "POST"}, {"name": "Get Purchase Order", "path": "/coupa/po/{id}", "method": "GET"}, {"name": "Get Invoice", "path": "/coupa/invoice/{id}", "method": "GET"}, {"name": "Approve Invoice", "path": "/coupa/invoice/{id}/approve", "method": "POST"}, {"name": "Get Supplier", "path": "/coupa/supplier/{id}", "method": "GET"}], "triggers": [{"name": "New Requisition", "event": "requisition.created"}, {"name": "PO Approved", "event": "po.approved"}, {"name": "Invoice Submitted", "event": "invoice.submitted"}], "auth_type": "oauth2", "workato_config": {"connection_type": "cloud", "recipe_template": "coupa_jaggaer_sync"}}	[]	t	f	2026-02-16 23:27:19.647433	2026-02-16 23:27:19.647433	system	{"source": "workato"}
workato-oracle	Oracle ERP Cloud (via Workato)	Connect to Oracle ERP Cloud for procurement, payables, and supplier management.	workato	erp	active	["oracle", "erp", "procurement", "payables"]	{"icon": "oracle", "actions": [{"name": "Get Purchase Order", "path": "/oracle/po/{id}", "method": "GET"}, {"name": "Create Requisition", "path": "/oracle/requisition", "method": "POST"}, {"name": "Get Supplier", "path": "/oracle/supplier/{id}", "method": "GET"}, {"name": "Create Invoice", "path": "/oracle/invoice", "method": "POST"}, {"name": "Get Receipt", "path": "/oracle/receipt/{id}", "method": "GET"}], "triggers": [{"name": "PO Created", "event": "po.created"}, {"name": "Invoice Approved", "event": "invoice.approved"}, {"name": "Supplier Updated", "event": "supplier.updated"}], "auth_type": "oauth2", "workato_config": {"connection_type": "cloud", "recipe_template": "oracle_procurement_sync"}}	[]	t	f	2026-02-16 23:27:19.647433	2026-02-16 23:27:19.647434	system	{"source": "workato"}
workato-netsuite	NetSuite ERP (via Workato)	Connect to NetSuite for vendor bills, purchase orders, and item management.	workato	erp	active	["netsuite", "erp", "vendor", "purchase-order"]	{"icon": "netsuite", "actions": [{"name": "Get Vendor Bill", "path": "/ns/vendorbill/{id}", "method": "GET"}, {"name": "Create Purchase Order", "path": "/ns/purchaseorder", "method": "POST"}, {"name": "Get Vendor", "path": "/ns/vendor/{id}", "method": "GET"}, {"name": "Search Items", "path": "/ns/item/search", "method": "GET"}], "triggers": [{"name": "New Vendor Bill", "event": "vendorbill.created"}, {"name": "PO Approved", "event": "purchaseorder.approved"}], "auth_type": "token", "workato_config": {"connection_type": "cloud", "recipe_template": "netsuite_procurement_sync"}}	[]	t	f	2026-02-16 23:27:19.647434	2026-02-16 23:27:19.647434	system	{"source": "workato"}
workato-slack	Slack Notifications (via Workato)	Send procurement notifications, approval requests, and alerts to Slack channels.	workato	collaboration	active	["slack", "notification", "collaboration", "approval"]	{"icon": "slack", "actions": [{"name": "Send Message", "path": "/slack/message", "method": "POST"}, {"name": "Send Approval Request", "path": "/slack/approval", "method": "POST"}, {"name": "Update Message", "path": "/slack/message/{ts}", "method": "PATCH"}, {"name": "Upload File", "path": "/slack/file", "method": "POST"}], "triggers": [{"name": "Message Received", "event": "message.received"}, {"name": "Approval Response", "event": "approval.responded"}], "auth_type": "oauth2", "workato_config": {"connection_type": "cloud", "recipe_template": "slack_procurement_alerts"}}	[]	t	f	2026-02-16 23:27:19.647434	2026-02-16 23:27:19.647434	system	{"source": "workato"}
workato-teams	Microsoft Teams (via Workato)	Send procurement notifications and approval requests to Microsoft Teams channels.	workato	collaboration	active	["teams", "microsoft", "notification", "collaboration"]	{"icon": "teams", "actions": [{"name": "Send Message", "path": "/teams/message", "method": "POST"}, {"name": "Create Adaptive Card", "path": "/teams/card", "method": "POST"}, {"name": "Send Approval", "path": "/teams/approval", "method": "POST"}], "triggers": [{"name": "Message Received", "event": "message.received"}, {"name": "Approval Completed", "event": "approval.completed"}], "auth_type": "oauth2", "workato_config": {"connection_type": "cloud", "recipe_template": "teams_procurement_alerts"}}	[]	t	f	2026-02-16 23:27:19.647434	2026-02-16 23:27:19.647434	system	{"source": "workato"}
workato-jira	Jira (via Workato)	Create and track procurement-related issues, tasks, and projects in Jira.	workato	project-management	active	["jira", "project-management", "task", "issue"]	{"icon": "jira", "actions": [{"name": "Create Issue", "path": "/jira/issue", "method": "POST"}, {"name": "Update Issue", "path": "/jira/issue/{id}", "method": "PATCH"}, {"name": "Get Issue", "path": "/jira/issue/{id}", "method": "GET"}, {"name": "Add Comment", "path": "/jira/issue/{id}/comment", "method": "POST"}, {"name": "Transition Issue", "path": "/jira/issue/{id}/transition", "method": "POST"}], "triggers": [{"name": "Issue Created", "event": "issue.created"}, {"name": "Issue Updated", "event": "issue.updated"}, {"name": "Issue Transitioned", "event": "issue.transitioned"}], "auth_type": "oauth2", "workato_config": {"connection_type": "cloud", "recipe_template": "jira_procurement_tasks"}}	[]	t	f	2026-02-16 23:27:19.647435	2026-02-16 23:27:19.647435	system	{"source": "workato"}
workato-docusign	DocuSign (via Workato)	Send contracts and procurement documents for electronic signature via DocuSign.	workato	document-management	active	["docusign", "e-signature", "contract", "document"]	{"icon": "docusign", "actions": [{"name": "Send Envelope", "path": "/docusign/envelope", "method": "POST"}, {"name": "Get Envelope Status", "path": "/docusign/envelope/{id}", "method": "GET"}, {"name": "Download Document", "path": "/docusign/envelope/{id}/document", "method": "GET"}, {"name": "Void Envelope", "path": "/docusign/envelope/{id}/void", "method": "POST"}], "triggers": [{"name": "Envelope Completed", "event": "envelope.completed"}, {"name": "Envelope Declined", "event": "envelope.declined"}, {"name": "Envelope Sent", "event": "envelope.sent"}], "auth_type": "oauth2", "workato_config": {"connection_type": "cloud", "recipe_template": "docusign_contract_signing"}}	[]	t	f	2026-02-16 23:27:19.647435	2026-02-16 23:27:19.647435	system	{"source": "workato"}
workato-sharepoint	SharePoint (via Workato)	Store and retrieve procurement documents, contracts, and compliance files in SharePoint.	workato	document-management	active	["sharepoint", "document", "storage", "microsoft"]	{"icon": "sharepoint", "actions": [{"name": "Upload File", "path": "/sharepoint/file", "method": "POST"}, {"name": "Get File", "path": "/sharepoint/file/{id}", "method": "GET"}, {"name": "List Files", "path": "/sharepoint/files", "method": "GET"}, {"name": "Create Folder", "path": "/sharepoint/folder", "method": "POST"}], "triggers": [{"name": "File Uploaded", "event": "file.uploaded"}, {"name": "File Modified", "event": "file.modified"}], "auth_type": "oauth2", "workato_config": {"connection_type": "cloud", "recipe_template": "sharepoint_document_sync"}}	[]	t	f	2026-02-16 23:27:19.647435	2026-02-16 23:27:19.647435	system	{"source": "workato"}
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, username, email, password_hash, first_name, last_name, display_name, avatar_url, tenant_id, roles, is_active, preferences, created_at, last_login, metadata_json) FROM stdin;
admin-001	admin	admin@jaggaer.com	773d8104e66981ef0f1c852c00e0e489a7c96ad37565c55b887c2aa312d60309	Platform	Admin	Platform Admin		default	["platform_admin"]	t	{}	2026-02-16 23:27:19.639715	\N	{}
user-7611365d	amediratta@jaggaer.com	amediratta@jaggaer.com	665d3a3bd96b744c48fad8fb9e6a15de92cd7311d052df2ac555cd6f6fed780b	Aayush	Mediratta	Aayush Mediratta		default	["platform_admin"]	t	{}	2026-02-16 23:32:54.386892	\N	{}
\.


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: guardrail_rules guardrail_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.guardrail_rules
    ADD CONSTRAINT guardrail_rules_pkey PRIMARY KEY (id);


--
-- Name: integrations integrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_pkey PRIMARY KEY (id);


--
-- Name: prompt_templates prompt_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_pkey PRIMARY KEY (id);


--
-- Name: provider_credentials provider_credentials_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_credentials
    ADD CONSTRAINT provider_credentials_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_slug_key UNIQUE (slug);


--
-- Name: tools tools_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tools
    ADD CONSTRAINT tools_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: ix_agents_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_created_by ON public.agents USING btree (created_by);


--
-- Name: ix_agents_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_name ON public.agents USING btree (name);


--
-- Name: ix_agents_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_status ON public.agents USING btree (status);


--
-- Name: ix_agents_status_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agents_status_updated ON public.agents USING btree (status, updated_at);


--
-- Name: ix_guardrail_rules_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_guardrail_rules_name ON public.guardrail_rules USING btree (name);


--
-- Name: ix_guardrail_rules_rule_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_guardrail_rules_rule_type ON public.guardrail_rules USING btree (rule_type);


--
-- Name: ix_integrations_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integrations_provider ON public.integrations USING btree (provider);


--
-- Name: ix_prompt_templates_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_prompt_templates_name ON public.prompt_templates USING btree (name);


--
-- Name: ix_provider_credentials_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_credentials_provider ON public.provider_credentials USING btree (provider);


--
-- Name: ix_tools_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tools_name ON public.tools USING btree (name);


--
-- Name: ix_tools_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tools_status ON public.tools USING btree (status);


--
-- Name: agents agents_credential_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_credential_id_fkey FOREIGN KEY (credential_id) REFERENCES public.provider_credentials(id);


--
-- PostgreSQL database dump complete
--

\unrestrict RBysU0OB7YSezbXARmsNGTuN4LHHChxy9KyVGabzpOaE5o5HbUKqi3d9B38Xbmv

