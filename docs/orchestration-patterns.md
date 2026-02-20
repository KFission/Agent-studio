# Orchestration Patterns — Architecture & Implementation Guide

## Overview

JAI Agent OS supports three pipeline orchestration patterns for composing agents into multi-step workflows. Each pattern has distinct execution semantics, visual representation, and configuration options.

---

## 1. Sequential (Chain)

### Logic
Agent A → Agent B → Agent C. The output of one agent becomes the context/input for the next.

### Execution Engine (Backend — TODO)
- Implement `_run_sequential()` in `backend/orchestrator/orchestrator.py`
- Iterates through nodes in topological order
- Passes the output of the previous node into the Jinja2 template context of the next node
- Updates a `global_state` object at each step

### Data Model
```python
# backend/compiler/manifest.py
class PipelineType(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    SUPERVISOR = "supervisor"

class WorkflowManifest:
    type: PipelineType
    nodes: List[PipelineNode]       # ordered list
    edges: List[PipelineEdge]
    global_context: Dict[str, Any]  # shared state across steps
    state_mapping: Dict[str, str]   # maps output vars to input vars
```

### Canvas Rules
- Only 1-to-1 connections allowed (no branching)
- Nodes display step numbers (green badge, top-left)
- Linear vertical layout

### Data Mapping
When connecting Agent A → Agent B, click the edge to open the Data Mapping modal:
- Map `{{AgentA.output_field}}` → `AgentB.input_variable`

---

## 2. Parallel (Broadcast / Fork-Merge)

### Logic
One prompt is sent to N agents simultaneously. Results are combined at the end via a merge strategy.

### Execution Engine (Backend — TODO)
- Implement `_run_parallel()` in `backend/orchestrator/orchestrator.py`
- Uses `asyncio.gather` to execute all parallel agents concurrently
- Each agent receives the same initial input
- Implements a "Joiner" that merges all agent JSON responses
- **Error handling**: Configurable — fail-all or partial-success modes

### Canvas Rules
- **Splitter Node**: 1-to-Many fan-out from input
- **Merger Node**: Many-to-1 convergence
- Agents are arranged horizontally between splitter and merger

### Merge Strategies (configured on Merger node)
| Strategy | Behavior |
|----------|----------|
| `raw`    | JSON object containing all agent results keyed by agent name |
| `summary`| Use a "Final Agent" to summarize all parallel results into one output |

---

## 3. Supervisor (Hub-and-Spoke)

### Logic
An LLM "Supervisor" decides which Worker Agent to call based on the user's query. It can call agents multiple times or in any order. The loop continues until the Supervisor returns a `final_answer`.

### Execution Engine (Backend — TODO)
- Implement `_run_supervisor()` in `backend/orchestrator/orchestrator.py`
- Implements a "Reasoning Loop":
  1. Call the Manager Agent with the user query
  2. Manager returns JSON: `{"next_agent": "agent_id", "input": "..."}` or `{"final_answer": "..."}`
  3. If `next_agent` → call that worker, feed result back to Manager
  4. If `final_answer` → return to user
- Use LLM Tool Calling to trigger workers
- Loop has a configurable max_iterations safety limit

### Canvas Rules
- Central **Manager** node (highlighted with Crown badge)
- **Worker** nodes arranged in a circle around the Manager
- No connections between workers — all lines lead to/from the Manager
- Manager has an "Orchestration Logic" text area for routing rules

### Manager Configuration
```
Orchestration Logic (example):
- Code questions → Coder agent
- Writing tasks → Writer agent
- Data analysis → Analyst agent
- General questions → Generalist agent
```

---

## UI Components (Current Implementation)

### PipelineBuilder.jsx (`frontend/components/PipelineBuilder.jsx`)
Self-contained component with full create/edit/detail/run flow:

- **PipelineList**: Landing page with pattern filter cards, search, pipeline rows
- **PatternPicker**: Step 1 of create — three large pattern cards with visual diagrams and use case bullets
- **PipelineEditor**: Step 2 — name/description + pattern-specific agent assignment:
  - **SequentialEditor**: Vertical numbered step track with agent dropdowns, add/remove steps
  - **ParallelEditor**: Horizontal branch cards with agent dropdowns, merge strategy selector, add/remove branches
  - **SupervisorEditor**: Manager card (agent + orchestration logic textarea) + worker pool grid
- **PipelineDetail**: View pipeline config, run with animated execution trace, run history tab

### Navigation Flow
```
List → [Create Pipeline] → PatternPicker → PipelineEditor → (Save) → List
List → [Click pipeline] → PipelineDetail → [Edit] → PipelineEditor
PipelineDetail → [Run tab] → Input prompt → Animated execution trace → Results
```

### WorkflowBuilder.jsx (`frontend/components/WorkflowBuilder.jsx`)
Separate free-form n8n-style canvas for visual automations. No pipeline patterns — only unconstrained drag-and-drop.

**v2 Update:** Now uses a data-driven Node Registry (`frontend/stores/nodeRegistry.js`) with **24 node types** across 7 categories. Universal node renderer, schema-driven property panel (`NodePropertyPanel.jsx`), connection validation, and example workflow templates (RAG Q&A, Approval Chain, Integration Pipeline).

---

## Backend Implementation Plan (TODO)

### Phase 1: Data Model
- [ ] Add `PipelineType` enum to `backend/compiler/manifest.py`
- [ ] Add `WorkflowManifest` class with `nodes`, `edges`, `global_context`
- [ ] Update `backend/compiler/compiler.py` to validate pipeline structures

### Phase 2: Execution Engine
- [ ] `_run_sequential()` — recursive chain with global_state
- [ ] `_run_parallel()` — asyncio.gather with configurable error handling
- [ ] `_run_supervisor()` — reasoning loop with LLM tool calling

### Phase 3: API Routes
- [ ] `POST /execute-pipeline` — accepts pipeline config, runs the appropriate engine
- [ ] `GET /pipeline/{id}/runs` — run history
- [ ] WebSocket support for real-time execution log streaming

### Phase 4: Frontend Integration
- [ ] Replace mock execution in PipelineDetail with real API calls
- [ ] Wire agent dropdowns to real agent registry
- [ ] Add real-time log streaming via WebSocket
- [ ] Persist data mapping configs

---

## File References

| File | Purpose |
|------|---------|
| `frontend/components/PipelineBuilder.jsx` | Pipeline builder — list, pattern picker, editors, detail/run view |
| `frontend/components/WorkflowBuilder.jsx` | Free-form visual automation canvas (separate from pipelines) |
| `frontend/components/AgentStudio.jsx` | Main app shell — dynamically imports PipelinesPage |
| `docs/prd-pipelines-vs-workflows.md` | Product requirements for Pipelines vs Workflows distinction |
| `backend/orchestrator/orchestrator.py` | Execution engine (TODO: add pattern runners) |
| `backend/compiler/manifest.py` | Pipeline data model (TODO: add PipelineType enum) |
| `backend/compiler/compiler.py` | Manifest validation (TODO: pattern-specific rules) |
| `backend/llm_registry/provider_factory.py` | LLM calls (used by supervisor reasoning loop) |
