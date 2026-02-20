# JAI Agent OS — API Reference

> **Interactive Swagger UI** available at `http://localhost:8080/docs`
> **ReDoc** available at `http://localhost:8080/redoc`
> **OpenAPI JSON** available at `http://localhost:8080/openapi.json`

Click the **Help** button (top-right of Agent Studio) to open Swagger in a new tab.

---

## Base URL

```
http://localhost:8080
```

## Authentication

All protected routes require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

Public paths (no auth required): `/health`, `/info`, `/docs`, `/redoc`, `/openapi.json`, `/auth/login`, `/auth/logout`, `/auth/sso`

In dev mode (`ENVIRONMENT=dev`), auth is bypassed.

---

## API Sections

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check with model/provider status |
| GET | `/info` | Platform info — architecture, counts, monitoring |
| GET | `/executive/dashboard` | Executive dashboard with KPIs, trends |
| GET | `/dashboard/metrics` | CXO-level aggregated metrics |
| GET | `/ws/stats` | WebSocket connection statistics |
| GET | `/langsmith/status` | LangSmith observability status |
| GET | `/langsmith/runs` | List recent LangSmith runs |
| GET | `/langsmith/stats` | Aggregated run statistics |
| GET | `/monitoring/status` | Langfuse connection status |
| GET | `/monitoring/traces` | List LLM call traces |
| GET | `/monitoring/generations` | List LLM generations |
| GET | `/monitoring/scores` | List evaluation scores |
| GET | `/monitoring/sessions` | List conversation sessions |
| GET | `/monitoring/metrics` | Aggregated monitoring metrics |
| POST | `/monitoring/scores` | Submit evaluation score |
| GET | `/seed/settings` | Default platform settings |
| GET | `/seed/summary` | Seed data summary |

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Login with username/password (rate limited: 5/60s) |
| GET | `/auth/me` | Get current user from token |
| GET | `/roles` | List all RBAC roles |
| POST | `/roles/assign` | Assign role to user |
| POST | `/roles/revoke` | Revoke role from user |
| GET | `/audit-log` | RBAC audit log |
| GET | `/api-tokens` | List API tokens |
| POST | `/api-tokens` | Create API token |
| DELETE | `/api-tokens/{token_id}` | Revoke API token |

### Users
| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List all users |
| POST | `/users` | Create user (with password hash) |
| GET | `/users/{user_id}` | Get user profile |
| DELETE | `/users/{user_id}` | Delete user |
| GET | `/users/{user_id}/roles` | Get user's roles |
| POST | `/users/{user_id}/api-key` | Generate API key for user |
| GET | `/users/stats/summary` | User statistics |

### Groups
| Method | Path | Description |
|--------|------|-------------|
| GET | `/groups` | List groups (optionally by LoB) |
| POST | `/groups` | Create group with model/agent/role assignments |
| GET | `/groups/{group_id}` | Get group details |
| PUT | `/groups/{group_id}` | Update group |
| DELETE | `/groups/{group_id}` | Delete group |
| GET | `/groups/{group_id}/members` | List group members |
| POST | `/groups/{group_id}/members` | Add member to group |
| DELETE | `/groups/{group_id}/members/{user_id}` | Remove member |
| POST | `/groups/{group_id}/models` | Assign models to group |
| GET | `/groups/{group_id}/models` | List group's allowed models |
| POST | `/groups/{group_id}/agents` | Assign agents to group |
| POST | `/groups/{group_id}/roles` | Assign roles to group |
| GET | `/users/{user_id}/allowed-models` | User's allowed models (via groups) |
| GET | `/users/{user_id}/groups` | User's group memberships |

### Tenants
| Method | Path | Description |
|--------|------|-------------|
| GET | `/tenants` | List all tenants |
| POST | `/tenants` | Create tenant |
| GET | `/tenants/{tenant_id}` | Get tenant details |
| PUT | `/tenants/{tenant_id}` | Update tenant |
| DELETE | `/tenants/{tenant_id}` | Delete tenant |
| GET | `/tenants/{tenant_id}/usage` | Tenant usage stats |
| POST | `/tenants/{tenant_id}/api-keys` | Generate tenant API key |

### Agents
| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | List agents (filter by status, owner) |
| POST | `/agents` | Create agent with model config, RAG, memory |
| GET | `/agents/{agent_id}` | Get full agent definition |
| PUT | `/agents/{agent_id}` | Update agent (creates new version) |
| DELETE | `/agents/{agent_id}` | Delete agent |
| POST | `/agents/{agent_id}/status/{status}` | Set agent status (draft/active/paused/archived) |
| POST | `/agents/{agent_id}/clone` | Clone agent |
| GET | `/agents/{agent_id}/versions` | List all versions |
| GET | `/agents/{agent_id}/versions/{version}` | Get specific version detail |
| POST | `/agents/{agent_id}/rollback/{version}` | **Rollback** to previous version |
| GET | `/agents/{agent_id}/diff/{v_a}/{v_b}` | **Diff** between two versions |
| POST | `/agents/{agent_id}/invoke` | Invoke agent (AaaS endpoint) |
| GET | `/agents/{agent_id}/api-snippet` | Get curl/Python code snippets |
| POST | `/v1/chat/completions` | OpenAI-compatible chat endpoint |

### Agent Memory
| Method | Path | Description |
|--------|------|-------------|
| POST | `/agents/{id}/memory/message` | Add conversation message |
| GET | `/agents/{id}/memory/conversation` | Get conversation history |
| GET | `/agents/{id}/memory/sessions` | List memory sessions |
| POST | `/agents/{id}/memory/long-term` | Store long-term memory |
| GET | `/agents/{id}/memory/long-term` | Retrieve long-term memories |
| GET | `/agents/{id}/memory/stats` | Memory statistics |
| DELETE | `/agents/{id}/memory` | Clear all memory |

### Agent RAG
| Method | Path | Description |
|--------|------|-------------|
| GET | `/rag/collections` | List RAG collections |
| POST | `/rag/collections` | Create collection |
| DELETE | `/rag/collections/{id}` | Delete collection |
| POST | `/rag/collections/{id}/documents` | Add document |
| GET | `/rag/collections/{id}/documents` | List documents |
| POST | `/rag/retrieve` | Retrieve from collections |
| GET | `/knowledge-bases` | List knowledge bases |
| POST | `/knowledge-bases` | Create knowledge base |
| POST | `/knowledge-bases/{id}/upload` | Upload to KB |
| POST | `/knowledge-bases/{id}/test` | Test KB retrieval |
| POST | `/knowledge-bases/{id}/evaluate` | Evaluate KB (RAGAS metrics) |

### Models
| Method | Path | Description |
|--------|------|-------------|
| GET | `/models` | List models (filter by provider, capability) |
| GET | `/models/{model_id}` | Get model details |
| POST | `/models` | Register custom model |
| DELETE | `/models/{model_id}` | Unregister model |
| POST | `/models/{model_id}/test` | Test model connectivity |
| GET | `/models/compare/cost` | Compare costs across models |
| GET | `/providers` | List LLM providers |

### Prompts
| Method | Path | Description |
|--------|------|-------------|
| GET | `/prompts` | List prompts (Langfuse-backed) |
| GET | `/prompts/{name}` | Get prompt (by version or label) |
| POST | `/prompts` | Create/version prompt |
| GET | `/prompts/{name}/versions` | All versions of a prompt |
| POST | `/prompts/{name}/labels` | Set label (e.g. 'production') |
| POST | `/prompts/{name}/rollback` | Rollback to previous version |
| GET | `/prompts/{name}/diff` | Diff two versions |
| POST | `/prompts/render` | Render prompt with variables |
| GET | `/prompts/{name}/variables` | Extract prompt variables |
| POST | `/playground/run` | Execute prompt against LLM |

### Tools
| Method | Path | Description |
|--------|------|-------------|
| GET | `/tools` | List tools (filter by type, status) |
| POST | `/tools` | Create tool (code, REST API, or MCP) |
| PUT | `/tools/{tool_id}` | Update tool |
| GET | `/tools/{tool_id}` | Get tool definition |
| DELETE | `/tools/{tool_id}` | Delete tool |
| POST | `/tools/{tool_id}/execute` | Execute tool |
| POST | `/tools/{tool_id}/clone` | Clone tool |
| POST | `/tools/mcp/discover` | Discover MCP server tools |
| GET | `/tools/{tool_id}/logs` | Tool execution history |

### Pipelines
| Method | Path | Description |
|--------|------|-------------|
| GET | `/orchestrator/pipelines` | List pipelines |
| POST | `/orchestrator/pipelines` | Create pipeline |
| GET | `/orchestrator/pipelines/{id}` | Get pipeline |
| DELETE | `/orchestrator/pipelines/{id}` | Delete pipeline |
| POST | `/orchestrator/pipelines/{id}/execute` | Execute pipeline |
| GET | `/orchestrator/runs` | List pipeline runs |
| POST | `/workflows/{id}/invoke` | Invoke workflow (AaaS) |
| GET | `/workflows/{id}/api-snippet` | Get curl/Python snippets |

### Evaluation
| Method | Path | Description |
|--------|------|-------------|
| POST | `/eval/estimate-tokens` | Estimate tokens and cost |
| POST | `/eval/single` | Evaluate against single model |
| POST | `/eval/multi` | Side-by-side multi-model comparison |
| GET | `/eval/runs` | List evaluation runs |
| GET | `/eval/runs/{run_id}` | Get evaluation run details |

### Scoring
| Method | Path | Description |
|--------|------|-------------|
| POST | `/eval/score` | **Score output** — reference metrics + optional LLM judge |
| POST | `/eval/judge` | **LLM-as-judge** only |
| GET | `/eval/metrics` | List available metrics and judge criteria |

**Reference metrics:** `exact_match`, `contains`, `bleu`, `rouge_l`, `levenshtein`, `semantic_similarity`
**Judge criteria:** `relevance`, `coherence`, `helpfulness`, `accuracy`, `conciseness`, `safety`, `custom`

### Experiments
| Method | Path | Description |
|--------|------|-------------|
| GET | `/experiments/datasets` | List datasets |
| POST | `/experiments/datasets` | Create dataset |
| GET | `/experiments/datasets/{name}` | Get dataset with items |
| POST | `/experiments/dataset-items` | Add test case to dataset |
| GET | `/experiments/datasets/{name}/runs` | Get experiment runs |
| POST | `/experiments/run` | Run experiment (auto-scoring) |
| POST | `/experiments/run-ab` | A/B test across multiple models |

### Environments
| Method | Path | Description |
|--------|------|-------------|
| GET | `/environments` | List all environments (Dev/QA/UAT/Prod) |
| GET | `/environments/{env_id}` | Get environment with variables |
| POST | `/environments/{env_id}/variables` | Set environment variable |
| POST | `/environments/{env_id}/variables/bulk` | Bulk set variables |
| GET | `/environments/{env_id}/variables` | Get all variables |
| DELETE | `/environments/{env_id}/variables/{key}` | Delete variable |
| POST | `/environments/{env_id}/lock` | Lock environment |
| POST | `/environments/{env_id}/unlock` | Unlock environment |
| GET | `/environments/{env_id}/assets` | List deployed assets |
| GET | `/environments/stats` | Environment management stats |

### Promotions
| Method | Path | Description |
|--------|------|-------------|
| POST | `/environments/promotions` | Request asset promotion |
| GET | `/environments/promotions` | List promotion records |
| GET | `/environments/promotions/{id}` | Get promotion detail |
| POST | `/environments/promotions/{id}/approve` | Approve promotion |
| POST | `/environments/promotions/{id}/reject` | Reject promotion |
| POST | `/environments/promotions/{id}/rollback` | Rollback deployed promotion |
| GET | `/environments/diff/{env_a}/{env_b}` | Diff assets between environments |

**Promotion order:** Dev → QA (auto-approve) → UAT (requires approval) → Prod (requires approval)

### Threads
| Method | Path | Description |
|--------|------|-------------|
| GET | `/threads` | List threads |
| POST | `/threads` | Create thread |
| GET | `/threads/{id}` | Get thread |
| GET | `/threads/{id}/messages` | Get messages |
| POST | `/threads/{id}/messages` | Add message |
| GET | `/threads/by-agent/{agent_id}` | Threads by agent |
| DELETE | `/threads/{id}` | Delete thread |

### Inbox
| Method | Path | Description |
|--------|------|-------------|
| GET | `/inbox` | List inbox items (HITL approvals) |
| POST | `/inbox` | Create inbox item |
| GET | `/inbox/{item_id}` | Get inbox item |
| POST | `/inbox/{item_id}/resolve` | Resolve (approve/reject/escalate) |

### Metering
| Method | Path | Description |
|--------|------|-------------|
| GET | `/metering/summary` | Usage summary with cost |
| GET | `/metering/by-group` | Cost breakdown by group |
| GET | `/metering/by-lob` | Cost breakdown by LoB |
| GET | `/metering/by-agent` | Cost breakdown by agent |
| GET | `/metering/by-model` | Cost breakdown by model |
| GET | `/metering/by-user` | Cost breakdown by user |
| GET | `/metering/trend` | Daily cost trend |
| GET | `/metering/billing-export` | Billing export for chargeback |
| GET | `/metering/pricing` | Model pricing table |

### Webhooks
| Method | Path | Description |
|--------|------|-------------|
| GET | `/webhooks` | List webhooks |
| POST | `/webhooks` | Create webhook |
| DELETE | `/webhooks/{id}` | Delete webhook |
| POST | `/webhooks/inbound/{id}` | Receive inbound webhook |
| GET | `/webhooks/{id}/events` | Get webhook event history |

### Integrations
| Method | Path | Description |
|--------|------|-------------|
| GET | `/integrations` | List LLM provider integrations |
| POST | `/integrations` | Create integration (with credentials) |
| PUT | `/integrations/{id}` | Update integration |
| DELETE | `/integrations/{id}` | Delete integration |
| POST | `/integrations/{id}/test` | Test connectivity |
| POST | `/integrations/test-connection` | Test before saving |
| POST | `/integrations/{id}/push` | Push to groups |

### Guardrails
| Method | Path | Description |
|--------|------|-------------|
| GET | `/guardrails` | List guardrail rules |
| POST | `/guardrails` | Create rule |
| PUT | `/guardrails/{id}` | Update rule |
| DELETE | `/guardrails/{id}` | Delete rule |
| GET | `/guardrails/agent/{agent_id}` | Rules for an agent |
| GET | `/guardrails-ai/status` | Guardrails AI service status |
| POST | `/guardrails-ai/deploy` | Deploy guard to service |
| POST | `/guardrails-ai/validate` | Validate text against guard |
| POST | `/guardrails-ai/test` | Ad-hoc test (no deployment) |

### Connectors
| Method | Path | Description |
|--------|------|-------------|
| GET | `/connectors` | List Workato connectors |
| GET | `/connectors/{id}` | Get connector details |
| POST | `/connectors/connections` | Create connection |
| GET | `/connectors/connections/list` | List connections |
| POST | `/connectors/connections/{id}/test` | Test connection |
| POST | `/connectors/connections/{id}/execute` | Execute action |
| POST | `/connectors/recipes` | Create automation recipe |

---

## WebSocket

```
ws://localhost:8080/ws/{client_id}?user_id=...&tenant_id=...&channels=...
```

Real-time streaming for agent execution tokens.

## Streaming Chat

```
POST /chat/stream
{
  "model": "gemini-2.5-flash",
  "messages": [...],
  "ws_client_id": "my-client",
  "ws_channel": "agent-123"
}
```

Streams tokens to the connected WebSocket client in real-time.
