import { resolve } from "node:path";
import { build, createServer } from "vite";

const projectRoot = resolve(import.meta.dirname, "../..");
const staticDir = resolve(projectRoot, "static");
const port = Number(process.env.PORT || 5173);

const modes = ["app"];
const watchers = await Promise.all(modes.map((mode) => build({
  configFile: resolve(projectRoot, "vite.config.ts"),
  mode,
  build: { watch: {} },
})));
const server = await createServer({
  configFile: false,
  root: staticDir,
  server: {
    host: process.env.HOST || "127.0.0.1",
    port,
  },
});

await server.listen();
server.printUrls();

async function close() {
  await server.close();
  await Promise.all(watchers.map(async (watcher) => {
    if ("close" in watcher) await watcher.close();
  }));
}

process.once("SIGINT", async () => {
  await close();
  process.exit(0);
});
process.once("SIGTERM", async () => {
  await close();
  process.exit(0);
});
