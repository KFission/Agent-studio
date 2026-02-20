# JAI Agent OS — Master TODO & Go-Live Checklist

> **Consolidated from:** `todo.md`, `docs/todo.md`, `docs/todocodex.md`, `docs/todogemini.md`, `docs/PLAN.md`, `docs/ROADMAP.md`, `docs/JAGGAER_ROADMAP.md`, `docs/techdebt.md`
> **Last updated:** Feb 2026
> **Estimated production readiness:** ~42%

---

## 1. Go-Live Blockers (Hard Stops)

> Items that **must** be resolved before any customer-facing deployment.

- [ ] 🚨 **Auth bypass in dev mode** — `AuthMiddleware` allows all requests when `ENVIRONMENT=dev`. Add `AUTH_STRICT=true` default; refuse startup in prod-like env without strict auth.
- [ ] 🚨 **Workflow runtime is simulated** — Canvas nodes execute with `mockOutput` from `nodeRegistry.js`. No real backend execution engine for the 24 node types.
- [ ] 🚨 **Webhook signature validation not enforced** — Inbound webhook route does not enforce HMAC signature or timestamp/replay protection.
- [ ] 🚨 **Unsafe execution patterns** — Compiler conditional uses `eval`; code tool execution allows arbitrary runtime. Remove `eval`; sandbox code tools with restricted runtime.
- [ ] 🚨 **No production CI/CD quality gate** — No automated testing, linting, or security scanning before deployment.
- [ ] 🚨 **Secrets/deployment hardening incomplete** — K8s `secrets.yaml` has `REPLACE_ME` placeholders; insecure SSL bypass patterns in guardrails entrypoint.

---

## 2. Security

### 🔴 Critical

- [ ] **Password hashing uses static salt** — `seed_db.py` uses `salt="jai-agent-os"` for PBKDF2. Each user must have a unique random salt stored alongside the hash.
- [ ] **Token stored in-memory only** — `keycloak._token_cache` is a plain dict. Tokens lost on restart, no revocation. Move to Redis-backed token store.
- [ ] **CORS allows all origins** — `allow_origins=["*"]` by default. Lock down to specific domains in production via `CORS_ALLOWED_ORIGINS` env var.
- [ ] **Default admin password `admin123`** — Seeded in `seed_db.py`. Force password change on first login, or remove default credentials in non-dev environments.
- [ ] **Langfuse secrets use weak defaults** — `NEXTAUTH_SECRET=mysecretkey-change-in-production` and `SALT=mysalt-change-in-production`. Block launch if defaults used in prod.
- [ ] **`ENCRYPTION_KEY` can be empty** — If no Fernet key is set, credential encryption silently fails. Block startup without a valid key in prod.
- [ ] **K8s secrets.yaml has `REPLACE_ME` placeholders** — Use GCP Secret Manager or External Secrets Operator.
- [ ] **Postgres SSL disabled** — `connect_args={"ssl": "disable"}` in `engine.py`. Enable SSL for production.
- [ ] **API key stored in plaintext in token store** — `api_token_store` stores `token_plain`. Only store hash; return plaintext once at creation.
- [ ] **PII redaction not enforced** — Guardrails available but not mandatory on all output paths. Enforce pre-output PII scan with fail-closed mode.
- [ ] **Injection protection** — Compiler conditional uses `eval`; tool code execution allows arbitrary runtime. Remove `eval`; sandbox with restricted runtime.

### 🟡 Important

- [ ] **No CSRF protection** — Frontend stores auth tokens in localStorage (XSS-vulnerable). Consider httpOnly cookies with CSRF tokens.
- [ ] **Microsoft SSO not implemented** — `loginWithSSO()` shows "coming soon". Implement OIDC flow with Azure AD / Entra ID.
- [ ] **Keycloak integration scaffolded but unused** — Login bypasses Keycloak and uses local DB. Wire up for production SSO.
- [ ] **No request signing/HMAC on webhooks** — `webhook_handler.py` accepts webhooks without signature verification.
- [ ] **No input sanitization on SQL queries** — `agent_db.py` `execute_query()` accepts raw SQL. Enforce parameterized queries; block DDL.
- [ ] **Token expiry 24h with no refresh** — Implement token refresh endpoint.
- [ ] **RBAC enforcement incomplete** — `rbac.py` defines roles/permissions but routes don't check `request.state.user` roles.
- [ ] **Guardrails DB password hardcoded** — `PGPASSWORD=langfuse` in `docker-compose.yml`. Use secrets in production.
- [ ] **TLS/SSL safety** — Guardrails entrypoint temporarily installs global SSL bypass. Remove from production image.

### 🟢 Nice-to-have

- [ ] **Content-Security-Policy headers** — via nginx or Next.js middleware.
- [ ] **Security headers** — X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security.
- [ ] **API key scoping** — API keys currently grant full access. Add per-key permission scopes.
- [ ] **Audit log persistence** — `rbac_manager.get_audit_log()` is in-memory. Persist to DB.

---

## 3. Authentication & Authorization

### 🔴 Critical

- [ ] **Implement proper JWT tokens** — Replace `jai-{random}` tokens with signed JWTs (RS256) for stateless validation.
- [ ] **Enforce RBAC on all routes** — Every mutating endpoint must check `request.state.user.roles` against required permissions. Add route-level authorization decorators.
- [ ] **Multi-tenancy isolation** — Agents, tools, and data not scoped by tenant. A user from Tenant A can see Tenant B's agents. Implement central authorization policy with tenant/group/resource scoping.

### 🟡 Important

- [ ] **Forgot password flow** — `LoginPage.jsx` has button that does nothing. Implement with email verification.
- [ ] **User self-service profile** — No endpoint or UI for users to change password or profile.
- [ ] **Session management** — No way to list active sessions or force-logout other sessions.
- [ ] **Group-based permissions enforcement** — `GroupManager` tracks membership but doesn't enforce model/agent access in the gateway.

---

## 4. Core Features — Not Yet Implemented

### 🔴 Critical (Core Platform Gaps)

- [ ] **Workflow execution engine** — `WorkflowBuilder.jsx` defines 24 node types but there is no backend execution engine. Implement LangGraph-based workflow runner with deterministic DAG planner, persisted state transitions, and node-by-node runtime.
- [ ] **Real LLM agent execution** — `invoke_agent` does a single LLM call. No multi-step reasoning, tool use, or memory. Implement a proper agent loop (ReAct / tool-calling).
- [ ] **RAG with real vector store** — `AgentRAGManager` stores documents in Python dict with TF-IDF. Replace with vector database (pgvector / Vertex AI Vector Search). Implement file ingestion pipeline (PDF/Docx → chunking → embedding → storage).
- [ ] **Tool execution sandbox** — `ToolRegistry.execute()` returns fake results. Implement sandboxed code execution, real REST API calls, and MCP protocol support.
- [ ] **Pipeline orchestration persistence** — `AgentOrchestrator` runs pipelines in-memory with `time.sleep()`. Implement real async step execution with checkpointing.
- [ ] **Streaming responses** — `/v1/chat/completions` doesn't support SSE streaming. Implement for gateway and playground.

### 🟡 Important (Feature Completeness)

- [ ] **Knowledge Bases — file upload** — Upload UI exists but no backend processing (PDF, DOCX, CSV ingestion + chunking + embedding).
- [x] **Evaluation Studio — real evaluations** — LLM-as-judge and reference-based eval metrics (BLEU, ROUGE-L, Levenshtein, exact match, contains, word overlap) implemented in `backend/eval_studio/scoring.py`. Wired into Eval Studio multi-model comparison, experiments, A/B testing, and KB evaluation. Frontend `EvalPage.jsx` updated with quality scoring config panel, reference text input, metric selector, LLM-as-judge toggle, and quality score display in battle grid + comparison table.
- [ ] **Notification channels** — UI for Twilio/Teams/Email/Slack but no backend integrations.
- [ ] **Connector actions** — Workato connectors registered as tools but have no actual API integration.
- [ ] **Human-in-the-loop** — `AgentInbox` manages approvals in-memory. No real notification delivery, durable queue, SLA enforcement, or escalation execution.
- [x] **Environment promotion** — Full backend-enforced environment model already existed in `backend/environments/environment_manager.py` with promotion workflow (request→approve/reject→deploy), diffs, rollback, locking, and variables. Frontend `envStore.js` upgraded from simulated fake data to real backend API calls (`/environments/*`, `/environments/promotions/*`). `EnvironmentSwitcher.jsx` enhanced with `PromotionPanel` component: pending approvals queue with approve/reject, promotion history with rollback, cross-environment diff viewer, and per-env lock/unlock controls. `GlobalEnvSwitcher` now shows backend lock status and pending approval badge. `AgentsPage.jsx` agent detail view now includes "Promote" button with target env selector and approval-required warnings. `SettingsPage.jsx` gets new "Environments" tab rendering the full `PromotionPanel`.
- [x] **Agent versioning & rollback** — Backend already had `get_versions`, `get_version_detail`, `rollback_to_version`, `diff_versions` in `agent_registry.py` with API endpoints in `routes_v2.py` (`GET /agents/{id}/versions`, `GET /agents/{id}/versions/{version}`, `POST /agents/{id}/rollback/{version}`, `GET /agents/{id}/diff/{vA}/{vB}`). Frontend `AgentsPage.jsx` agent detail view upgraded: fake hardcoded version history replaced with real API-driven version list, per-version "Diff" button showing side-by-side field comparison modal (old vs new values), "Rollback" button with confirmation dialog that creates a new version from the target snapshot.
- [ ] **Structured output enforcement** — Optional in configs; no strict parse/retry loop globally. Implement schema-first responses with deterministic parser and corrective retry.
- [ ] **Idempotency handling** — No idempotency keys on invoke endpoints. Require for mutating invoke paths; persist dedupe windows.

### 🟢 Nice-to-have

- [x] **Agent marketplace/sharing** — Full marketplace implemented: `backend/marketplace/marketplace_manager.py` with publish, browse, install (clone to tenant), rate/review, featured listings. 15+ API endpoints under `/marketplace/*`. Frontend `TemplateGalleryPage.jsx` upgraded to dual-tab Templates + Marketplace with publish modal, install flow, star ratings, reviews, detail view, category filtering, and sort. Sidebar label updated to "Marketplace".
- [ ] **Scheduled agent runs** — `scheduleTrigger` node type exists but no cron scheduler.
- [x] **Import/export agents** — Full JSON import/export implemented. Backend: `GET /agents/{id}/export` (single), `POST /agents/export-bulk` (multi), `POST /agents/import` (single), `POST /agents/import-bulk` (multi). Portable `_export_format: jai-agent-os` envelope with full agent config (model, RAG, memory, DB, tools, access control, metadata). Import creates new agent as draft with `imported` tag and provenance metadata. Frontend: `AgentsPage.jsx` toolbar has Import (file picker) and Export All buttons; per-agent Export JSON in card menu calls backend API for full definition.
- [ ] **Collaborative editing** — Multiple users editing same workflow.
- [ ] **Dark mode** — UI is light-mode only.
- [ ] **MCP tool execution** — Connect to MCP server, list tools, call from agent context.
- [ ] **Tool playground** — Interactive tool testing UI (schema-driven form + response viewer).
- [ ] **File upload in chat** — PDF/image upload, extract text, inject into LLM context.
- [ ] **Cost alerting** — Threshold alerts when group/agent exceeds budget.

---

## 5. Database & Data Persistence

### 🔴 Critical

- [ ] **Postgres dev-mode tuning in production** — `docker-compose.yml` runs Postgres with `fsync=off`, `synchronous_commit=off`, `full_page_writes=off`. **Will cause data loss on crash.** Remove for production.
- [ ] **No database backups** — No backup strategy, no point-in-time recovery.

### 🟡 Important

- [ ] **Connection pool tuning** — `pool_size=20, max_overflow=10` hardcoded. Make configurable via env vars.
- [ ] **No database indexing strategy** — Only basic indexes. Add indexes for common query patterns.
- [ ] **Dual data path confusion** — Both in-memory and DB-backed agent CRUD exist (`/agents` vs `/db/agents`). Consolidate to single DB-backed path.
- [ ] **No data retention policy** — LLM logs, audit logs, thread history grow unbounded. Implement TTL-based cleanup.

---

## 6. AI & RAG Reliability

| Area | Current State | Required Before Customer Exposure |
|---|---|---|
| Citation enforcement | Not reliably enforced | Make citations mandatory for RAG answers; validate format + source presence |
| No-context handling | Configurable in UI but not enforced | Add explicit no-context branch policy and safe fallback templates |
| Guardrails enforcement | CRUD/deploy exists; inconsistent | Insert mandatory pre/post LLM guardrail pipeline in all invoke paths |
| Jailbreak resistance | Regex/pattern-based controls, limited | Add layered detection + policy model + adversarial test set |
| Structured output | Optional and provider-dependent | Require schema validation with retry-on-parse-fail |
| Model configuration safety | Mixed controls; allowlists not enforced | Enforce model allowlist by group/tenant before invocation |
| Prompt management maturity | Broad features; incomplete operational controls | Add promotion workflow, approval, immutable prod versions |
| RAG retrieval quality | In-memory keyword matching | Production vector index, embeddings lifecycle, re-ranker, retrieval QA |
| Token/cost safety | Cost estimation exists; budget controls partial | Hard budget guardrails and per-run/token quotas |
| Hallucination mitigation | Some scaffolding; not systematic | Retrieval-grounded answer policy + confidence thresholds + refusal templates |
| Retry + backoff for LLM | Partial, not standardized | Shared resilient call wrapper with exponential backoff + jitter + provider fallback |

---

## 7. Performance & Scalability

### 🔴 Critical

### 🟡 Important

- [x] **No connection pooling for external APIs** — Persistent `httpx.Client` in LangfuseManager + LRU cache (32 slots) in ProviderFactory.
- [x] **No request timeout enforcement** — TimeoutMiddleware: 120s default, 300s for LLM/pipeline/chat endpoints. Returns 504 on timeout.
- [x] **Frontend bundle optimization** — `modularizeImports` in next.config.js transforms lucide-react barrel imports to per-icon imports.
- [ ] **No CDN for static assets** — Frontend served directly by Next.js. Put behind CDN for production.
- [ ] **HPA configuration needs tuning** — `backend-hpa.yaml` thresholds should be load-tested.
- [ ] **No database read replicas** — Single Postgres instance.
- [x] **Parallel execution stability** — Real `asyncio.gather` with `Semaphore(10)` bounded concurrency + per-step timeouts in orchestrator.
- [ ] **Long-running workflows** — Limited persistence/checkpointing. Add checkpoint persistence and resumable execution.

---

## 8. Observability & Monitoring

### 🟡 Important

- [ ] **No structured logging** — Backend uses `print()` and basic `logging`. Implement structured JSON logging (`structlog`).
- [ ] **No metrics endpoint** — No Prometheus `/metrics`. Add request latency, error rates, LLM call durations.
- [ ] **No alerting** — No PagerDuty/OpsGenie/Slack integration for errors or SLA breaches.
- [ ] **No OpenTelemetry** — Langfuse is the only observability tool. Add distributed tracing across services.
- [x] **Health check is minimal** — `/health` now probes PostgreSQL (SELECT 1), Redis (info), and Langfuse (traces API). Returns degraded status.
- [ ] **No frontend error tracking** — No Sentry/LogRocket for frontend exceptions.
- [ ] **LLM cost tracking is estimate-only** — Static price table. Track actual costs from provider responses.
- [ ] **No correlation IDs** — No universal request/run correlation ID propagation across API, runtime, tool calls, notifications.
- [x] **Run history not durable** — `list_runs` and `get_run` now query PipelineRunModel from PostgreSQL with in-memory fallback.

---

## 9. Testing & QA

### 🔴 Critical

- [ ] **Only 1 test file exists** — `test_db_e2e.py` covers agent CRUD (6 tests). No tests for: API routes, auth middleware, RBAC, LLM provider factory, frontend components, integration tests.
- [ ] **No CI/CD pipeline** — No GitHub Actions or automated testing on PRs.

### 🟡 Important

- [ ] **No load testing** — No k6/Locust/Artillery for capacity planning. Create script simulating 50 concurrent users.
- [ ] **No contract tests** — Frontend and backend can drift. Add OpenAPI schema validation.
- [ ] **Test DB shares production schema** — Use separate test database or SQLite for unit tests.

### Required Test Suites

| Test File | Coverage |
|---|---|
| `tests/test_auth.py` | Login flow, token generation, RBAC rejection |
| `tests/test_agents.py` | CRUD operations, tool binding |
| `tests/test_execution.py` | Mock LLM calls, verify Orchestrator runs sequential pipeline |
| `tests/test_rag.py` | Document ingestion, retrieval accuracy (mock embeddings) |
| `tests/integration/test_full_flow.py` | Create Agent → Add Tool → Start Chat → Verify Response |
| Security/jailbreak tests | Prompt-injection suites, webhook signature validation, RBAC boundary tests |
| Workflow execution tests | Deterministic DAG execution, branching, retries, timeout, resumability |
| Failure scenario tests | Provider outage, DB outage, connector failure, retry/backoff, idempotency |

---

## 10. Infrastructure & DevOps

### 🔴 Critical

- [ ] **No CI/CD pipeline** — Set up GitHub Actions → lint, test, build Docker images, deploy to staging.
- [ ] **No Dockerfile for guardrails** — `docker-compose.yml` references `Dockerfile.guardrails` but it's missing.
- [ ] **K8s manifests need production values** — `ingress.yaml` uses `agent-os.example.com`. Replace with real domain. Replace `REPLACE_ME` placeholders (Helm or Kustomize).
- [ ] **No Terraform/Pulumi for infrastructure** — GKE cluster, Cloud SQL, Redis, networking not codified.

### 🟡 Important

- [ ] **No Docker image registry** — No GCR/Artifact Registry configuration.
- [ ] **No rollback strategy** — K8s deployments lack rollback annotations or canary config.
- [ ] **No network policies** — K8s pods can communicate freely.
- [ ] **No resource quotas** — K8s namespace has no resource quotas or limit ranges.
- [ ] **Nginx proxy config leftover** — `nginx-proxy.conf` has `/buyer/` and `/api/` routes to `host.docker.internal:5173` from another project.
- [ ] **Docker optimization** — Update Dockerfiles for production (multi-stage builds, non-root users). Remove dev-mode flags from `nginx.conf`.
- [ ] **K8s probes** — Define liveness and readiness probes for all services. Define CPU/Memory resource requests and limits.
- [ ] **Feature flags** — Feature state is code-conditional. Introduce server-managed feature flags for staged rollout.
- [ ] **Migration governance** — Alembic exists but release migration governance is light. Introduce migration review gates.

---

## 11. Code Quality & Architecture

### 🟡 Important

- [ ] **`server.py` is ~2000 lines** — Continue breaking routes into versioned modules.
- [ ] **Circular dependency risk** — Global instances created at module level. Consider dependency injection.
- [ ] **`datetime.utcnow()` is deprecated** — Replace with `datetime.now(UTC)`.
- [ ] **`.bak` files in repo** — `PlaygroundPage.jsx.bak` and `PromptsPage.jsx.bak` should be removed.
- [ ] **No linting in CI** — `ruff` is in requirements but no pre-commit hooks or CI lint step.
- [ ] **Frontend has no TypeScript** — Components are `.jsx`. Consider migrating to `.tsx` (TypeScript deps already installed).
- [ ] **No API versioning prefix** — Routes are flat (`/agents`, `/tools`). Consider `/api/v1/` prefix.
- [ ] **API versioning fragmentation** — Routes split across `routes_v2.py`, `routes_v3.py`, `routes_v4.py` without unified strategy.
- [ ] **LLM resiliency** — `ProviderFactory` lacks model fallback logic.
- [ ] **Redundant Pydantic schemas** — Duplicated across `compiler/manifest.py` and `api/routes_v2.py`.
- [ ] **Environment variable sprawl** — `.env` cluttered. Group by module in `settings.py`.
- [ ] **Error handling** — Implement global FastAPI exception handler returning structured JSON errors (Code, Message, RequestID).
- [ ] **Type safety** — Add Pydantic response models to all API endpoints for consistent contracts.

---

## 12. Documentation

### 🟡 Important

- [ ] **No API documentation beyond auto-generated** — Need usage guides, auth docs, onboarding tutorials.
- [ ] **README needs updating** — Local setup, Docker Compose, env vars, architecture diagram, contributing guide.
- [ ] **No architecture decision records (ADRs)** — Key decisions should be documented.
- [ ] **Existing docs are roadmap-focused** — Need operational runbooks and deployment guides.
- [ ] **No CHANGELOG** — No version history or release notes.
- [ ] **API Reference** — Generate ReDoc/Swagger static HTML.
- [ ] **Deployment Guide** — Step-by-step runbook for GKE/EKS.
- [ ] **User Manual** — "Creating your first Agent" and "Connecting a Tool" guides.

---

## 13. Workflow Node Completion Matrix

All 24 workflow node types defined in `frontend/stores/nodeRegistry.js`:

| Node Type | UI | Config Schema | UI Validation | Runtime | Error Handling | Prod Ready |
|---|---|---|---|---|---|---|
| startInput | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| webhookTrigger | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| scheduleTrigger | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| ifCondition | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| switchRoute | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| loopMap | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| parallelFork | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| joinMerge | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| delayWait | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| tryCatch | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| transform | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| script | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| validate | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| httpRequest | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| connectorAction | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| notify | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| llmCall | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| ragRetrieve | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| runAgent | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| guardrailsCheck | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| humanReview | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| createTicket | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| outputReturn | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| logTrace | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 14. OAP Feature Audit

| # | Feature | Status | Gap |
|---|---------|--------|-----|
| 1 | Chat Interface | ✅ Basic | Missing: streaming, file upload, tool call rendering, interrupt handling |
| 2 | Agent Config Sidebar | ✅ Basic | Missing: tool selection list, RAG collection picker, supervisor picker |
| 3 | Thread History Sidebar | ✅ Basic | Missing: load from backend |
| 4 | Agents — Templates | ✅ Done | — |
| 5 | Agents — All Agents | ✅ Basic | Missing: filter dropdown, deployment badges |
| 6 | Tools Page | ✅ Basic | Missing: MCP integration, load more, tool details |
| 7 | Tool Playground | ❌ | Missing entirely |
| 8 | RAG Page | ✅ Basic | Missing: file upload, text upload, pagination |
| 9 | Agent Inbox | ✅ Basic | Missing: durable persistence, channel reliability |
| 10 | Settings — API Keys | ✅ Done | — |
| 11 | Auth System | ✅ Done | — |
| 12 | Multi-deployment | ❌ | Missing entirely |

### JAI-Only Features (Beyond OAP)

| # | Feature | Status |
|---|---------|--------|
| 13 | Agent-as-a-Service Gateway | ⚠️ Basic (works for demo) |
| 14 | LLM Logs & Diagnostics | ⚠️ In-memory only |
| 15 | Multi-Tenancy | ❌ Not enforced |
| 16 | Agent Orchestrator | ✅ Backend (in-memory) |
| 17 | Tool Builder | ✅ Backend (in-memory) |
| 18 | Prompt Studio | ✅ Versioning done |
| 19 | Eval Studio | ✅ A/B comparison done |
| 20 | GKE Scaling | ⚠️ Untested manifests |

---

## 15. Roadmap

### MVP1 — Core Platform (Target: 3-4 weeks)

| # | Feature | Effort | Status |
|---|---------|--------|--------|
| 1 | PostgreSQL persistence (all managers) | L (5-7 days) | 🔴 Partial (Thread + Usage done) |
| 2 | Streaming chat | M (2-3 days) | 🟡 WebSocket streaming done, SSE pending |
| 3 | End-to-end agent → chat flow | M (2-3 days) | 🔴 Pending |
| 4 | Real LangGraph execution | M (3-4 days) | 🔴 Pending |
| 5 | RAG with real vector store | M (3-4 days) | 🔴 Pending |
| 6 | Seed data that persists | S (1 day) | 🔴 Pending |
| 7 | Error handling & loading states | S (1-2 days) | 🔴 Pending |
| 8 | Docker Compose production-ready | S (1 day) | 🟡 Partial |
| 9 | Basic E2E smoke test | S (1-2 days) | 🔴 Pending |

### MVP1.1 — Production Hardening (Weeks 5-8)

- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Unit + integration tests (80%+ backend coverage)
- [ ] API rate limiting (per-tenant, per-API-key with Redis)
- [ ] Audit logging (immutable, persistent)
- [ ] CORS & security hardening
- [ ] Agent templates (pre-built)
- [ ] Webhook delivery (retry, HMAC, event log)
- [ ] Multi-turn memory (summarization, long-term retrieval)
- [ ] Model fallback (auto-failover)
- [ ] OpenAPI docs polish

### MVP2 — Scale & Enterprise (Weeks 9-16)

- [ ] GKE deployment (validated, HPA for 1000 req/sec)
- [ ] Multi-tenancy enforcement (real isolation, row-level security)
- [ ] SSO (SAML/OIDC via Keycloak)
- [ ] Real connector framework (Salesforce, SAP, ServiceNow)
- [ ] Agent marketplace
- [ ] Advanced RAG (hybrid search, re-ranking, multi-collection)
- [ ] Guardrail enforcement (PII, toxicity, hallucination)
- [ ] Cost chargeback (finance-ready reports)
- [ ] Agent versioning & rollback (dev → staging → prod)
- [ ] Observability dashboards (percentiles, forecasting, anomaly detection)
- [ ] Snowflake integration (real queries)
- [ ] Custom LLM providers (Azure OpenAI, Bedrock, Cohere, Mistral)

### MVP3 — Advanced Autonomy (Weeks 17+)

- [ ] Autonomous agent loops (plan, execute, self-correct)
- [ ] Inter-agent communication (messaging, delegation, supervisor)
- [ ] Scheduled agent runs (cron-based)
- [ ] HITL workflows (approval chains, escalation, SLA)
- [ ] Fine-tuning integration
- [ ] Plugin system (third-party API)
- [ ] Mobile companion app

### Jaggaer Release Plan (Target: June 2026)

| Phase | Month | Focus |
|---|---|---|
| Phase 1 | March | Core Studio & Connectivity — LangGraph execution, compiler hardening |
| Phase 2 | April | Procurement Intelligence & RAG — Vertex AI, HITL inbox, procurement templates |
| Phase 3 | May | Enterprise Readiness — AaaS gateway polish, usage metering, dev kit & docs, packaging |

**KPI Targets:**
1. Developer Self-Service: Build a new tool in < 30 mins
2. Business Ease-of-Use: Create an agent from template in < 5 mins
3. Connectivity: Out-of-the-box support for 5+ Jaggaer Core APIs

---

## 17. 90-Day Readiness Track

### Phase 1 (Weeks 1-3): Hardening Foundations
- Enforce strict auth/RBAC and remove bypass paths
- Lock webhook auth, idempotency, and input validation
- Remove unsafe `eval`; sandbox code execution
- Make DB-backed persistence mandatory for production mode

### Phase 2 (Weeks 4-7): Runtime and Reliability
- Implement real workflow node runtime for 24-node canvas
- Unify node schema contracts across UI/backend
- Add deterministic run engine with retries/timeouts/checkpointing
- Enforce citation and structured output validation

### Phase 3 (Weeks 8-10): Observability and QA Gate
- Add correlation IDs, metrics, trace coverage, run history durability
- Build comprehensive test suites (unit/integration/security/E2E/load)
- Introduce CI quality gates and deployment promotion controls

### Phase 4 (Weeks 11-12): Pre-Go-Live Validation
- Security review and penetration testing
- Staged soak/load tests and failure drills
- Launch checklist sign-off with rollback plan

---

## 18. Nice-to-Have Enhancements (Post-Launch)

| Enhancement | Why It Matters |
|---|---|
| Visual workflow diff viewer | Change review and auditability across versions/environments |
| Advanced run replay debugger | Replay from intermediate checkpoints |
| Prompt experiment auto-ranking | Select best prompt versions via objective metrics |
| Cost forecasting and anomaly alerts | Budget governance for enterprise teams |
| Connector marketplace UX | Adoption and discoverability of integrations |
| Policy-as-code editor for guardrails | Compliance teams own policy updates |
| Multi-region runtime support | Latency, resiliency, data residency |
| SLA dashboard for HITL inbox | Operational accountability for approval workflows |

---

## Priority Summary

| Category | 🔴 Critical | 🟡 Important | 🟢 Nice-to-have |
|----------|------------|-------------|-----------------|
| Security | 11 | 9 | 4 |
| Auth & Authz | 3 | 4 | — |
| Features | 6 | 9 | 10 |
| Database | 4 | 4 | — |Client-side Error
Zap is not defined

ReferenceError: Zap is not defined
    at E (http://localhost:3000/_next/static/chunks/19.36f9290bc7a62b14.js:1:3170)
    at l9 (http://localhost:3000/_next/static/chunks/4bd1b696-409494caf8c83275.js:1:51129)
    at o_ (http://localhost:3000/_next/static/chunks/4bd1b696-409494caf8c83275.js:1:70989)
    at oq (http://localhost:3000/_next/static/chunks/4bd1b696-409494caf8c83275.js:1:82019)
    at ik (http://localhost:3000/_next/static/chunks/4bd1b696-409494caf8c83275.js:1:114681)
    at http://localhost:3000/_next/static/chunks/4bd1b696-409494caf8c83275.js:1:114526
    at ib (http://localhost:3000/_next/static/chunks/4bd1b696-409494caf8c83275.js:1:114534)
    at iu (http://localhost:3000/_next/static/chunks/4bd1b696-409494caf8c83275.js:1:111617)
    at iX (http://localhost:3000/_next/static/chunks/4bd1b696-409494caf8c83275.js:1:132933)
    at MessagePort.w (http://localhost:3000/_next/static/chunks/255-091853b4155593e2.js:1:64168)
Try Again
| AI & RAG | — | 11 | — |
| Performance | 3 | 8 | — |
| Observability | — | 9 | — |
| Testing | 2 | 3 | — |
| Infrastructure | 4 | 9 | — |
| Code Quality | — | 13 | — |
| Documentation | — | 8 | — |
| **Total** | **33** | **87** | **14** |

---

---

## Completed Items

### Frontend & UI
- [x] **Frontend Auth Flow** — MS SSO-styled login page, email+password flow, Zustand auth store, protected routes
- [x] **Workflow Builder v2** — 24 data-driven node types across 7 categories via `nodeRegistry.js`, schema-driven property panel, connection validation, example templates
- [x] **Environment Management** — 3-environment model (Dev/UAT/Prod), Zustand env store, environment switcher, permission model, env badges, production safety guardrails
- [x] **Resources Reuse (Mosaic Design System)** — All 304 Mosaic icons synced, `<MosaicIcon>` component, `<BrandIllustration>` component, 24 illustrations, sidebar uses Mosaic icons, 13 empty states use branded illustrations
- [x] **Solution Branding** — 20 icons synced to `frontend/public/branding/` (Default + Inverted)
- [x] **Mosaic Icon Library** — All 304 SVGs synced to `frontend/public/icons/`. `<MosaicIcon>` component created. Sidebar uses Mosaic icons.
- [x] **Illustrations** — All 24 SVGs synced to `frontend/public/illustrations/`. `<BrandIllustration>` component created. 13 empty states use branded illustrations.
- [x] **`AgentStudio.jsx` code-split** — Code-split into 18 lazy-loaded page modules under `frontend/components/pages/` + shared UI in `frontend/components/shared/StudioUI.jsx`. Reduced from 6,082 lines (408KB) to 454 lines (29KB) — 93% reduction.

### Backend & Infrastructure
- [x] **Docker Compose** — Backend + frontend + Redis + Langfuse + Langfuse-DB, health checks
- [x] **Monitoring** — Traces, generations, scores via Langfuse (persistent)
- [x] **Rate limiting on auth endpoints** — IP-based rate limiter on `/auth/login`: max 5 attempts per 60s per IP, HTTP 429, auto-prune
- [x] **In-memory state → Redis** — `RedisStateManager` in `backend/cache/redis_state.py` provides Redis-backed shared state for all registries with in-memory fallback. Wired into FastAPI lifespan.
- [x] **Caching layer** — `CacheLayer` in `backend/cache/cache_layer.py` provides two-tier (L1 in-memory + L2 Redis) TTL cache with async decorator. API endpoints for stats/invalidation added.

### Data Persistence
- [x] **Data persistence complete** — All 8 managers (`UserManager`, `GroupManager`, `TenantManager`, `ToolRegistry`, `AgentOrchestrator`, `AgentInbox`, `AgentMemoryManager`, `AgentRAGManager`) now PostgreSQL-backed with in-memory fallback. 7 new DB models added. Alembic migration `003`. Shared `sync_bridge.py` for async-to-sync bridge.
- [x] **All managers PostgreSQL-backed** — 7 new ORM models (`GroupModel`, `PipelineModel`, `PipelineRunModel`, `InboxItemModel`, `MemoryEntryModel`, `RAGCollectionModel`, `RAGDocumentModel`). ThreadManager and UsageMeteringManager were already DB-backed.
- [x] **Alembic migrations complete** — Migration `003` added for groups, pipelines, pipeline_runs, inbox_items, memory_entries, rag_collections, rag_documents tables.

### AI & LLM
- [x] **Prompt versioning in Langfuse** — `rollback_to_version()`, `diff_versions()` methods. `/prompts/{name}/rollback` and `/prompts/{name}/diff` endpoints
- [x] **Experiment manager** — `ExperimentManager.run_experiment()` wired to Langfuse datasets + LLM execution. `/experiments/run-ab` multi-model A/B comparison endpoint
- [x] **Thread/conversation persistence** — `ThreadManager` rewritten to PostgreSQL via async SQLAlchemy. `ThreadModel` + `ThreadMessageModel` ORM models. Alembic migration `002`
- [x] **Usage metering billing** — `UsageMeteringManager` rewritten to PostgreSQL. Real cost calculation from `MODEL_PRICING` table (16 models). `/metering/billing-export`, `/metering/pricing` endpoints
- [x] **WebSocket real-time updates** — `WebSocketManager` wired into agent execution. Enhanced `/ws/{client_id}` with user/tenant/channel support. `/chat/stream` endpoint streams LLM tokens

### Agent Import/Export
- [x] **Agent import/export** — Backend endpoints in `routes_v2.py`: `GET /agents/{id}/export`, `POST /agents/export-bulk`, `POST /agents/import`, `POST /agents/import-bulk`. JSON standard format with `_export_format: jai-agent-os` envelope. Frontend `AgentsPage.jsx`: Import button (file picker, supports single + bulk), Export All button (bulk), per-agent Export JSON via card menu. Imported agents get `imported` tag, draft status, and provenance metadata.

---

*Merged from 8 source files — Feb 2026*
*Source files deleted: `todo.md`, `docs/todo.md`, `docs/todocodex.md`, `docs/todogemini.md`, `docs/PLAN.md`, `docs/ROADMAP.md`, `docs/JAGGAER_ROADMAP.md`, `docs/techdebt.md`*
