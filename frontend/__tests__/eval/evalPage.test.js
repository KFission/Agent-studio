/**
 * Eval Studio tests — verify streaming architecture, model selection,
 * token display, and full-response rendering.
 */
const fs = require("fs");
const path = require("path");

const evalSrc = fs.readFileSync(
  path.resolve(__dirname, "../../components/pages/EvalPage.jsx"), "utf-8"
);

describe("Eval Studio: streaming architecture", () => {
  it("uses /eval/stream SSE endpoint instead of /eval/multi", () => {
    expect(evalSrc).toContain("/eval/stream");
  });

  it("reads SSE events via ReadableStream reader", () => {
    expect(evalSrc).toContain("r.body.getReader()");
    expect(evalSrc).toContain("TextDecoder");
  });

  it("parses SSE data lines and dispatches result events", () => {
    expect(evalSrc).toContain('line.startsWith("data: ")');
    expect(evalSrc).toContain('evt.event === "result"');
  });

  it("updates results progressively as each model completes", () => {
    expect(evalSrc).toContain("setResults(prev =>");
    expect(evalSrc).toContain("results.push(evt)");
  });
});

describe("Eval Studio: model selection", () => {
  it("does NOT contain hardcoded MODEL_PRICING constant", () => {
    expect(evalSrc).not.toMatch(/^const MODEL_PRICING\s*=/m);
  });

  it("builds availableModels from /models API response only", () => {
    expect(evalSrc).toContain("models.map(m =>");
    expect(evalSrc).toContain("m.display_name || m.model_id");
  });

  it("auto-selects first 2 models from API on load", () => {
    expect(evalSrc).toContain("m.slice(0, Math.min(2, m.length))");
  });

  it("does NOT hardcode gpt-4o or gpt-4o-mini as default selection", () => {
    expect(evalSrc).not.toContain('"gpt-4o-mini"');
    expect(evalSrc).not.toContain('"gpt-4o"');
  });

  it("judge model dropdown uses dynamic models from API", () => {
    expect(evalSrc).toContain("models.map(m => <option");
  });
});

describe("Eval Studio: output display", () => {
  it("does NOT use line-clamp-6 truncation on response output", () => {
    expect(evalSrc).not.toContain("line-clamp-6");
  });

  it("uses scrollable container for full response (max-h-[400px])", () => {
    expect(evalSrc).toContain("max-h-[400px] overflow-y-auto");
  });
});

describe("Eval Studio: loading state", () => {
  it("shows loading spinner cards for models still running", () => {
    expect(evalSrc).toContain("Running evaluation...");
    expect(evalSrc).toContain("animate-spin");
  });

  it("renders grid for all selected models (not just completed results)", () => {
    expect(evalSrc).toContain("selModels.map((modelId");
  });
});

describe("Eval Studio: metric descriptions", () => {
  it("has plain-English descriptions (not jargon) for all metrics", () => {
    // Old jargon descriptions should NOT appear
    expect(evalSrc).not.toContain('"Longest common subsequence"');
    expect(evalSrc).not.toContain('"N-gram precision"');
    expect(evalSrc).not.toContain('"Jaccard word similarity"');
  });

  it("descriptions explain what the metric does in user-friendly terms", () => {
    expect(evalSrc).toContain("key phrasing from your reference");
    expect(evalSrc).toContain("wording matches your reference");
    expect(evalSrc).toContain("includes specific text");
    expect(evalSrc).toContain("match the reference word-for-word");
    expect(evalSrc).toContain("character edits");
    expect(evalSrc).toContain("same words appear");
  });

  it("shows descriptions inline (not hidden in title tooltips)", () => {
    // The metric selector should use visible description divs, not title attrs
    expect(evalSrc).toContain("{m.desc}</div>");
  });

  it("maps raw metric IDs to friendly labels via METRIC_LABEL_MAP", () => {
    expect(evalSrc).toContain("METRIC_LABEL_MAP");
    expect(evalSrc).toContain("METRIC_LABEL_MAP[s.metric]");
    expect(evalSrc).toContain("METRIC_LABEL_MAP[metricName]");
  });
});

describe("Eval Studio: token display", () => {
  it("renders input_tokens and output_tokens in metrics grid", () => {
    expect(evalSrc).toContain("r.input_tokens");
    expect(evalSrc).toContain("r.output_tokens");
  });
});

describe("Backend: token counting fix", () => {
  const evaluatorSrc = fs.readFileSync(
    path.resolve(__dirname, "../../../backend/eval_studio/evaluator.py"), "utf-8"
  );

  it("handles dict-style usage_metadata (Google models)", () => {
    expect(evaluatorSrc).toContain('isinstance(usage, dict)');
    expect(evaluatorSrc).toContain('usage.get("input_tokens"');
  });

  it("handles object-style usage_metadata (Anthropic/OpenAI)", () => {
    expect(evaluatorSrc).toContain('getattr(usage, "input_tokens"');
  });

  it("falls back to estimate_tokens when provider reports 0", () => {
    expect(evaluatorSrc).toContain("estimate_tokens(prompt)");
    expect(evaluatorSrc).toContain("estimate_tokens(content)");
  });

  it("resolves integration credentials via _resolve_credentials", () => {
    expect(evaluatorSrc).toContain("def _resolve_credentials");
    expect(evaluatorSrc).toContain("integration_id");
    expect(evaluatorSrc).toContain('extra_kwargs["google_api_key"]');
  });
});

describe("Backend: streaming eval endpoint", () => {
  const serverSrc = fs.readFileSync(
    path.resolve(__dirname, "../../../backend/api/server.py"), "utf-8"
  );

  it("defines POST /eval/stream endpoint", () => {
    expect(serverSrc).toContain('@app.post("/eval/stream")');
  });

  it("runs models concurrently with asyncio", () => {
    expect(serverSrc).toContain("asyncio.create_task");
    expect(serverSrc).toContain("asyncio.as_completed");
  });

  it("returns StreamingResponse with SSE media type", () => {
    expect(serverSrc).toContain('media_type="text/event-stream"');
  });

  it("streams start, result, and done events", () => {
    expect(serverSrc).toMatch(/event.*start/);
    expect(serverSrc).toMatch(/event.*result/);
    expect(serverSrc).toMatch(/event.*done/);
  });
});
