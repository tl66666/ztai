const assert = require("node:assert/strict");
const { createOpportunityHistoryController } = require("../../static/js/opportunity_history.js");

class FakeWindow {
  constructor(initialUrl) {
    this.entries = [new URL(initialUrl)];
    this.index = 0;
    this.listeners = new Map();
    this.location = {};
    Object.defineProperty(this.location, "href", {
      get: () => this.entries[this.index].href,
    });
    this.history = {
      pushState: (_state, _title, url) => {
        this.entries = this.entries.slice(0, this.index + 1);
        this.entries.push(new URL(String(url), this.location.href));
        this.index += 1;
      },
      replaceState: (_state, _title, url) => {
        this.entries[this.index] = new URL(String(url), this.location.href);
      },
    };
  }

  addEventListener(name, listener) {
    const listeners = this.listeners.get(name) || [];
    listeners.push(listener);
    this.listeners.set(name, listeners);
  }

  async dispatch(name) {
    await Promise.all((this.listeners.get(name) || []).map((listener) => listener()));
  }

  async back() {
    if (this.index > 0) this.index -= 1;
    await this.dispatch("popstate");
  }

  async forward() {
    if (this.index < this.entries.length - 1) this.index += 1;
    await this.dispatch("popstate");
  }
}

async function main() {
  const browser = new FakeWindow("http://localhost/?page=home");
  const state = { page: null, currentOpportunityId: null, loads: [], closes: 0, notices: [] };
  const controller = createOpportunityHistoryController({
    window: browser,
    showPage: (page) => { state.page = page; },
    loadWorkspace: async (id) => {
      state.loads.push(id);
      if (id === 404) return false;
      state.currentOpportunityId = id;
      return true;
    },
    closeWorkspace: () => {
      state.currentOpportunityId = null;
      state.closes += 1;
    },
    notifyStale: () => state.notices.push("stale"),
  });
  controller.bind();

  await controller.sync();
  assert.equal(state.page, "home");
  assert.equal(state.currentOpportunityId, null);

  await controller.open(11);
  assert.equal(state.page, "tracker");
  await controller.open(22);
  assert.equal(state.currentOpportunityId, 22);
  assert.deepEqual(state.loads, [11, 22]);

  await browser.back();
  assert.equal(state.currentOpportunityId, 11, "Back must restore opportunity A");
  await browser.back();
  assert.equal(state.currentOpportunityId, null, "Back to the baseline must close the workspace");
  assert.equal(state.page, "home", "Back must restore the active page");

  await browser.forward();
  assert.equal(state.currentOpportunityId, 11, "Forward must restore opportunity A");
  await browser.forward();
  assert.equal(state.currentOpportunityId, 22, "Forward must restore opportunity B");
  assert.deepEqual(state.loads, [11, 22, 11, 11, 22]);

  browser.history.pushState({}, "", "?page=tracker&opportunity=invalid");
  await browser.dispatch("popstate");
  assert.equal(state.currentOpportunityId, null);
  assert.equal(new URL(browser.location.href).searchParams.has("opportunity"), false);

  await controller.open(404);
  assert.equal(state.currentOpportunityId, null, "A stale owned route must close the workspace");
  assert.equal(new URL(browser.location.href).searchParams.has("opportunity"), false);
  assert.deepEqual(state.notices, ["stale"]);

  console.log("opportunity history behavior: ok");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
