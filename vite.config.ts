import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig(({ mode }) => {
  const interview = mode === "interview";
  return {
    build: {
      lib: {
        entry: resolve(
          import.meta.dirname,
          interview
            ? "frontend/src/interview/interview-controller.ts"
            : "frontend/src/resume/resume-controller.ts",
        ),
        name: interview ? "JobHunterInterviewController" : "JobHunterResumeController",
        formats: ["iife"],
        fileName: () => interview ? "interview_controller.js" : "resume_controller.js",
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
