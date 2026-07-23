type HistoryMode = "push" | "replace" | "none";

interface Route {
  page: string | null;
  module: string | null;
}

interface NavigationHistory {
  navigate(
    page: string,
    settings?: { module?: string | null; historyMode?: HistoryMode },
  ): Promise<unknown> | unknown;
  sync(): Promise<unknown>;
}

interface ShellState {
  currentPage: string;
  currentModule: string;
  pendingApplicationHandoff?: unknown;
  matchOpportunityId?: number | null;
  interviewOpportunityHandoff?: unknown;
}

export interface ShellControllerDependencies {
  state: ShellState;
  byId: (id: string) => HTMLElement | null;
  history: () => NavigationHistory;
  playTone: (type: string) => unknown;
  syncAgentContext: () => unknown;
  loadAgentCommandCenter: () => unknown;
  routeLeavesFlow: (
    previous: Route,
    next: Route,
    page: string,
    module: string,
  ) => boolean;
  clearApplicationHandoff: () => unknown;
  clearMatchOpportunityLink: () => unknown;
  pageTitles?: Record<string, string>;
  windowObject?: Window;
  documentObject?: Document;
}

export interface ShellController {
  bindNavigation(): void;
  renderPage(page: string): void;
  applyInitialRoute(): Promise<void>;
  filterModules(page: string, module: string, activeButton: Element): void;
  renderModule(page: string, module: string): void;
  navigate(
    page: string,
    module?: string | null,
    options?: { historyMode?: HistoryMode },
  ): Promise<unknown> | unknown;
  jumpToModule(page: string, module: string): Promise<unknown> | unknown;
  defaultModuleForPage(page: string): string | null;
  handleRouteTransition(previous: Route, next: Route): void;
  focusCleanedRoute(route: Route): void;
}

const DEFAULT_PAGE_TITLES: Record<string, string> = {
  home: "项目总览",
  resume: "简历实验室",
  interview: "面试训练场",
  tracker: "投递看板",
  agent: "求职指挥台",
};

export function createShellController(
  deps: ShellControllerDependencies,
): ShellController {
  const {
    state,
    byId,
    history,
    playTone,
    syncAgentContext,
    loadAgentCommandCenter,
    routeLeavesFlow,
    clearApplicationHandoff,
    clearMatchOpportunityLink,
    pageTitles = DEFAULT_PAGE_TITLES,
    windowObject = window,
    documentObject = document,
  } = deps;
  let navigationBound = false;

  function bindNavigation(): void {
    if (navigationBound) return;
    navigationBound = true;
    documentObject.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const item = target.closest<HTMLElement>("[data-page]");
      const page = item?.dataset.page;
      if (!page) return;
      playTone("jump");
      void navigate(page);
    });
  }

  function renderPage(page: string): void {
    const pageNode = byId(`page-${page}`);
    if (!pageNode) return;
    if (state.currentPage !== page) state.currentModule = "";
    state.currentPage = page;
    documentObject.querySelectorAll(".page").forEach((item) => item.classList.remove("active"));
    pageNode.classList.add("active");
    documentObject.querySelectorAll<HTMLElement>(".nav-item").forEach((item) => {
      item.classList.toggle("active", item.dataset.page === page);
    });
    const title = byId("pageTitle");
    if (title) title.textContent = pageTitles[page] || "JobHunter AI";
    syncAgentContext();
    if (page === "agent") loadAgentCommandCenter();
    windowObject.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function applyInitialRoute(): Promise<void> {
    await history().sync();
    const params = new URLSearchParams(windowObject.location.search);
    if (params.get("record") !== "audio") return;
    windowObject.setTimeout(() => {
      const card = [...documentObject.querySelectorAll<HTMLElement>(".record-card")]
        .find((item) => (
          item.textContent?.includes("语音")
          || item.textContent?.includes("录音")
          || item.textContent?.includes("表达")
        ));
      card?.querySelector<HTMLButtonElement>(".record-actions button")?.click();
    }, 500);
  }

  function filterModules(page: string, module: string, activeButton: Element): void {
    documentObject.querySelectorAll(`[data-filter-page="${page}"] button`).forEach((button) => {
      button.classList.toggle("active", button === activeButton);
    });
    documentObject
      .querySelectorAll<HTMLElement>(`.module-panel[data-module-page="${page}"]`)
      .forEach((panel) => {
        panel.classList.toggle("is-filtered-out", panel.dataset.module !== module);
      });
  }

  function renderModule(page: string, module: string): void {
    if (page === state.currentPage) state.currentModule = module || "";
    const button = documentObject.querySelector(
      `[data-section-filter="${page}:${module}"]`,
    );
    if (button) filterModules(page, module, button);
    syncAgentContext();
  }

  function navigate(
    page: string,
    module: string | null = null,
    options: { historyMode?: HistoryMode } = {},
  ): Promise<unknown> | unknown {
    return history().navigate(page, {
      module,
      historyMode: options.historyMode || "push",
    });
  }

  function jumpToModule(page: string, module: string): Promise<unknown> | unknown {
    return navigate(page, module);
  }

  function defaultModuleForPage(page: string): string | null {
    const value = documentObject
      .querySelector<HTMLElement>(`[data-filter-page="${page}"] [data-section-filter]`)
      ?.dataset.sectionFilter;
    return value?.split(":")[1] || null;
  }

  function handleRouteTransition(previous: Route, next: Route): void {
    if (
      state.pendingApplicationHandoff
      && routeLeavesFlow(previous, next, "tracker", "add")
    ) {
      clearApplicationHandoff();
    }
    if (
      state.matchOpportunityId
      && routeLeavesFlow(previous, next, "resume", "jd")
    ) {
      clearMatchOpportunityLink();
    }
    if (
      state.interviewOpportunityHandoff
      && routeLeavesFlow(previous, next, "interview", "mock")
    ) {
      state.interviewOpportunityHandoff = null;
    }
  }

  function focusCleanedRoute(route: Route): void {
    const panel = route.module
      ? documentObject.querySelector(
          `.module-panel[data-module-page="${route.page}"][data-module="${route.module}"]:not(.is-filtered-out)`,
        )
      : null;
    const target = panel?.querySelector<HTMLElement>("h2, h3") || byId("pageTitle");
    if (!target) return;
    target.tabIndex = -1;
    target.focus({ preventScroll: true });
  }

  return {
    bindNavigation,
    renderPage,
    applyInitialRoute,
    filterModules,
    renderModule,
    navigate,
    jumpToModule,
    defaultModuleForPage,
    handleRouteTransition,
    focusCleanedRoute,
  };
}
