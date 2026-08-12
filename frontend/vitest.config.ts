import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Route Handler tests import real (non-type-only) modules that transitively import
// `src/lib/env.ts`, which parses `process.env` at import time. Vite only exposes `.env*`
// files to `import.meta.env` by default, not `process.env` — so without this, any test
// touching that import chain fails with a Zod error before the test body ever runs.
const envVars = loadEnv("test", process.cwd(), "");

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    env: envVars,
    coverage: { reporter: ["text", "text-summary"] },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "server-only": path.resolve(__dirname, "./vitest.server-only-shim.ts"),
    },
  },
});
