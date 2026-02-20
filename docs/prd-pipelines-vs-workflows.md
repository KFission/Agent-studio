# PRD: Pipelines vs Workflows — Product Definitions & UI Requirements

> **Status**: Draft · Feb 2026
> **Audience**: Product, Design, Engineering

---

## Corrected Direction — Summary

The **Three Orchestration Patterns** (Sequential, Parallel, Supervisor) belong exclusively in the **Pipelines tab** (`Build → Pipelines`). They were incorrectly implemented inside the Workflows canvas. This document re-derives the requirements from first principles and establishes clear product boundaries between the two features.

**Core insight**: Pipelines and Workflows solve different problems for different moments in the agent lifecycle. Conflating them creates a confusing UX where users don't know which tool to reach for.

---

## 1. Definitions

### Pipeline

> **A Pipeline is a structured, pattern-based composition of agents.**

- The user picks a **pattern** (Sequential, Parallel, or Supervisor) and then assigns agents to roles within that pattern.
- The topology is **constrained by the pattern** — the user does not draw connections manually.
- Pipelines are **agent-centric**: every node is an agent (or a system node like Splitter/Merger/Supervisor).
- Think of it as a **"no-code orchestration recipe"** — opinionated, fast to set up, easy to reason about.

**Analogy**: A Pipeline is like a meeting agenda — structured roles, defined order, clear handoffs.

### Workflow

> **A Workflow is a general-purpose visual automation built on a free-form canvas.**

- The user drags arbitrary node types (triggers, logic, HTTP calls, code blocks, agents, tools, human review) onto an n8n-style canvas and wires them together manually.
- The topology is **unconstrained** — any node can connect to any other node.
- Workflows are **automation-centric**: agents are just one of many node types alongside webhooks, conditionals, loops, API calls, and code.
- Think of it as a **"visual programming environment"** — flexible, powerful, requires more effort.

**Analogy**: A Workflow is like a Zapier/n8n automation — arbitrary steps, any integration, custom logic.

---

## 2. Decision Guidance — When to Use Which

| Dimension | Pipeline | Workflow |
|-----------|----------|----------|
| **Primary question** | "How should my agents work together?" | "How do I automate a multi-step process?" |
| **Core unit** | Agent | Any node (agent, API, code, logic, tool) |
| **Topology** | Fixed by pattern (Sequential / Parallel / Supervisor) | Free-form, user-defined |
| **Setup time** | Minutes (pick pattern → assign agents → done) | Longer (design graph, configure each node) |
| **Flexibility** | Low — intentionally constrained | High — anything goes |
| **Target persona** | AI Product Manager, Business Analyst | Automation Engineer, Developer |
| **Entry point** | Build → Pipelines | Build → Workflows |

### When to use a **Pipeline**

- "I want Agent A to classify, then Agent B to process, then Agent C to summarize." → **Sequential**
- "I want three specialist agents to analyze the same input and merge their outputs." → **Parallel**
- "I want a smart router agent to decide which specialist to call based on the query." → **Supervisor**

### When to use a **Workflow**

- "I need a webhook trigger that calls an API, runs a code transform, then sends to an agent, with a human approval gate."
- "I want conditional branching: if the agent says X, call API A; if Y, call API B."
- "I need a loop that retries an agent call until a quality threshold is met."

### Edge Cases

| Scenario | Recommendation |
|----------|---------------|
| User wants agents + one HTTP call | Start with Workflow (needs non-agent nodes) |
| User wants 2 agents in sequence | Pipeline (simpler); Workflow also works but overkill |
| User wants a supervisor that also calls APIs | Start as Pipeline; if it outgrows the pattern, migrate to Workflow |
| User wants to test different agent combos quickly | Pipeline (fast iteration on agent assignments) |

---

## 3. Personas & Roles

| Persona | Role | Primary Use |
|---------|------|------------|
| **AI Product Manager** | Defines agent orchestration strategies | Creates and iterates on Pipelines |
| **Business Analyst** | Sets up agent chains for specific business processes | Creates Pipelines, monitors runs |
| **Automation Engineer** | Builds complex multi-step automations | Creates Workflows with logic, APIs, code |
| **Platform Admin** | Manages and monitors all automations | Views run history, manages permissions |

---

## 4. Information Architecture — Pipelines Tab

### Navigation Path
`Sidebar → Build → Pipelines`

### Page Structure

```
Pipelines Tab
├── Pipeline List (default view)
│   ├── Header: "Pipelines" title + "Create Pipeline" CTA
│   ├── Pattern Picker Cards (Sequential / Parallel / Supervisor) — act as filters AND creation entry points
│   ├── Search + filter bar
│   └── Pipeline list (table/cards)
│
├── Pipeline Builder (entered via Create or Edit)
│   ├── Step 1: Pattern Selection (if creating new)
│   │   └── Full-page pattern chooser with visual diagrams
│   ├── Step 2: Agent Assignment
│   │   ├── Pattern-specific layout showing slots
│   │   ├── Agent picker for each slot (dropdown or drag from sidebar)
│   │   └── Pattern-specific config:
│   │       ├── Sequential: data mapping between steps
│   │       ├── Parallel: merge strategy selector
│   │       └── Supervisor: orchestration logic text area
│   └── Step 3: Review & Save
│       ├── Visual preview of the pipeline
│       ├── Name, description fields
│       └── Save / Run / API snippet
│
├── Pipeline Detail / Run View (entered via clicking a pipeline)
│   ├── Config summary
│   ├── Run button + run history
│   └── Execution logs with step-by-step trace
│
└── Empty State
    └── Illustration + "Create your first pipeline" with pattern quick-start buttons
```

---

## 5. Key User Flows

### Flow 1: Create a New Pipeline

```
1. User clicks "Create Pipeline" button (or clicks a pattern card)
2. → Pattern Selection screen
   - Three large cards: Sequential / Parallel / Supervisor
   - Each shows: icon, name, one-line description, animated diagram
   - User clicks one
3. → Agent Assignment screen
   - Canvas shows the selected pattern's topology (read-only structure)
   - Empty slots where agents go (e.g., "Step 1", "Step 2", "Step 3")
   - User assigns agents to each slot via dropdown or drag
   - Optional: Configure data mapping (Sequential), merge strategy (Parallel), routing logic (Supervisor)
4. → User enters pipeline name and description
5. → User clicks Save
6. → Redirected back to Pipeline list (new pipeline appears)
```

### Flow 2: Edit an Existing Pipeline

```
1. User clicks a pipeline row in the list
2. → Pipeline Detail page shows current config
3. User clicks "Edit"
4. → Agent Assignment screen (pre-filled with current agents)
5. User can change agents, re-order (Sequential), add/remove parallel tracks, etc.
6. → Save
```

### Flow 3: Run a Pipeline

```
1. User clicks "Run" on a pipeline (from list or detail page)
2. → Input modal appears (user provides the initial prompt/input)
3. → Execution starts; live progress shown:
   - Sequential: steps light up one by one
   - Parallel: all branches animate simultaneously, then merger lights up
   - Supervisor: manager node pulses, worker nodes light up as called
4. → Execution completes; results shown inline
5. → Run is saved to run history
```

### Flow 4: View Run History

```
1. User opens a pipeline's detail page
2. → "Runs" tab shows past executions
3. Each run shows: timestamp, input, status, duration, output
4. Clicking a run expands it to show step-by-step trace with per-node input/output
```

---

## 6. Screen-by-Screen Requirements

### Screen A: Pipeline List

| Element | Spec |
|---------|------|
| **Header** | Title "Pipelines", subtitle "Compose agents into structured execution patterns" |
| **CTA** | "Create Pipeline" button (primary brand color) |
| **Pattern cards** | 3 cards in a row (Sequential / Parallel / Supervisor). Click = filter list by that pattern. Click active = clear filter. Each shows: icon/emoji, label, one-line desc, count of pipelines using that pattern |
| **Search bar** | Filters by pipeline name |
| **Pipeline rows** | Each row: pattern icon, name, ID (mono), pattern badge, step count, last run timestamp, Run button, kebab menu (Edit, Duplicate, Delete, API) |
| **Empty state** | Illustration + "No pipelines yet" + "Create your first pipeline" link |
| **Loading state** | Skeleton rows |
| **Error state** | Retry banner |

### Screen B: Pattern Selection (Create — Step 1)

| Element | Spec |
|---------|------|
| **Layout** | Full-content area, centered, max-width 800px |
| **Back button** | Returns to Pipeline list |
| **Title** | "Choose an orchestration pattern" |
| **Cards** | Three large cards (min-height 200px each), arranged in a row or stacked on mobile |
| **Card contents** | Pattern icon (large), name, 2-line description, small animated/static diagram showing the topology, "Select" button |
| **Sequential card** | Shows: Input → Agent → Agent → Agent → Output linear diagram |
| **Parallel card** | Shows: Input → [3 branches] → Merge → Output fork diagram |
| **Supervisor card** | Shows: Central node + 4 surrounding nodes hub diagram |

### Screen C: Agent Assignment (Create/Edit — Step 2)

This screen is **pattern-specific**:

#### Sequential Layout
| Element | Spec |
|---------|------|
| **Visual** | Vertical track with numbered slots (Step 0: Input, Step 1-N: Agent slots, Final: Output) |
| **Each slot** | Agent dropdown (searchable, shows agent name + model), "Configure" link for data mapping |
| **Add step** | "+ Add Step" button between any two steps to insert another agent |
| **Remove step** | "×" on each agent step (min 1 agent required) |
| **Data mapping** | Clicking "Configure" on an arrow/link opens a side panel: map `{{prev_step.output_field}}` → `{{this_step.input_var}}` |
| **Validation** | At least 1 agent assigned. No empty slots allowed at save time. |

#### Parallel Layout
| Element | Spec |
|---------|------|
| **Visual** | Input at top → Splitter → N horizontal agent cards → Merger → Output at bottom |
| **Each branch** | Agent dropdown, optional label |
| **Add branch** | "+ Add Branch" button adds another parallel agent card |
| **Remove branch** | "×" on each branch (min 2 branches required) |
| **Merger config** | Dropdown on Merger node: "Raw Merge (JSON object)" or "Summary (use a final agent)" |
| **If Summary** | An additional agent dropdown appears for the summarizer |
| **Validation** | At least 2 parallel agents. Merge strategy selected. |

#### Supervisor Layout
| Element | Spec |
|---------|------|
| **Visual** | Central Manager card, Worker cards in a circle/grid around it |
| **Manager** | Agent dropdown + "Orchestration Logic" textarea (routing rules in plain text) |
| **Worker pool** | List of agent dropdowns. Each has a "Role label" text input (e.g., "Coder", "Writer") |
| **Add worker** | "+ Add Worker" button |
| **Remove worker** | "×" on each worker (min 1 worker required) |
| **Validation** | Manager agent assigned. At least 1 worker. Orchestration logic not empty. |

### Screen D: Pipeline Detail / Run View

| Element | Spec |
|---------|------|
| **Header** | Pipeline name, pattern badge, edit button, run button |
| **Config section** | Read-only view of the pipeline structure (agents, pattern, mapping) |
| **Tabs** | "Overview" (config), "Runs" (history), "API" (snippet) |
| **Run panel** | Input textarea + "Run Pipeline" button. Results appear below with animated step-by-step trace. |
| **Run history** | Table: run ID, timestamp, status (success/failed/running), duration, input preview. Expandable rows show per-step trace. |

---

## 7. Acceptance Criteria

### Pipeline List
- [ ] User sees all pipelines with pattern filter cards
- [ ] Clicking a pattern card filters the list; clicking again clears
- [ ] Search filters by name in real-time
- [ ] "Create Pipeline" button navigates to pattern selection
- [ ] Empty state shown when no pipelines exist
- [ ] Each pipeline row shows pattern icon, name, step count, and has a Run button

### Pattern Selection
- [ ] Three pattern cards displayed with clear visual distinction
- [ ] Clicking a card advances to Agent Assignment with the selected pattern
- [ ] Back button returns to Pipeline list without side effects

### Agent Assignment
- [ ] Sequential: vertical step list, add/remove steps, data mapping config
- [ ] Parallel: horizontal branch layout, add/remove branches, merge strategy dropdown
- [ ] Supervisor: central manager + worker pool, orchestration logic textarea
- [ ] Agent dropdowns populated from the platform's agent registry
- [ ] Validation prevents saving with empty required fields
- [ ] Save creates the pipeline and returns to the list

### Pipeline Execution
- [ ] Run button opens input prompt
- [ ] Execution shows live step-by-step progress (animated)
- [ ] Sequential: steps light up in order
- [ ] Parallel: branches animate simultaneously, then merger
- [ ] Supervisor: manager pulses, workers light up as called
- [ ] Completed run shows full output and per-step trace
- [ ] Run is recorded in history

### Pipeline vs Workflow Separation
- [ ] Pipelines tab has NO free-form canvas or arbitrary node types
- [ ] Workflows tab has NO pattern selector or constrained topologies
- [ ] Both are separate sidebar nav items under "Build"
- [ ] Data model distinguishes pipelines from workflows

---

## 8. What Changes Are Needed (Current → Target)

### Current State (Broken)
| Item | Location | Issue |
|------|----------|-------|
| Pattern mode switcher | WorkflowBuilder.jsx toolbar | **Wrong location** — should be in Pipelines, not Workflows |
| `generateTemplate()` | WorkflowBuilder.jsx | Generates pattern templates on the Workflow canvas |
| `DataMappingModal` | WorkflowBuilder.jsx | Correct concept, wrong page |
| `ExecutionLogsPanel` | WorkflowBuilder.jsx | Useful for both, but pipeline-specific execution logs should live in Pipelines |
| `OrchestratorPage` | AgentStudio.jsx | Only a listing page — no builder, no execution, "Create Pipeline" button is a no-op |

### Target State
| Item | Location | Purpose |
|------|----------|---------|
| Pattern mode switcher | Remove from WorkflowBuilder | Workflows are always free-form |
| Pattern Selection screen | New: Pipelines tab (step 1 of create flow) | User picks Sequential/Parallel/Supervisor |
| Agent Assignment screen | New: Pipelines tab (step 2 of create flow) | Pattern-specific slot-based agent assignment |
| Data Mapping | Pipelines tab (Sequential config) | Map outputs → inputs between steps |
| Merge Strategy | Pipelines tab (Parallel config) | Configure how parallel results combine |
| Orchestration Logic | Pipelines tab (Supervisor config) | Define routing rules for manager |
| Execution + Logs | Pipelines tab (Run view) | Animated execution with step trace |
| `OrchestratorPage` | AgentStudio.jsx | Expanded to full Pipeline builder with list → create → detail → run flow |
| WorkflowBuilder.jsx | Keep as-is (minus pattern code) | Free-form visual automation canvas |

---

## Appendix: Visual Quick Reference

```
┌─────────────────────────────────────────────────────┐
│                    PIPELINES                         │
│                                                      │
│  "How should my agents collaborate?"                 │
│                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐  │
│  │ Sequential  │ │  Parallel   │ │  Supervisor   │  │
│  │  A → B → C  │ │  ⇉ fork &   │ │  ⊛ hub &     │  │
│  │             │ │    merge    │ │    spoke      │  │
│  └─────────────┘ └─────────────┘ └──────────────┘  │
│                                                      │
│  • Agent-only nodes                                  │
│  • Fixed topology per pattern                        │
│  • Fast setup (minutes)                              │
│  • Slot-based assignment, no free-form canvas        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                    WORKFLOWS                         │
│                                                      │
│  "How do I automate a complex multi-step process?"   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Free-form ReactFlow canvas                   │   │
│  │  Triggers + Logic + APIs + Agents + Tools     │   │
│  │  Any-to-any connections                       │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  • Any node type (webhook, code, API, agent, ...)    │
│  • Unconstrained topology                            │
│  • Powerful but more setup effort                    │
│  • Full n8n-style canvas builder                     │
└─────────────────────────────────────────────────────┘
```
