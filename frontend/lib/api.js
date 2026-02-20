/**
 * Agent Studio API Client
 * Connects the React frontend to the FastAPI backend.
 * All calls proxy through nginx rewrites to backend:8080
 */

const API_BASE = "/api";

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.error || JSON.stringify(err));
  }
  return res.json();
}

// ── Health ────────────────────────────────────────────────────────
export const getHealth = () => request("/health");
export const getInfo = () => request("/info");

// ── LLM Model Library ────────────────────────────────────────────
export const listModels = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/models${qs ? `?${qs}` : ""}`);
};
export const getModel = (id) => request(`/models/${id}`);
export const registerModel = (data) =>
  request("/models", { method: "POST", body: JSON.stringify(data) });
export const deleteModel = (id) =>
  request(`/models/${id}`, { method: "DELETE" });
export const testModel = (id, prompt) =>
  request(`/models/${id}/test?prompt=${encodeURIComponent(prompt)}`, { method: "POST" });
export const compareCosts = (inputTokens, outputTokens) =>
  request(`/models/compare/cost?input_tokens=${inputTokens}&output_tokens=${outputTokens}`);
export const listProviders = () => request("/providers");

// ── Prompt Studio ────────────────────────────────────────────────
export const listPrompts = (category) =>
  request(`/prompts${category ? `?category=${category}` : ""}`);
export const getPrompt = (id) => request(`/prompts/${id}`);
export const createPrompt = (data) =>
  request("/prompts", { method: "POST", body: JSON.stringify(data) });
export const updatePrompt = (id, data) =>
  request(`/prompts/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deletePrompt = (id) =>
  request(`/prompts/${id}`, { method: "DELETE" });
export const renderPrompt = (data) =>
  request("/prompts/render", { method: "POST", body: JSON.stringify(data) });
export const getPromptVariables = (id) => request(`/prompts/${id}/variables`);
export const searchPrompts = (query) => request(`/prompts/search/${encodeURIComponent(query)}`);

// ── Evaluation Studio ────────────────────────────────────────────
export const estimateTokens = (text) =>
  request(`/eval/estimate-tokens?text=${encodeURIComponent(text)}`, { method: "POST" });
export const evalSingle = (data) =>
  request("/eval/single", { method: "POST", body: JSON.stringify(data) });
export const evalMulti = (data) =>
  request("/eval/multi", { method: "POST", body: JSON.stringify(data) });
export const listEvalRuns = (limit = 20) => request(`/eval/runs?limit=${limit}`);
export const getEvalRun = (id) => request(`/eval/runs/${id}`);

// ── Channels: Webhooks ───────────────────────────────────────────
export const listWebhooks = () => request("/webhooks");
export const createWebhook = (data) =>
  request("/webhooks", { method: "POST", body: JSON.stringify(data) });
export const deleteWebhook = (id) =>
  request(`/webhooks/${id}`, { method: "DELETE" });
export const getWebhookEvents = (id, limit = 20) =>
  request(`/webhooks/${id}/events?limit=${limit}`);

// ── Channels: WebSocket ──────────────────────────────────────────
export const getWsStats = () => request("/ws/stats");

export function createWebSocket(clientId, onMessage) {
  const protocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = typeof window !== "undefined" ? window.location.host : "localhost:3000";
  const ws = new WebSocket(`${protocol}//${host}/ws/${clientId}`);
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };
  return ws;
}

// ── Channels: Jaggaer SaaS LLM ──────────────────────────────────
export const jaggaerInvoke = (data) =>
  request("/jaggaer/llm/invoke", { method: "POST", body: JSON.stringify(data) });
export const jaggaerUsage = (tenantId) =>
  request(`/jaggaer/usage${tenantId ? `?tenant_id=${tenantId}` : ""}`);
export const jaggaerUsageSummary = (tenantId) =>
  request(`/jaggaer/usage/summary${tenantId ? `?tenant_id=${tenantId}` : ""}`);

// ── LangSmith Observability ──────────────────────────────────────
export const langsmithStatus = () => request("/langsmith/status");
export const langsmithRuns = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/langsmith/runs${qs ? `?${qs}` : ""}`);
};
export const langsmithRunDetail = (id) => request(`/langsmith/runs/${id}`);
export const langsmithStats = (hours = 24) => request(`/langsmith/stats?hours=${hours}`);
export const langsmithFeedback = (data) =>
  request("/langsmith/feedback", { method: "POST", body: JSON.stringify(data) });

// ── Graph Compiler & Registry ────────────────────────────────────
export const listGraphs = (status) =>
  request(`/graphs${status ? `?status=${status}` : ""}`);
export const getGraph = (id) => request(`/graphs/${id}`);
export const createGraph = (data) =>
  request("/graphs", { method: "POST", body: JSON.stringify(data) });
export const updateGraph = (id, data) =>
  request(`/graphs/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteGraph = (id) =>
  request(`/graphs/${id}`, { method: "DELETE" });
export const listGraphVersions = (id) => request(`/graphs/${id}/versions`);
export const getGraphVersion = (id, version) => request(`/graphs/${id}/versions/${version}`);
export const rollbackGraph = (id, version) =>
  request(`/graphs/${id}/rollback/${version}`, { method: "POST" });
export const setGraphStatus = (id, status) =>
  request(`/graphs/${id}/status/${status}`, { method: "POST" });
export const validateGraph = (id) =>
  request(`/graphs/${id}/validate`, { method: "POST" });
export const compileGraph = (id) =>
  request(`/graphs/${id}/compile`, { method: "POST" });
export const runGraph = (id, initialState = {}) =>
  request(`/graphs/${id}/run`, { method: "POST", body: JSON.stringify({ initial_state: initialState }) });
export const listCompiledGraphs = () => request("/graphs/compiled/list");
export const exportGraph = (id) => request(`/graphs/${id}/export`);
export const importGraph = (data) =>
  request("/graphs/import", { method: "POST", body: JSON.stringify(data) });

// ── Templates ────────────────────────────────────────────────────
export const listTemplates = () => request("/templates");
export const saveAsTemplate = (manifestId, name) =>
  request(`/templates/${manifestId}?name=${encodeURIComponent(name)}`, { method: "POST" });
export const createFromTemplate = (templateId, name) =>
  request(`/templates/${templateId}/create?name=${encodeURIComponent(name)}`, { method: "POST" });

export const graphStats = () => request("/graphs/stats");
export const searchGraphs = (query) => request(`/graphs/search/${encodeURIComponent(query)}`);
