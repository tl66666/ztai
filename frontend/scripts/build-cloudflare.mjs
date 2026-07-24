import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const projectRoot = resolve(import.meta.dirname, "../..");
const staticDir = resolve(projectRoot, "static");
const outputDir = resolve(projectRoot, "dist");
const workerSource = resolve(projectRoot, "frontend/cloudflare/worker.mjs");
const apiBaseUrl = String(process.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

if (!apiBaseUrl) {
  throw new Error(
    "VITE_API_BASE_URL is required for a Cloudflare build (for example https://api.example.com)",
  );
}

await rm(outputDir, { recursive: true, force: true });
await mkdir(outputDir, { recursive: true });
await cp(staticDir, outputDir, {
  recursive: true,
  filter: (source) => !source.endsWith(".map"),
});
await cp(workerSource, resolve(outputDir, "_worker.js"));

await writeFile(
  resolve(outputDir, "config.js"),
  `window.__JOBHUNTER_CONFIG__ = Object.freeze({ apiBaseUrl: ${JSON.stringify(apiBaseUrl)} });\n`,
  "utf8",
);
await writeFile(
  resolve(outputDir, "_headers"),
  `/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(self), microphone=(self)

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/config.js
  Cache-Control: no-store
`,
  "utf8",
);

console.log(`Cloudflare static output: ${outputDir}`);
console.log(`Backend origin: ${apiBaseUrl}`);
