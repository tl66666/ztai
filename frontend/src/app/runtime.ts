// Runtime composition is migrated incrementally from the historical browser script.
// All feature modules are imported directly so Vite emits one ES module graph.
import { createAgentController } from "../agent/agent-controller";
import { createAgentWorkspace } from "../agent/agent-workspace";
import * as ContextualAgent from "../agent/contextual-agent.mjs";
import * as CareerForm from "../career/career-form.mjs";
import * as BrowserCapabilities from "../interview/browser-capabilities.mjs";
import { createInterviewController } from "../interview/interview-controller";
import * as InterviewMedia from "../interview/interview-media.mjs";
import { escapeAttr } from "../interview/interview-renderers";
import * as InterviewSubmission from "../interview/interview-submission";
import { createOpportunityController } from "../opportunity/opportunity-controller";
import * as OpportunityHistory from "../opportunity/opportunity-history.mjs";
import {
  applicationPayloadForJob,
  buildApplicationHandoff,
  buildInterviewHandoff,
  buildInterviewStartPayload,
  buildMatchPayload,
  routeLeavesFlow,
} from "../opportunity/opportunity-handoffs";
import { createResumeController } from "../resume/resume-controller";
import { createApiClient, resolveBaseUrl } from "../shared/api-client";
import { createRuntimeUi } from "../shared/runtime-ui";
import { createShellController } from "../shell/shell-controller";
import { createTopbarController } from "../shell/topbar-controller";

declare global {
  interface Window {
    __JOBHUNTER_CONFIG__?: { apiBaseUrl?: string };
    lucide?: { createIcons(): void };
    ContextualAgent?: any;
    webkitAudioContext?: typeof AudioContext;
  }
}

const API = resolveBaseUrl({
  location: window.location,
  runtimeConfig: window.__JOBHUNTER_CONFIG__,
});
const USER_ID = 1;
const JOBHUNTER_AGENT_CONVERSATION = `jobhunter_agent_conversation_${USER_ID}`;
const api = createApiClient({ baseUrl: API });

const state: any = {
  resumes: [],
  providers: [],
  careerProfiles: [],
  careerProfile: localStorage.getItem("jobhunter_career_profile") || "tech",
  activeInterview: null,
  interviewStageIndex: 0,
  pendingInterviewSubmission: null,
  interviewSubmitting: false,
  currentInterviewSession: null,
  skillChart: null,
  recognition: null,
  speechController: null,
  recognizing: false,
  currentPracticeCategory: "general",
  theme: localStorage.getItem("jobhunter_theme") || "glass",
  editingResumeId: null,
  editingAppId: null,
  applicationStatuses: [],
  currentOpportunityId: null,
  currentOpportunityWorkspace: null,
  opportunityLoadGeneration: 0,
  pendingApplicationHandoff: null,
  interviewOpportunityHandoff: null,
  matchOpportunityId: null,
  opportunityOpener: null,
  applications: [],
  recordingController: null,
  audioBlob: null,
  audioMetrics: null,
  soundEnabled: localStorage.getItem("jobhunter_sound") !== "off",
  audioContext: null,
  agentConversationId: localStorage.getItem(JOBHUNTER_AGENT_CONVERSATION) || "",
  agentDrawerOpener: null,
  agentProposals: new Map(),
  agentProposalEpochs: new Map(),
  agentProposalMutationEpoch: 0,
  agentConversationProposalIds: new Set(),
  agentCommandProposalIds: new Set(),
  currentPage: "home",
  currentModule: "",
};

const runtimeUi = createRuntimeUi(state);
const $ = (id: string): any => runtimeUi.byId(id);
const {
  downloadBlob,
  downloadResponse,
  escapeHtml,
  playTone: playUiTone,
  renderIcons,
  renderText,
  toast,
  withLoading,
} = runtimeUi;

const PAGE_TITLES = {
  home: "项目总览",
  resume: "简历实验室",
  interview: "面试训练场",
  tracker: "投递看板",
  agent: "求职指挥台",
};
const topbarController = createTopbarController({
  state,
  request: api,
  ui: runtimeUi,
  careerForm: CareerForm,
  loadQuestions: (category) => interviewController.loadQuestions(category),
  afterCareerGoalSaved: async () => {
    await opportunityController.loadDashboard();
    agentController.syncContext();
  },
});
const { selectedCareerProfile, careerProfileLabel } = topbarController;
let agentController: ReturnType<typeof createAgentController>;
const agentWorkspace = createAgentWorkspace({
  userId: USER_ID,
  conversationStorageKey: JOBHUNTER_AGENT_CONVERSATION,
  state,
  request: api,
  ui: runtimeUi,
  contextualAgent: ContextualAgent,
  contextPayload: () => agentController.contextPayload(),
  openDrawer: (event) => agentController.openDrawer(event),
  closeDrawer: () => agentController.closeDrawer(),
  navigate: (page, module) => shellController.jumpToModule(page, module),
  loadResumes: () => resumeController.load(),
  loadApplications: () => opportunityController.loadApplications(),
  loadDashboard: () => opportunityController.loadDashboard(),
  loadOpportunityWorkspace: (id, request) => (
    opportunityController.loadWorkspace(id, request)
  ),
  syncAgentContext: () => agentController.syncContext(),
});
const {
  clearConversation: clearAgentConversation,
  createConversation: createAgentConversation,
  focusResultFromLocation: focusAgentResultFromQuery,
  generateCareerReport,
  handleChatLogClick: handleAgentChatLogClick,
  loadCommandCenter: loadAgentCommandCenter,
  loadConversations: loadAgentConversations,
  openProposal: openAgentProposal,
  renderCommandOpportunities: renderAgentCommandOpportunities,
  sendMessage: sendAgentMessage,
} = agentWorkspace;
agentController = createAgentController({
  state,
  byId: $,
  contextualAgent: ContextualAgent,
  escapeHtml,
  escapeAttr,
  renderIcons,
  loadCommandCenter: () => agentWorkspace.loadCommandCenter(),
  documentObject: document,
  windowObject: window,
});
const shellController = createShellController({
  state,
  byId: $,
  history: () => opportunityHistory,
  playTone: playUiTone,
  syncAgentContext: () => agentController.syncContext(),
  loadAgentCommandCenter: () => agentWorkspace.loadCommandCenter(),
  routeLeavesFlow,
  clearApplicationHandoff,
  clearMatchOpportunityLink,
  pageTitles: PAGE_TITLES,
  windowObject: window,
  documentObject: document,
});
const resumeController = createResumeController({
  userId: USER_ID,
  apiBaseUrl: API,
  state,
  request: api,
  byId: $,
  escapeHtml,
  renderText,
  toast,
  withLoading,
  renderIcons,
  syncAgentContext: () => agentController.syncContext(),
  jumpToModule: (page, module) => shellController.jumpToModule(page, module),
  closeAgentDrawer: () => agentController.closeDrawer(),
  selectedCareerProfile,
  careerProfileLabel,
  loadDashboard: () => opportunityController.loadDashboard(),
  clearMatchOpportunityLink,
  buildMatchPayload,
  downloadResponse,
});
const interviewController = createInterviewController({
  userId: USER_ID,
  apiBaseUrl: API,
  state,
  request: api,
  byId: $,
  escapeHtml,
  renderText,
  toast,
  withLoading,
  renderIcons,
  selectedCareerProfile,
  loadDashboard: () => opportunityController.loadDashboard(),
  buildInterviewStartPayload,
  downloadBlob,
  downloadResponse,
  confirmAction: (message) => window.confirm(message),
  submission: InterviewSubmission,
  media: InterviewMedia,
  capabilities: BrowserCapabilities,
});
const opportunityHistory = OpportunityHistory.createOpportunityHistoryController({
  window,
  defaultModule: shellController.defaultModuleForPage,
  onRouteTransition: shellController.handleRouteTransition,
  focusRoute: shellController.focusCleanedRoute,
  showPage: (page: string) => {
    if ($(`page-${page}`)) shellController.renderPage(page);
  },
  showModule: shellController.renderModule,
  loadWorkspace: (id: number, request: any) => opportunityController.loadWorkspace(id, request),
  closeWorkspace: (context: any) => opportunityController.resetWorkspace(context),
  notifyStale: () => toast("机会详情不存在或已删除，链接已重置。"),
  notifyForbidden: () => toast("无权访问该机会详情，链接已重置。"),
  notifyRetryable: () => {
    if (state.currentOpportunityId) {
      opportunityController.showWorkspaceError(
        state.currentOpportunityId,
        "机会详情暂时无法加载，请稍后重试。",
      );
    }
  },
});
const opportunityController = createOpportunityController({
  userId: USER_ID,
  state,
  request: api,
  byId: $,
  escapeHtml,
  renderText,
  toast,
  withLoading,
  renderIcons,
  syncAgentContext: () => agentController.syncContext(),
  jumpToModule: (page, module) => shellController.jumpToModule(page, module),
  filterModules: (page, module, button) => (
    shellController.filterModules(page, module, button)
  ),
  renderAgentCommandOpportunities,
  applicationPayloadForJob,
  buildInterviewHandoff,
  renderApplicationHandoffNotice,
  clearApplicationHandoff,
  renderMatchOpportunityNotice,
  openOriginalResume: (id) => resumeController.openOriginal(id),
  fillResume: (id) => resumeController.fill(id),
  openInterviewRoom: (data) => interviewController.openRoom(data),
  parseFeedbackSummary: (feedback) => interviewController.parseFeedbackSummary(feedback),
  confirmAction: (message) => window.confirm(message),
  history: opportunityHistory,
});
const {
  applyInitialRoute: applyInitialRouteFromQuery,
  bindNavigation,
  filterModules,
  jumpToModule,
  navigate: navigateToRoute,
} = shellController;
const {
  analyze: analyzeResume,
  analyzeJd: analyzeJdOnly,
  auditSelected: auditSelectedResume,
  cancelEdit: cancelResumeEdit,
  convertDocument,
  export: exportResume,
  fill: fillResume,
  fillTitleFromFile: fillResumeTitleFromFile,
  generate: generateResume,
  improveSelected: improveSelectedResume,
  load: loadResumes,
  match: matchResume,
  openOriginal: openOriginalResume,
  remove: deleteResume,
  renderSkills,
  replaceOriginal: replaceOriginalResume,
  save: saveResume,
  selectedResumeId,
  selectedTailorId: selectedTailorResumeId,
  tailor: tailorResume,
} = resumeController;
const {
  analyzeRecordedAudio,
  analyzeVoice,
  applyBrowserCapabilities,
  categoryName,
  clearTrainingRecords,
  computeAudioMetrics,
  deleteTrainingRecord,
  downloadSavedAudio,
  extensionFromMime: audioExtensionFromMime,
  formatDate,
  getRecordingController,
  handleAudioUpload,
  loadProfessionalPack,
  loadQuestions,
  loadTrainingRecords,
  openRoom: openInterviewRoom,
  parseFeedbackSummary,
  renderAudioPreview,
  renderConversation,
  renderFeedback,
  renderFeedbackHtml,
  renderRecordColumn,
  renderRecordDetail,
  safeJson,
  scorePractice,
  scoreProfessionalAnswer,
  selectProfessionalQuestion,
  selectQuestion,
  sendAnswer: sendInterviewAnswer,
  sendRoomAnswer,
  setupSpeechRecognition,
  showProfessionalReference,
  showSampleAnswer,
  stageName,
  start: startInterview,
  startAudioRecording,
  stopAudioRecording,
  toggleVoiceInput,
  updateQuestion: updateInterviewQuestion,
  viewTrainingRecord,
} = interviewController;
const {
  advanceApplication,
  closeWorkspace: closeOpportunityWorkspace,
  coachApplication,
  continueInterview: continueOpportunityInterview,
  deleteApplication,
  editApplication,
  evaluateSalary,
  handleTabKeydown: handleOpportunityTabKeydown,
  loadApplications,
  loadDashboard,
  loadWorkspace: loadOpportunityWorkspace,
  openWorkspace: openOpportunityWorkspace,
  openWorkspaceResume,
  prepareInterview: prepareInterviewFromOpportunity,
  renderCareerPulse,
  renderMatch: renderOpportunityMatch,
  renderNextActions,
  renderOverview: renderOpportunityOverview,
  renderResume: renderOpportunityResume,
  renderTimeline: renderOpportunityTimeline,
  renderWorkspace: renderOpportunityWorkspace,
  resetWorkspace: resetOpportunityWorkspaceView,
  retryWorkspace: retryOpportunityWorkspace,
  saveApplication,
  selectTab: selectOpportunityTab,
  showWorkspaceError: showOpportunityWorkspaceError,
  useWorkspaceJd,
  workspaceDate,
} = opportunityController;
const {
  closeDrawer: closeAgentDrawer,
  currentResumeId: currentAgentResumeId,
  handleDrawerKeydown: handleAgentDrawerKeydown,
  openDrawer: openAgentDrawer,
  renderContextChips: renderAgentContextChips,
  syncContext: syncAgentContext,
} = agentController;
document.addEventListener("DOMContentLoaded", async () => {
  opportunityHistory.bind();
  bindNavigation();
  bindActions();
  applyBrowserCapabilities();
  setupSpeechRecognition();
  await topbarController.initialize();
  await Promise.all([loadResumes(), loadDashboard(), loadApplications(), loadQuestions(), loadTrainingRecords()]);
  await loadAgentConversations();
  await applyInitialRouteFromQuery();
  await loadAgentCommandCenter();
  await focusAgentResultFromQuery();
  syncAgentContext();
  renderIcons();
});

function bindActions() {
  agentController.bind();
  topbarController.bind();
  document.addEventListener("click", handleApplicationCommand);
  document.addEventListener("change", handleApplicationChange);
  document.querySelectorAll<HTMLElement>("[data-flow-jump]").forEach((button) => {
    button.addEventListener("click", () => {
      const [page, module] = (button.dataset.flowJump || "").split(":");
      playUiTone("jump");
      jumpToModule(page, module);
    });
  });
  document.querySelectorAll<HTMLElement>("[data-section-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      const [page, module] = (button.dataset.sectionFilter || "").split(":");
      playUiTone("tap");
      navigateToRoute(page, module);
    });
  });
  document.querySelectorAll(".page-subnav").forEach((nav) => {
    const first = nav.querySelector<HTMLElement>("[data-section-filter]");
    if (first) {
      const [page, module] = (first.dataset.sectionFilter || "").split(":");
      filterModules(page, module, first);
    }
  });
  $("refreshResumesBtn").addEventListener("click", loadResumes);
  $("saveResumeBtn").addEventListener("click", saveResume);
  $("cancelResumeEditBtn")?.addEventListener("click", cancelResumeEdit);
  $("generateResumeBtn").addEventListener("click", generateResume);
  $("exportPdfBtn").addEventListener("click", () => exportResume("pdf"));
  $("exportWordBtn").addEventListener("click", () => exportResume("word"));
  $("pdfToWordFile").addEventListener("change", () => convertDocument("pdf-to-word", "pdfToWordFile"));
  $("wordToPdfFile").addEventListener("change", () => convertDocument("word-to-pdf", "wordToPdfFile"));
  $("tailorBtn").addEventListener("click", tailorResume);
  $("matchBtn").addEventListener("click", matchResume);
  $("analyzeJdBtn").addEventListener("click", analyzeJdOnly);
  $("resumeAuditBtn").addEventListener("click", auditSelectedResume);
  $("resumeImproveBtn").addEventListener("click", improveSelectedResume);
  $("skillsBtn").addEventListener("click", renderSkills);
  $("startInterviewBtn").addEventListener("click", startInterview);
  $("sendAnswerBtn").addEventListener("click", sendInterviewAnswer);
  $("roomSubmitBtn").addEventListener("click", sendRoomAnswer);
  $("closeInterviewRoom").addEventListener("click", () => $("interviewRoom").classList.add("hidden"));
  $("roomVoiceCopyBtn").addEventListener("click", () => {
    $("answerInput").value = $("roomAnswer").value;
    $("interviewRoom").classList.add("hidden");
    jumpToModule("interview", "mock");
    $("answerInput").focus();
  });
  $("analyzeVoiceBtn").addEventListener("click", analyzeVoice);
  $("voiceBtn").addEventListener("click", toggleVoiceInput);
  $("recordAudioBtn").addEventListener("click", () => startAudioRecording("answer"));
  $("stopAudioBtn").addEventListener("click", stopAudioRecording);
  $("analyzeAudioBtn").addEventListener("click", () => analyzeRecordedAudio("answer"));
  $("audioFileInput").addEventListener("change", handleAudioUpload);
  $("roomRecordBtn").addEventListener("click", () => startAudioRecording("room"));
  $("roomStopRecordBtn").addEventListener("click", stopAudioRecording);
  $("roomAnalyzeAudioBtn").addEventListener("click", () => analyzeRecordedAudio("room"));
  $("loadQuestionsBtn").addEventListener("click", () => loadQuestions($("questionCategory").value));
  $("questionCategory").addEventListener("change", () => loadQuestions($("questionCategory").value));
  $("scorePracticeBtn").addEventListener("click", scorePractice);
  $("professionalPackBtn").addEventListener("click", loadProfessionalPack);
  $("scoreProfessionalBtn").addEventListener("click", scoreProfessionalAnswer);
  $("clearTrainingRecordsBtn").addEventListener("click", clearTrainingRecords);
  $("saveAppBtn").addEventListener("click", saveApplication);
  $("clearApplicationHandoff")?.addEventListener("click", clearApplicationHandoff);
  $("clearMatchOpportunityLink")?.addEventListener("click", clearMatchOpportunityLink);
  $("appJob")?.addEventListener("input", () => {
    if (state.pendingApplicationHandoff
        && !Object.keys(applicationPayloadForJob(state.pendingApplicationHandoff, $("appJob").value)).length) {
      clearApplicationHandoff();
    }
  });
  $("closeOpportunityWorkspace")?.addEventListener("click", closeOpportunityWorkspace);
  document.querySelectorAll<HTMLElement>('.opportunity-tabs [role="tab"]').forEach((tab) => {
    tab.addEventListener("click", () => selectOpportunityTab(tab));
    tab.addEventListener("keydown", (event) => {
      handleOpportunityTabKeydown(event as KeyboardEvent);
    });
  });
  $("salaryBtn").addEventListener("click", evaluateSalary);
  $("chatLog")?.addEventListener("click", handleAgentChatLogClick);
  $("agentResumeUpload")?.addEventListener("click", openResumeUploadFromAgent);
  $("sendAgentBtn").addEventListener("click", () => sendAgentMessage());
  $("careerReportBtn").addEventListener("click", generateCareerReport);
  $("newAgentConversation")?.addEventListener("click", () => createAgentConversation());
  $("clearAgentConversation")?.addEventListener("click", clearAgentConversation);
  $("agentConversationSelect")?.addEventListener("change", async () => {
    state.agentConversationId = $("agentConversationSelect").value;
    localStorage.setItem(JOBHUNTER_AGENT_CONVERSATION, state.agentConversationId);
    await agentWorkspace.loadConversations(state.agentConversationId, true);
  });
  $("agentInput").addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendAgentMessage();
    }
  });
  $("resumeFile")?.addEventListener("change", fillResumeTitleFromFile);
  document.querySelectorAll<HTMLElement>("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      $("agentInput").value = button.dataset.prompt;
      sendAgentMessage();
    });
  });
}

function positiveInteger(value: any) {
  const result = Number(value);
  return Number.isInteger(result) && result > 0 ? result : null;
}

function handleApplicationChange(event: any) {
  const input = event.target instanceof HTMLInputElement
    ? event.target.closest("[data-command-change]")
    : null;
  if (!input || input.dataset.commandChange !== "resume-replace-original") return;
  const resumeId = positiveInteger(input.dataset.resumeId);
  if (resumeId) void replaceOriginalResume(resumeId, input);
}

function handleApplicationCommand(event: any) {
  const control = event.target instanceof Element
    ? event.target.closest("[data-command], [data-route-page]")
    : null;
  if (!(control instanceof HTMLElement)) return;
  const routePage = control.dataset.routePage;
  if (routePage) {
    void jumpToModule(routePage, control.dataset.routeModule || "");
    return;
  }
  const command = control.dataset.command;
  if (!command) return;
  const resumeId = positiveInteger(control.dataset.resumeId);
  const opportunityId = positiveInteger(control.dataset.opportunityId);
  const recordId = positiveInteger(control.dataset.recordId);
  const sessionId = positiveInteger(control.dataset.sessionId);
  const actionId = positiveInteger(control.dataset.actionId);
  const proposalId = positiveInteger(control.dataset.proposalId);
  const actions = {
    "resume-edit": () => resumeId && fillResume(resumeId),
    "resume-open-original": () => resumeId && openOriginalResume(resumeId),
    "resume-analyze": () => resumeId && analyzeResume(resumeId),
    "resume-delete": () => resumeId && deleteResume(resumeId),
    "resume-improve-selected": improveSelectedResume,
    "resume-tailor": tailorResume,
    "prepare-interview-from-jd": prepareInterviewFromJd,
    "prepare-application-from-jd": prepareApplicationFromJd,
    "interview-select-question": () => selectQuestion(
      control.dataset.question || "",
      control.dataset.category || "general",
    ),
    "interview-show-sample": () => showSampleAnswer(control.dataset.answer || ""),
    "training-view": () => recordId && viewTrainingRecord(control.dataset.recordType || "", recordId),
    "training-delete": () => recordId && deleteTrainingRecord(control.dataset.recordType || "", recordId),
    "training-audio-download": () => downloadSavedAudio(
      control.dataset.audioFile || "",
      control.dataset.audioFormat || "wav",
    ),
    "interview-select-professional": () => selectProfessionalQuestion(control.dataset.question || ""),
    "interview-show-professional-reference": () => showProfessionalReference(control.dataset.reference || ""),
    "opportunity-open": () => opportunityId && openOpportunityWorkspace(opportunityId),
    "opportunity-refresh": () => opportunityId && openOpportunityWorkspace(opportunityId, { updateUrl: false }),
    "opportunity-retry": () => opportunityId && retryOpportunityWorkspace(opportunityId),
    "opportunity-edit": () => opportunityId && editApplication(opportunityId),
    "opportunity-delete": () => opportunityId && deleteApplication(opportunityId),
    "opportunity-coach": () => opportunityId && coachApplication(opportunityId),
    "opportunity-advance": () => opportunityId && advanceApplication(opportunityId),
    "opportunity-use-jd": useWorkspaceJd,
    "opportunity-open-resume": () => resumeId && openWorkspaceResume(
      resumeId,
      control.dataset.hasOriginal === "true",
    ),
    "opportunity-continue-interview": () => sessionId && continueOpportunityInterview(sessionId),
    "opportunity-prepare-interview": () => prepareInterviewFromOpportunity(actionId),
    "agent-command-retry": loadAgentCommandCenter,
    "agent-proposal-open": () => proposalId && openAgentProposal(proposalId, control),
    "agent-opportunity-open": () => {
      closeAgentDrawer();
      if (opportunityId) void openOpportunityWorkspace(opportunityId);
    },
    "agent-result-retry": focusAgentResultFromQuery,
  };
  const action = (actions as Record<string, (() => unknown)>)[command];
  if (action) void action();
}

function openResumeUploadFromAgent() {
  cancelResumeEdit();
  return resumeController.openUploadFromAgent();
}

function prepareInterviewFromJd() {
  state.interviewOpportunityHandoff = null;
  $("interviewJobTitle").value = $("jobTitleInput").value || $("interviewJobTitle").value;
  $("interviewJd").value = $("jdInput").value || $("interviewJd").value;
  $("interviewResumeSelect").value = selectedTailorResumeId() || selectedResumeId() || "";
  jumpToModule("interview", "mock");
  toast("已把岗位信息带入模拟面试");
}

function prepareApplicationFromJd() {
  const jobTitle = $("jobTitleInput").value || $("appJob").value;
  state.pendingApplicationHandoff = buildApplicationHandoff({
    jobTitle,
    jd: $("jdInput").value.trim(),
    resumeId: selectedTailorResumeId() || selectedResumeId(),
  });
  $("appJob").value = jobTitle;
  $("appNotes").value = $("jdInput").value ? `JD 摘要：${$("jdInput").value.slice(0, 180)}` : $("appNotes").value;
  renderApplicationHandoffNotice();
  jumpToModule("tracker", "add");
  toast("已带入岗位信息，补公司名后即可保存投递");
}

function renderApplicationHandoffNotice() {
  const handoff = state.pendingApplicationHandoff;
  $("applicationHandoffNotice")?.classList.toggle("hidden", !handoff);
  if (!handoff || !$("applicationHandoffContext")) return;
  const resume = state.resumes.find((item: any) => item.id === handoff.resumeId)?.title || "未关联简历";
  $("applicationHandoffContext").textContent = `${handoff.jobTitle} · ${resume}${handoff.jd ? " · 已带入 JD" : ""}`;
}

function clearApplicationHandoff() {
  state.pendingApplicationHandoff = null;
  renderApplicationHandoffNotice();
}

function clearMatchOpportunityLink() {
  state.matchOpportunityId = null;
  renderMatchOpportunityNotice();
}

function renderMatchOpportunityNotice() {
  const opportunityId = state.matchOpportunityId;
  $("matchOpportunityNotice")?.classList.toggle("hidden", !opportunityId);
  if (opportunityId && $("matchOpportunityContext")) {
    $("matchOpportunityContext").textContent = `机会 #${opportunityId}`;
  }
}
