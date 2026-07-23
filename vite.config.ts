import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  build: {
    lib: {
      entry: resolve(import.meta.dirname, "frontend/src/resume/resume-controller.ts"),
      name: "JobHunterResumeController",
      formats: ["iife"],
      fileName: () => "resume_controller.js",
    },
    outDir: resolve(import.meta.dirname, "static/js"),
    emptyOutDir: false,
    sourcemap: false,
  },
  test: {
    environment: "happy-dom",
    include: ["frontend/**/*.test.ts"],
    clearMocks: true,
  },
});
