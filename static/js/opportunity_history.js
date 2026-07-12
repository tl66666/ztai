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
      module: url.searchParams.get("module"),
      opportunityId,
      hasOpportunity: rawOpportunity !== null,
    };
  }

  function createOpportunityHistoryController(options) {
    const windowObject = options.window;
    let bound = false;

    function routeUrl(page, settings = {}) {
      const url = new URL(windowObject.location.href);
      url.searchParams.set("page", page);
      url.searchParams.delete("record");
      if (settings.module) url.searchParams.set("module", settings.module);
      else url.searchParams.delete("module");
      if (settings.opportunityId) url.searchParams.set("opportunity", String(settings.opportunityId));
      else url.searchParams.delete("opportunity");
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
      if (route.page && route.module) options.showModule?.(route.page, route.module);
      if (route.page === "tracker" && route.opportunityId !== null) {
        let result;
        try {
          result = await options.loadWorkspace(route.opportunityId, { routeDriven: true });
        } catch (error) {
          result = { status: "retryable", error };
        }
        const status = result === true ? "ok" : result === false ? "stale" : result?.status;
        if (status === "stale" || status === "forbidden") {
          options.closeWorkspace({ routeDriven: true, page: route.page });
          removeOpportunityFromUrl();
          if (status === "forbidden") options.notifyForbidden?.(result);
          else options.notifyStale?.(result);
        } else if (status === "retryable") {
          options.notifyRetryable?.(result);
        }
        return result;
      }
      options.closeWorkspace({ routeDriven: true, page: route.page });
      if (route.hasOpportunity) removeOpportunityFromUrl();
      return { status: "ok" };
    }

    async function sync() {
      return activate(readRoute(windowObject));
    }

    async function open(opportunityId, settings = {}) {
      const id = Number(opportunityId);
      if (!Number.isSafeInteger(id) || id <= 0) {
        options.closeWorkspace({ routeDriven: false });
        removeOpportunityFromUrl();
        return false;
      }
      const historyMode = settings.historyMode || "push";
      const url = routeUrl("tracker", { opportunityId: id });
      if (historyMode === "push") windowObject.history.pushState({}, "", url);
      else if (historyMode === "replace") windowObject.history.replaceState({}, "", url);
      return activate({ page: "tracker", module: null, opportunityId: id, hasOpportunity: true });
    }

    async function navigate(page, settings = {}) {
      const historyMode = settings.historyMode || "push";
      const url = routeUrl(page, settings);
      if (historyMode === "push") windowObject.history.pushState({}, "", url);
      else if (historyMode === "replace") windowObject.history.replaceState({}, "", url);
      return activate({
        page, module: settings.module || null,
        opportunityId: settings.opportunityId || null,
        hasOpportunity: Boolean(settings.opportunityId),
      });
    }

    async function reload(opportunityId) {
      const id = Number(opportunityId);
      return activate({ page: "tracker", module: null, opportunityId: id, hasOpportunity: true });
    }

    async function close(settings = {}) {
      options.closeWorkspace({
        routeDriven: !settings.restoreFocus,
        restoreFocus: Boolean(settings.restoreFocus),
        page: settings.page || "tracker",
      });
      const historyMode = settings.historyMode || "replace";
      if (historyMode === "none") return;
      const url = routeUrl(settings.page || "tracker", { module: settings.module || "board" });
      if (historyMode === "push") windowObject.history.pushState({}, "", url);
      else windowObject.history.replaceState({}, "", url);
    }

    function bind() {
      if (bound) return;
      bound = true;
      windowObject.addEventListener("popstate", () => {
        sync().catch((error) => options.notifyRetryable?.({ status: "retryable", error }));
      });
    }

    return { bind, close, navigate, open, readRoute: () => readRoute(windowObject), reload, sync };
  }

  return { createOpportunityHistoryController, readRoute };
}));
