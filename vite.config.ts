import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig(({ mode }) => {
  const targets = {
    agent: {
      entry: "frontend/src/agent/agent-controller.ts",
      name: "JobHunterAgentController",
      file: "agent_controller.js",
    },
    interview: {
      entry: "frontend/src/interview/interview-controller.ts",
      name: "JobHunterInterviewController",
      file: "interview_controller.js",
    },
    opportunity: {
      entry: "frontend/src/opportunity/opportunity-controller.ts",
      name: "JobHunterOpportunityController",
      file: "opportunity_controller.js",
    },
    shell: {
      entry: "frontend/src/shell/shell-controller.ts",
      name: "JobHunterShellController",
      file: "shell_controller.js",
    },
    resume: {
      entry: "frontend/src/resume/resume-controller.ts",
      name: "JobHunterResumeController",
      file: "resume_controller.js",
    },
  } as const;
  const target = targets[mode as keyof typeof targets] || targets.resume;
  return {
    build: {
      lib: {
        entry: resolve(import.meta.dirname, target.entry),
        name: target.name,
        formats: ["iife"],
        fileName: () => target.file,
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
  };
});
