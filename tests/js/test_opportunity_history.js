const assert = require("node:assert/strict");
const { createOpportunityHistoryController } = require("../../static/js/opportunity_history.js");

class FakeWindow {
  constructor(initialUrl) {
    this.entries = [new URL(initialUrl)]; this.index = 0; this.listeners = new Map(); this.location = {};
    Object.defineProperty(this.location, "href", { get: () => this.entries[this.index].href });
    this.history = {
      pushState: (_s, _t, url) => { this.entries = this.entries.slice(0, this.index + 1); this.entries.push(new URL(String(url), this.location.href)); this.index += 1; },
      replaceState: (_s, _t, url) => { this.entries[this.index] = new URL(String(url), this.location.href); },
    };
  }
  addEventListener(name, listener) { this.listeners.set(name, [...(this.listeners.get(name) || []), listener]); }
  async dispatch(name) { await Promise.all((this.listeners.get(name) || []).map((listener) => listener())); }
  async back() { if (this.index > 0) this.index -= 1; await this.dispatch("popstate"); }
  async forward() { if (this.index < this.entries.length - 1) this.index += 1; await this.dispatch("popstate"); }
}

async function main() {
  const browser = new FakeWindow("http://localhost/?page=home");
  const outcomes = new Map();
  const state = { page: null, module: null, current: null, loads: [], closes: [], notices: [] };
  const controller = createOpportunityHistoryController({
    window: browser,
    showPage: (page) => { state.page = page; },
    showModule: (page, module) => { state.page = page; state.module = module; },
    loadWorkspace: async (id) => {
      state.loads.push(id);
      const outcome = outcomes.get(id) || { status: "ok" };
      if (outcome.status === "throw") throw new Error("offline");
      if (outcome.status === "ok") state.current = id;
      return outcome;
    },
    closeWorkspace: (context) => { state.current = null; state.closes.push(context); },
    notifyStale: () => state.notices.push("stale"),
    notifyForbidden: () => state.notices.push("forbidden"),
    notifyRetryable: () => state.notices.push("retryable"),
  });
  controller.bind();
  await controller.sync();
  assert.equal(browser.entries.length, 1, "initial route sync must not push history");

  await controller.open(11);
  await controller.navigate("resume", { module: "jd" });
  await controller.navigate("interview", { module: "mock" });
  assert.equal(new URL(browser.location.href).searchParams.has("opportunity"), false);
  await browser.back();
  assert.deepEqual([state.page, state.module, state.current], ["resume", "jd", null]);
  await browser.back();
  assert.deepEqual([state.page, state.current], ["tracker", 11]);

  const beforeRefresh = browser.entries.length;
  const refreshed = createOpportunityHistoryController({
    window: browser,
    showPage: (page) => { state.page = page; },
    showModule: () => {},
    loadWorkspace: async (id) => { state.loads.push(id); state.current = id; return { status: "ok" }; },
    closeWorkspace: () => { state.current = null; },
  });
  await refreshed.sync();
  assert.equal(state.current, 11, "shared URL refresh must restore the workspace");
  assert.equal(browser.entries.length, beforeRefresh, "refresh sync must not push history");

  outcomes.set(404, { status: "stale" }); await controller.open(404);
  assert.equal(state.current, null); assert.equal(new URL(browser.location.href).searchParams.has("opportunity"), false);
  outcomes.set(403, { status: "forbidden" }); await controller.open(403);
  assert.equal(state.notices.at(-1), "forbidden"); assert.equal(new URL(browser.location.href).searchParams.has("opportunity"), false);
  outcomes.set(500, { status: "retryable" }); await controller.open(500);
  assert.equal(new URL(browser.location.href).searchParams.get("opportunity"), "500", "500 must preserve deep link");
  outcomes.set(500, { status: "ok" }); await controller.reload(500);
  assert.equal(state.current, 500, "retry must load the same ID without pushing");
  outcomes.set(599, { status: "throw" }); await controller.open(599);
  assert.equal(new URL(browser.location.href).searchParams.get("opportunity"), "599");
  assert.equal(state.notices.at(-1), "retryable", "rejected loads must be contained");

  await controller.close({ historyMode: "push", restoreFocus: true });
  assert.equal(state.closes.at(-1).restoreFocus, true);
  assert.equal(new URL(browser.location.href).searchParams.has("opportunity"), false);
  console.log("opportunity history quality behavior: ok");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
