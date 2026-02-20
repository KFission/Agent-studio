# Agent Studio Platform

**Low-Code / No-Code Agent Builder on LangGraph + LangChain OAP**

Enterprise-grade platform for visually composing, testing, deploying, and monitoring agentic AI workflows. Built for JAGGAER Direct Sourcing with multi-provider LLM support.

---

## API Documentation

| Resource | URL |
|----------|-----|
| **Swagger UI** | [http://localhost:8080/docs](http://localhost:8080/docs) |
| **ReDoc** | [http://localhost:8080/redoc](http://localhost:8080/redoc) |
| **OpenAPI JSON** | [http://localhost:8080/openapi.json](http://localhost:8080/openapi.json) |
| **API Reference** | [docs/API_REFERENCE.md](API_REFERENCE.md) |

> Click the **Help** button (top-right corner of Agent Studio) to open Swagger in a new tab.

All 200+ API endpoints are organized into 25 tag groups with full request/response schemas.

---

## Architecture (6 Layers)

| Layer | Component | Technology |
|-------|-----------|------------|
| **L1 — Presentation** | Agent Studio Canvas | React 19, Next.js 15, ReactFlow, Zustand, TailwindCSS, Lucide React |
| **L2 — API Gateway** | Studio API + Serving Gateway | FastAPI, WebSockets, Webhooks |
| **L3 — Orchestration** | Graph Compiler + LangGraph Runtime | LangGraph, Custom Compiler |
| **L4 — Services** | LLM Registry, Prompt Studio, Eval Studio | Multi-provider LLM, Channels |
| **L5 — State & Data** | Persistence Layer | Redis, PostgreSQL, Snowflake |
| **L6 — Observability** | Monitoring + Analytics | Langfuse (self-hosted), HTTP-native tracing, Cost Attribution |

---

## Features

### Dashboard (Default Landing)
- **KPI summary cards:** Total agents, pending approvals, LLM calls today, total cost
- **Pending approvals panel:** Latest HITL inbox items with direct link to Inbox
- **Recent LLM calls panel:** Latest gateway requests with model, tokens, latency, cost
- **Quick actions:** One-click navigation to New Agent, Open Chat, Run Eval, Manage Groups
- **Cost & Usage Metering widget:** Donut chart (cost breakdown by LoB/Group/Agent/Model/User), area chart (daily cost trend), horizontal bar breakdown, summary KPIs — all with dimension and period filters

### Grouped Sidebar Navigation
- **4 collapsible sections:** Build (Agents, Workflows, Orchestrator, Tools, RAG, Prompts), Run & Test (Chat, Inbox, Eval Studio), Operate (Models, Gateway, LLM Logs, Connectors), Admin (Groups, LLM Integrations, Users, Settings)
- **Inbox notification badge:** Amber count of pending HITL approvals
- **Collapsible:** Sidebar collapses to icon-only mode (56px)
- **Lucide React icons** throughout

### Agent-Centric Navigation
- **Agent detail view:** Click any agent card to see config, stats (runs, latency, cost), system prompt
- **Contextual actions:** Chat (pre-scoped to agent), Edit, Deploy buttons from detail view
- **Back navigation:** Return to agent list

### LLM Model Library
- **15+ built-in models** across 4 providers
- **Google Gemini**: 2.0 Flash, 2.5 Flash, 2.5 Pro (via Vertex AI / ADC)
- **Anthropic Claude**: Haiku 3.5, Sonnet 4, Opus 4
- **OpenAI**: GPT-4o, GPT-4o Mini, o3-mini
- **Ollama (Local)**: Gemma 2 (9B/27B), Kimi K2, Llama 3.1, Qwen 3
- Token-based pricing, cost comparison, model capability tagging
- Register custom models at runtime via API

### Prompt Studio (with Versioning & AI Improvement)
- Template CRUD with `{{variable}}` injection
- **Full version history sidebar:** View all versions with version number, change note, author, date, content hash
- **View any version:** Click to view content; "(not current)" indicator for old versions
- **Restore old versions:** Opens editor pre-filled with version content and auto-change-note
- **AI-Powered Improvement:** "Improve with AI" button sends prompt to LLM meta-prompt that preserves variables, adds output format instructions, chain-of-thought guidance; accepts optional optimization goal
- **Live variables preview:** `{{variable}}` placeholders extracted and displayed as badges during editing
- **Edit mode:** Full-screen monospace editor with change note field; saving creates a new immutable version
- Built-in templates: Intent Classifier, Entity Extractor, Agent Reasoning, Result Summarizer
- Category-based organization (agent, classifier, extractor, summarizer, validator)
- Search and filter across template library

### Evaluation Studio
- **SSE streaming**: Models run concurrently on backend; results stream to UI as each completes
- **Dynamic model list**: Model selector and pricing built from `/models` API (no hardcoded list)
- **Multi-model comparison**: side-by-side eval across any combination of models
- **Quality scoring**: ROUGE-L, BLEU, exact match, keyword overlap, LLM judge with per-criterion scores
- **Metric descriptions**: Plain-English explanations shown inline (not hidden in tooltips)
- **Langfuse tracing**: All eval calls create Langfuse traces with per-model generation logs
- **Side-by-side comparison table:** Status, Latency, Tokens, Cost, Output; "Fastest" and "Cheapest" badges
- Token estimation and cost calculator across all models
- Run history with fastest/cheapest model identification

### Channel Connectors
- **Webhooks**: Inbound (trigger agents) + Outbound (deliver results), HMAC-SHA256 signatures, retry logic
- **WebSockets**: Real-time streaming for LLM tokens, run progress, HITL approvals
- **Jaggaer SaaS REST API**: Standardized LLM call interface with auto model routing, rate limiting, usage metering

### LangSmith Observability
- Browse recent runs (filter by type, errors)
- Drill into run details with child steps
- View/create feedback on runs

### Monitoring (Langfuse-Powered Observability)
- **All LLM calls traced** — Chat, Playground, Eval Studio, and Gateway calls automatically appear in Langfuse
- **LLM Traces:** Full input/output, tokens, latency, and cost for every call
- **LLM Generations:** Detailed input/output pairs per model call
- **Detail panel:** Preview, Scores, Metadata, and **JSON** tabs per trace/observation
- **JSON tab:** Full raw trace data with "Copy JSON" button
- **Stats for root trace:** Tokens, latency, cost shown for both root trace (aggregated) and observations
- **Beautified preview:** Formatted response display (handles raw dict/JSON)
- **User identity:** Traces tagged with actual logged-in user (e.g. "Platform Admin")
- **Evaluations & Scores:** Submit numeric scores to any trace via `POST /monitoring/scores`
- **Cost & Token Analytics:** KPI cards with total traces, tokens, cost, error counts
- **Session Tracking:** Group traces into multi-turn conversations
- Aggregated stats: success rate, latency percentiles, token usage, cost

### Chat UX
- **Persistent thread list:** Left panel with thread history, "New Thread" button
- **Rich agent picker:** Popover showing agent name, description, RAG/Tools badges (not a plain dropdown)
- **Suggested prompts:** Domain-specific prompt chips on empty state
- **Configuration sidebar:** Toggle right panel for model, system prompt, temperature, RAG, memory

### HITL Inbox
- **SLA countdown:** Live timer per item (configurable SLA hours); turns red and pulses when <1 hour; "Overdue" when breached
- **Group by agent:** Items grouped under collapsible agent headers with counts
- **Priority filtering:** Filter by all/pending/approved/rejected
- **Approve/Reject/Edit & Approve** action buttons per item

### Groups (LoB/Teams)
- **Create groups** by Line of Business (e.g., Procurement, Sourcing, Finance)
- **Assign members:** Add/remove users from groups
- **Push models to groups:** Admin assigns models; devs use them without needing API keys
- **Assign agents to groups:** Control which teams can access which agents
- **Assign roles to groups:** Members inherit group-level roles (platform_admin, agent_developer, agent_operator, viewer)
- **Monthly budget cap:** Optional per-group spending limit for chargeback
- **Detail view:** 4-panel layout with Members, Roles, Allowed Models, Allowed Agents

### LLM Integrations (replaces Multi-Tenancy)
- **Admin-managed provider credentials:** Create integrations for OpenAI, Anthropic, Google, Ollama, Azure OpenAI, AWS Bedrock
- **API key abstraction:** Admin stores API keys; developers never see them
- **Push to groups:** Assign integrations to groups so members get instant access
- **Per-integration config:** Default model, endpoint URL, GCP project ID, rate limits
- **Test connectivity:** One-click test button per integration
- **Status tracking:** Active / Inactive / Error states with last-tested timestamp

### Usage Metering & Cost Attribution
- **Dashboard widget:** Cost & Usage Metering panel with SVG donut chart and area chart
- **Donut chart:** Cost breakdown by selected dimension (LoB/Group/Agent/Model/User) with color-coded legend
- **Area chart:** Daily cost trend with gradient fill and hover tooltips
- **Horizontal bars:** Color-coded breakdown with cost, request count, and token count
- **Summary KPIs:** Total requests, tokens, cost, avg latency, success rate
- **Filters:** Dimension selector + period (7/30/90 days)
- **Chargeback ready:** Per-LoB and per-group cost attribution for finance reporting

### Workflow Builder (ReactFlow) — v2
- **Visual workflow canvas** powered by @xyflow/react (ReactFlow v12)
- **24 custom node types** across **7 categories**, driven by a data-driven Node Registry (`nodeRegistry.js`):
  - **Triggers (4):** Webhook, Schedule (Cron), Manual, Start Input
  - **Control Flow (5):** Condition (IF), Switch, Loop, Delay/Timer, Error Handler
  - **Data & Transformation (3):** HTTP Request, Code (JS/Python), Data Transform
  - **Integrations (3):** Jaggaer API, Snowflake Query, Generic Connector
  - **AI (4):** Run Agent, LLM Call, RAG Lookup, Guardrail Check
  - **Human & Tickets (3):** Human Approval, Notification, Create Ticket
  - **Output & Observability (2):** Workflow Output, Log / Trace
- **Node Library sidebar:** Searchable, collapsible categories with node count badges
- **Universal node renderer:** Single data-driven component renders all 24 types with typed input/output handles, validation badges, and execution status
- **Schema-driven property panel** (`NodePropertyPanel.jsx`): 12 field renderers (text, number, range, boolean, enum, textarea, code, JSON, tags, key-value, datetime, retry policy), conditional field visibility, advanced accordion, validation errors/warnings
- **Connection validation:** Registry-driven rules prevent invalid connections (e.g., can't connect to a trigger's input, can't connect from a terminal's output)
- **Example workflow templates:** RAG Q&A, Approval Chain, Integration Pipeline — load pre-built workflows from the empty canvas
- **Execution simulation:** Topological-sort runner with per-node queued → running → success/error states, animated edge flow, mock output data from registry
- **Smooth animated edges** with arrow markers and smart routing
- **MiniMap & Controls:** Zoom, pan, fit-to-view, minimap with color-coded node types
- **Save/Load:** Persists workflow as orchestration pipeline with ReactFlow node/edge data in metadata
- **Workflow list:** Grid/list view of saved workflows with node count, version, environment badge

### Authentication
- **Microsoft SSO simulation:** "Sign in with Microsoft" button (simulated, auto-logs in as admin@jaggaer.com)
- **Email + password flow:** Two-step authentication (enter email → enter password, accepts any combo for dev)
- **Auth store:** Zustand-based auth state with login, loginWithSSO, and logout actions
- **Protected routes:** Main app gated behind authentication; shows LoginPage when not authenticated

### Environment Management
- **3 environments:** Development, UAT, Production with color-coded badges
- **Environment switcher:** Global dropdown in the top header for switching environments
- **Permission model:** Dev = full edit, UAT = read-only, Prod = read-only with confirmation dialogs
- **Environment badges:** Displayed on agent cards, workflow cards, pipeline cards, KB items
- **Version metadata:** Per-environment version, last updated, updated by info
- **Safety guardrails:** Production edit confirmation dialog, UAT/Prod warning banners, unsaved changes dialog

---

## Quick Start

### Backend

```bash
cd agent_studio
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

# Start the API server
python -m backend.api.server
# or
uvicorn backend.api.server:app --reload --port 8080
```

### Frontend

```bash
cd agent_studio/frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## API Reference

### Health & Info
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Platform health check |
| GET | `/info` | Platform info with module counts |

### LLM Model Library
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/models` | List all models (filter by provider, capability, local) |
| GET | `/models/{id}` | Get model details |
| POST | `/models` | Register custom model |
| DELETE | `/models/{id}` | Remove model |
| POST | `/models/{id}/test` | Test model connectivity |
| GET | `/models/compare/cost` | Compare costs across models |
| GET | `/providers` | List provider status |

### Prompt Studio
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/prompts` | List templates (filter by category) |
| GET | `/prompts/{id}` | Get template with full version history |
| POST | `/prompts` | Create template (initial version) |
| PUT | `/prompts/{id}` | Add new version (with change note) |
| DELETE | `/prompts/{id}` | Delete template |
| POST | `/prompts/render` | Render template with variables |
| GET | `/prompts/{id}/variables` | List template variables |
| GET | `/prompts/search/{query}` | Search templates |
| POST | `/prompts/improve` | **AI-powered prompt improvement** (sends to LLM with meta-prompt, preserves variables) |

### Evaluation Studio
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/eval/estimate-tokens` | Estimate tokens and cost |
| POST | `/eval/single` | Evaluate prompt on one model (traced to Langfuse) |
| POST | `/eval/multi` | Compare prompt across models (traced to Langfuse) |
| POST | `/eval/stream` | **SSE streaming** — concurrent eval with real-time results |
| GET | `/eval/runs` | List evaluation runs |
| GET | `/eval/runs/{id}` | Get comparison table |

### Channels
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/webhooks` | List webhooks |
| POST | `/webhooks` | Create webhook |
| DELETE | `/webhooks/{id}` | Delete webhook |
| POST | `/webhooks/inbound/{id}` | Receive inbound webhook |
| GET | `/webhooks/{id}/events` | Get webhook event history |
| WS | `/ws/{client_id}` | WebSocket connection |
| GET | `/ws/stats` | WebSocket stats |

### Jaggaer SaaS LLM API
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/jaggaer/llm/invoke` | Make LLM call from Jaggaer SaaS |
| GET | `/jaggaer/usage` | Get usage records |
| GET | `/jaggaer/usage/summary` | Aggregated usage with cost breakdown |

### LangSmith Observability
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/langsmith/status` | LangSmith project info |
| GET | `/langsmith/runs` | List recent runs |
| GET | `/langsmith/runs/{id}` | Run detail with child steps |
| GET | `/langsmith/stats` | Aggregated run statistics |
| POST | `/langsmith/feedback` | Create feedback on a run |

### Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/monitoring/status` | Observability backend connection status |
| GET | `/monitoring/traces` | List recent LLM call traces |
| GET | `/monitoring/generations` | List LLM generations (input/output pairs) |
| GET | `/monitoring/scores` | List evaluation scores |
| GET | `/monitoring/sessions` | List conversation sessions |
| POST | `/monitoring/scores` | Submit evaluation score for a trace |

### Graph Compiler & Registry (Layer 3)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/graphs` | List all graphs (filter by status) |
| POST | `/graphs` | Create new graph manifest |
| GET | `/graphs/{id}` | Get graph manifest |
| PUT | `/graphs/{id}` | Update graph (creates new version) |
| DELETE | `/graphs/{id}` | Delete graph |
| GET | `/graphs/{id}/versions` | List all versions |
| GET | `/graphs/{id}/versions/{v}` | Get specific version |
| POST | `/graphs/{id}/rollback/{v}` | Rollback to version |
| POST | `/graphs/{id}/status/{s}` | Transition lifecycle (draft→published→deployed→deprecated→archived) |
| POST | `/graphs/{id}/validate` | Validate manifest for errors |
| POST | `/graphs/{id}/compile` | Compile to executable LangGraph StateGraph |
| POST | `/graphs/{id}/run` | Execute compiled graph with initial state |
| GET | `/graphs/compiled/list` | List compiled graphs ready for execution |
| GET | `/graphs/{id}/export` | Export manifest as JSON |
| POST | `/graphs/import` | Import manifest from JSON |
| GET | `/graphs/stats` | Registry statistics |
| GET | `/graphs/search/{query}` | Search graphs |

### Templates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/templates` | List reusable graph templates |
| POST | `/templates/{id}` | Save graph as template |
| POST | `/templates/{id}/create` | Create new graph from template |

### Groups (LoB/Teams)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/groups` | List all groups (filter by LoB) |
| GET | `/groups/stats` | Group statistics |
| GET | `/groups/{id}` | Get group details |
| POST | `/groups` | Create group (name, LoB, budget) |
| PUT | `/groups/{id}` | Update group |
| DELETE | `/groups/{id}` | Delete group |
| GET | `/groups/{id}/members` | List group members |
| POST | `/groups/{id}/members` | Add member to group |
| DELETE | `/groups/{id}/members/{uid}` | Remove member |
| GET | `/groups/{id}/models` | List models pushed to group |
| POST | `/groups/{id}/models` | Push models to group |
| DELETE | `/groups/{id}/models` | Revoke models from group |
| POST | `/groups/{id}/agents` | Assign agents to group |
| DELETE | `/groups/{id}/agents` | Revoke agents from group |
| POST | `/groups/{id}/roles` | Assign roles to group |
| GET | `/users/{uid}/allowed-models` | Models user can access via groups |
| GET | `/users/{uid}/groups` | User's group memberships |

### Usage Metering
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/metering/summary` | Aggregated summary (filter by group/LoB/agent/period) |
| GET | `/metering/by-group` | Cost breakdown by group |
| GET | `/metering/by-lob` | Cost breakdown by Line of Business |
| GET | `/metering/by-agent` | Cost breakdown by agent |
| GET | `/metering/by-model` | Cost breakdown by model |
| GET | `/metering/by-user` | Cost breakdown by user |
| GET | `/metering/trend` | Daily cost trend |

### LLM Integrations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/integrations` | List all integrations (filter by provider) |
| GET | `/integrations/stats` | Integration statistics |
| GET | `/integrations/{id}` | Get integration details (API key masked) |
| POST | `/integrations` | Create integration (provider + API key + config) |
| PUT | `/integrations/{id}` | Update integration |
| DELETE | `/integrations/{id}` | Delete integration |
| POST | `/integrations/{id}/push` | Push integration to groups |
| POST | `/integrations/{id}/revoke` | Revoke integration from groups |
| GET | `/integrations/by-group/{gid}` | List integrations available to a group |
| POST | `/integrations/{id}/test` | Test integration connectivity |

---

## Configuration

All settings are managed via environment variables (`.env` file). See `.env.example` for the complete list.

### Required
- **GCP_PROJECT_ID** — for Gemini models via Vertex AI
- At least one LLM provider API key (or Ollama running locally)

### Optional
- **ANTHROPIC_API_KEY** — for Claude models
- **OPENAI_API_KEY** — for GPT models
- **OLLAMA_BASE_URL** — for local models (default: `http://localhost:11434`)
- **LANGCHAIN_API_KEY** — for LangSmith observability
- **LANGFUSE_HOST** — Monitoring backend URL (default: `http://localhost:3030`)
- **LANGFUSE_PUBLIC_KEY** — Monitoring backend public key
- **LANGFUSE_SECRET_KEY** — Monitoring backend secret key
- **JAGGAER_API_KEY** — for Jaggaer SaaS integration

---

## Project Structure

```
agent_studio/
├── backend/
│   ├── api/
│   │   ├── server.py              # FastAPI server (main routes + wiring)
│   │   ├── routes_v2.py           # Auth, Users, Agents, Orchestrator, Tools, RAG
│   │   ├── routes_v3.py           # Tenancy, Gateway, LLM Logs, Threads, Inbox
│   │   └── routes_v4.py           # Groups, Usage Metering, LLM Integrations
│   ├── auth/
│   │   ├── keycloak_provider.py   # Keycloak SSO integration
│   │   ├── rbac.py                # Role-based access control (4 built-in roles)
│   │   ├── user_manager.py        # User profiles, API keys, preferences
│   │   └── group_manager.py       # Group/LoB CRUD, model/agent/role assignment
│   ├── integrations/
│   │   └── llm_integration_manager.py  # Admin LLM provider integrations, push to groups
│   ├── metering/
│   │   └── usage_metering.py      # Cost tracking per group/LoB/agent/model/time
│   ├── config/
│   │   └── settings.py            # Pydantic settings from .env
│   ├── llm_registry/
│   │   ├── model_library.py       # 15+ model definitions, pricing, capabilities
│   │   └── provider_factory.py    # Unified LLM creation across all providers
│   ├── compiler/
│   │   ├── manifest.py            # Graph Manifest schema (12 node types, edges, state)
│   │   ├── compiler.py            # Compile visual JSON → LangGraph StateGraph
│   │   └── registry.py            # Graph CRUD, versioning, lifecycle, templates
│   ├── prompt_studio/
│   │   └── prompt_manager.py      # Template CRUD, versioning, rendering, AI improve
│   ├── eval_studio/
│   │   └── evaluator.py           # Token estimation, cost calc, model comparison
│   ├── channels/
│   │   ├── webhook_handler.py     # Inbound/outbound webhooks with HMAC
│   │   ├── websocket_manager.py   # Real-time streaming and pub/sub
│   │   └── jaggaer_channel.py     # Jaggaer SaaS LLM API with rate limiting
│   └── observability/
│       ├── langsmith_viewer.py    # LangSmith trace/run/feedback viewer
│       └── langfuse_integration.py # Native monitoring: tracing, evals, cost analytics
├── frontend/
│   ├── app/
│   │   ├── layout.jsx             # Next.js root layout
│   │   ├── page.jsx               # Main page
│   │   └── globals.css            # Tailwind + custom styles
│   ├── components/
│   │   ├── AgentStudio.jsx        # Full app shell: Dashboard, Sidebar, 18 pages (Tailwind CSS)
│   │   ├── WorkflowBuilder.jsx    # Visual workflow builder (ReactFlow canvas, 24 node types, Node Library)
│   │   ├── NodePropertyPanel.jsx  # Schema-driven property panel (12 field renderers, validation)
│   │   ├── PipelineBuilder.jsx    # Pipeline builder (Sequential/Parallel/Supervisor patterns)
│   │   ├── LoginPage.jsx          # MS SSO-styled login page with email+password flow
│   │   ├── EnvironmentSwitcher.jsx # Env badges, version meta, warning banners, switcher
│   │   ├── KnowledgeBasesPage.jsx # Knowledge base management
│   │   ├── ToolsPage.jsx          # Tool management
│   │   ├── NotificationChannelsPage.jsx
│   │   └── ExecutiveDashboard.jsx # Executive dashboard
│   ├── stores/
│   │   ├── nodeRegistry.js        # 24 workflow node types, schemas, defaults, validation, handles
│   │   ├── envStore.js            # Environment state, permissions, switching logic
│   │   └── authStore.js           # Auth state with login/logout actions
│   ├── lib/
│   │   └── cn.js                  # clsx + tailwind-merge utility
│   ├── package.json               # React 18, ReactFlow, Zustand, D3, Tailwind
│   ├── next.config.js             # API proxy to backend
│   ├── tailwind.config.js
│   └── postcss.config.js
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
└── README.md
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Next.js 15, ReactFlow, Zustand, TailwindCSS, Lucide React, clsx + tailwind-merge |
| API | FastAPI, WebSockets, SSE Streaming |
| LLM Providers | Google Gemini, Anthropic Claude, OpenAI GPT, Ollama (local) |
| Agent Runtime | LangGraph, LangChain |
| Observability | Langfuse (self-hosted), HTTP-native tracing |
| State | Redis 7, PostgreSQL 16 |
| Testing | Jest (frontend, 143 tests), pytest (backend, 175 tests) |
