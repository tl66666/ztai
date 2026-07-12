const fs = require("node:fs");
const path = require("node:path");

function artifactNames(browsers, viewports) {
  return browsers.flatMap((browser) => viewports.flatMap((viewport) => {
    const base = `${browser}-${viewport}`;
    return [`${base}.png`, `${base}-trace.zip`, `${base}-server.log`];
  }));
}

function cleanupArtifacts(options) {
  const {
    directory,
    browsers,
    viewports,
    ensureDirectory = () => fs.mkdirSync(directory, { recursive: true }),
    remove = (file) => fs.rmSync(file, { force: true }),
  } = options;
  ensureDirectory();
  artifactNames(browsers, viewports).forEach((name) => remove(path.join(directory, name)));
}

module.exports = { artifactNames, cleanupArtifacts };
