const assert = require("node:assert/strict");

async function endStream(stream) {
  if (!stream || stream.writableEnded) return;
  await new Promise((resolve) => stream.end(resolve));
}

async function stopChild(child) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (stopped) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(stopped);
    };
    const timer = setTimeout(() => finish(false), 5_000);
    child.once("exit", () => finish(true));
    child.kill();
  });
}

async function startIsolatedServer(options) {
  const {
    baseURL,
    createLogStream,
    removeTempDirectory,
    spawnProcess,
    tempDirectory,
    waitUntilReady,
  } = options;
  const log = createLogStream();
  let child = null;
  let cleaned = false;

  async function cleanup() {
    if (cleaned) return;
    cleaned = true;
    if (child && child.exitCode === null) {
      const stopped = await stopChild(child);
      if (!stopped && child.exitCode === null) {
        throw new Error(`Isolated Flask service did not stop: ${tempDirectory}`);
      }
    }
    child?.stdout?.destroy();
    child?.stderr?.destroy();
    await endStream(log);
    removeTempDirectory(tempDirectory);
  }

  try {
    child = spawnProcess();
    assert.ok(child && typeof child.once === "function", "spawnProcess must return a child process");
    child.stdout?.pipe(log, { end: false });
    child.stderr?.pipe(log, { end: false });
    const spawnError = new Promise((_, reject) => child.once("error", reject));
    await Promise.race([waitUntilReady(baseURL, child), spawnError]);
    return { baseURL, close: cleanup };
  } catch (error) {
    try {
      await cleanup();
    } catch (cleanupError) {
      error.cause = cleanupError;
    }
    throw error;
  }
}

module.exports = { startIsolatedServer };
