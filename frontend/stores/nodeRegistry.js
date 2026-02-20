// ═══════════════════════════════════════════════════════════════════
// NODE REGISTRY — Data-driven definitions for all 24 workflow node types
// Each node type defines: meta, schema fields, defaults, validation, handles
// ═══════════════════════════════════════════════════════════════════

// ── Shared Sub-Schemas ──────────────────────────────────────────
export const RETRY_POLICY_SCHEMA = [
  { key: "maxAttempts", label: "Max Attempts", type: "number", default: 3, min: 1, max: 20 },
  { key: "backoffMode", label: "Backoff Mode", type: "enum", options: ["fixed", "exponential"], default: "exponential" },
  { key: "baseDelayMs", label: "Base Delay (ms)", type: "number", default: 1000, min: 100 },
  { key: "maxDelayMs", label: "Max Delay (ms)", type: "number", default: 30000, min: 1000 },
  { key: "retryOn", label: "Retry On (codes/types)", type: "tags", default: ["5xx", "timeout"] },
  { key: "jitter", label: "Add Jitter", type: "boolean", default: true },
];

// ── Field type definitions ──────────────────────────────────────
// type: text | number | boolean | enum | code | json | tags | textarea
//       keyvalue | mapping | array | retryPolicy | datetime | range
// advanced: true → show in Advanced accordion

// ── Categories ──────────────────────────────────────────────────
export const NODE_CATEGORIES = [
  { id: "triggers", label: "Start & Triggers", color: "#10b981" },
  { id: "control", label: "Control Flow", color: "#f59e0b" },
  { id: "data", label: "Data & Transformation", color: "#3b82f6" },
  { id: "integrations", label: "Integrations", color: "#8b5cf6" },
  { id: "ai", label: "AI", color: "#e11d48" },
  { id: "human", label: "Human & Tickets", color: "#d97706" },
  { id: "output", label: "Output & Observability", color: "#64748b" },
];

// ── Handle Definitions ──────────────────────────────────────────
// inputHandles: array of { id, label }  — empty for triggers
// outputHandles: array of { id, label, color? } — branching nodes have multiple
const IN = [{ id: "in", label: "In" }];
const OUT = [{ id: "out", label: "Out" }];

// ═══════════════════════════════════════════════════════════════════
// NODE TYPE REGISTRY
// ═══════════════════════════════════════════════════════════════════

const REGISTRY = {

  // ── A) START & TRIGGERS ───────────────────────────────────────

  startInput: {
    type: "startInput",
    label: "Start / Input",
    icon: "PlayCircle",
    category: "triggers",
    color: "#10b981",
    desc: "Define workflow input schema and initial variables",
    inputHandles: [],
    outputHandles: OUT,
    fields: [
      { key: "inputSchema", label: "Input Schema", type: "json", default: '{\n  "query": { "type": "string" }\n}', desc: "JSON Schema for workflow input", rows: 5 },
      { key: "requiredFields", label: "Required Fields", type: "tags", default: ["query"], desc: "Fields that must be present" },
      { key: "defaultValues", label: "Default Values", type: "json", default: "{}", desc: "Default input values", rows: 3 },
      { key: "sampleInput", label: "Sample Input", type: "json", default: '{\n  "query": "Analyze recent spend"\n}', desc: "Sample payload for testing", rows: 4 },
      { key: "validationMode", label: "Validation Mode", type: "enum", options: ["strict", "lenient"], default: "strict" },
      { key: "initVars", label: "Initialize Variables", type: "json", default: "{}", desc: "Variables to initialize in context", advanced: true, rows: 3 },
      { key: "rbacContext", label: "RBAC Context", type: "enum", options: ["buyer", "supplier", "auto"], default: "auto", advanced: true },
      { key: "appContext", label: "App Context", type: "enum", options: ["JI", "JA", "JD", "auto"], default: "auto", advanced: true },
      { key: "locale", label: "Locale", type: "text", default: "en-US", advanced: true },
      { key: "runMode", label: "Run Mode", type: "enum", options: ["test", "prod"], default: "test", advanced: true },
    ],
    mockOutput: { input: { query: "Analyze recent spend data" }, vars: {}, runMode: "test" },
  },

  webhookTrigger: {
    type: "webhookTrigger",
    label: "Webhook Trigger",
    icon: "Globe",
    category: "triggers",
    color: "#10b981",
    desc: "Receive HTTP webhook calls to start workflow",
    inputHandles: [],
    outputHandles: OUT,
    fields: [
      { key: "path", label: "Webhook Path", type: "text", default: "/webhook", desc: "URL path for the webhook", required: true },
      { key: "methods", label: "HTTP Methods", type: "tags", default: ["POST"], desc: "Allowed methods", options: ["GET", "POST", "PUT", "PATCH"] },
      { key: "authType", label: "Auth Type", type: "enum", options: ["none", "apiKey", "oauth2", "jwt", "hmac"], default: "none" },
      { key: "secretRef", label: "Secret Reference", type: "text", default: "", desc: "Reference to stored secret (never store raw)" },
      { key: "requestSchema", label: "Request Schema", type: "json", default: "{}", desc: "Expected request body schema", rows: 4 },
      { key: "rateLimitRpm", label: "Rate Limit (RPM)", type: "number", default: 100, min: 1, advanced: true },
      { key: "ipAllowlist", label: "IP Allowlist (CIDR)", type: "tags", default: [], advanced: true },
      { key: "responseMode", label: "Response Mode", type: "enum", options: ["ackImmediately", "waitForResult"], default: "ackImmediately", advanced: true },
      { key: "replayProtection", label: "Replay Protection", type: "boolean", default: false, advanced: true },
      { key: "mapping", label: "Request Mapping", type: "json", default: "{}", desc: "Map headers/body to input fields", advanced: true, rows: 3 },
    ],
    mockOutput: { body: { id: 123, type: "purchase_request", amount: 5000 }, headers: { "content-type": "application/json" } },
  },

  scheduleTrigger: {
    type: "scheduleTrigger",
    label: "Schedule Trigger",
    icon: "CalendarClock",
    category: "triggers",
    color: "#10b981",
    desc: "Run workflow on a cron schedule or interval",
    inputHandles: [],
    outputHandles: OUT,
    fields: [
      { key: "scheduleMode", label: "Schedule Mode", type: "enum", options: ["cron", "interval"], default: "cron" },
      { key: "cron", label: "Cron Expression", type: "text", default: "0 9 * * 1-5", desc: 'e.g. "0 9 * * 1-5" = weekdays at 9am', showWhen: { scheduleMode: "cron" } },
      { key: "intervalMinutes", label: "Interval (minutes)", type: "number", default: 60, min: 1, showWhen: { scheduleMode: "interval" } },
      { key: "timezone", label: "Timezone", type: "text", default: "UTC" },
      { key: "startAt", label: "Start At", type: "datetime", default: "" },
      { key: "endAt", label: "End At", type: "datetime", default: "", advanced: true },
      { key: "runWindow", label: "Run Window", type: "enum", options: ["anytime", "businessHours"], default: "anytime", advanced: true },
      { key: "concurrencyPolicy", label: "Concurrency Policy", type: "enum", options: ["skip", "queue", "latestOnly"], default: "skip", advanced: true },
      { key: "retryPolicy", label: "Retry Policy", type: "retryPolicy", default: {}, advanced: true },
      { key: "enabled", label: "Enabled", type: "boolean", default: true },
    ],
    mockOutput: { triggered_at: new Date().toISOString(), schedule: "0 9 * * 1-5" },
  },

  // ── B) CONTROL FLOW ───────────────────────────────────────────

  ifCondition: {
    type: "ifCondition",
    label: "If / Condition",
    icon: "GitBranch",
    category: "control",
    color: "#f59e0b",
    desc: "Branch workflow based on a condition (true/false)",
    inputHandles: IN,
    outputHandles: [
      { id: "true", label: "True", color: "#10b981" },
      { id: "false", label: "False", color: "#ef4444" },
    ],
    fields: [
      { key: "mode", label: "Mode", type: "enum", options: ["builder", "expression"], default: "builder" },
      { key: "conditions", label: "Conditions", type: "json", default: '[{"left": "{{vars.amount}}", "operator": ">", "right": "1000"}]', desc: "Array of {left, operator, right}", showWhen: { mode: "builder" }, rows: 4 },
      { key: "expression", label: "Expression", type: "text", default: "", desc: "JavaScript expression", showWhen: { mode: "expression" } },
      { key: "nullHandling", label: "Null Handling", type: "enum", options: ["false", "error", "coalesceEmpty"], default: "false" },
      { key: "typeCoercion", label: "Type Coercion", type: "boolean", default: true },
      { key: "caseSensitive", label: "Case Sensitive", type: "boolean", default: false, advanced: true },
      { key: "trueLabel", label: "True Label", type: "text", default: "Yes", advanced: true },
      { key: "falseLabel", label: "False Label", type: "text", default: "No", advanced: true },
      { key: "onInvalidCondition", label: "On Invalid Condition", type: "enum", options: ["error", "treatAsFalse"], default: "treatAsFalse", advanced: true },
      { key: "debugSample", label: "Debug Sample", type: "json", default: "", desc: "Test with this sample input", advanced: true, rows: 3 },
    ],
    mockOutput: { branch: "true", condition_met: true },
  },

  switchRoute: {
    type: "switchRoute",
    label: "Switch / Route",
    icon: "Shuffle",
    category: "control",
    color: "#f59e0b",
    desc: "Multi-way branch based on a value",
    inputHandles: IN,
    outputHandles: [
      { id: "case:0", label: "Case 1", color: "#3b82f6" },
      { id: "case:1", label: "Case 2", color: "#8b5cf6" },
      { id: "default", label: "Default", color: "#94a3b8" },
    ],
    dynamicOutputs: true,
    fields: [
      { key: "routeBy", label: "Route By", type: "text", default: "{{vars.category}}", desc: "Expression/path to switch on", required: true },
      { key: "cases", label: "Cases", type: "json", default: '[\n  {"matchType": "equals", "matchValue": "electronics", "label": "Electronics"},\n  {"matchType": "equals", "matchValue": "furniture", "label": "Furniture"}\n]', rows: 6, desc: "Array of {matchType, matchValue, label}" },
      { key: "matchType", label: "Default Match Type", type: "enum", options: ["equals", "contains", "regex", "in"], default: "equals" },
      { key: "firstMatchOnly", label: "First Match Only", type: "boolean", default: true },
      { key: "defaultBranchLabel", label: "Default Branch Label", type: "text", default: "Other" },
      { key: "unmatchedBehavior", label: "Unmatched Behavior", type: "enum", options: ["default", "error"], default: "default" },
      { key: "maxBranches", label: "Max Branches", type: "number", default: 10, min: 2, max: 20, advanced: true },
      { key: "debugSample", label: "Debug Sample", type: "json", default: "", advanced: true, rows: 3 },
      { key: "telemetryTags", label: "Telemetry Tags", type: "keyvalue", default: {}, advanced: true },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { matched_case: "electronics", value: "electronics" },
  },

  loopMap: {
    type: "loopMap",
    label: "Loop / Map",
    icon: "Repeat",
    category: "control",
    color: "#f59e0b",
    desc: "Iterate over a collection, executing a sub-flow per item",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "collectionPath", label: "Collection Path", type: "text", default: "{{vars.items}}", desc: "Path to iterable array", required: true },
      { key: "itemVar", label: "Item Variable", type: "text", default: "item" },
      { key: "indexVar", label: "Index Variable", type: "text", default: "index" },
      { key: "concurrency", label: "Concurrency", type: "enum", options: ["sequential", "parallel"], default: "sequential" },
      { key: "maxParallel", label: "Max Parallel", type: "number", default: 5, min: 1, showWhen: { concurrency: "parallel" } },
      { key: "batchSize", label: "Batch Size", type: "number", default: 0, desc: "0 = no batching", advanced: true },
      { key: "onItemError", label: "On Item Error", type: "enum", options: ["fail", "skip", "retry"], default: "skip" },
      { key: "timeoutPerItemMs", label: "Timeout per Item (ms)", type: "number", default: 30000, advanced: true },
      { key: "maxIterations", label: "Max Iterations", type: "number", default: 1000, advanced: true },
      { key: "aggregateResults", label: "Aggregate Results", type: "boolean", default: true },
    ],
    mockOutput: { iteration: 1, items_processed: 5, results: [] },
  },

  parallelFork: {
    type: "parallelFork",
    label: "Parallel Fork",
    icon: "GitFork",
    category: "control",
    color: "#f59e0b",
    desc: "Execute multiple branches in parallel",
    inputHandles: IN,
    outputHandles: [
      { id: "branch:0", label: "Branch 1", color: "#3b82f6" },
      { id: "branch:1", label: "Branch 2", color: "#8b5cf6" },
    ],
    dynamicOutputs: true,
    fields: [
      { key: "branchCount", label: "Branch Count", type: "number", default: 2, min: 2, max: 10 },
      { key: "branchNames", label: "Branch Names", type: "tags", default: ["Branch 1", "Branch 2"] },
      { key: "inputMappingPerBranch", label: "Input Mapping (per branch)", type: "json", default: "{}", rows: 4, advanced: true },
      { key: "maxParallel", label: "Max Parallel", type: "number", default: 10, advanced: true },
      { key: "onBranchFailure", label: "On Branch Failure", type: "enum", options: ["failAll", "continuePartial"], default: "failAll" },
      { key: "timeoutPerBranchMs", label: "Timeout per Branch (ms)", type: "number", default: 60000, advanced: true },
      { key: "cancelBehavior", label: "Cancel Behavior", type: "enum", options: ["cancelAll", "cancelFailedOnly", "none"], default: "cancelAll", advanced: true },
      { key: "requiredBranches", label: "Required Branches", type: "tags", default: [], advanced: true },
      { key: "telemetryTags", label: "Telemetry Tags", type: "keyvalue", default: {}, advanced: true },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { branches_started: 2, all_completed: true },
  },

  joinMerge: {
    type: "joinMerge",
    label: "Join / Merge",
    icon: "Merge",
    category: "control",
    color: "#f59e0b",
    desc: "Wait for and merge multiple parallel branches",
    inputHandles: [
      { id: "in:0", label: "In 1" },
      { id: "in:1", label: "In 2" },
    ],
    multiInput: true,
    outputHandles: OUT,
    fields: [
      { key: "joinType", label: "Join Type", type: "enum", options: ["waitAll", "waitAny", "majority"], default: "waitAll" },
      { key: "mergeStrategy", label: "Merge Strategy", type: "enum", options: ["deepMerge", "overwrite", "appendLists"], default: "deepMerge" },
      { key: "conflictResolution", label: "Conflict Resolution", type: "enum", options: ["preferLeft", "preferRight", "preferLatest"], default: "preferLatest" },
      { key: "timeoutMs", label: "Timeout (ms)", type: "number", default: 120000 },
      { key: "missingBranchBehavior", label: "Missing Branch", type: "enum", options: ["error", "skip", "useDefault"], default: "error" },
      { key: "defaultBranchValues", label: "Default Branch Values", type: "json", default: "{}", advanced: true, rows: 3 },
      { key: "outputShape", label: "Output Shape Hint", type: "json", default: "{}", advanced: true, rows: 3 },
      { key: "preserveBranchOutputs", label: "Preserve Branch Outputs", type: "boolean", default: false, advanced: true },
      { key: "telemetryTags", label: "Telemetry Tags", type: "keyvalue", default: {}, advanced: true },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { merged: true, sources: 2, strategy: "deepMerge" },
  },

  delayWait: {
    type: "delayWait",
    label: "Delay / Wait",
    icon: "Clock",
    category: "control",
    color: "#f59e0b",
    desc: "Pause execution for a duration or until a time",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "waitMode", label: "Wait Mode", type: "enum", options: ["duration", "untilTime"], default: "duration" },
      { key: "durationMs", label: "Duration (ms)", type: "number", default: 5000, min: 100, showWhen: { waitMode: "duration" } },
      { key: "untilTime", label: "Until Time", type: "datetime", default: "", showWhen: { waitMode: "untilTime" } },
      { key: "timezone", label: "Timezone", type: "text", default: "UTC" },
      { key: "businessHoursOnly", label: "Business Hours Only", type: "boolean", default: false },
      { key: "cancelCondition", label: "Cancel Condition", type: "text", default: "", desc: "Optional expression to cancel wait", advanced: true },
      { key: "maxWaitMs", label: "Max Wait (ms)", type: "number", default: 3600000, advanced: true },
      { key: "jitterMs", label: "Jitter (ms)", type: "number", default: 0, advanced: true },
      { key: "resumeNotify", label: "Notify on Resume", type: "boolean", default: false, advanced: true },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { waited_ms: 5000, resumed_at: new Date().toISOString() },
  },

  tryCatch: {
    type: "tryCatch",
    label: "Try / Catch",
    icon: "ShieldAlert",
    category: "control",
    color: "#f59e0b",
    desc: "Error boundary — catch and handle errors",
    inputHandles: IN,
    outputHandles: [
      { id: "try", label: "Try (success)", color: "#10b981" },
      { id: "catch", label: "Catch (error)", color: "#ef4444" },
    ],
    fields: [
      { key: "scope", label: "Scope", type: "enum", options: ["nodeOnly", "downstreamBlock"], default: "nodeOnly" },
      { key: "catchMode", label: "Catch Mode", type: "enum", options: ["any", "byStatus", "byType"], default: "any" },
      { key: "catchRules", label: "Catch Rules", type: "json", default: "[]", desc: "Rules for byStatus/byType modes", rows: 3 },
      { key: "storeErrorAs", label: "Store Error As", type: "text", default: "vars.error" },
      { key: "onCaughtError", label: "On Caught Error", type: "enum", options: ["continue", "stop"], default: "continue" },
      { key: "retryPolicy", label: "Retry Policy", type: "retryPolicy", default: {}, advanced: true },
      { key: "notifyOnCatch", label: "Notify on Catch", type: "boolean", default: false, advanced: true },
      { key: "redactionMode", label: "Redaction Mode", type: "enum", options: ["standard", "strict"], default: "standard", advanced: true },
      { key: "metricsCategory", label: "Metrics Category", type: "text", default: "", advanced: true },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { caught: false, status: "success" },
  },

  // ── C) DATA & TRANSFORMATION ─────────────────────────────────

  transform: {
    type: "transform",
    label: "Transform",
    icon: "ArrowRightLeft",
    category: "data",
    color: "#3b82f6",
    desc: "No-code data mapping and transformation",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "mappings", label: "Mappings", type: "json", default: '[\n  {"fromPath": "input.name", "toPath": "output.fullName", "transform": "none"}\n]', desc: "Array of {fromPath, toPath, transform}", rows: 5, required: true },
      { key: "renameRules", label: "Rename Rules", type: "json", default: "[]", rows: 2, advanced: true },
      { key: "dropFields", label: "Drop Fields", type: "tags", default: [] },
      { key: "templates", label: "Templates", type: "json", default: "[]", desc: "Array of {toPath, templateString}", rows: 3, advanced: true },
      { key: "typeConversions", label: "Type Conversions", type: "json", default: "[]", advanced: true, rows: 2 },
      { key: "coalesceDefaults", label: "Coalesce Defaults", type: "json", default: "{}", advanced: true, rows: 2 },
      { key: "expressionMode", label: "Expression Mode", type: "enum", options: ["off", "basic"], default: "off", advanced: true },
      { key: "outputPreviewEnabled", label: "Preview Output", type: "boolean", default: true },
      { key: "outputSchemaHint", label: "Output Schema Hint", type: "json", default: "{}", advanced: true, rows: 3 },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { transformed: true, output: { fullName: "Processed Result" } },
  },

  script: {
    type: "script",
    label: "Script",
    icon: "Code2",
    category: "data",
    color: "#3b82f6",
    desc: "Run custom JavaScript or Python code",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "language", label: "Language", type: "enum", options: ["javascript", "python"], default: "javascript" },
      { key: "code", label: "Code", type: "code", default: '// Access context via `input` variable\nconst result = {\n  processed: true,\n  value: input.query?.toUpperCase()\n};\nreturn result;', rows: 12 },
      { key: "inputBindings", label: "Available Inputs", type: "json", default: "{}", desc: "Read-only: variables available to script", readonly: true, rows: 3 },
      { key: "returnContract", label: "Return Type", type: "enum", options: ["object", "string", "json"], default: "object" },
      { key: "timeoutMs", label: "Timeout (ms)", type: "number", default: 10000, min: 1000 },
      { key: "resourceProfile", label: "Resource Profile", type: "enum", options: ["light", "standard"], default: "light", advanced: true },
      { key: "packagesAllowlist", label: "Packages Allowlist", type: "tags", default: [], advanced: true },
      { key: "secretsAccess", label: "Secrets Access", type: "tags", default: [], desc: "Secret references (refs only)", advanced: true },
      { key: "logLevel", label: "Log Level", type: "enum", options: ["error", "warn", "info", "debug"], default: "info", advanced: true },
      { key: "testSampleInput", label: "Test Sample Input", type: "json", default: "", desc: "Defaults to Start node sample", advanced: true, rows: 3 },
    ],
    mockOutput: { result: { processed: true, value: "ANALYZE RECENT SPEND" } },
  },

  validate: {
    type: "validate",
    label: "Validate",
    icon: "ShieldCheck",
    category: "data",
    color: "#3b82f6",
    desc: "Validate data against a JSON schema",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "schema", label: "JSON Schema", type: "json", default: '{\n  "type": "object",\n  "required": ["query"]\n}', rows: 6, required: true },
      { key: "requiredFields", label: "Required Fields", type: "tags", default: [] },
      { key: "strictMode", label: "Strict Mode", type: "boolean", default: false },
      { key: "errorMessageMode", label: "Error Messages", type: "enum", options: ["detailed", "userFriendly"], default: "detailed" },
      { key: "onFail", label: "On Fail", type: "enum", options: ["stop", "routeToBranch"], default: "stop" },
      { key: "coerceTypes", label: "Coerce Types", type: "boolean", default: false, advanced: true },
      { key: "constraints", label: "Constraints", type: "json", default: "{}", desc: "min/max/length constraints", advanced: true, rows: 3 },
      { key: "piiChecks", label: "PII Checks", type: "boolean", default: false, advanced: true },
      { key: "debugSample", label: "Debug Sample", type: "json", default: "", advanced: true, rows: 3 },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { valid: true, errors: [] },
  },

  // ── D) INTEGRATIONS ───────────────────────────────────────────

  httpRequest: {
    type: "httpRequest",
    label: "HTTP Request",
    icon: "Globe",
    category: "integrations",
    color: "#8b5cf6",
    desc: "Make an HTTP request to any REST API",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "method", label: "Method", type: "enum", options: ["GET", "POST", "PUT", "PATCH", "DELETE"], default: "GET", required: true },
      { key: "url", label: "URL", type: "text", default: "", placeholder: "https://api.example.com/data", required: true, templated: true },
      { key: "queryParams", label: "Query Parameters", type: "keyvalue", default: {} },
      { key: "headers", label: "Headers", type: "keyvalue", default: {}, templated: true },
      { key: "authType", label: "Auth Type", type: "enum", options: ["none", "apiKey", "bearer", "oauth2", "mtls"], default: "none" },
      { key: "credentialRef", label: "Credential Reference", type: "text", default: "", showWhen: { authType: ["apiKey", "bearer", "oauth2", "mtls"] } },
      { key: "bodyMode", label: "Body Mode", type: "enum", options: ["none", "json", "form", "multipart"], default: "none" },
      { key: "body", label: "Body", type: "json", default: "", rows: 4, showWhen: { bodyMode: ["json", "form", "multipart"] }, templated: true },
      { key: "timeoutMs", label: "Timeout (ms)", type: "number", default: 30000, advanced: true },
      { key: "retryPolicy", label: "Retry Policy", type: "retryPolicy", default: {}, advanced: true },
      { key: "responseMapping", label: "Response Mapping", type: "json", default: "{}", desc: "Map response fields to vars", advanced: true, rows: 3 },
    ],
    mockOutput: { status: 200, data: { results: [{ id: 1, name: "Item A" }] } },
  },

  connectorAction: {
    type: "connectorAction",
    label: "Connector Action",
    icon: "Plug",
    category: "integrations",
    color: "#8b5cf6",
    desc: "Invoke a platform connector/tool action",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "connector", label: "Connector", type: "enum", options: ["SAP Ariba", "Coupa", "Salesforce", "ServiceNow", "Jira", "Custom"], default: "", required: true },
      { key: "action", label: "Action", type: "text", default: "", desc: "Action name (populated by connector)", required: true },
      { key: "inputs", label: "Input Mapping", type: "json", default: "{}", rows: 4 },
      { key: "outputMapping", label: "Output Mapping", type: "json", default: "{}", rows: 3 },
      { key: "credentialRef", label: "Credential", type: "text", default: "" },
      { key: "pagination", label: "Pagination", type: "json", default: '{"mode": "none", "pageSize": 50, "maxPages": 10}', advanced: true, rows: 2 },
      { key: "rateLimitHandling", label: "Rate Limit Handling", type: "enum", options: ["auto", "fail", "backoff"], default: "auto", advanced: true },
      { key: "timeoutMs", label: "Timeout (ms)", type: "number", default: 30000, advanced: true },
      { key: "retryPolicy", label: "Retry Policy", type: "retryPolicy", default: {}, advanced: true },
      { key: "audit", label: "Audit Trail", type: "boolean", default: true, advanced: true },
    ],
    mockOutput: { result: "Action executed", status: "ok", records: 12 },
  },

  notify: {
    type: "notify",
    label: "Notify",
    icon: "Bell",
    category: "integrations",
    color: "#8b5cf6",
    desc: "Send notifications via Teams, Slack, Email, or webhook",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "channelType", label: "Channel", type: "enum", options: ["teams", "slack", "email", "webhook", "inApp"], default: "email", required: true },
      { key: "recipients", label: "Recipients", type: "tags", default: [], desc: "Users, groups, or roles" },
      { key: "messageTemplate", label: "Message Template", type: "textarea", default: "Workflow notification: {{vars.summary}}", rows: 4, templated: true },
      { key: "severity", label: "Severity", type: "enum", options: ["info", "warning", "critical"], default: "info" },
      { key: "attachments", label: "Attachments", type: "enum", options: ["none", "allow"], default: "none", advanced: true },
      { key: "threadingKey", label: "Threading Key", type: "text", default: "", advanced: true },
      { key: "rateLimit", label: "Rate Limit (per hour)", type: "number", default: 0, desc: "0 = unlimited", advanced: true },
      { key: "escalationPolicy", label: "Escalation Policy", type: "text", default: "", advanced: true },
      { key: "locale", label: "Locale", type: "text", default: "en-US", advanced: true },
      { key: "audit", label: "Audit Trail", type: "boolean", default: true, advanced: true },
    ],
    mockOutput: { sent: true, channel: "email", recipients: 2 },
  },

  // ── E) AI ─────────────────────────────────────────────────────

  llmCall: {
    type: "llmCall",
    label: "LLM Call",
    icon: "MessageSquare",
    category: "ai",
    color: "#e11d48",
    desc: "Direct LLM invocation with prompt and model selection",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "provider", label: "Provider", type: "enum", options: ["Google", "OpenAI", "Anthropic", "Azure OpenAI"], default: "Google" },
      { key: "model", label: "Model", type: "enum", options: ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o", "gpt-4o-mini", "claude-sonnet-4", "claude-haiku"], default: "gemini-2.5-flash" },
      { key: "systemPrompt", label: "System Prompt", type: "textarea", default: "You are a helpful assistant.", rows: 3, templated: true },
      { key: "userPrompt", label: "User Prompt", type: "textarea", default: "{{input.query}}", rows: 4, required: true, templated: true },
      { key: "allowToolCalling", label: "Allow Tool Calling", type: "boolean", default: false },
      { key: "allowAttachments", label: "Allow Attachments", type: "boolean", default: false },
      { key: "maxTokens", label: "Max Tokens", type: "number", default: 2048, min: 1, max: 128000 },
      { key: "temperature", label: "Temperature", type: "range", default: 0.7, min: 0, max: 2, step: 0.1 },
      { key: "structuredOutput", label: "Structured Output", type: "enum", options: ["none", "jsonSchema"], default: "none", advanced: true },
      { key: "outputSchema", label: "Output Schema", type: "json", default: "{}", showWhen: { structuredOutput: "jsonSchema" }, advanced: true, rows: 4 },
      { key: "contextPolicy", label: "Context Policy", type: "enum", options: ["truncate", "summarize", "errorIfTooLong"], default: "truncate", advanced: true },
      { key: "safetyPolicyRef", label: "Safety Policy", type: "text", default: "", advanced: true },
    ],
    mockOutput: { response: "Based on the analysis, the total spend is...", tokens: { prompt: 120, completion: 85 } },
  },

  ragRetrieve: {
    type: "ragRetrieve",
    label: "RAG Retrieve",
    icon: "Brain",
    category: "ai",
    color: "#e11d48",
    desc: "Query a knowledge base for relevant context chunks",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "knowledgeBase", label: "Knowledge Base", type: "enum", options: ["(load from API)"], default: "", required: true, dynamic: true },
      { key: "queryTemplate", label: "Query Template", type: "textarea", default: "{{input.query}}", rows: 2, required: true, templated: true },
      { key: "topK", label: "Top K", type: "number", default: 5, min: 1, max: 50 },
      { key: "filters", label: "Filters", type: "json", default: "{}", desc: "tags, doctype, tenant, audience, appContext", rows: 3 },
      { key: "rerank", label: "Re-rank Results", type: "boolean", default: false },
      { key: "minScoreThreshold", label: "Min Score Threshold", type: "range", default: 0.5, min: 0, max: 1, step: 0.05 },
      { key: "multiKbMergeStrategy", label: "Multi-KB Merge", type: "enum", options: ["concat", "dedupe", "bestOnly"], default: "concat", advanced: true },
      { key: "citationFormat", label: "Citation Format", type: "enum", options: ["titleSection", "chunkId", "urlTitle"], default: "titleSection", advanced: true },
      { key: "onNoResults", label: "On No Results", type: "enum", options: ["route", "continueEmpty", "error"], default: "continueEmpty", advanced: true },
      { key: "debugShowChunks", label: "Debug: Show Chunks", type: "boolean", default: false, advanced: true },
    ],
    mockOutput: { chunks: [{ text: "Relevant document excerpt...", score: 0.89, source: "policy-doc" }], count: 5 },
  },

  runAgent: {
    type: "runAgent",
    label: "Run Agent",
    icon: "Bot",
    category: "ai",
    color: "#e11d48",
    desc: "Execute an existing platform agent",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "agentId", label: "Agent", type: "enum", options: ["(load from API)"], default: "", required: true, dynamic: true },
      { key: "inputMapping", label: "Input Mapping", type: "json", default: '{\n  "message": "{{input.query}}"\n}', rows: 4 },
      { key: "toolPermissions", label: "Tool Permissions", type: "tags", default: [], desc: "Allowed tool IDs" },
      { key: "ragAccessPolicy", label: "RAG Access Policy", type: "tags", default: [], desc: "Allowed KB IDs" },
      { key: "outputContract", label: "Output Contract", type: "json", default: "{}", desc: "Expected output schema", rows: 3, advanced: true },
      { key: "maxSteps", label: "Max Steps", type: "number", default: 10, min: 1, advanced: true },
      { key: "timeoutMs", label: "Timeout (ms)", type: "number", default: 60000, advanced: true },
      { key: "allowAttachments", label: "Allow Attachments", type: "boolean", default: false, advanced: true },
      { key: "telemetryTags", label: "Telemetry Tags", type: "keyvalue", default: {}, advanced: true },
      { key: "versionEnvironment", label: "Version/Env", type: "enum", options: ["dev", "qa", "uat", "prod"], default: "dev", advanced: true },
    ],
    mockOutput: { response: "Based on the analysis, I recommend...", confidence: 0.92, steps: 3 },
  },

  guardrailsCheck: {
    type: "guardrailsCheck",
    label: "Guardrails / Policy",
    icon: "Shield",
    category: "ai",
    color: "#e11d48",
    desc: "Run content through safety and policy checks",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "policyPack", label: "Policy Pack", type: "enum", options: ["default", "strict", "custom"], default: "default" },
      { key: "disallowedTopics", label: "Disallowed Topics", type: "tags", default: [] },
      { key: "piiRedaction", label: "PII Redaction", type: "boolean", default: true },
      { key: "jailbreakSensitivity", label: "Jailbreak Sensitivity", type: "enum", options: ["low", "med", "high"], default: "med" },
      { key: "competitorRules", label: "Competitor Rules", type: "enum", options: ["allowMention", "block", "rewriteNeutral"], default: "block" },
      { key: "toneProfile", label: "Tone Profile", type: "enum", options: ["enterprise", "friendly", "strict"], default: "enterprise" },
      { key: "onViolation", label: "On Violation", type: "enum", options: ["block", "route", "rewrite"], default: "block" },
      { key: "explainToUser", label: "Explain to User", type: "boolean", default: true, advanced: true },
      { key: "audit", label: "Audit Trail", type: "boolean", default: true, advanced: true },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { passed: true, violations: [], pii_found: false },
  },

  // ── F) HUMAN & TICKETS ────────────────────────────────────────

  humanReview: {
    type: "humanReview",
    label: "Human Review",
    icon: "UserCheck",
    category: "human",
    color: "#d97706",
    desc: "Pause workflow for human review or approval",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "channels", label: "Notification Channels", type: "tags", default: ["inApp"], options: ["teams", "slack", "email", "inApp"] },
      { key: "assignees", label: "Assignees", type: "tags", default: [], desc: "Users, groups, or roles" },
      { key: "approvalMode", label: "Approval Mode", type: "enum", options: ["approveReject", "commentOnly", "editAndApprove"], default: "approveReject" },
      { key: "slaDueMinutes", label: "SLA Due (minutes)", type: "number", default: 1440, min: 5 },
      { key: "reminders", label: "Reminder Schedule", type: "text", default: "50%,90%", desc: "Send reminders at % of SLA" },
      { key: "escalation", label: "Escalation Policy", type: "text", default: "", advanced: true },
      { key: "displayPayload", label: "Display Payload", type: "json", default: "{}", desc: "What the reviewer sees", rows: 4, advanced: true },
      { key: "editableFields", label: "Editable Fields", type: "tags", default: [], advanced: true },
      { key: "resultMapping", label: "Result Mapping", type: "json", default: "{}", desc: "Map decision to vars", advanced: true, rows: 3 },
      { key: "auditTrail", label: "Audit Trail", type: "boolean", default: true, advanced: true },
    ],
    mockOutput: { approved: true, reviewer: "manager@jaggaer.com", decision: "approve", comments: "" },
  },

  createTicket: {
    type: "createTicket",
    label: "Create Ticket / Case",
    icon: "Ticket",
    category: "human",
    color: "#d97706",
    desc: "Create a ticket in Jira, ServiceNow, or internal system",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "system", label: "System", type: "enum", options: ["jira", "servicenow", "internal"], default: "internal", required: true },
      { key: "ticketType", label: "Ticket Type", type: "text", default: "Task", desc: "Bug, Task, Story, Incident, etc." },
      { key: "priorityRule", label: "Priority Rule", type: "enum", options: ["low", "medium", "high", "critical", "dynamic"], default: "medium" },
      { key: "requiredFieldMapping", label: "Field Mapping", type: "json", default: '{\n  "title": "{{vars.summary}}",\n  "description": "{{vars.details}}"\n}', rows: 5 },
      { key: "piiRedactionBeforeCreate", label: "PII Redaction", type: "boolean", default: true },
      { key: "attachments", label: "Attachments", type: "enum", options: ["none", "include"], default: "none" },
      { key: "dedupeStrategy", label: "Dedup Strategy", type: "enum", options: ["none", "similarity", "keyFields"], default: "none", advanced: true },
      { key: "routing", label: "Routing", type: "text", default: "", desc: "Assignee or group", advanced: true },
      { key: "statusSync", label: "Status Sync", type: "boolean", default: false, advanced: true },
      { key: "storeLinkAs", label: "Store Link As", type: "text", default: "vars.ticketUrl", advanced: true },
    ],
    mockOutput: { ticket_id: "TICKET-123", url: "https://jira.example.com/TICKET-123", status: "created" },
  },

  // ── G) OUTPUT & OBSERVABILITY ─────────────────────────────────

  outputReturn: {
    type: "outputReturn",
    label: "Output / Return",
    icon: "LogOut",
    category: "output",
    color: "#64748b",
    desc: "Define the workflow's final output",
    inputHandles: IN,
    outputHandles: [],
    fields: [
      { key: "outputMode", label: "Output Mode", type: "enum", options: ["markdown", "plain", "json"], default: "json" },
      { key: "outputSchema", label: "Output Schema", type: "json", default: "{}", showWhen: { outputMode: "json" }, rows: 4 },
      { key: "includeCitations", label: "Include Citations", type: "boolean", default: false },
      { key: "citationStyle", label: "Citation Style", type: "enum", options: ["inline", "footnote", "appendix"], default: "inline", showWhen: { includeCitations: true } },
      { key: "includeDebugFields", label: "Include Debug Fields", type: "boolean", default: false, desc: "Hidden in prod" },
      { key: "errorOutputMode", label: "Error Output Mode", type: "enum", options: ["standard", "verbose"], default: "standard", advanced: true },
      { key: "localization", label: "Localization", type: "text", default: "en-US", advanced: true },
      { key: "truncatePolicy", label: "Truncate Policy", type: "enum", options: ["hardLimit", "summarize", "error"], default: "hardLimit", advanced: true },
      { key: "uiHints", label: "UI Hints", type: "enum", options: ["none", "cards", "tables"], default: "none", advanced: true },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { final_output: "Workflow complete", mode: "json" },
  },

  logTrace: {
    type: "logTrace",
    label: "Log / Trace",
    icon: "FileText",
    category: "output",
    color: "#64748b",
    desc: "Emit structured logs and traces for observability",
    inputHandles: IN,
    outputHandles: OUT,
    fields: [
      { key: "level", label: "Level", type: "enum", options: ["error", "warn", "info", "debug"], default: "info" },
      { key: "messageTemplate", label: "Message Template", type: "textarea", default: "Step completed: {{vars.step}}", rows: 3, templated: true },
      { key: "fieldsInclude", label: "Fields to Include", type: "tags", default: [] },
      { key: "fieldsExclude", label: "Fields to Exclude", type: "tags", default: [] },
      { key: "piiRedaction", label: "PII Redaction", type: "boolean", default: true },
      { key: "correlationId", label: "Correlation ID Path", type: "text", default: "vars.correlationId", advanced: true },
      { key: "tags", label: "Tags", type: "keyvalue", default: {}, advanced: true },
      { key: "samplingRate", label: "Sampling Rate (0-1)", type: "range", default: 1, min: 0, max: 1, step: 0.05, advanced: true },
      { key: "exportTarget", label: "Export Target", type: "enum", options: ["internal", "external"], default: "internal", advanced: true },
      { key: "notes", label: "Notes", type: "textarea", default: "", advanced: true },
    ],
    mockOutput: { logged: true, level: "info", timestamp: new Date().toISOString() },
  },
};

// ═══════════════════════════════════════════════════════════════════
// EXPORTS
// ═══════════════════════════════════════════════════════════════════

export default REGISTRY;

export function getNodeDef(type) {
  return REGISTRY[type] || null;
}

export function getNodesByCategory(categoryId) {
  return Object.values(REGISTRY).filter(n => n.category === categoryId);
}

export function getAllNodeTypes() {
  return Object.values(REGISTRY);
}

export function getDefaultConfig(type) {
  const def = REGISTRY[type];
  if (!def) return {};
  const config = {};
  def.fields.forEach(f => {
    config[f.key] = f.default !== undefined ? (typeof f.default === "object" ? JSON.parse(JSON.stringify(f.default)) : f.default) : "";
  });
  return config;
}

export function validateNodeConfig(type, config) {
  const def = REGISTRY[type];
  if (!def) return { errors: [], warnings: [] };
  const errors = [];
  const warnings = [];

  def.fields.forEach(f => {
    // Check required
    if (f.required) {
      const val = config[f.key];
      if (val === undefined || val === null || val === "" || (Array.isArray(val) && val.length === 0)) {
        errors.push({ field: f.key, message: `${f.label} is required` });
      }
    }
    // Check number ranges
    if (f.type === "number" && config[f.key] !== undefined) {
      const v = Number(config[f.key]);
      if (f.min !== undefined && v < f.min) errors.push({ field: f.key, message: `${f.label} must be >= ${f.min}` });
      if (f.max !== undefined && v > f.max) errors.push({ field: f.key, message: `${f.label} must be <= ${f.max}` });
    }
  });

  return { errors, warnings };
}

export function shouldShowField(field, config) {
  if (!field.showWhen) return true;
  return Object.entries(field.showWhen).every(([key, val]) => {
    if (Array.isArray(val)) return val.includes(config[key]);
    return config[key] === val;
  });
}

// Trigger types that have no input handles
export function isTriggerNode(type) {
  const def = REGISTRY[type];
  return def ? def.inputHandles.length === 0 : false;
}

// Branching nodes that have multiple output handles
export function isBranchingNode(type) {
  const def = REGISTRY[type];
  return def ? def.outputHandles.length > 1 : false;
}

// Terminal nodes that have no output handles
export function isTerminalNode(type) {
  const def = REGISTRY[type];
  return def ? def.outputHandles.length === 0 : false;
}

// Connection validation
export function canConnect(sourceType, targetType) {
  // Terminal nodes can't be sources
  if (isTerminalNode(sourceType)) return false;
  // Trigger nodes can't be targets
  if (isTriggerNode(targetType)) return false;
  return true;
}

// ── Example Workflows ───────────────────────────────────────────

export const EXAMPLE_WORKFLOWS = {
  ragAnswer: {
    name: "RAG Answer Workflow",
    description: "Start → RAG Retrieve → LLM Call → Output",
    nodes: [
      { id: "n1", type: "startInput", position: { x: 250, y: 50 }, data: { label: "Start", _nodeType: "startInput", config: { sampleInput: '{"query": "What is our refund policy?"}' } } },
      { id: "n2", type: "ragRetrieve", position: { x: 250, y: 200 }, data: { label: "RAG Retrieve", _nodeType: "ragRetrieve", config: { topK: 5, queryTemplate: "{{input.query}}" } } },
      { id: "n3", type: "llmCall", position: { x: 250, y: 350 }, data: { label: "Generate Answer", _nodeType: "llmCall", config: { model: "gemini-2.5-flash", userPrompt: "Based on context:\n{{rag.chunks}}\n\nAnswer: {{input.query}}" } } },
      { id: "n4", type: "outputReturn", position: { x: 250, y: 500 }, data: { label: "Output", _nodeType: "outputReturn", config: { outputMode: "markdown", includeCitations: true } } },
    ],
    edges: [
      { id: "e1", source: "n1", target: "n2", sourceHandle: "out", targetHandle: "in" },
      { id: "e2", source: "n2", target: "n3", sourceHandle: "out", targetHandle: "in" },
      { id: "e3", source: "n3", target: "n4", sourceHandle: "out", targetHandle: "in" },
    ],
  },
  approvalWorkflow: {
    name: "Approval Workflow",
    description: "Start → RAG → LLM → Human Review → If → Output",
    nodes: [
      { id: "n1", type: "startInput", position: { x: 300, y: 50 }, data: { label: "Start", _nodeType: "startInput", config: {} } },
      { id: "n2", type: "ragRetrieve", position: { x: 300, y: 180 }, data: { label: "Retrieve Context", _nodeType: "ragRetrieve", config: { topK: 3 } } },
      { id: "n3", type: "llmCall", position: { x: 300, y: 310 }, data: { label: "Draft Response", _nodeType: "llmCall", config: { model: "gemini-2.5-flash" } } },
      { id: "n4", type: "humanReview", position: { x: 300, y: 440 }, data: { label: "Manager Approval", _nodeType: "humanReview", config: { approvalMode: "editAndApprove", slaDueMinutes: 60 } } },
      { id: "n5", type: "ifCondition", position: { x: 300, y: 570 }, data: { label: "Approved?", _nodeType: "ifCondition", config: { expression: "{{vars.decision}} === 'approve'" } } },
      { id: "n6", type: "outputReturn", position: { x: 150, y: 720 }, data: { label: "Send Response", _nodeType: "outputReturn", config: { outputMode: "markdown" } } },
      { id: "n7", type: "notify", position: { x: 450, y: 720 }, data: { label: "Notify Rejection", _nodeType: "notify", config: { channelType: "email", severity: "warning" } } },
    ],
    edges: [
      { id: "e1", source: "n1", target: "n2", sourceHandle: "out", targetHandle: "in" },
      { id: "e2", source: "n2", target: "n3", sourceHandle: "out", targetHandle: "in" },
      { id: "e3", source: "n3", target: "n4", sourceHandle: "out", targetHandle: "in" },
      { id: "e4", source: "n4", target: "n5", sourceHandle: "out", targetHandle: "in" },
      { id: "e5", source: "n5", target: "n6", sourceHandle: "true", targetHandle: "in" },
      { id: "e6", source: "n5", target: "n7", sourceHandle: "false", targetHandle: "in" },
    ],
  },
  integrationWorkflow: {
    name: "Integration Workflow",
    description: "Webhook → Validate → HTTP Request → Transform → Output",
    nodes: [
      { id: "n1", type: "webhookTrigger", position: { x: 300, y: 50 }, data: { label: "Webhook", _nodeType: "webhookTrigger", config: { path: "/inbound", methods: ["POST"] } } },
      { id: "n2", type: "validate", position: { x: 300, y: 200 }, data: { label: "Validate Input", _nodeType: "validate", config: { strictMode: true } } },
      { id: "n3", type: "httpRequest", position: { x: 300, y: 350 }, data: { label: "Fetch Data", _nodeType: "httpRequest", config: { method: "GET", url: "https://api.example.com/data/{{input.id}}" } } },
      { id: "n4", type: "transform", position: { x: 300, y: 500 }, data: { label: "Transform", _nodeType: "transform", config: {} } },
      { id: "n5", type: "outputReturn", position: { x: 300, y: 650 }, data: { label: "Output", _nodeType: "outputReturn", config: { outputMode: "json" } } },
    ],
    edges: [
      { id: "e1", source: "n1", target: "n2", sourceHandle: "out", targetHandle: "in" },
      { id: "e2", source: "n2", target: "n3", sourceHandle: "out", targetHandle: "in" },
      { id: "e3", source: "n3", target: "n4", sourceHandle: "out", targetHandle: "in" },
      { id: "e4", source: "n4", target: "n5", sourceHandle: "out", targetHandle: "in" },
    ],
  },
};
