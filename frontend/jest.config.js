const nextJest = require("next/jest");
const path = require("path");

const createJestConfig = nextJest({ dir: "./" });

/** @type {import('jest').Config} */
const customJestConfig = {
  testEnvironment: "jsdom",
  testEnvironmentOptions: { customExportConditions: [""] },
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
    "^lucide-react$": "<rootDir>/__mocks__/lucide-react.js",
    "\\.(css|less|scss|sass)$": "identity-obj-proxy",
    "\\.(jpg|jpeg|png|gif|webp|svg)$": "<rootDir>/__mocks__/fileMock.js",
  },
  testMatch: ["<rootDir>/__tests__/**/*.test.{js,jsx,ts,tsx}"],
  transformIgnorePatterns: [
    "/node_modules/(?!(lucide-react|@xyflow|d3|internmap|delaunator|robust-predicates)/)",
  ],
};

module.exports = async () => {
  const resolved = await createJestConfig(customJestConfig)();
  // Force-inject setup file (next/jest can silently drop it)
  resolved.setupFilesAfterSetup = [path.resolve(__dirname, "jest.setup.js")];
  // Force transformIgnorePatterns (next/jest overrides ours)
  resolved.transformIgnorePatterns = [
    "/node_modules/(?!(lucide-react|@xyflow|d3|internmap|delaunator|robust-predicates)/)",
  ];
  return resolved;
};
