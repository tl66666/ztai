const assert = require("node:assert/strict");
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
    "C:\\artifacts\\firefox-desktop.png",
    "C:\\artifacts\\firefox-desktop-trace.zip",
    "C:\\artifacts\\firefox-desktop-server.log",
    "C:\\artifacts\\firefox-mobile.png",
    "C:\\artifacts\\firefox-mobile-trace.zip",
    "C:\\artifacts\\firefox-mobile-server.log",
  ]);
});
