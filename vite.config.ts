import { defineConfig } from "vite";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const targets = {
    agent: {
      entry: "frontend/src/agent/agent-controller.ts",
      name: "JobHunterAgentController",
      file: "agent_controller.js",
      formats: ["iife"],
    },
    app: {
      entry: "frontend/src/app/main.tsx",
      name: "JobHunterReactApp",
      file: "react_app.js",
      formats: ["es"],
    },
    interview: {
      entry: "frontend/src/interview/interview-controller.ts",
      name: "JobHunterInterviewController",
      file: "interview_controller.js",
      formats: ["iife"],
    },
    opportunity: {
      entry: "frontend/src/opportunity/opportunity-controller.ts",
      name: "JobHunterOpportunityController",
      file: "opportunity_controller.js",
      formats: ["iife"],
    },
    shell: {
      entry: "frontend/src/shell/shell-controller.ts",
      name: "JobHunterShellController",
      file: "shell_controller.js",
      formats: ["iife"],
    },
    resume: {
      entry: "frontend/src/resume/resume-controller.ts",
      name: "JobHunterResumeController",
      file: "resume_controller.js",
      formats: ["iife"],
    },
  } as const;
  const target = targets[mode as keyof typeof targets] || targets.resume;
  return {
    define: mode === "app"
      ? { "process.env.NODE_ENV": JSON.stringify("production") }
      : undefined,
    plugins: mode === "app" ? [react()] : [],
    build: {
      minify: mode === "app" ? "oxc" : undefined,
      lib: {
        entry: resolve(import.meta.dirname, target.entry),
        name: target.name,
        formats: [...target.formats],
        fileName: () => target.file,
      },
      outDir: resolve(import.meta.dirname, "static/js"),
      emptyOutDir: false,
      sourcemap: false,
    },
    test: {
      environment: "happy-dom",
      include: ["frontend/**/*.test.{ts,tsx}"],
      clearMocks: true,
    },
  };
});
