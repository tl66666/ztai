const assert = require("node:assert/strict");

async function endStream(stream) {
  if (!stream || stream.writableEnded) return;
  await new Promise((resolve) => stream.end(resolve));
}

async function stopChild(child) {
  if (!child) return;
  if (child.exitCode !== null) return;
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (error = null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      child.removeListener("exit", onExit);
      if (error) reject(error);
      else resolve();
    };
    const onExit = () => finish();
    const timer = setTimeout(() => {
      finish(new Error("Timed out after 5000ms waiting for isolated Flask service to stop on Windows"));
    }, 5_000);
    child.once("exit", onExit);
    try {
      const signaled = child.kill();
      if (signaled === false && child.exitCode === null) {
        finish(new Error("Windows could not signal the isolated Flask service to stop"));
      }
    } catch (error) {
      finish(error);
    }
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
  const completed = {
    child: false,
    stdout: false,
    stderr: false,
    log: false,
    temp: false,
  };

  async function cleanup() {
    const errors = [];
    if (!completed.child) {
      try {
        await stopChild(child);
        completed.child = true;
      } catch (error) {
        errors.push(error);
      }
    }
    for (const [stage, stream] of [["stdout", child?.stdout], ["stderr", child?.stderr]]) {
      if (completed[stage]) continue;
      try {
        stream?.destroy();
        completed[stage] = true;
      } catch (error) {
        errors.push(error);
      }
    }
    if (!completed.log) {
      try {
        await endStream(log);
        completed.log = true;
      } catch (error) {
        errors.push(error);
      }
    }
    if (!completed.temp) {
      try {
        removeTempDirectory(tempDirectory);
        completed.temp = true;
      } catch (error) {
        errors.push(error);
      }
    }
    if (errors.length) {
      const details = errors.map((error) => error?.message || String(error)).join("; ");
      throw new AggregateError(errors, `Isolated Flask cleanup incomplete: ${details} (${tempDirectory})`);
    }
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
      const combined = new AggregateError(
        [error, cleanupError],
        `Isolated server startup failed: ${error.message}`,
        { cause: error },
      );
      combined.retryCleanup = cleanup;
      throw combined;
    }
    error.retryCleanup = cleanup;
    throw error;
  }
}

module.exports = { startIsolatedServer };
