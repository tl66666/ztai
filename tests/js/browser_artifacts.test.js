const assert = require("node:assert/strict");
const path = require("node:path");
const test = require("node:test");

const { artifactNames, cleanupArtifacts } = require("../browser/artifacts.js");

test("artifact names include every browser and viewport even when a browser will skip", () => {
  assert.deepEqual(
    artifactNames(["chromium", "firefox"], ["desktop", "mobile"]),
    [
      "chromium-desktop.png", "chromium-desktop-trace.zip", "chromium-desktop-server.log",
      "chromium-mobile.png", "chromium-mobile-trace.zip", "chromium-mobile-server.log",
      "firefox-desktop.png", "firefox-desktop-trace.zip", "firefox-desktop-server.log",
      "firefox-mobile.png", "firefox-mobile-trace.zip", "firefox-mobile-server.log",
    ],
  );
});

test("suite cleanup removes stale artifacts before skipped tests are registered", () => {
  const removed = [];
  cleanupArtifacts({
    directory: "C:\\artifacts",
    browsers: ["firefox"],
    viewports: ["desktop", "mobile"],
    remove: (file) => removed.push(file),
    ensureDirectory() {},
  });
  assert.deepEqual(removed, [
    path.join("C:\\artifacts", "firefox-desktop.png"),
    path.join("C:\\artifacts", "firefox-desktop-trace.zip"),
    path.join("C:\\artifacts", "firefox-desktop-server.log"),
    path.join("C:\\artifacts", "firefox-mobile.png"),
    path.join("C:\\artifacts", "firefox-mobile-trace.zip"),
    path.join("C:\\artifacts", "firefox-mobile-server.log"),
  ]);
});
