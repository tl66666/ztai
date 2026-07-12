const assert = require("node:assert/strict");
const test = require("node:test");
const { EventEmitter } = require("node:events");
const { PassThrough } = require("node:stream");

const { startIsolatedServer } = require("../browser/isolated_server.js");

test("startup failure cleans child streams and temp directory before rethrow", async () => {
  const child = new EventEmitter();
  child.stdout = new PassThrough();
  child.stderr = new PassThrough();
  child.exitCode = null;
  child.killedByCleanup = false;
  child.kill = () => {
    child.killedByCleanup = true;
    child.exitCode = 1;
    queueMicrotask(() => child.emit("exit", 1));
    return true;
  };
  const log = new PassThrough();
  let removed = 0;

  await assert.rejects(
    startIsolatedServer({
      label: "failing-start",
      baseURL: "http://127.0.0.1:59999",
      tempDirectory: "C:\\Temp\\jobhunter-e2e-failing-start",
      dbPath: "C:\\Temp\\jobhunter-e2e-failing-start\\jobhunter-e2e.db",
      program: "raise RuntimeError()",
      spawnProcess: () => child,
      waitUntilReady: async () => { throw new Error("readiness failed"); },
      createLogStream: () => log,
      removeTempDirectory: () => { removed += 1; },
    }),
    /readiness failed/,
  );

  assert.equal(child.killedByCleanup, true);
  assert.equal(log.writableEnded, true);
  assert.equal(removed, 1);
});

test("spawn errors are handled and cleaned without an unhandled error event", async () => {
  const child = new EventEmitter();
  child.stdout = new PassThrough();
  child.stderr = new PassThrough();
  child.exitCode = null;
  child.kill = () => { child.exitCode = 1; queueMicrotask(() => child.emit("exit", 1)); return true; };
  const log = new PassThrough();
  let removed = 0;

  const result = startIsolatedServer({
    label: "spawn-error",
    baseURL: "http://127.0.0.1:59998",
    tempDirectory: "C:\\Temp\\jobhunter-e2e-spawn-error",
    dbPath: "C:\\Temp\\jobhunter-e2e-spawn-error\\jobhunter-e2e.db",
    program: "pass",
    spawnProcess: () => child,
    waitUntilReady: () => new Promise(() => {}),
    createLogStream: () => log,
    removeTempDirectory: () => { removed += 1; },
  });
  queueMicrotask(() => child.emit("error", new Error("spawn failed")));

  await assert.rejects(result, /spawn failed/);
  assert.equal(log.writableEnded, true);
  assert.equal(removed, 1);
});
