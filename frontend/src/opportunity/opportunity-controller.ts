import { createApplicationBoard } from "./application-board";
import { createOpportunityDashboard } from "./opportunity-dashboard";
import { createOpportunityWorkspace } from "./opportunity-workspace";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown>;
};
export type OpportunityRequest = (
  path: string,
  options?: RequestOptions,
) => Promise<any>;

export interface OpportunityControllerDependencies {
  userId: number;
  state: any;
  request: OpportunityRequest;
  byId: (id: string) => HTMLElement | null;
  escapeHtml: (value: unknown) => string;
  renderText: (value: unknown) => string;
  toast: (message: string) => unknown;
  withLoading: <T>(task: () => Promise<T>, message?: string) => Promise<T>;
  renderIcons: () => unknown;
  syncAgentContext: () => unknown;
  jumpToModule: (page: string, module: string) => unknown;
  filterModules: (page: string, module: string, activeButton: Element) => unknown;
  renderAgentCommandOpportunities: () => unknown;
  applicationPayloadForJob: (handoff: any, job: string) => Record<string, unknown>;
  buildInterviewHandoff: (value: any) => any;
  renderApplicationHandoffNotice: () => unknown;
  clearApplicationHandoff: () => unknown;
  renderMatchOpportunityNotice: () => unknown;
  openOriginalResume: (id: number) => unknown;
  fillResume: (id: number) => unknown;
  openInterviewRoom: (data: any) => unknown;
  parseFeedbackSummary: (feedback: unknown) => string;
  confirmAction: (message: string) => boolean;
  history: any;
}

export interface OpportunityController {
  saveApplication(): Promise<void>;
  editApplication(id: number): Promise<void>;
  deleteApplication(id: number): Promise<void>;
  loadApplications(): Promise<void>;
  openWorkspace(id: number, options?: any): Promise<unknown>;
  loadWorkspace(id: number, request?: any): Promise<any>;
  showWorkspaceError(id: number, message: string): void;
  retryWorkspace(id: number): unknown;
  resetWorkspace(context?: any): void;
  closeWorkspace(): unknown;
  selectTab(tab: HTMLElement | null, moveFocus?: boolean): void;
  handleTabKeydown(event: KeyboardEvent): void;
  renderWorkspace(workspace: any): void;
  workspaceDate(value: unknown, fallback?: string): string;
  renderOverview(workspace: any): void;
  renderMatch(workspace: any): void;
  useWorkspaceJd(): void;
  renderResume(workspace: any): void;
  openWorkspaceResume(id: number, hasOriginal: boolean): unknown;
  renderInterview(workspace: any): void;
  prepareInterview(actionId?: number | null): void;
  continueInterview(id: number): Promise<void>;
  renderTimeline(workspace: any): void;
  advanceApplication(id: number): Promise<void>;
  coachApplication(id: number): Promise<void>;
  evaluateSalary(): Promise<void>;
  loadDashboard(): Promise<void>;
  renderCareerPulse(pulse: any): void;
  renderNextActions(actions: any[]): void;
}

export function createOpportunityController(
  deps: OpportunityControllerDependencies,
): OpportunityController {
  const dashboard = createOpportunityDashboard(deps);
  const workspace = createOpportunityWorkspace(deps);
  const board = createApplicationBoard(deps, {
    loadDashboard: dashboard.load,
    openWorkspace: (id) => workspace.open(id),
    closeWorkspace: workspace.close,
  });
  return {
    saveApplication: board.save,
    editApplication: board.edit,
    deleteApplication: board.remove,
    loadApplications: board.load,
    openWorkspace: workspace.open,
    loadWorkspace: workspace.load,
    showWorkspaceError: workspace.showError,
    retryWorkspace: workspace.retry,
    resetWorkspace: workspace.reset,
    closeWorkspace: workspace.close,
    selectTab: workspace.selectTab,
    handleTabKeydown: workspace.handleTabKeydown,
    renderWorkspace: workspace.render,
    workspaceDate: workspace.date,
    renderOverview: workspace.renderOverview,
    renderMatch: workspace.renderMatch,
    useWorkspaceJd: workspace.useJd,
    renderResume: workspace.renderResume,
    openWorkspaceResume: workspace.openResume,
    renderInterview: workspace.renderInterview,
    prepareInterview: workspace.prepareInterview,
    continueInterview: workspace.continueInterview,
    renderTimeline: workspace.renderTimeline,
    advanceApplication: board.advance,
    coachApplication: board.coach,
    evaluateSalary: dashboard.evaluateSalary,
    loadDashboard: dashboard.load,
    renderCareerPulse: dashboard.renderCareerPulse,
    renderNextActions: dashboard.renderNextActions,
  };
}
