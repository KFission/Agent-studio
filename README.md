# JAI Agent OS

**Enterprise Agentic AI Platform — Low-Code Agent Builder on LangGraph + LangChain**

Build, test, deploy, and monitor agentic AI workflows with full Langfuse observability. Built for JAGGAER with multi-provider LLM support.

---

## Quick Start (Automated)

```bash
git clone <repo-url> && cd jai-agentos
chmod +x setup.sh
./setup.sh
```

The setup script handles everything automatically:
- Checks prerequisites (Docker, Docker Compose)
- Generates `.env` with secrets and encryption keys
- Builds and starts all services (backend, frontend, Langfuse, Guardrails, Postgres, Redis)
- Auto-provisions Langfuse project and API keys (no manual UI setup)
- Seeds the admin user and default data

### Access

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend UI** | http://localhost:3000 | `admin@jaggaer.com` / `admin123` |
| **Backend API** | http://localhost:8080 | — |
| **API Docs** | http://localhost:8080/docs | — |
| **Langfuse UI** | http://localhost:3030 | `admin@jaggaer.com` / `admin123` |

### Adding LLM Provider Keys

After setup, edit `.env` and add your API keys, then restart the backend:

```bash
# Edit .env — add at least one provider key:
#   GOOGLE_API_KEY=your-gemini-key
#   ANTHROPIC_API_KEY=your-anthropic-key
#   OPENAI_API_KEY=your-openai-key

docker compose up -d backend
```

---

## Features

### Prompt Management (Langfuse-backed)
- Full prompt versioning with `#version` numbering and labels (`latest`, `production`, `experiment-*`)
- Chat (System/Assistant/User messages) and text prompt types
- Tabs: **Prompt** | **Config** | **Linked Generations** | **Use Prompt** (code snippets)
- Promote versions to production with one click
- Variables with `{{variable}}` syntax, auto-detected

### LLM Playground (Multi-Window)
- Side-by-side testing with up to 3 windows (different models per window)
- Message editor with System/User/Assistant roles, drag handles, `+ Message` / `+ Placeholder`
- **Run All** (Ctrl+Enter) executes all windows simultaneously
- Load prompts directly from Prompt Management
- **Playground button** on prompt detail navigates and pre-loads the prompt
- Output with token breakdown, latency, and Langfuse trace ID

### Eval Studio (Side-by-Side Model Comparison)
- **SSE streaming** — Models run concurrently; results stream to UI as each completes
- **Dynamic model list** — Model selector and pricing built from `/models` API
- Multi-model comparison with tokens, latency, cost, and tokens/second
- Quality scoring: ROUGE-L, BLEU, exact match, keyword overlap, LLM judge
- **Metric descriptions** — Plain-English explanations shown inline
- All eval calls automatically traced to Langfuse with per-model generation logs

### Experiments (Langfuse Datasets)
- Create datasets with test cases (input variables + expected outputs)
- Run experiments: execute a prompt version against all dataset items
- Per-item results with output, expected output, latency, token counts
- All experiment traces linked to Langfuse datasets for analysis

### Monitoring (Langfuse-style Observability)
- **All LLM calls traced** — Chat, Playground, Eval Studio, and Gateway calls automatically appear in Langfuse
- Nested timeline tree view for trace details (spans, generations)
- Detail panel with **Preview**, **Scores**, **Metadata**, and **JSON** tabs
- JSON tab shows full raw trace/observation data with "Copy JSON" button
- **Tokens, latency, cost** displayed for both root trace (aggregated) and individual observations
- Beautified response preview (handles raw dict/JSON formatting)
- Sessions, Users, Dashboard (model breakdown, daily volume), Scores views
- KPI cards: total traces, latency, token usage, cost
- **User identity tracking** — traces tagged with the actual logged-in user (e.g. "Platform Admin")

### Agent Builder
- Visual drag-and-drop workflow builder with LangGraph
- Multi-step pipeline orchestration
- Tool registry with API bindings
- Knowledge bases (RAG) with document collections
- Guardrails (content filters, safety rules)

### Gateway (OpenAI-Compatible)
- `POST /v1/chat/completions` — drop-in replacement for OpenAI API
- Multi-tenant rate limiting and routing
- Automatic Langfuse tracing on every request

---

## Architecture

| Layer | Component | Technology |
|-------|-----------|------------|
| **L1 — Presentation** | Agent Studio UI | React 19, Next.js 15, TailwindCSS, Lucide React, Zustand |
| **L2 — API Gateway** | Studio API + LLM Gateway | FastAPI, WebSockets, SSE Streaming |
| **L3 — Orchestration** | Graph Compiler + Runtime | LangGraph, LangChain |
| **L4 — Services** | LLM Registry, Prompt Studio, Eval Studio | Multi-provider LLM (Google, Anthropic, OpenAI, Ollama) |
| **L5 — State & Data** | Persistence | PostgreSQL 16, Redis 7 |
| **L6 — Observability** | Monitoring + Tracing | Langfuse (self-hosted), HTTP-native tracing |

---

## Services (Docker Compose)

| Container | Image | Port | Description |
|-----------|-------|------|-------------|
| `jai-backend` | Custom (FastAPI) | 8080 | API server, LLM gateway, prompt management |
| `jai-frontend` | Custom (Next.js) | — | Agent Studio UI |
| `jai-nginx` | nginx:alpine | 3000 | Reverse proxy |
| `jai-langfuse` | langfuse/langfuse:2 | 3030 | Observability platform |
| `jai-postgres` | postgres:16-alpine | 5433 | Shared DB (Langfuse + Agent Studio + Guardrails) |
| `jai-redis` | redis:7-alpine | 6379 | Cache, checkpoints, queues |
| `jai-guardrails` | Custom | 8000 | Guardrails AI server |

---

## Project Structure

```
jai-agentos/
├── setup.sh                    # Automated setup script
├── docker-compose.yml          # Full stack definition
├── .env                        # Environment configuration
├── backend/
│   ├── api/
│   │   ├── server.py           # FastAPI app, all endpoints
│   │   ├── routes_v2.py        # Auth, users, agents, tools
│   │   ├── routes_v3.py        # Gateway (OpenAI-compatible)
│   │   └── routes_v4.py        # Integrations, models
│   ├── prompt_studio/
│   │   ├── langfuse_prompt_manager.py  # Langfuse-backed prompts
│   │   └── experiment_manager.py       # Datasets + experiment runner
│   ├── observability/
│   │   └── langfuse_integration.py     # Langfuse HTTP client
│   ├── gateway/
│   │   └── aaas_gateway.py     # LLM gateway with tracing
│   ├── llm_registry/           # Provider factory, model library
│   ├── auth/                   # User manager, RBAC, Keycloak
│   ├── db/                     # SQLAlchemy models, migrations, seeding
│   └── config/                 # Settings (env-based)
├── frontend/
│   ├── components/
│   │   ├── AgentStudio.jsx     # Main app shell, navigation
│   │   ├── PromptsPage.jsx     # Langfuse-style prompt management
│   │   ├── PlaygroundPage.jsx  # Multi-window LLM playground
│   │   └── MonitoringPage.jsx  # Langfuse-style observability UI
│   ├── stores/                 # Zustand stores
│   └── lib/                    # Utilities (apiFetch, etc.)
├── scripts/
│   └── init-db.sh              # Postgres init (creates DBs)
└── docs/                       # Roadmap, plans, tech debt
```

---

## Useful Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild after code changes
docker compose build backend frontend
docker compose up -d backend frontend

# Stop everything
docker compose down

# Full reset (wipe data)
docker compose down
rm -rf .local/
./setup.sh

# Run frontend tests (143 tests)
cd frontend && npx jest --verbose

# Run backend tests (175 tests)
python3 -m pytest tests/ -v --tb=short
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [JAGGAER Roadmap](docs/JAGGAER_ROADMAP.md) | 3-Month release plan for June 2026 release |
| [Tech Debt](docs/techdebt.md) | Architectural gaps and refactoring needs |
| [Full README](docs/README.md) | Detailed architecture and API reference |
| [Roadmap](docs/ROADMAP.md) | MVP1 scope and phased delivery |
| [Plan](docs/PLAN.md) | Feature audit vs OAP, priorities |
