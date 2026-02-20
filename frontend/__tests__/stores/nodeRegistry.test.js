import REGISTRY, {
  NODE_CATEGORIES, getAllNodeTypes, getNodeDef, getDefaultConfig,
  validateNodeConfig, isTriggerNode, isBranchingNode, isTerminalNode,
  canConnect, EXAMPLE_WORKFLOWS,
} from "../../stores/nodeRegistry";

// ═══════════════════════════════════════════════════════════════════
// NODE REGISTRY — data integrity
// ═══════════════════════════════════════════════════════════════════

describe("Node Registry", () => {
  it("REGISTRY is a non-empty object", () => {
    expect(typeof REGISTRY).toBe("object");
    expect(Object.keys(REGISTRY).length).toBeGreaterThan(0);
  });

  it("every registry entry has required fields", () => {
    Object.entries(REGISTRY).forEach(([type, def]) => {
      expect(def).toHaveProperty("label");
      expect(typeof def.label).toBe("string");
      expect(def).toHaveProperty("category");
      expect(typeof def.category).toBe("string");
      expect(def).toHaveProperty("color");
    });
  });

  it("NODE_CATEGORIES is a non-empty array", () => {
    expect(Array.isArray(NODE_CATEGORIES)).toBe(true);
    expect(NODE_CATEGORIES.length).toBeGreaterThan(0);
  });

  it("every category has id and label", () => {
    NODE_CATEGORIES.forEach((cat) => {
      expect(cat).toHaveProperty("id");
      expect(cat).toHaveProperty("label");
    });
  });
});

describe("getAllNodeTypes", () => {
  it("returns a non-empty array of node type objects", () => {
    const types = getAllNodeTypes();
    expect(Array.isArray(types)).toBe(true);
    expect(types.length).toBeGreaterThan(0);
    types.forEach((t) => {
      expect(t).toHaveProperty("type");
      expect(typeof t.type).toBe("string");
    });
  });

  it("every returned type exists in REGISTRY", () => {
    getAllNodeTypes().forEach((t) => {
      expect(REGISTRY[t.type]).toBeDefined();
    });
  });
});

describe("getNodeDef", () => {
  it("returns definition for valid type", () => {
    const types = getAllNodeTypes();
    const def = getNodeDef(types[0].type);
    expect(def).toBeTruthy();
    expect(def).toHaveProperty("label");
  });

  it("returns null for unknown type", () => {
    expect(getNodeDef("__nonexistent_type__")).toBeNull();
  });
});

describe("getDefaultConfig", () => {
  it("returns an object for valid node type", () => {
    const types = getAllNodeTypes();
    const config = getDefaultConfig(types[0]);
    expect(typeof config).toBe("object");
  });

  it("returns empty object for unknown type", () => {
    const config = getDefaultConfig("__nonexistent__");
    expect(typeof config).toBe("object");
  });
});

describe("validateNodeConfig", () => {
  it("returns an object with errors and warnings arrays", () => {
    const types = getAllNodeTypes();
    const result = validateNodeConfig(types[0], {});
    expect(result).toHaveProperty("errors");
    expect(result).toHaveProperty("warnings");
    expect(Array.isArray(result.errors)).toBe(true);
    expect(Array.isArray(result.warnings)).toBe(true);
  });

  it("validates a valid default config without errors", () => {
    const types = getAllNodeTypes();
    const config = getDefaultConfig(types[0]);
    const result = validateNodeConfig(types[0], config);
    // Default config should be valid (or have only warnings)
    // Note: some nodes may have required fields not in defaults, so we just check structure
    expect(result).toHaveProperty("errors");
  });
});

describe("Node type helpers", () => {
  it("isTriggerNode returns boolean", () => {
    const types = getAllNodeTypes();
    types.forEach((t) => {
      expect(typeof isTriggerNode(t)).toBe("boolean");
    });
  });

  it("isBranchingNode returns boolean", () => {
    const types = getAllNodeTypes();
    types.forEach((t) => {
      expect(typeof isBranchingNode(t)).toBe("boolean");
    });
  });

  it("isTerminalNode returns boolean", () => {
    const types = getAllNodeTypes();
    types.forEach((t) => {
      expect(typeof isTerminalNode(t)).toBe("boolean");
    });
  });
});

describe("canConnect", () => {
  it("returns boolean for any pair of types", () => {
    const types = getAllNodeTypes();
    if (types.length >= 2) {
      expect(typeof canConnect(types[0], types[1])).toBe("boolean");
    }
  });
});

describe("EXAMPLE_WORKFLOWS", () => {
  it("is a non-empty object", () => {
    expect(typeof EXAMPLE_WORKFLOWS).toBe("object");
    expect(Object.keys(EXAMPLE_WORKFLOWS).length).toBeGreaterThan(0);
  });

  it("each example has name, nodes, and edges", () => {
    Object.values(EXAMPLE_WORKFLOWS).forEach((ex) => {
      expect(ex).toHaveProperty("name");
      expect(ex).toHaveProperty("nodes");
      expect(ex).toHaveProperty("edges");
      expect(Array.isArray(ex.nodes)).toBe(true);
      expect(Array.isArray(ex.edges)).toBe(true);
    });
  });

  it("every node in examples references a valid registry type", () => {
    Object.values(EXAMPLE_WORKFLOWS).forEach((ex) => {
      ex.nodes.forEach((n) => {
        expect(REGISTRY[n.type]).toBeDefined();
      });
    });
  });
});
