const assert = require("node:assert/strict");
const { createOpportunityHistoryController } = require("../../static/js/opportunity_history.js");

class FakeWindow {
  constructor(initialUrl) {
    this.entries = [new URL(initialUrl)]; this.index = 0; this.location = {};
    Object.defineProperty(this.location, "href", { get: () => this.entries[this.index].href });
    this.history = {
      pushState: (_s, _t, url) => { this.entries.push(new URL(String(url), this.location.href)); this.index += 1; },
      replaceState: (_s, _t, url) => { this.entries[this.index] = new URL(String(url), this.location.href); },
    };
  }
  addEventListener() {}
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

async function main() {
  const browser = new FakeWindow("http://localhost/?page=tracker");
  const requests = [];
  const rendered = [];
  const transitions = [];
  const controller = createOpportunityHistoryController({
    window: browser,
    defaultModule: (page) => (page === "tracker" ? "add" : null),
    onRouteTransition: (previous, next) => transitions.push([previous, next]),
    showPage: () => {}, showModule: () => {}, closeWorkspace: () => {},
    loadWorkspace: async (id, context) => {
      const pending = deferred();
      requests.push({ id, context, pending });
      const value = await pending.promise;
      if (!context.isCurrent()) return { status: "superseded" };
      rendered.push(value);
      return { status: "ok" };
    },
  });

  await controller.sync();
  const first = controller.open(51);
  const entryCount = browser.entries.length;
  const second = controller.open(51);
  assert.equal(browser.entries.length, entryCount, "double-clicking the same opportunity must not add duplicate history");
  assert.equal(requests.length, 1, "double-clicking an in-flight opportunity must reuse its GET");
  const retry = controller.reload(51);
  assert.equal(requests.length, 2, "an explicit retry must always start a fresh GET");
  assert.equal(requests[0].context.isCurrent(), false, "a retry must supersede the old request even for the same ID");
  assert.equal(requests[1].context.isCurrent(), true);
  requests[1].pending.resolve("new response");
  await retry;
  requests[0].pending.resolve("old response");
  await Promise.all([first, second]);
  assert.deepEqual(rendered, ["new response"], "an old response must never overwrite a newer retry");

  await controller.navigate("resume", { module: "jd" });
  const reopened = controller.open(51);
  assert.equal(requests.length, 3, "leaving an opportunity and returning must start a normal GET");
  requests[2].pending.resolve("reopened response");
  await reopened;
  await controller.navigate("resume", { module: "jd" });
  await controller.navigate("interview", { module: "mock" });
  assert.deepEqual(
    transitions.at(-1),
    [{ page: "resume", module: "jd", opportunityId: null, hasOpportunity: false }, { page: "interview", module: "mock", opportunityId: null, hasOpportunity: false }],
    "all navigation paths must pass through one route-transition callback",
  );
  console.log("opportunity load generation behavior: ok");
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
