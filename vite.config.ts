import { defineConfig } from "vite";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const targets = {
    app: {
      entry: "frontend/src/app/main.tsx",
      name: "JobHunterReactApp",
      file: "react_app.js",
      formats: ["es"],
    },
  } as const;
  const target = targets[mode as keyof typeof targets] || targets.app;
  return {
    define: mode === "app"
      ? { "process.env.NODE_ENV": JSON.stringify("production") }
      : undefined,
    plugins: mode === "app" ? [react()] : [],
    build: {
      minify: "oxc",
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
