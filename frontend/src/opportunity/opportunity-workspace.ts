import type { OpportunityControllerDependencies } from "./opportunity-controller";
import { createOpportunityWorkspaceRenderer } from "./opportunity-workspace-renderer";

export interface OpportunityWorkspace {
  open(id: number, options?: any): Promise<unknown>;
  load(id: number, request?: any): Promise<any>;
  showError(opportunityId: number, message: string): void;
  retry(opportunityId: number): unknown;
  reset(context?: any): void;
  close(): unknown;
  selectTab(selectedTab: HTMLElement | null, moveFocus?: boolean): void;
  handleTabKeydown(event: KeyboardEvent): void;
  render(workspace: any): void;
  date(value: unknown, fallback?: string): string;
  renderOverview(workspace: any): void;
  renderMatch(workspace: any): void;
  useJd(): void;
  renderResume(workspace: any): void;
  openResume(resumeId: number, hasOriginal: boolean): unknown;
  renderInterview(workspace: any): void;
  prepareInterview(actionId?: number | null): void;
  continueInterview(sessionId: number): Promise<void>;
  renderTimeline(workspace: any): void;
}

function required<T extends HTMLElement>(
  byId: OpportunityControllerDependencies["byId"],
  id: string,
): T {
  const node = byId(id);
  if (!node) throw new Error(`Missing opportunity workspace control: #${id}`);
  return node as T;
}

export function createOpportunityWorkspace(
  deps: OpportunityControllerDependencies,
): OpportunityWorkspace {
  const {
    state,
    request,
    byId,
    escapeHtml,
    renderIcons,
    syncAgentContext,
    filterModules,
    renderMatchOpportunityNotice,
    jumpToModule,
    openOriginalResume,
    fillResume,
    buildInterviewHandoff,
    toast,
    openInterviewRoom,
    history,
  } = deps;
  const renderer = createOpportunityWorkspaceRenderer(deps);

  async function open(id: number, options: any = {}): Promise<unknown> {
    if (options.updateUrl !== false && document.activeElement instanceof HTMLElement) {
      state.opportunityOpener = document.activeElement;
    }
    const historyMode = options.historyMode || (options.updateUrl === false ? "none" : "push");
    return history.open(id, { historyMode });
  }

  async function load(id: number, requestState: any = {}): Promise<any> {
    const opportunityId = Number(id);
    if (!Number.isInteger(opportunityId) || opportunityId <= 0) return false;
    const generation = ++state.opportunityLoadGeneration;
    const isCurrent = () => generation === state.opportunityLoadGeneration
      && state.currentOpportunityId === opportunityId
      && (!requestState.isCurrent || requestState.isCurrent());
    state.currentOpportunityId = opportunityId;
    const boardButton = document.querySelector('[data-section-filter="tracker:board"]');
    if (boardButton) filterModules("tracker", "board", boardButton);
    required(byId, "opportunityWorkspace").classList.remove("hidden");
    required(byId, "opportunityWorkspaceError").classList.add("hidden");
    required(byId, "opportunityWorkspaceTitle").textContent = "正在加载机会详情";
    required(byId, "opportunityWorkspaceSubtitle").textContent = "正在读取本地关联记录...";

    let workspace;
    try {
      workspace = await request(`/opportunities/${opportunityId}/workspace`);
    } catch {
      if (!isCurrent()) return { status: "superseded" };
      showError(opportunityId, "网络连接失败，请检查连接后重试。");
      return { status: "retryable" };
    }
    if (!isCurrent()) return { status: "superseded" };
    if (!workspace.success) {
      if ([404, 410].includes(workspace.http_status)) return { status: "stale" };
      if (workspace.http_status === 403) return { status: "forbidden" };
      showError(opportunityId, "机会详情暂时无法加载，请稍后重试。");
      return { status: "retryable" };
    }
    state.currentOpportunityWorkspace = workspace;
    renderer.render(workspace);
    syncAgentContext();
    selectTab(required(byId, "opportunity-tab-overview"), false);
    required(byId, "opportunityWorkspace").scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
    return { status: "ok" };
  }

  function showError(opportunityId: number, message: string): void {
    required(byId, "opportunityWorkspaceTitle").textContent = "机会详情暂时不可用";
    required(byId, "opportunityWorkspaceSubtitle").textContent = "链接已保留，可直接重试。";
    const error = required(byId, "opportunityWorkspaceError");
    error.classList.remove("hidden");
    error.innerHTML = `${escapeHtml(message)}<button type="button" class="ghost" onclick="retryOpportunityWorkspace(${opportunityId})"><i data-lucide="refresh-cw"></i>重试</button>`;
    renderIcons();
  }

  function retry(opportunityId: number): unknown {
    required(byId, "opportunityWorkspaceError").classList.add("hidden");
    return history.reload(opportunityId);
  }

  function reset(context: any = {}): void {
    const workspace = required(byId, "opportunityWorkspace");
    const wasOpen = state.currentOpportunityId !== null
      || !workspace.classList.contains("hidden");
    state.opportunityLoadGeneration += 1;
    state.currentOpportunityId = null;
    state.currentOpportunityWorkspace = null;
    syncAgentContext();
    workspace.classList.add("hidden");
    required(byId, "opportunityWorkspaceError").classList.add("hidden");
    if (!wasOpen) return;
    const opener = context.restoreFocus && state.opportunityOpener?.isConnected
      ? state.opportunityOpener
      : (context.page === "tracker" ? byId("applicationBoardHeading") : byId("pageTitle"));
    state.opportunityOpener = null;
    opener?.focus({ preventScroll: true });
  }

  function close(): unknown {
    return history.close({ historyMode: "push", restoreFocus: true });
  }

  function selectTab(selectedTab: HTMLElement | null, moveFocus = true): void {
    if (!selectedTab) return;
    document.querySelectorAll<HTMLElement>('.opportunity-tabs [role="tab"]').forEach((tab) => {
      const selected = tab === selectedTab;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      byId(tab.getAttribute("aria-controls") || "")?.classList.toggle("hidden", !selected);
    });
    if (moveFocus) selectedTab.focus();
  }

  function handleTabKeydown(event: KeyboardEvent): void {
    if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const tabs = [...document.querySelectorAll<HTMLElement>('.opportunity-tabs [role="tab"]')];
    const current = tabs.indexOf(event.currentTarget as HTMLElement);
    let next = current;
    if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
    if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    selectTab(tabs[next]);
  }

  function useJd(): void {
    const opportunity = state.currentOpportunityWorkspace?.opportunity;
    if (!opportunity) return;
    state.matchOpportunityId = opportunity.id;
    renderMatchOpportunityNotice();
    required<HTMLInputElement>(byId, "jobTitleInput").value = opportunity.job_title || "";
    required<HTMLTextAreaElement>(byId, "jdInput").value = opportunity.jd_text || "";
    if (opportunity.resume_id) {
      required<HTMLSelectElement>(byId, "tailorResumeSelect").value = String(opportunity.resume_id);
    }
    jumpToModule("resume", "jd");
  }

  function openResume(resumeId: number, hasOriginal: boolean): unknown {
    if (hasOriginal) return openOriginalResume(resumeId);
    jumpToModule("resume", "input");
    return fillResume(resumeId);
  }

  function prepareInterview(actionId: number | null = null): void {
    const workspace = state.currentOpportunityWorkspace;
    if (!workspace?.opportunity) return;
    state.interviewOpportunityHandoff = buildInterviewHandoff({
      opportunityId: workspace.opportunity.id,
      resumeId: workspace.resume?.id,
      actionId,
      jobTitle: workspace.opportunity.job_title,
      jd: workspace.opportunity.jd_text,
    });
    if (!state.interviewOpportunityHandoff) {
      toast("请先为该机会关联简历");
      return;
    }
    required<HTMLInputElement>(byId, "interviewJobTitle").value = workspace.opportunity.job_title || "";
    required<HTMLTextAreaElement>(byId, "interviewJd").value = workspace.opportunity.jd_text || "";
    if (workspace.resume?.id) {
      required<HTMLSelectElement>(byId, "interviewResumeSelect").value = String(workspace.resume.id);
    }
    jumpToModule("interview", "mock");
    toast("已关联机会和简历，可开始模拟面试");
  }

  async function continueInterview(sessionId: number): Promise<void> {
    const data = await request(`/interview/sessions/${sessionId}`);
    if (!data.success) {
      toast(data.message || "面试记录无法继续");
      return;
    }
    state.activeInterview = String(sessionId);
    state.pendingInterviewSubmission = null;
    state.interviewSubmitting = false;
    jumpToModule("interview", "mock");
    openInterviewRoom(data);
  }

  return {
    open,
    load,
    showError,
    retry,
    reset,
    close,
    selectTab,
    handleTabKeydown,
    render: renderer.render,
    date: renderer.date,
    renderOverview: renderer.overview,
    renderMatch: renderer.match,
    useJd,
    renderResume: renderer.resume,
    openResume,
    renderInterview: renderer.interview,
    prepareInterview,
    continueInterview,
    renderTimeline: renderer.timeline,
  };
}
