# Changelog

## v0.3.0 — Langfuse Monitoring & Eval Tracing (Feb 2026)

### Langfuse Tracing (All LLM Calls)
- **Eval Studio** — `/eval/stream`, `/eval/single`, `/eval/multi` now create Langfuse traces with one generation per model, including tokens, latency, cost
- **Chat (Playground)** — Rewrote `/chat/stream` to return SSE (was WebSocket-only), add Langfuse trace + generation logging, resolve integration credentials
- **Playground** — `/playground/run` now includes `user_id` in Langfuse traces
- **User identity** — All endpoints read `X-User-Display-Name` header (sent by `apiFetch`) instead of hardcoded `"playground"` / `"eval-studio"`

### Monitoring UI
- **JSON tab** — New tab alongside Preview / Scores / Metadata showing full raw JSON with "Copy JSON" button
- **Stats for root trace** — Tokens, latency, cost, model now shown for root trace (aggregated from observations), not just individual observations
- **Beautified preview** — `extractContent` handles Python dict repr strings (single quotes → double quotes) for proper formatted display

### Eval Studio
- **SSE streaming** — Models run concurrently on backend; results stream to UI as each completes
- **Dynamic model list** — Model selector and pricing built from `/models` API (no hardcoded list)
- **Metric descriptions** — Plain-English descriptions shown inline (not hidden in tooltips)

### Frontend Auth
- **`apiFetch`** sends `X-User-Display-Name` header with logged-in user's display name on every API call

### Setup
- **DB seed verification** — `setup.sh` now verifies admin login after backend starts; auto-restarts backend up to 3 times if seeding failed

### Infrastructure
- **Docker volumes** — Replaced named volumes with local bind mounts under `.local/` for Postgres and Redis
- **Chat layout** — `overflow-hidden` for full-height Chat page; `PageTransition` passes `h-full`

### Tests
- 143 frontend tests (Jest), 175 backend tests (pytest) — all passing

---

## Unreleased — `feat/implement-new-md-20260217-WS`

### Shell & Information Architecture
- **Sidebar restructured** into 3 lean sections (Build 4, Test 2, Operate 3) + Admin as single bottom destination
- **AdminHub page** — card grid landing page for all admin sub-pages (Organizations, Teams, Users, API Tokens, Notifications, Connectors, Audit Trail, Settings)
- Removed `Integrations → Models` duplicate route and `LLMPlayground` orphan route
- Build + Test sections expanded by default; Operate collapsed

### Workflow Builder
- **Canvas is now full-width by default** — the hero surface
- Node Library is a toggleable overlay on the left (via toolbar "Nodes" button)
- Properties Panel is an auto-showing overlay on the right (appears when a node is selected)
- Toolbar follows single dominant CTA pattern (Execute primary, Save secondary)

### Typography
- **Normalized all 9-10px text to 11px minimum** across 27 component files (372 instances)
- Ensures minimum readable font size per Apple Gold Standard spec

### Action Clutter
- AgentsPage toolbar: secondary actions (Templates, Import, Export All) consolidated into ⋯ overflow menu
- Single primary CTA ("New Agent") stands alone
- `AgentListOverflow` component uses portal-based dropdown matching existing `AgentCardMenu` pattern

### Chat
- Config sidebar remains hidden by default
- **Auto-configures chat from agent properties** (model, system prompt, RAG, temperature) when agent is selected

### Command Palette (⌘K)
- **Arrow key navigation** with active item highlight
- **Enter to select**, mouse hover updates active index
- **Recency tracking** via localStorage (last 8 items shown in "Recent" section)
- Actions section prioritized above Pages when no query
- `animate-scale-in` on open

### Motion & Consistency
- Added `animate-fade-up` entrance animation to all 23 page wrapper divs
- Consistent with `PageTransition` wrapper in AgentStudio shell

### Prior Session (included in branch)
- Templates + Marketplace merged into single unified `TemplateGalleryPage`
- `EnvBadge` removed from workflow list header, grid cards, and list rows
- `OrgSwitcher` + `EnvSwitcher` replaced with portal-based `WorkspaceContext` component
