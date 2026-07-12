(function exposeOpportunityHistory(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.OpportunityHistory = api;
}(typeof globalThis !== "undefined" ? globalThis : this, function buildOpportunityHistory() {
  function readRoute(windowObject) {
    const url = new URL(windowObject.location.href);
    const rawOpportunity = url.searchParams.get("opportunity");
    const numericOpportunity = rawOpportunity === null ? null : Number(rawOpportunity);
    const opportunityId = Number.isSafeInteger(numericOpportunity) && numericOpportunity > 0
      && String(numericOpportunity) === rawOpportunity
      ? numericOpportunity
      : null;
    return {
      page: url.searchParams.get("page"),
      opportunityId,
      hasOpportunity: rawOpportunity !== null,
    };
  }

  function createOpportunityHistoryController(options) {
    const windowObject = options.window;
    let bound = false;

    function opportunityUrl(opportunityId) {
      const url = new URL(windowObject.location.href);
      url.searchParams.set("page", "tracker");
      url.searchParams.delete("module");
      url.searchParams.set("opportunity", String(opportunityId));
      return url;
    }

    function removeOpportunityFromUrl() {
      const url = new URL(windowObject.location.href);
      if (!url.searchParams.has("opportunity")) return;
      url.searchParams.delete("opportunity");
      windowObject.history.replaceState({}, "", url);
    }

    async function activate(route) {
      if (route.page) options.showPage(route.page);
      if (route.page === "tracker" && route.opportunityId !== null) {
        const loaded = await options.loadWorkspace(route.opportunityId);
        if (loaded === false) {
          options.closeWorkspace();
          removeOpportunityFromUrl();
          options.notifyStale?.();
        }
        return loaded;
      }
      options.closeWorkspace();
      if (route.hasOpportunity) removeOpportunityFromUrl();
      return true;
    }

    async function sync() {
      return activate(readRoute(windowObject));
    }

    async function open(opportunityId, settings = {}) {
      const id = Number(opportunityId);
      if (!Number.isSafeInteger(id) || id <= 0) {
        options.closeWorkspace();
        removeOpportunityFromUrl();
        return false;
      }
      const historyMode = settings.historyMode || "push";
      if (historyMode === "push") {
        windowObject.history.pushState({}, "", opportunityUrl(id));
      } else if (historyMode === "replace") {
        windowObject.history.replaceState({}, "", opportunityUrl(id));
      }
      return activate({ page: "tracker", opportunityId: id, hasOpportunity: true });
    }

    function close(settings = {}) {
      options.closeWorkspace();
      if ((settings.historyMode || "replace") !== "none") removeOpportunityFromUrl();
    }

    function bind() {
      if (bound) return;
      bound = true;
      windowObject.addEventListener("popstate", () => sync());
    }

    return { bind, close, open, readRoute: () => readRoute(windowObject), sync };
  }

  return { createOpportunityHistoryController, readRoute };
}));
