const API = JobHunterApiClient.resolveBaseUrl({
  location: window.location,
  runtimeConfig: window.__JOBHUNTER_CONFIG__,
});
const USER_ID = 1;
const JOBHUNTER_AGENT_CONVERSATION = `jobhunter_agent_conversation_${USER_ID}`;
const api = JobHunterApiClient.create({ baseUrl: API });

const state = {
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

const $ = (id) => document.getElementById(id);

function renderIcons() {
  if (!window.lucide || typeof window.lucide.createIcons !== "function") return false;
  try {
    window.lucide.createIcons();
    return true;
  } catch (error) {
    console.warn("Icon rendering is unavailable; text controls remain usable.", error);
    return false;
  }
}

const agentConversationEpoch = ContextualAgent.createConversationEpoch();
const agentCommandCenterGate = ContextualAgent.createLatestRequestGate();
const {
  applicationPayloadForJob,
  buildApplicationHandoff,
  buildInterviewHandoff,
  buildInterviewStartPayload,
  buildMatchPayload,
  routeLeavesFlow,
} = OpportunityHandoffs;
const PAGE_TITLES = {
  home: "项目总览",
  resume: "简历实验室",
  interview: "面试训练场",
  tracker: "投递看板",
  agent: "求职指挥台",
};
const agentController = JobHunterAgentController.createAgentController({
  state,
  byId: $,
  contextualAgent: ContextualAgent,
  escapeHtml,
  escapeAttr,
  renderIcons,
  loadCommandCenter: loadAgentCommandCenter,
  documentObject: document,
  windowObject: window,
});
const shellController = JobHunterShellController.createShellController({
  state,
  byId: $,
  history: () => opportunityHistory,
  playTone: playUiTone,
  syncAgentContext,
  loadAgentCommandCenter,
  routeLeavesFlow,
  clearApplicationHandoff,
  clearMatchOpportunityLink,
  pageTitles: PAGE_TITLES,
  windowObject: window,
  documentObject: document,
});
const resumeController = JobHunterResumeController.create({
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
  syncAgentContext,
  jumpToModule,
  closeAgentDrawer,
  selectedCareerProfile,
  careerProfileLabel,
  loadDashboard,
  clearMatchOpportunityLink,
  buildMatchPayload,
  downloadResponse,
});
const interviewController = JobHunterInterviewController.create({
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
  loadDashboard,
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
  showPage: (page) => {
    if ($(`page-${page}`)) shellController.renderPage(page);
  },
  showModule: shellController.renderModule,
  loadWorkspace: loadOpportunityWorkspace,
  closeWorkspace: resetOpportunityWorkspaceView,
  notifyStale: () => toast("机会详情不存在或已删除，链接已重置。"),
  notifyForbidden: () => toast("无权访问该机会详情，链接已重置。"),
  notifyRetryable: () => {
    if (state.currentOpportunityId) {
      showOpportunityWorkspaceError(state.currentOpportunityId, "机会详情暂时无法加载，请稍后重试。");
    }
  },
});
const opportunityController = JobHunterOpportunityController.create({
  userId: USER_ID,
  state,
  request: api,
  byId: $,
  escapeHtml,
  renderText,
  toast,
  withLoading,
  renderIcons,
  syncAgentContext,
  jumpToModule,
  filterModules,
  renderAgentCommandOpportunities,
  applicationPayloadForJob,
  buildInterviewHandoff,
  renderApplicationHandoffNotice,
  clearApplicationHandoff,
  renderMatchOpportunityNotice,
  openOriginalResume,
  fillResume,
  openInterviewRoom,
  parseFeedbackSummary,
  confirmAction: (message) => window.confirm(message),
  history: opportunityHistory,
});
const PROVIDER_LINKS = {
  glm: [
    ["智谱开放平台", "https://open.bigmodel.cn/"],
    ["API Key 管理", "https://open.bigmodel.cn/apikey/platform"],
  ],
  deepseek: [
    ["DeepSeek 平台", "https://platform.deepseek.com/"],
    ["API Keys", "https://platform.deepseek.com/api_keys"],
  ],
  kimi: [
    ["Moonshot 控制台", "https://platform.moonshot.cn/"],
    ["API Key 管理", "https://platform.moonshot.cn/console/api-keys"],
  ],
};

document.addEventListener("DOMContentLoaded", async () => {
  opportunityHistory.bind();
  bindNavigation();
  bindActions();
  applyTheme(state.theme);
  applyBrowserCapabilities();
  setupSpeechRecognition();
  await loadCareerProfiles();
  await loadCareerGoal();
  await loadProviders();
  await Promise.all([loadResumes(), loadDashboard(), loadApplications(), loadQuestions(), loadTrainingRecords()]);
  await loadAgentConversations();
  await applyInitialRouteFromQuery();
  await loadAgentCommandCenter();
  await focusAgentResultFromQuery();
  syncAgentContext();
  renderIcons();
});

function bindNavigation() {
  return shellController.bindNavigation();
}

function renderPage(page) {
  return shellController.renderPage(page);
}

async function applyInitialRouteFromQuery() {
  return shellController.applyInitialRoute();
}

function bindActions() {
  agentController.bind();
  updateSoundButton();
  $("modelConfigBtn").addEventListener("click", () => {
    playUiTone("tap");
    $("modelConfigPanel").classList.toggle("hidden");
  });
  $("soundToggleBtn")?.addEventListener("click", () => {
    state.soundEnabled = !state.soundEnabled;
    localStorage.setItem("jobhunter_sound", state.soundEnabled ? "on" : "off");
    updateSoundButton();
    if (state.soundEnabled) playUiTone("success");
    toast(state.soundEnabled ? "界面音效已开启" : "界面音效已关闭", { silent: true });
  });
  $("closeModelPanel").addEventListener("click", () => $("modelConfigPanel").classList.add("hidden"));
  $("saveProviderBtn").addEventListener("click", saveProvider);
  $("providerSelect").addEventListener("change", () => {
    renderModelOptions($("providerSelect").value);
    renderProviderLinks($("providerSelect").value);
  });
  $("modelSelect").addEventListener("change", toggleCustomModelInput);
  document.querySelectorAll("[data-theme-choice]").forEach((button) => {
    button.addEventListener("click", () => {
      playUiTone("tap");
      applyTheme(button.dataset.themeChoice);
    });
  });
  $("careerProfileSelect")?.addEventListener("change", () => {
    state.careerProfile = $("careerProfileSelect").value || "tech";
    localStorage.setItem("jobhunter_career_profile", state.careerProfile);
    syncCareerProfileToForms();
    loadQuestions($("questionCategory")?.value || "general");
    toast(`已切换求职方向：${careerProfileLabel(state.careerProfile)}`);
  });
  $("careerGoalForm")?.addEventListener("submit", saveCareerGoal);
  $("retryCareerGoalBtn")?.addEventListener("click", loadCareerGoal);
  document.querySelectorAll("[data-flow-jump]").forEach((button) => {
    button.addEventListener("click", () => {
      const [page, module] = button.dataset.flowJump.split(":");
      playUiTone("jump");
      jumpToModule(page, module);
    });
  });
  document.querySelectorAll("[data-section-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      const [page, module] = button.dataset.sectionFilter.split(":");
      playUiTone("tap");
      navigateToRoute(page, module);
    });
  });
  document.querySelectorAll(".page-subnav").forEach((nav) => {
    const first = nav.querySelector("[data-section-filter]");
    if (first) {
      const [page, module] = first.dataset.sectionFilter.split(":");
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
  document.querySelectorAll('.opportunity-tabs [role="tab"]').forEach((tab) => {
    tab.addEventListener("click", () => selectOpportunityTab(tab));
    tab.addEventListener("keydown", handleOpportunityTabKeydown);
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
    await restoreAgentMessages();
  });
  $("agentInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendAgentMessage();
    }
  });
  $("resumeFile")?.addEventListener("change", fillResumeTitleFromFile);
  document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      $("agentInput").value = button.dataset.prompt;
      sendAgentMessage();
    });
  });
}

async function loadCareerProfiles() {
  const data = await api("/career/profiles");
  state.careerProfiles = data.success ? data.profiles : [];
  const select = $("careerProfileSelect");
  if (!select) return;
  select.innerHTML = state.careerProfiles.map((item) => `<option value="${item.id}">${escapeHtml(item.label)}</option>`).join("");
  select.value = state.careerProfiles.some((item) => item.id === state.careerProfile) ? state.careerProfile : (data.default || "tech");
  state.careerProfile = select.value;
  localStorage.setItem("jobhunter_career_profile", state.careerProfile);
  syncCareerProfileToForms();
}

function listInputValue(id) {
  return CareerForm.parseList($(id).value);
}

function optionalNumberValue(id) {
  const value = $(id).value.trim();
  return value === "" ? null : Number(value);
}

async function loadCareerGoal() {
  const result = await CareerForm.loadProfile({
    request: () => api("/profile"),
    controls: {
      role: $("careerGoalRole"),
      cities: $("careerGoalCities"),
      salaryMin: $("careerGoalSalaryMin"),
      salaryMax: $("careerGoalSalaryMax"),
      skills: $("careerGoalSkills"),
      direction: $("careerProfileSelect"),
      status: $("careerGoalStatus"),
      retry: $("retryCareerGoalBtn"),
    },
    state,
  });
  if (result.ok && result.direction.matched) {
    localStorage.setItem("jobhunter_career_profile", state.careerProfile);
    syncCareerProfileToForms();
  }
}

async function saveCareerGoal(event) {
  event?.preventDefault();
  const targetRole = $("careerGoalRole").value.trim();
  const salaryMin = optionalNumberValue("careerGoalSalaryMin");
  const salaryMax = optionalNumberValue("careerGoalSalaryMax");
  if (!targetRole) {
    $("careerGoalStatus").textContent = "请填写目标岗位。";
    $("careerGoalRole").focus();
    return;
  }
  if (salaryMin !== null && salaryMax !== null && salaryMin > salaryMax) {
    $("careerGoalStatus").textContent = "薪资下限不能高于上限。";
    $("careerGoalSalaryMin").focus();
    return;
  }
  const payload = {
    career_direction: selectedCareerProfile(),
    target_role: targetRole,
    cities: listInputValue("careerGoalCities"),
    salary: { min: salaryMin, max: salaryMax },
    confirmed_skills: listInputValue("careerGoalSkills"),
    source_metadata: { form: "career-goal-editor" },
  };
  await CareerForm.saveProfile({
    request: (body) => api("/profile", { method: "PUT", body }),
    payload,
    status: $("careerGoalStatus"),
    onSuccess: async () => {
      toast("求职目标档案已保存");
      await loadDashboard();
      syncAgentContext();
    },
  });
}

function selectedCareerProfile() {
  return $("careerProfileSelect")?.value || state.careerProfile || "tech";
}

function careerProfileLabel(profileId = selectedCareerProfile()) {
  return state.careerProfiles.find((item) => item.id === profileId)?.label || "计算机 / 软件 / AI";
}

function syncCareerProfileToForms() {
  const profile = selectedCareerProfile();
  if ($("flowProfileLabel")) $("flowProfileLabel").textContent = careerProfileLabel(profile);
  const examples = {
    tech: "软件测试工程师 / AI 应用测试",
    ops: "新媒体运营 / 用户运营",
    marketing: "市场专员 / 商务拓展",
    finance: "财务助理 / 会计实习生",
    education: "学科教师 / 教务助理",
    hr: "人事行政专员 / 招聘助理",
  };
  const placeholder = examples[profile] || examples.tech;
  ["analysisJobTitle", "jobTitleInput", "interviewJobTitle", "professionalJobTitle"].forEach((id) => {
    const el = $(id);
    if (el) el.placeholder = `目标岗位，例如：${placeholder}`;
  });
  if ($("professionalCategory")?.value === "career" && $("questionCategory")?.value === "career") {
    loadQuestions("career");
  }
}

async function withLoading(task, message = "AI 正在整理你的求职策略...") {
  const layer = $("loadingLayer");
  const label = layer?.querySelector("span");
  if (label) label.textContent = message;
  layer?.classList.remove("hidden");
  try {
    return await task();
  } finally {
    layer?.classList.add("hidden");
  }
}

function updateSoundButton() {
  const button = $("soundToggleBtn");
  if (!button) return;
  button.classList.toggle("is-off", !state.soundEnabled);
  button.title = state.soundEnabled ? "关闭界面音效" : "开启界面音效";
  button.innerHTML = `<i data-lucide="${state.soundEnabled ? "volume-2" : "volume-x"}"></i>`;
  renderIcons();
}

function playUiTone(type = "tap") {
  if (!state.soundEnabled) return;
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return;
  try {
    state.audioContext = state.audioContext || new AudioCtx();
    if (state.audioContext.state === "suspended") state.audioContext.resume();
    const now = state.audioContext.currentTime;
    const oscillator = state.audioContext.createOscillator();
    const gain = state.audioContext.createGain();
    const presets = {
      tap: { freq: 520, duration: 0.055, volume: 0.018 },
      jump: { freq: 660, duration: 0.075, volume: 0.022 },
      success: { freq: 840, duration: 0.09, volume: 0.025 },
      warn: { freq: 260, duration: 0.08, volume: 0.018 },
    };
    const tone = presets[type] || presets.tap;
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(tone.freq, now);
    oscillator.frequency.exponentialRampToValueAtTime(Math.max(120, tone.freq * 0.82), now + tone.duration);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(tone.volume, now + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + tone.duration);
    oscillator.connect(gain);
    gain.connect(state.audioContext.destination);
    oscillator.start(now);
    oscillator.stop(now + tone.duration + 0.02);
  } catch (error) {
    console.warn("UI sound skipped", error);
  }
}

function toast(message, options = {}) {
  const node = $("toast");
  node.textContent = message;
  node.classList.remove("hidden");
  clearTimeout(node.timer);
  node.timer = setTimeout(() => node.classList.add("hidden"), 2600);
  if (!options.silent) {
    const isWarning = /失败|请先|不支持|不存在|错误/.test(message);
    playUiTone(isWarning ? "warn" : "success");
  }
}

function escapeHtml(text = "") {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderText(text = "") {
  return escapeHtml(text)
    .replace(/^### (.*)$/gm, "<h5>$1</h5>")
    .replace(/^## (.*)$/gm, "<h4>$1</h4>")
    .replace(/^\s*---+\s*$/gm, "<hr>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^(\d+)\. (.*)$/gm, "<div>$1. $2</div>")
    .replace(/^- (.*)$/gm, "<div>• $1</div>")
    .replace(/\n/g, "<br>");
}

async function loadProviders() {
  const data = await api("/config/ai-status");
  if (!data.success) return;
  state.providers = data.providers || [];
  $("providerSelect").innerHTML = data.providers.map((provider) => (
    `<option value="${provider.id}" ${provider.id === data.provider ? "selected" : ""}>${provider.name}</option>`
  )).join("");
  renderModelOptions(data.provider, data.selected_model || data.model);
  renderProviderLinks(data.provider);
  $("providerName").textContent = data.ai_enabled ? data.provider_name : "本地兜底";
  $("providerModel").textContent = data.ai_enabled ? data.model : "规则引擎可用";
  if ($("agentModeLabel")) {
    $("agentModeLabel").textContent = data.ai_enabled
      ? `${data.provider_name} 已连接`
      : "本地智能求职助手";
  }
  if ($("agentModeDetail")) {
    $("agentModeDetail").textContent = data.ai_enabled
      ? "本地任务优先执行；开放问题由模型增强，写入仍需你确认。"
      : "本地任务可直接执行；开放问题与完整简历深度改写需配置模型。";
  }
  $("providerDot").style.background = data.ai_enabled ? "var(--mint)" : "var(--yellow)";
}

function renderProviderLinks(providerId) {
  const links = PROVIDER_LINKS[providerId] || [];
  $("providerLinkList").innerHTML = links.map(([label, href]) => (
    `<a href="${href}" target="_blank" rel="noreferrer">${label}</a>`
  )).join("") || `<span class="muted-note">选择厂商后显示 API 获取入口。</span>`;
}

function filterModules(page, module, activeButton) {
  return shellController.filterModules(page, module, activeButton);
}

function renderModule(page, module) {
  return shellController.renderModule(page, module);
}

function navigateToRoute(page, module = null, options = {}) {
  return shellController.navigate(page, module, options);
}

function jumpToModule(page, module) {
  return shellController.jumpToModule(page, module);
}

function defaultModuleForPage(page) {
  return shellController.defaultModuleForPage(page);
}

function handleRouteTransition(previous, next) {
  return shellController.handleRouteTransition(previous, next);
}

function focusCleanedRoute(route) {
  return shellController.focusCleanedRoute(route);
}

function renderModelOptions(providerId, selectedModel = "") {
  const provider = state.providers.find((item) => item.id === providerId);
  if (!provider) {
    $("modelSelect").innerHTML = "";
    return;
  }
  const models = provider.models || [];
  const selected = selectedModel || provider.default_model || provider.model;
  $("modelSelect").innerHTML = models.map((model) => (
    `<option value="${model.id}" ${model.id === selected ? "selected" : ""}>${model.name}</option>`
  )).join("") + `<option value="custom">自定义模型 ID...</option>`;
  toggleCustomModelInput();
}

function toggleCustomModelInput() {
  const input = $("customModelInput");
  const select = $("modelSelect");
  if (!input || !select) return;
  const isCustom = select.value === "custom";
  input.classList.toggle("hidden", !isCustom);
  if (!isCustom) input.value = "";
}

async function saveProvider() {
  const provider = $("providerSelect").value;
  let model = $("modelSelect").value;
  if (model === "custom") {
    model = $("customModelInput").value.trim();
    if (!model) return toast("请输入自定义模型 ID，例如 deepseek-chat、kimi-k2.6");
  }
  const key = $("apiKeyInput").value.trim();
  const data = await api("/config/ai-key", { method: "POST", body: { provider, model, api_key: key } });
  if (data.success) {
    $("apiKeyInput").value = "";
    toast(key ? `已保存并启用 ${data.provider} / ${data.model}` : "已切换模型；未填 Key 时使用本地兜底");
    loadProviders();
  }
}

function applyTheme(theme) {
  state.theme = theme;
  localStorage.setItem("jobhunter_theme", theme);
  document.body.dataset.theme = theme;
  document.querySelectorAll("[data-theme-choice]").forEach((button) => {
    button.classList.toggle("active", button.dataset.themeChoice === theme);
  });

  const suffix = theme === "anime" ? "%20(2)" : "";
  const imageMap = {
    brandLogo: `/assets/images/logo${suffix}.png`,
    heroImage: `/assets/images/hero-bg${suffix}.png`,
    dashboardImage: `/assets/images/dashboard${suffix}.png`,
    resumeImage: `/assets/images/resume-analysis${suffix}.png`,
    jobMatchImage: `/assets/images/job-match${suffix}.png`,
    interviewImage: `/assets/images/interview-scene${suffix}.png`,
    interviewAvatar: `/assets/images/ai-avatar${suffix}.png`,
    trackImage: `/assets/images/application-track${suffix}.png`,
    coachAvatar: `/assets/images/ai-avatar${suffix}.png`,
  };
  const visualPositions = {
    resumeImage: "center 42%",
    interviewImage: "center 42%",
    trackImage: "center 72%",
    dashboardImage: "center",
  };
  Object.entries(imageMap).forEach(([id, src]) => {
    const node = $(id);
    if (node) {
      node.src = src;
      if (["resumeImage", "interviewImage", "trackImage", "dashboardImage"].includes(id)) {
        node.parentElement?.style.setProperty("--asset-bg", `url("${src}")`);
        node.parentElement?.style.setProperty("--asset-pos", visualPositions[id] || "center");
      }
    }
  });
  const loadingVideo = $("loadingVideo");
  if (loadingVideo) loadingVideo.src = `/assets/images/loading${theme === "anime" ? "%20(2)" : ""}.mp4`;
}

async function loadResumes() {
  return resumeController.load();
}

function updateResumeSelects() {
  return resumeController.updateSelects();
}

async function fillResume(id) {
  return resumeController.fill(id);
}

function openResumeUploadFromAgent() {
  cancelResumeEdit();
  return resumeController.openUploadFromAgent();
}

function fillResumeTitleFromFile() {
  return resumeController.fillTitleFromFile();
}

function setResumeEditNotice(title = "") {
  return resumeController.setEditNotice(title);
}

function cancelResumeEdit() {
  return resumeController.cancelEdit();
}

function openOriginalResume(id) {
  return resumeController.openOriginal(id);
}

async function replaceOriginalResume(id, input) {
  return resumeController.replaceOriginal(id, input);
}

async function saveResume() {
  return resumeController.save();
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function audioExtensionFromMime(mime = "") {
  return interviewController.extensionFromMime(mime);
}

async function downloadSavedAudio(filename, format = "wav") {
  return interviewController.downloadSavedAudio(filename, format);
}

async function downloadResponse(response, fallbackName) {
  if (!response.ok) {
    const text = await response.text();
    try {
      const data = JSON.parse(text);
      toast(data.message || "文件处理失败");
    } catch {
      toast("文件处理失败");
    }
    return;
  }
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i);
  const filename = decodeURIComponent(match?.[1] || match?.[2] || fallbackName);
  downloadBlob(await response.blob(), filename);
  toast("文件已生成并开始下载");
}

async function exportResume(format) {
  return resumeController.export(format);
}

async function convertDocument(route, inputId) {
  return resumeController.convertDocument(route, inputId);
}

async function generateResume() {
  return resumeController.generate();
}

function renderResumeAuditResult(data) {
  return resumeController.renderAudit(data);
}

async function analyzeResume(id) {
  return resumeController.analyze(id);
}

function selectedAnalysisResumeId() {
  return resumeController.selectedAnalysisId();
}

async function auditSelectedResume() {
  return resumeController.auditSelected();
}

async function improveSelectedResume() {
  return resumeController.improveSelected();
}

async function deleteResume(id) {
  return resumeController.remove(id);
}

function selectedResumeId() {
  return resumeController.selectedResumeId();
}

function selectedTailorResumeId() {
  return resumeController.selectedTailorId();
}

function selectedSkillResumeId() {
  return resumeController.selectedSkillId();
}

async function tailorResume() {
  return resumeController.tailor();
}

async function matchResume() {
  return resumeController.match();
}

async function analyzeJdOnly() {
  return resumeController.analyzeJd();
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
  const resume = state.resumes.find((item) => item.id === handoff.resumeId)?.title || "未关联简历";
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

async function renderSkills() {
  return resumeController.renderSkills();
}

async function startInterview() {
  return interviewController.start();
}

function updateInterviewQuestion(data) {
  return interviewController.updateQuestion(data);
}

function openInterviewRoom(data) {
  return interviewController.openRoom(data);
}

function stageName(stage) {
  return interviewController.stageName(stage);
}

async function sendInterviewAnswer() {
  return interviewController.sendAnswer();
}

async function sendRoomAnswer() {
  return interviewController.sendRoomAnswer();
}

function renderFeedback(feedback) {
  return interviewController.renderFeedback(feedback);
}

function renderFeedbackHtml(feedback) {
  return interviewController.renderFeedbackHtml(feedback);
}

async function analyzeVoice() {
  return interviewController.analyzeVoice();
}

function getRecordingController() {
  return interviewController.getRecordingController();
}

async function startAudioRecording(target = "answer") {
  return interviewController.startAudioRecording(target);
}

function stopAudioRecording() {
  return interviewController.stopAudioRecording();
}

async function handleAudioUpload() {
  return interviewController.handleAudioUpload();
}

async function computeAudioMetrics(blob, source = "upload", startedAt = 0) {
  return interviewController.computeAudioMetrics(blob, source, startedAt);
}

function renderAudioPreview(target = "answer") {
  return interviewController.renderAudioPreview(target);
}

async function analyzeRecordedAudio(target = "answer") {
  return interviewController.analyzeRecordedAudio(target);
}

async function loadQuestions(category = "all") {
  return interviewController.loadQuestions(category);
}

function escapeAttr(text = "") {
  return interviewController.escapeAttr(text);
}

function categoryName(category) {
  return interviewController.categoryName(category);
}

function selectQuestion(question, category) {
  return interviewController.selectQuestion(question, category);
}

function showSampleAnswer(answer) {
  return interviewController.showSampleAnswer(answer);
}

async function loadTrainingRecords() {
  return interviewController.loadTrainingRecords();
}

function renderRecordColumn(title, type, items, bodyRenderer) {
  return interviewController.renderRecordColumn(title, type, items, bodyRenderer);
}

async function viewTrainingRecord(type, id) {
  return interviewController.viewTrainingRecord(type, id);
}

function renderRecordDetail(type, item) {
  return interviewController.renderRecordDetail(type, item);
}

function safeJson(value) {
  return interviewController.safeJson(value);
}

function renderConversation(value) {
  return interviewController.renderConversation(value);
}

function parseFeedbackSummary(feedback) {
  return interviewController.parseFeedbackSummary(feedback);
}

function formatDate(value) {
  return interviewController.formatDate(value);
}

async function deleteTrainingRecord(type, id) {
  return interviewController.deleteTrainingRecord(type, id);
}

async function clearTrainingRecords() {
  return interviewController.clearTrainingRecords();
}

async function loadProfessionalPack() {
  return interviewController.loadProfessionalPack();
}

function selectProfessionalQuestion(question) {
  return interviewController.selectProfessionalQuestion(question);
}

function showProfessionalReference(reference) {
  return interviewController.showProfessionalReference(reference);
}

async function scoreProfessionalAnswer() {
  return interviewController.scoreProfessionalAnswer();
}

async function scorePractice() {
  return interviewController.scorePractice();
}

function applyBrowserCapabilities() {
  return interviewController.applyBrowserCapabilities();
}

function setupSpeechRecognition() {
  return interviewController.setupSpeechRecognition();
}

function toggleVoiceInput() {
  return interviewController.toggleVoiceInput();
}

async function saveApplication() {
  return opportunityController.saveApplication();
}

async function editApplication(id) {
  return opportunityController.editApplication(id);
}

async function deleteApplication(id) {
  return opportunityController.deleteApplication(id);
}

async function loadApplications() {
  return opportunityController.loadApplications();
}

async function openOpportunityWorkspace(id, options = {}) {
  return opportunityController.openWorkspace(id, options);
}

async function loadOpportunityWorkspace(id, request = {}) {
  return opportunityController.loadWorkspace(id, request);
}

function showOpportunityWorkspaceError(opportunityId, message) {
  return opportunityController.showWorkspaceError(opportunityId, message);
}

function retryOpportunityWorkspace(opportunityId) {
  return opportunityController.retryWorkspace(opportunityId);
}

function resetOpportunityWorkspaceView(context = {}) {
  return opportunityController.resetWorkspace(context);
}

function closeOpportunityWorkspace() {
  return opportunityController.closeWorkspace();
}

function selectOpportunityTab(selectedTab, moveFocus = true) {
  return opportunityController.selectTab(selectedTab, moveFocus);
}

function handleOpportunityTabKeydown(event) {
  return opportunityController.handleTabKeydown(event);
}

function renderOpportunityWorkspace(workspace) {
  return opportunityController.renderWorkspace(workspace);
}

function workspaceDate(value, fallback = "未设置") {
  return opportunityController.workspaceDate(value, fallback);
}

function renderOpportunityOverview(workspace) {
  return opportunityController.renderOverview(workspace);
}

function renderOpportunityMatch(workspace) {
  return opportunityController.renderMatch(workspace);
}

function useWorkspaceJd() {
  return opportunityController.useWorkspaceJd();
}

function renderOpportunityResume(workspace) {
  return opportunityController.renderResume(workspace);
}

function openWorkspaceResume(resumeId, hasOriginal) {
  return opportunityController.openWorkspaceResume(resumeId, hasOriginal);
}

function renderOpportunityInterview(workspace) {
  return opportunityController.renderInterview(workspace);
}

function prepareInterviewFromOpportunity(actionId = null) {
  return opportunityController.prepareInterview(actionId);
}

async function continueOpportunityInterview(sessionId) {
  return opportunityController.continueInterview(sessionId);
}

function renderOpportunityTimeline(workspace) {
  return opportunityController.renderTimeline(workspace);
}

async function advanceApplication(id) {
  return opportunityController.advanceApplication(id);
}

async function coachApplication(id) {
  return opportunityController.coachApplication(id);
}

async function evaluateSalary() {
  return opportunityController.evaluateSalary();
}

async function loadDashboard() {
  return opportunityController.loadDashboard();
}

function renderCareerPulse(pulse) {
  return opportunityController.renderCareerPulse(pulse);
}

function renderNextActions(actions) {
  return opportunityController.renderNextActions(actions);
}

function currentAgentResumeId() {
  return agentController.currentResumeId();
}

function syncAgentContext() {
  return agentController.syncContext();
}

function renderAgentContextChips() {
  return agentController.renderContextChips();
}

function openAgentDrawer(event) {
  return agentController.openDrawer(event);
}

function closeAgentDrawer() {
  return agentController.closeDrawer();
}

function handleAgentDrawerKeydown(event) {
  return agentController.handleDrawerKeydown(event);
}

async function loadAgentCommandCenter() {
  const request = agentCommandCenterGate.begin("command-center");
  const proposalEpoch = state.agentProposalMutationEpoch;
  let data;
  try {
    data = await api("/agent/actions");
  } catch (_error) {
    data = { success: false, actions: [] };
  }
  if (
    !agentCommandCenterGate.isCurrent(request, "command-center")
    || proposalEpoch !== state.agentProposalMutationEpoch
  ) return;
  const actions = data.success ? data.actions || [] : [];
  state.agentCommandProposalIds.forEach((proposalId) => {
    if (!state.agentConversationProposalIds.has(proposalId)) state.agentProposals.delete(proposalId);
  });
  const mergedActions = actions
    .map((proposal) => mergeAgentProposal(proposal, proposalEpoch))
    .filter((proposal) => proposal?.status === "pending");
  state.agentCommandProposalIds = new Set(mergedActions.map((proposal) => Number(proposal.id)));
  renderAgentCommandActions(mergedActions, data.success ? "" : "待确认操作暂时无法加载");
  renderAgentCommandOpportunities();
}

function renderAgentCommandActions(actions, error = "") {
  const box = $("agentActiveActions");
  const count = actions.length;
  $("agentActionCount").textContent = String(count);
  $("agentLauncherBadge").textContent = String(count);
  $("agentLauncherBadge").classList.toggle("hidden", !count);
  if (!box) return;
  if (error) {
    box.innerHTML = `<div class="command-empty" role="alert">${escapeHtml(error)}<button type="button" class="ghost small" onclick="loadAgentCommandCenter()">重试</button></div>`;
    return;
  }
  box.innerHTML = count ? actions.map((proposal) => `
    <button type="button" class="command-row" onclick="openAgentProposal(${Number(proposal.id)}, this)">
      <span><b>${escapeHtml(proposal.preview || "待确认操作")}</b><small>${escapeHtml(proposal.risk_level === "high" ? "高风险" : proposal.risk_level === "medium" ? "需确认" : "低风险")}</small></span>
      <i data-lucide="arrow-right"></i>
    </button>`).join("") : '<div class="command-empty"><b>没有待确认操作</b><span>Agent 提出的写入动作会先出现在这里。</span></div>';
  renderIcons();
}

function renderAgentCommandOpportunities() {
  const box = $("agentCommandOpportunities");
  if (!box) return;
  const active = state.applications.filter((item) => (
    ContextualAgent.isActiveOpportunity(item.status, state.applicationStatuses)
  )).slice(0, 6);
  box.innerHTML = active.length ? active.map((item) => `
    <button type="button" class="command-row" onclick="closeAgentDrawer(); openOpportunityWorkspace(${Number(item.id)})">
      <span><b>${escapeHtml(item.company || "未命名公司")} / ${escapeHtml(item.job_title || "目标岗位")}</b><small>${escapeHtml(item.needs_status_review ? "待确认" : item.status || "未设置")}</small></span>
      <i data-lucide="panel-right-open"></i>
    </button>`).join("") : '<div class="command-empty"><b>暂无活跃机会</b><span>在投递看板添加机会后，会同步到这里。</span></div>';
  renderIcons();
}

function openAgentProposal(proposalId, opener = null) {
  openAgentDrawer({ currentTarget: opener || $("agentLauncher") });
  const existing = $("chatLog").querySelector(`[data-proposal-id="${Number(proposalId)}"]`);
  if (existing) return existing.scrollIntoView({ block: "center", behavior: "smooth" });
  const proposal = state.agentProposals.get(Number(proposalId));
  if (!proposal) return;
  appendMessage("这项操作需要你的确认。", "bot", { proposals: [proposal] });
}

async function sendAgentMessage(forcedMessage = "", extraContext = {}) {
  const input = $("agentInput");
  const hasForcedMessage = typeof forcedMessage === "string" && forcedMessage.trim();
  const message = ContextualAgent.outboundMessage(forcedMessage, input?.value || "");
  if (!message) return;
  if (!state.agentConversationId) await createAgentConversation();
  const conversationId = state.agentConversationId;
  if (!conversationId) return;
  agentConversationEpoch.invalidate();
  appendMessage(message, "user");
  if (!hasForcedMessage) input.value = "";
  const chatRequest = {
    ...ContextualAgent.chatPayload(message, conversationId, {
      ...agentController.contextPayload(),
      ...extraContext,
    }),
    conversation_id: conversationId,
  };
  const data = await withLoading(
    () => api("/agent/chat", {
      method: "POST",
      body: chatRequest,
    }),
    "求职 Agent 正在读取上下文并处理任务..."
  );
  if (state.agentConversationId !== conversationId || (data.success && data.conversation_id !== conversationId)) return;
  if (!data.success) return toast(data.message || "求职 Agent 暂时不可用");
  localStorage.setItem(JOBHUNTER_AGENT_CONVERSATION, conversationId);
  const reply = data.reply || data.message || "我暂时没想好，换个问法试试。";
  appendMessage(reply, "bot", {
    proposals: data.action_proposals || [],
    inputRequest: data.input_request || {},
  });
  renderAgentEvents(data.events || [], data.status);
  renderAgentSuggestedActions(data.suggested_actions || []);
  await loadAgentConversations(conversationId, false);
  await loadAgentCommandCenter();
}

async function generateCareerReport() {
  $("agentInput").value = "结合我的简历、面试和投递数据，生成一份求职作战报告";
  await sendAgentMessage();
}

function appendMessage(text, type, options = {}) {
  const node = document.createElement("div");
  node.className = `message ${type}`;
  node.innerHTML = renderText(text);
  $("chatLog").appendChild(node);
  renderAgentProposals(options.proposals || [], node);
  renderAgentInputRequest(options.inputRequest || {}, node);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}

function renderAgentInputRequest(inputRequest, messageNode) {
  if (!messageNode || !window.ContextualAgent) return;
  const html = ContextualAgent.inputRequestHtml(inputRequest);
  if (html) messageNode.insertAdjacentHTML("beforeend", html);
}

async function loadAgentConversations(preferredId = "", restore = true) {
  const data = await api(`/agent/conversations/${USER_ID}`);
  if (!data.success) return;
  let conversations = data.conversations || [];
  if (!conversations.length) {
    await createAgentConversation();
    return;
  }
  const saved = preferredId || state.agentConversationId || localStorage.getItem(JOBHUNTER_AGENT_CONVERSATION);
  state.agentConversationId = conversations.some((item) => item.id === saved)
    ? saved
    : conversations[0].id;
  localStorage.setItem(JOBHUNTER_AGENT_CONVERSATION, state.agentConversationId);
  const select = $("agentConversationSelect");
  select.innerHTML = conversations.map((item) => (
    `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title || "新对话")}</option>`
  )).join("");
  select.value = state.agentConversationId;
  if (restore) await restoreAgentMessages();
}

async function createAgentConversation() {
  const data = await api("/agent/conversations", {
    method: "POST",
    body: { user_id: USER_ID, title: "新对话" },
  });
  if (!data.success) return toast(data.message || "新建会话失败");
  agentConversationEpoch.invalidate();
  state.agentConversationId = data.conversation.id;
  localStorage.setItem(JOBHUNTER_AGENT_CONVERSATION, state.agentConversationId);
  await loadAgentConversations(state.agentConversationId, false);
  renderAgentWelcome();
  $("agentInput")?.focus();
}

async function clearAgentConversation() {
  if (!state.agentConversationId) return;
  if (!confirm("确定清空当前求职 Agent 会话吗？其他会话和求职数据不会受影响。")) return;
  const data = await api(`/agent/conversations/${state.agentConversationId}/clear`, {
    method: "POST",
    body: { user_id: USER_ID },
  });
  if (!data.success) return toast(data.message || "清空失败");
  agentConversationEpoch.invalidate();
  renderAgentWelcome();
  toast("当前会话已清空");
}

async function restoreAgentMessages() {
  const conversationId = state.agentConversationId;
  if (!conversationId) {
    agentConversationEpoch.invalidate();
    return renderAgentWelcome();
  }
  const request = agentConversationEpoch.begin(conversationId);
  let data;
  try {
    data = await api(
      `/agent/conversations/${conversationId}/messages?user_id=${USER_ID}`
    );
  } catch (_error) {
    data = { success: false, messages: [] };
  }
  if (!agentConversationEpoch.isCurrent(request, state.agentConversationId)) return;
  if (!data.success || !data.messages?.length) return renderAgentWelcome();
  const preparedMessages = [];
  for (const message of data.messages) {
    const proposals = message.role === "assistant"
      ? await hydrateAgentProposals(ContextualAgent.proposalsFromMetadata(message.metadata))
      : [];
    if (!agentConversationEpoch.isCurrent(request, state.agentConversationId)) return;
    preparedMessages.push({ message, proposals });
  }
  if (!agentConversationEpoch.isCurrent(request, state.agentConversationId)) return;
  state.agentConversationProposalIds.forEach((proposalId) => {
    if (!state.agentCommandProposalIds.has(proposalId)) state.agentProposals.delete(proposalId);
  });
  state.agentConversationProposalIds = new Set(
    preparedMessages.flatMap(({ proposals }) => proposals.map((proposal) => Number(proposal.id)))
  );
  $("chatLog").innerHTML = "";
  for (const { message, proposals } of preparedMessages) {
    appendMessage(message.content, message.role === "user" ? "user" : "bot", {
      proposals,
      inputRequest: message.metadata?.input_request || {},
    });
    if (message.role === "assistant") {
      renderAgentEvents(message.metadata?.events || [], message.metadata?.status || "completed");
      renderAgentSuggestedActions(message.metadata?.suggested_actions || []);
    }
  }
}

async function hydrateAgentProposals(proposals) {
  return Promise.all(proposals.map(hydrateAgentProposal));
}

async function hydrateAgentProposal(proposal) {
  let latest;
  try {
    latest = await api(`/agent/actions/${Number(proposal.id)}`);
  } catch (_error) {
    return ContextualAgent.unavailableProposal(
      proposal, ContextualAgent.hydrationFailureKind(null, _error)
    );
  }
  if (!latest.success) {
    return ContextualAgent.unavailableProposal(
      proposal, ContextualAgent.hydrationFailureKind(latest)
    );
  }
  return ContextualAgent.authoritativeHydrationSuccess(latest.action);
}

function renderAgentProposals(proposals, messageNode) {
  if (!messageNode || !proposals.length) return;
  proposals.forEach((proposal) => {
    state.agentConversationProposalIds.add(Number(proposal.id));
    const merged = mergeAgentProposal(proposal, state.agentProposalMutationEpoch);
    messageNode.insertAdjacentHTML("beforeend", ContextualAgent.proposalHtml(merged));
  });
}

function mergeAgentProposal(proposal, incomingEpoch = state.agentProposalMutationEpoch) {
  const proposalId = Number(proposal?.id);
  if (!Number.isInteger(proposalId) || proposalId <= 0) return proposal;
  const current = state.agentProposals.get(proposalId);
  const currentEpoch = state.agentProposalEpochs.get(proposalId) || 0;
  const merged = ContextualAgent.mergeProposalState(current, proposal, {
    currentEpoch,
    incomingEpoch,
  });
  if (merged !== current) {
    state.agentProposals.set(proposalId, merged);
    state.agentProposalEpochs.set(proposalId, Math.max(currentEpoch, incomingEpoch));
  }
  return merged;
}

function advanceAgentProposalMutation() {
  state.agentProposalMutationEpoch += 1;
  agentConversationEpoch.invalidate();
  return state.agentProposalMutationEpoch;
}

function proposalError(data, fallback) {
  return data?.error?.message || data?.message || fallback;
}

function proposalChanges(card, proposal) {
  const changes = {};
  card.querySelectorAll("[data-agent-edit-field]").forEach((input) => {
    const path = input.dataset.agentEditField.split(".");
    const original = path.reduce((value, key) => value?.[key], proposal.editable);
    let value = input.value;
    if (typeof original === "number") value = Number(value);
    if (Array.isArray(original)) {
      try { value = JSON.parse(value); } catch (_error) { value = input.value.split(",").map((item) => item.trim()).filter(Boolean); }
    }
    let target = changes;
    path.forEach((key, index) => {
      if (index === path.length - 1) target[key] = value;
      else target = target[key] ||= {};
    });
  });
  return changes;
}

function replaceProposalCard(card, proposal, incomingEpoch = state.agentProposalMutationEpoch) {
  const merged = mergeAgentProposal(proposal, incomingEpoch);
  card.outerHTML = ContextualAgent.proposalHtml(merged);
  renderIcons();
  return merged;
}

async function handleAgentChatLogClick(event) {
  const navigation = event.target.closest("[data-agent-navigation]");
  if (navigation) {
    const actions = ContextualAgent.normalizedSuggestedActions([{
      label: navigation.textContent || "下一步",
      page: navigation.dataset.agentPage,
      module: navigation.dataset.agentModule,
    }]);
    if (actions[0]) {
      closeAgentDrawer();
      jumpToModule(actions[0].page, actions[0].module);
    }
    return;
  }
  const choice = event.target.closest("[data-agent-resume-choice]");
  if (choice) {
    const resumeId = Number(choice.dataset.agentResumeChoice);
    const workflow = ["revision", "analysis", "interview_questions"].includes(choice.dataset.agentWorkflow)
      ? choice.dataset.agentWorkflow : "analysis";
    const message = ContextualAgent.selectionMessage({ workflow }, {
      id: resumeId,
      label: choice.dataset.agentResumeLabel,
    });
    if (message) await sendAgentMessage(message, { resume_id: resumeId });
    return;
  }
  await handleProposalClick(event);
}

async function openAgentResumeDraft(card, proposal) {
  const existing = card.querySelector(".agent-draft-editor");
  if (existing) return existing.scrollIntoView({ block: "nearest", behavior: "smooth" });
  let data;
  try {
    data = await api(`/agent/actions/${Number(proposal.id)}/draft`);
  } catch (_error) {
    toast("草稿暂时无法加载，请重试");
    return;
  }
  if (!data.success || !data.draft) {
    toast(proposalError(data, "草稿暂时无法加载"));
    return;
  }
  const draft = data.draft;
  const editor = document.createElement("section");
  editor.className = "agent-draft-editor";
  editor.innerHTML = `<header><b>版本草稿</b><small>确认前可编辑；保存后会新建版本，不覆盖原简历。</small></header>`;
  const textarea = document.createElement("textarea");
  textarea.className = "input textarea agent-draft-content";
  textarea.rows = 12;
  textarea.value = String(draft.content || "");
  textarea.setAttribute("aria-label", "可编辑的简历版本草稿");
  const controls = document.createElement("div");
  controls.className = "proposal-controls";
  const save = document.createElement("button");
  save.type = "button";
  save.className = "ghost";
  save.dataset.agentAction = "save-draft";
  save.textContent = "保存草稿修改";
  controls.appendChild(save);
  editor.append(textarea, controls);
  card.appendChild(editor);
  textarea.focus({ preventScroll: true });
}

async function saveAgentResumeDraft(card, proposal) {
  const textarea = card.querySelector(".agent-draft-content");
  const content = String(textarea?.value || "").trim();
  if (!content) return toast("草稿正文不能为空");
  const save = card.querySelector('[data-agent-action="save-draft"]');
  if (save) save.disabled = true;
  try {
    const data = await api(`/agent/actions/${Number(proposal.id)}/edit`, {
      method: "POST", body: { content },
    });
    if (!data.success) return toast(proposalError(data, "草稿保存失败，请重试"));
    mergeAgentProposal(data.action, advanceAgentProposalMutation());
    toast("草稿已更新，确认后才会保存为新版本");
  } catch (_error) {
    toast("网络连接失败，草稿未保存");
  } finally {
    if (save) save.disabled = false;
  }
}

async function handleProposalClick(event) {
  const button = event.target.closest("[data-agent-action]");
  if (!button) return;
  const card = button.closest("[data-proposal-id]");
  const proposalId = Number(card?.dataset.proposalId);
  const actionName = button.dataset.agentAction;
  const proposal = state.agentProposals.get(proposalId);
  if (card && proposal && actionName === "open-draft") {
    await openAgentResumeDraft(card, proposal);
    return;
  }
  if (card && proposal && actionName === "save-draft") {
    await saveAgentResumeDraft(card, proposal);
    return;
  }
  if (card && proposal && actionName === "retry-hydration") {
    const hydrationEpoch = advanceAgentProposalMutation();
    const source = proposal.hydrationSource || proposal;
    replaceProposalCard(card, { ...proposal, hydrationRetry: false, busy: true }, hydrationEpoch);
    const hydrated = await hydrateAgentProposal(source);
    const freshCard = $("chatLog").querySelector(`[data-proposal-id="${proposalId}"]`);
    if (freshCard) replaceProposalCard(freshCard, hydrated, hydrationEpoch);
    return;
  }
  if (!card || !proposal || proposal.status !== "pending") return;
  const mutationEpoch = advanceAgentProposalMutation();
  const body = actionName === "edit" ? proposalChanges(card, proposal) : {};
  const startEvent = `${actionName}_start`;
  let next = ContextualAgent.transitionProposal(proposal, startEvent);
  replaceProposalCard(card, next, mutationEpoch);
  try {
    const data = await api(`/agent/actions/${proposalId}/${actionName}`, { method: "POST", body });
    const freshCard = $("chatLog").querySelector(`[data-proposal-id="${proposalId}"]`);
    if (!data.success) {
      next = ContextualAgent.transitionProposal(next, `${actionName}_error`, {
        error: proposalError(data, "操作失败，请重试"),
      });
      if (freshCard) replaceProposalCard(freshCard, next, mutationEpoch);
      return;
    }
    const successEpoch = advanceAgentProposalMutation();
    next = ContextualAgent.transitionProposal(next, `${actionName}_success`, { action: data.action });
    if (freshCard) replaceProposalCard(freshCard, next, successEpoch);
    const commandRefresh = loadAgentCommandCenter();
    if (actionName === "confirm") {
      await refreshAfterAgentAction(next.result);
      toast("操作已确认并完成");
    } else if (actionName === "cancel") {
      toast("操作已取消，业务数据未改变");
    } else {
      toast("预览已更新，请确认后执行");
    }
    await commandRefresh;
  } catch (_error) {
    const freshCard = $("chatLog").querySelector(`[data-proposal-id="${proposalId}"]`);
    next = ContextualAgent.transitionProposal(next, `${actionName}_error`, { error: "网络连接失败，请重试" });
    if (freshCard) replaceProposalCard(freshCard, next, mutationEpoch);
  }
}

async function focusAgentResultFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const mappings = ["resume", "action", "profile", "report"];
  const key = mappings.find((candidate) => params.has(candidate));
  if (!key) return;
  const id = Number(params.get(key));
  if (!Number.isInteger(id) || id <= 0) return;
  $("focusedAgentResult")?.remove();
  $("agentResultFocus")?.classList.add("hidden");
  if (key === "resume") {
    const card = document.querySelector(`[data-resume-id="${id}"]`);
    if (!card) return toast("结果简历不存在或已归档");
    card.classList.add("is-result-highlight");
    card.focus({ preventScroll: true });
    card.scrollIntoView({ block: "center", behavior: "smooth" });
    return;
  }
  if (key === "action") {
    let data;
    try {
      const response = await api("/action-items");
      const action = response.success
        ? (response.data || []).find((item) => Number(item.id) === id)
        : null;
      data = action
        ? { success: true, data: action }
        : { success: false, http_status: response.http_status || 404 };
    } catch (error) {
      return renderAgentResultLookup(key, id, ContextualAgent.resultLookupState(id, null, error));
    }
    const lookup = ContextualAgent.resultLookupState(id, data);
    const action = lookup.entity;
    if (action) {
      $("agentActiveActions").insertAdjacentHTML("afterbegin", `
        <div class="command-row is-result-highlight" tabindex="-1" id="focusedAgentResult"><span><b>${escapeHtml(action.title)}</b><small>${escapeHtml(action.status || "pending")} · 行动 #${id}</small></span></div>`);
      $("focusedAgentResult").focus({ preventScroll: true });
      return;
    }
    return renderAgentResultLookup(key, id, lookup);
  }
  const endpoint = key === "profile" ? `/profile/${id}` : `/career-reports/${id}`;
  let response;
  try {
    response = await api(endpoint);
  } catch (error) {
    return renderAgentResultLookup(key, id, ContextualAgent.resultLookupState(id, null, error));
  }
  const lookup = ContextualAgent.resultLookupState(id, response);
  if (lookup.status !== "located") return renderAgentResultLookup(key, id, lookup);
  renderAgentResultLookup(key, id, lookup);
}

function renderAgentResultLookup(key, id, lookup) {
  const labels = { action: "行动", profile: "求职目标", report: "求职报告" };
  const host = key === "profile" ? $("agentResultFocus") : $("agentActiveActions");
  if (!host) return;
  host.classList.remove("hidden");
  if (lookup.status === "located") {
    const entity = lookup.entity || {};
    if (key === "profile") {
      host.innerHTML = ContextualAgent.profileResultHtml(lookup.entity);
    } else {
      host.insertAdjacentHTML("afterbegin", `
        <div class="command-row is-result-highlight" id="focusedAgentResult" tabindex="-1"><span><b>${escapeHtml(entity.title || labels[key])}</b><small>已验证 ${escapeHtml(labels[key])} #${id}</small></span></div>`);
    }
  } else {
    const message = lookup.status === "missing" ? "结果不存在或已失效" : "结果暂时无法读取";
    host.insertAdjacentHTML("afterbegin", `
      <div class="command-empty" id="focusedAgentResult" tabindex="-1" role="status"><b>${message}</b><span>${escapeHtml(labels[key])} #${id}</span>${lookup.retry ? '<button type="button" class="ghost small" onclick="focusAgentResultFromQuery()">重试</button>' : ""}</div>`);
  }
  $("focusedAgentResult")?.focus({ preventScroll: true });
}

async function refreshAfterAgentAction(result) {
  const openOpportunityId = state.currentOpportunityId;
  await Promise.all([loadResumes(), loadApplications(), loadDashboard()]);
  if (openOpportunityId) {
    await loadOpportunityWorkspace(openOpportunityId, { isCurrent: () => true });
  }
  syncAgentContext();
}

function renderAgentWelcome() {
  state.agentConversationProposalIds.forEach((proposalId) => {
    if (!state.agentCommandProposalIds.has(proposalId)) state.agentProposals.delete(proposalId);
  });
  state.agentConversationProposalIds = new Set();
  $("chatLog").innerHTML = "";
  appendMessage(
    "你好，我是你的求职 Agent。无需 API Key 也能读取本地求职数据、诊断当前进度并安排下一步；配置模型后还可以处理更开放的问题。",
    "bot"
  );
}

function renderAgentEvents(events, status = "completed") {
  if (!events.length && status === "completed") return;
  const labels = {
    list_resumes: "读取简历列表",
    get_resume: "读取简历正文",
    analyze_resume: "分析简历",
    diagnose_resume: "本地诊断简历",
    prepare_resume_revision: "生成可编辑草稿",
    propose_career_action: "创建待确认操作",
    match_job: "匹配目标岗位",
    analyze_jd: "解析岗位 JD",
    get_interview_question: "获取面试题",
    generate_resume_interview_questions: "生成定制面试题",
    evaluate_answer: "评估面试回答",
    list_applications: "读取投递记录",
    get_dashboard: "读取求职看板",
    get_career_profile: "读取职业目标",
    list_action_items: "读取行动项",
    get_training_insights: "汇总训练记录",
    generate_career_report: "汇总求职报告",
    web_search: "搜索公开信息",
    fetch_webpage: "读取公开网页",
  };
  const rows = events.map((event) => `
    <span class="agent-event ${event.status === "success" ? "is-success" : "is-error"}">
      <i data-lucide="${event.status === "success" ? "check" : "triangle-alert"}"></i>
      ${escapeHtml(labels[event.name] || event.name)}
    </span>
  `).join("");
  const statusText = status === "degraded" ? "本地执行" : status === "needs_input" ? "选择简历后继续" : "任务记录";
  const node = $("chatLog").lastElementChild;
  node?.insertAdjacentHTML("beforeend", `<div class="agent-events"><small>${statusText}</small>${rows}</div>`);
  renderIcons();
}

function renderAgentSuggestedActions(actions) {
  const html = ContextualAgent.suggestedActionsHtml(actions);
  if (!html) return;
  const node = $("chatLog").lastElementChild;
  node?.insertAdjacentHTML("beforeend", html);
  renderIcons();
}
