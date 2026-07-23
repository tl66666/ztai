import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig(({ mode }) => {
  const target = mode === "interview"
    ? {
        entry: "frontend/src/interview/interview-controller.ts",
        name: "JobHunterInterviewController",
        file: "interview_controller.js",
      }
    : mode === "opportunity"
      ? {
          entry: "frontend/src/opportunity/opportunity-controller.ts",
          name: "JobHunterOpportunityController",
          file: "opportunity_controller.js",
        }
      : {
          entry: "frontend/src/resume/resume-controller.ts",
          name: "JobHunterResumeController",
          file: "resume_controller.js",
        };
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
