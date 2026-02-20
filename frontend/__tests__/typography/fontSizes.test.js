/**
 * Typography normalization test — verify no 9px or 10px font sizes remain
 * in core component surfaces.
 */
const { execSync } = require("child_process");
const path = require("path");

const COMPONENTS_DIR = path.resolve(__dirname, "../../components");

describe("Typography minimum 11px enforcement", () => {
  it("no text-[9px] exists in any .jsx component file", () => {
    try {
      const result = execSync(
        `grep -rn 'text-\\[9px\\]' "${COMPONENTS_DIR}" --include="*.jsx"`,
        { encoding: "utf-8" }
      );
      // If grep finds matches, fail the test
      fail(`Found text-[9px] in components:\n${result}`);
    } catch (e) {
      // grep returns exit code 1 when no matches — that's what we want
      expect(e.status).toBe(1);
    }
  });

  it("no text-[10px] exists in any .jsx component file", () => {
    try {
      const result = execSync(
        `grep -rn 'text-\\[10px\\]' "${COMPONENTS_DIR}" --include="*.jsx"`,
        { encoding: "utf-8" }
      );
      fail(`Found text-[10px] in components:\n${result}`);
    } catch (e) {
      expect(e.status).toBe(1);
    }
  });

  it("text-[11px] is used as the minimum small text size", () => {
    try {
      const result = execSync(
        `grep -rn 'text-\\[11px\\]' "${COMPONENTS_DIR}" --include="*.jsx" | wc -l`,
        { encoding: "utf-8" }
      );
      const count = parseInt(result.trim(), 10);
      expect(count).toBeGreaterThan(0);
    } catch (e) {
      fail("Expected text-[11px] to be present in components");
    }
  });
});

describe("No unused EnvBadge import in WorkflowBuilder", () => {
  it("WorkflowBuilder.jsx does not import EnvBadge", () => {
    try {
      const result = execSync(
        `grep -n 'EnvBadge' "${path.join(COMPONENTS_DIR, "WorkflowBuilder.jsx")}"`,
        { encoding: "utf-8" }
      );
      fail(`EnvBadge still referenced in WorkflowBuilder.jsx:\n${result}`);
    } catch (e) {
      expect(e.status).toBe(1);
    }
  });
});
