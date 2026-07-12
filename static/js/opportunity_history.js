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
    let activeRoute = null;
    let activationGeneration = 0;
    let pendingOpen = null;

    function resolveRoute(route) {
      const resolved = {
        page: route.page || null,
        module: route.module || null,
        opportunityId: route.opportunityId || null,
        hasOpportunity: Boolean(route.hasOpportunity),
      };
      if (resolved.page && !resolved.module && resolved.opportunityId === null) {
        resolved.module = options.defaultModule?.(resolved.page) || null;
      }
      return resolved;
    }

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

    function writeRoute(url, historyMode) {
      if (new URL(windowObject.location.href).href === url.href) return;
      if (historyMode === "push") windowObject.history.pushState({}, "", url);
      else if (historyMode === "replace") windowObject.history.replaceState({}, "", url);
    }

    function applyRoute(rawRoute) {
      const route = resolveRoute(rawRoute);
      const previous = activeRoute;
      if (previous) options.onRouteTransition?.(previous, route);
      activeRoute = route;
      if (route.page) options.showPage(route.page);
      if (route.page && route.module) options.showModule?.(route.page, route.module);
      return route;
    }

    async function activate(rawRoute, settings = {}) {
      const generation = ++activationGeneration;
      const request = {
        generation,
        isCurrent: () => generation === activationGeneration,
        routeDriven: true,
      };
      const route = applyRoute(rawRoute);
      if (route.page === "tracker" && route.opportunityId !== null) {
        let result;
        try {
          result = await options.loadWorkspace(route.opportunityId, request);
        } catch (error) {
          result = request.isCurrent() ? { status: "retryable", error } : { status: "superseded" };
        }
        if (!request.isCurrent()) return { status: "superseded" };
        const status = result === true ? "ok" : result === false ? "stale" : result?.status;
        if (status === "stale" || status === "forbidden") {
          options.closeWorkspace({ routeDriven: true, page: route.page });
          removeOpportunityFromUrl();
          const cleanedRoute = applyRoute({ ...route, module: null, opportunityId: null, hasOpportunity: false });
          options.focusRoute?.(cleanedRoute);
          if (status === "forbidden") options.notifyForbidden?.(result);
          else options.notifyStale?.(result);
        } else if (status === "retryable") {
          options.notifyRetryable?.(result);
        }
        return result;
      }
      options.closeWorkspace({ routeDriven: true, page: route.page, ...(settings.closeContext || {}) });
      if (route.hasOpportunity) {
        removeOpportunityFromUrl();
        applyRoute({ ...route, module: null, opportunityId: null, hasOpportunity: false });
      }
      return { status: "ok" };
    }

    async function sync() {
      pendingOpen = null;
      return activate(readRoute(windowObject));
    }

    async function open(opportunityId, settings = {}) {
      const id = Number(opportunityId);
      if (!Number.isSafeInteger(id) || id <= 0) {
        options.closeWorkspace({ routeDriven: false });
        removeOpportunityFromUrl();
        return false;
      }
      if (pendingOpen?.id === id && activeRoute?.page === "tracker" && activeRoute.opportunityId === id) {
        return pendingOpen.promise;
      }
      const historyMode = settings.historyMode || "push";
      const url = routeUrl("tracker", { opportunityId: id });
      writeRoute(url, historyMode);
      const marker = {
        id,
        promise: activate({ page: "tracker", module: null, opportunityId: id, hasOpportunity: true }),
      };
      pendingOpen = marker;
      try {
        return await marker.promise;
      } finally {
        if (pendingOpen === marker) pendingOpen = null;
      }
    }

    async function navigate(page, settings = {}) {
      pendingOpen = null;
      const historyMode = settings.historyMode || "push";
      const url = routeUrl(page, settings);
      writeRoute(url, historyMode);
      return activate({
        page, module: settings.module || null,
        opportunityId: settings.opportunityId || null,
        hasOpportunity: Boolean(settings.opportunityId),
      });
    }

    async function reload(opportunityId) {
      pendingOpen = null;
      const id = Number(opportunityId);
      return activate({ page: "tracker", module: null, opportunityId: id, hasOpportunity: true });
    }

    async function close(settings = {}) {
      pendingOpen = null;
      const historyMode = settings.historyMode || "replace";
      const url = routeUrl(settings.page || "tracker", { module: settings.module || "board" });
      if (historyMode !== "none") writeRoute(url, historyMode);
      return activate({
        page: settings.page || "tracker",
        module: settings.module || "board",
        opportunityId: null,
        hasOpportunity: false,
      }, {
        closeContext: {
          routeDriven: !settings.restoreFocus,
          restoreFocus: Boolean(settings.restoreFocus),
          page: settings.page || "tracker",
        },
      });
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
