import { createAgentDrawer } from "./agent-drawer";

interface AgentState {
  currentPage: string;
  currentModule: string;
  currentOpportunityId: number | null;
  currentOpportunityWorkspace?: any;
  editingResumeId?: number | null;
  applications: any[];
  applicationStatuses: string[];
  resumes: any[];
  agentDrawerOpener: Element | null;
}

export interface AgentControllerDependencies {
  state: AgentState;
  byId: (id: string) => HTMLElement | null;
  contextualAgent: any;
  escapeHtml: (value: unknown) => string;
  escapeAttr: (value?: string) => string;
  renderIcons: () => unknown;
  loadCommandCenter: () => unknown;
  documentObject?: Document;
  windowObject?: Window;
}

export interface AgentController {
  bind(): void;
  currentResumeId(): number | null;
  syncContext(): void;
  renderContextChips(): void;
  removeContext(kind: string): void;
  contextPayload(): Record<string, unknown>;
  openDrawer(event?: { currentTarget?: EventTarget | null }): void;
  closeDrawer(): void;
  handleDrawerKeydown(event: KeyboardEvent): void;
}

const RESUME_SELECTOR_BY_MODULE: Record<string, string> = {
  "resume:analysis": "analysisResumeSelect",
  "resume:export": "exportResumeSelect",
  "resume:jd": "tailorResumeSelect",
  "resume:skills": "skillResumeSelect",
  "interview:mock": "interviewResumeSelect",
};

const MODULE_LABELS: Record<string, string> = {
  home: "项目总览",
  resume: "简历实验室",
  interview: "面试训练场",
  tracker: "投递看板",
  agent: "行动指挥台",
};

const DRAWER_OPENERS = new Set([
  "agentLauncher",
  "openAgentWorkspace",
  "openAgentWorkspaceFromHelper",
]);

const CONTEXT_SELECTORS = new Set([
  "analysisResumeSelect",
  "exportResumeSelect",
  "tailorResumeSelect",
  "skillResumeSelect",
  "interviewResumeSelect",
]);

export function createAgentController(
  deps: AgentControllerDependencies,
): AgentController {
  const {
    state,
    byId,
    contextualAgent,
    escapeHtml,
    escapeAttr,
    renderIcons,
    loadCommandCenter,
    documentObject = document,
    windowObject = window,
  } = deps;
  const context = contextualAgent.createContextStore();
  let bound = false;

  function currentResumeId(): number | null {
    if (state.currentOpportunityWorkspace?.resume?.id) {
      return Number(state.currentOpportunityWorkspace.resume.id);
    }
    if (state.currentPage === "resume" && state.editingResumeId) {
      return Number(state.editingResumeId);
    }
    const id = RESUME_SELECTOR_BY_MODULE[
      `${state.currentPage}:${state.currentModule}`
    ];
    return id ? Number((byId(id) as HTMLSelectElement | null)?.value || 0) || null : null;
  }

  function contextPayload(): Record<string, unknown> {
    return context.payload();
  }

  function syncContext(): void {
    context.sync({
      module: state.currentModule
        ? `${state.currentPage}:${state.currentModule}`
        : state.currentPage,
      opportunityId: state.currentOpportunityId,
      resumeId: currentResumeId(),
    });
    renderContextChips();
  }

  function renderContextChips(): void {
    const box = byId("agentContextChips");
    if (!box) return;
    const payload = contextPayload() as any;
    const values: Array<[string, string]> = [];
    if (payload.module) {
      const [page, module] = String(payload.module).split(":");
      const moduleButton = module
        ? documentObject.querySelector(`[data-section-filter="${page}:${module}"]`)
        : null;
      const label = moduleButton?.textContent?.trim() || MODULE_LABELS[page] || page;
      values.push(["module", `模块：${label}`]);
    }
    if (payload.opportunity_id) {
      const opportunity = state.currentOpportunityWorkspace?.opportunity
        || state.applications.find(
          (item) => Number(item.id) === Number(payload.opportunity_id),
        );
      const label = opportunity
        ? `${opportunity.company} / ${opportunity.job_title}`
        : `#${payload.opportunity_id}`;
      values.push(["opportunity", `机会：${label}`]);
    }
    if (payload.resume_id) {
      const resume = state.resumes.find(
        (item) => Number(item.id) === Number(payload.resume_id),
      );
      values.push(["resume", `简历：${resume?.title || `#${payload.resume_id}`}`]);
    }
    box.innerHTML = values.length
      ? values.map(([kind, label]) => `
        <span class="agent-context-chip">${escapeHtml(label)}<button type="button" data-remove-agent-context="${kind}" aria-label="移除${escapeAttr(label)}上下文" title="移除上下文"><i data-lucide="x"></i></button></span>
      `).join("")
      : '<span class="agent-context-empty">未附加上下文</span>';
    renderIcons();
  }

  function removeContext(kind: string): void {
    context.remove(kind);
    renderContextChips();
  }

  const drawer = createAgentDrawer({
    state,
    byId,
    syncContext,
    loadCommandCenter,
    documentObject,
    windowObject,
  });

  function bind(): void {
    if (bound) return;
    bound = true;
    documentObject.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const control = target.closest<HTMLElement>(
        "#agentLauncher, #openAgentWorkspace, #openAgentWorkspaceFromHelper, "
        + "#closeAgentDrawer, #agentDrawerBackdrop",
      );
      if (control?.id && DRAWER_OPENERS.has(control.id)) {
        drawer.open({ currentTarget: control });
        return;
      }
      if (control?.id === "closeAgentDrawer" || control?.id === "agentDrawerBackdrop") {
        drawer.close();
        return;
      }
      const remove = target.closest<HTMLElement>("[data-remove-agent-context]");
      if (remove?.dataset.removeAgentContext) {
        removeContext(remove.dataset.removeAgentContext);
      }
    });
    documentObject.addEventListener("change", (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && CONTEXT_SELECTORS.has(target.id)) {
        syncContext();
      }
    });
    documentObject.addEventListener("keydown", drawer.handleKeydown);
  }

  return {
    bind,
    currentResumeId,
    syncContext,
    renderContextChips,
    removeContext,
    contextPayload,
    openDrawer: drawer.open,
    closeDrawer: drawer.close,
    handleDrawerKeydown: drawer.handleKeydown,
  };
}
