import useEnvStore, { ENVIRONMENTS, ENV_MAP } from "../../stores/envStore";

describe("Environment definitions", () => {
  it("ENVIRONMENTS has 4 entries (dev, qa, uat, prod)", () => {
    expect(ENVIRONMENTS.length).toBe(4);
    expect(ENVIRONMENTS.map(e => e.id)).toEqual(["dev", "qa", "uat", "prod"]);
  });

  it("every environment has required visual fields", () => {
    ENVIRONMENTS.forEach((env) => {
      expect(env).toHaveProperty("id");
      expect(env).toHaveProperty("label");
      expect(env).toHaveProperty("color");
      expect(env).toHaveProperty("bg");
      expect(env).toHaveProperty("text");
      expect(env).toHaveProperty("border");
      expect(env).toHaveProperty("dot");
      expect(env).toHaveProperty("description");
    });
  });

  it("ENV_MAP maps id to env object correctly", () => {
    expect(ENV_MAP.dev.label).toBe("Dev");
    expect(ENV_MAP.prod.label).toBe("Prod");
    expect(ENV_MAP.qa.label).toBe("QA");
    expect(ENV_MAP.uat.label).toBe("UAT");
  });
});

describe("Zustand envStore", () => {
  it("initial state has currentEnv = dev", () => {
    const state = useEnvStore.getState();
    expect(state.currentEnv).toBe("dev");
  });

  it("switchEnv changes the current environment", () => {
    const store = useEnvStore.getState();
    store.switchEnv("qa");
    expect(useEnvStore.getState().currentEnv).toBe("qa");
    // Reset
    store.switchEnv("dev");
  });

  it("canEdit returns a function", () => {
    const state = useEnvStore.getState();
    expect(typeof state.canEdit).toBe("function");
  });

  it("canEdit returns true for dev environment", () => {
    const state = useEnvStore.getState();
    state.switchEnv("dev");
    expect(state.canEdit()).toBe(true);
  });

  it("permissions object exists for all environments", () => {
    const state = useEnvStore.getState();
    expect(state.permissions).toHaveProperty("dev");
    expect(state.permissions).toHaveProperty("qa");
    expect(state.permissions).toHaveProperty("uat");
    expect(state.permissions).toHaveProperty("prod");
  });

  it("each permission has canView and canEdit", () => {
    const state = useEnvStore.getState();
    Object.values(state.permissions).forEach((perm) => {
      expect(perm).toHaveProperty("canView");
      expect(perm).toHaveProperty("canEdit");
    });
  });
});
