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

const agentContext = ContextualAgent.createContextStore();
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
  defaultModule: defaultModuleForPage,
  onRouteTransition: handleRouteTransition,
  focusRoute: focusCleanedRoute,
  showPage: (page) => {
    if ($(`page-${page}`)) renderPage(page);
  },
  showModule: renderModule,
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
  document.querySelectorAll("[data-page]").forEach((item) => {
    item.addEventListener("click", () => {
      playUiTone("jump");
      navigateToRoute(item.dataset.page);
    });
  });
}

function renderPage(page) {
  if (state.currentPage !== page) state.currentModule = "";
  state.currentPage = page;
  document.querySelectorAll(".page").forEach((item) => item.classList.remove("active"));
  $(`page-${page}`).classList.add("active");
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.page === page));
  const titles = {
    home: "项目总览",
    resume: "简历实验室",
    interview: "面试训练场",
    tracker: "投递看板",
    agent: "求职指挥台",
  };
  $("pageTitle").textContent = titles[page] || "JobHunter AI";
  syncAgentContext();
  if (page === "agent") loadAgentCommandCenter();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function applyInitialRouteFromQuery() {
  await opportunityHistory.sync();
  const params = new URLSearchParams(window.location.search);
  const record = params.get("record");
  if (record === "audio") {
    setTimeout(() => {
      const audioCard = [...document.querySelectorAll(".record-card")].find((card) => card.textContent.includes("语音") || card.textContent.includes("录音") || card.textContent.includes("表达"));
      audioCard?.querySelector(".record-actions button")?.click();
    }, 500);
  }
}

function bindActions() {
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
  $("agentLauncher")?.addEventListener("click", openAgentDrawer);
$("openAgentWorkspace")?.addEventListener("click", openAgentDrawer);
$("openAgentWorkspaceFromHelper")?.addEventListener("click", openAgentDrawer);
  $("closeAgentDrawer")?.addEventListener("click", closeAgentDrawer);
  $("agentDrawerBackdrop")?.addEventListener("click", closeAgentDrawer);
  $("agentContextChips")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-agent-context]");
    if (!button) return;
    agentContext.remove(button.dataset.removeAgentContext);
    renderAgentContextChips();
  });
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
  ["analysisResumeSelect", "exportResumeSelect", "tailorResumeSelect", "skillResumeSelect", "interviewResumeSelect"].forEach((id) => {
    $(id)?.addEventListener("change", syncAgentContext);
  });
  document.addEventListener("keydown", handleAgentDrawerKeydown);
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
  document.querySelectorAll(`[data-filter-page="${page}"] button`).forEach((button) => {
    button.classList.toggle("active", button === activeButton);
  });
  document.querySelectorAll(`.module-panel[data-module-page="${page}"]`).forEach((panel) => {
    panel.classList.toggle("is-filtered-out", panel.dataset.module !== module);
  });
}

function renderModule(page, module) {
  if (page === state.currentPage) state.currentModule = module || "";
  const button = document.querySelector(`[data-section-filter="${page}:${module}"]`);
  if (button) filterModules(page, module, button);
  syncAgentContext();
}

function navigateToRoute(page, module = null, options = {}) {
  return opportunityHistory.navigate(page, { module, historyMode: options.historyMode || "push" });
}

function jumpToModule(page, module) {
  return navigateToRoute(page, module);
}

function defaultModuleForPage(page) {
  return document.querySelector(`[data-filter-page="${page}"] [data-section-filter]`)
    ?.dataset.sectionFilter.split(":")[1] || null;
}

function handleRouteTransition(previous, next) {
  if (state.pendingApplicationHandoff && routeLeavesFlow(previous, next, "tracker", "add")) {
    clearApplicationHandoff();
  }
  if (state.matchOpportunityId && routeLeavesFlow(previous, next, "resume", "jd")) {
    clearMatchOpportunityLink();
  }
  if (state.interviewOpportunityHandoff && routeLeavesFlow(previous, next, "interview", "mock")) {
    state.interviewOpportunityHandoff = null;
  }
}

function focusCleanedRoute(route) {
  const panel = route.module
    ? document.querySelector(`.module-panel[data-module-page="${route.page}"][data-module="${route.module}"]:not(.is-filtered-out)`)
    : null;
  const target = panel?.querySelector("h2, h3") || $("pageTitle");
  if (!target) return;
  target.tabIndex = -1;
  target.focus({ preventScroll: true });
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
  const company = $("appCompany").value.trim();
  const job = $("appJob").value.trim();
  if (!company || !job) return toast("请填写公司和岗位");
  const payload = {
    user_id: USER_ID,
    company,
    job_title: job,
    status: $("appStatus").value,
    city: $("appCity").value,
    notes: $("appNotes").value,
    ...applicationPayloadForJob(state.pendingApplicationHandoff, job),
  };
  if (state.editingAppId) {
    delete payload.jd_text;
    delete payload.resume_id;
  }
  Object.keys(payload).forEach((key) => payload[key] === undefined && delete payload[key]);
  const editingId = state.editingAppId;
  const data = await api(state.editingAppId ? `/applications/${state.editingAppId}` : "/applications", {
    method: state.editingAppId ? "PUT" : "POST",
    body: payload,
  });
  if (data.success) {
    const savedId = editingId || Number(data.application_id);
    toast(editingId ? "投递记录已更新" : "投递记录已添加");
    state.editingAppId = null;
    clearApplicationHandoff();
    $("saveAppBtn").innerHTML = `<i data-lucide="plus"></i>添加记录`;
    ["appCompany", "appJob", "appCity", "appNotes"].forEach((id) => $(id).value = "");
    await Promise.all([loadApplications(), loadDashboard()]);
    if (Number.isInteger(savedId) && savedId > 0) await openOpportunityWorkspace(savedId);
    renderIcons();
  }
}

async function editApplication(id) {
  const data = await api(`/applications/detail/${id}`);
  if (!data.success) return toast(data.message || "投递记录不存在");
  const item = data.data;
  clearApplicationHandoff();
  state.editingAppId = id;
  $("appCompany").value = item.company || "";
  $("appJob").value = item.job_title || "";
  if (![...$("appStatus").options].some((option) => option.value === item.status)) {
    $("appStatus").add(new Option(`待确认：${item.status || "未设置"}`, item.status, true, true));
  }
  $("appStatus").value = item.status || "已投递";
  $("appCity").value = item.city || "";
  $("appNotes").value = item.notes || "";
  $("saveAppBtn").innerHTML = `<i data-lucide="save"></i>更新记录`;
  jumpToModule("tracker", "add");
  renderIcons();
}

async function deleteApplication(id) {
  if (!confirm("确定删除这条投递记录吗？")) return;
  const data = await api(`/applications/${id}`, { method: "DELETE" });
  if (!data.success) return toast(data.message || "删除失败");
  toast("投递记录已删除");
  if (state.currentOpportunityId === id) closeOpportunityWorkspace();
  await loadApplications();
  await loadDashboard();
}

async function loadApplications() {
  const data = await api(`/applications/${USER_ID}`);
  if (!data.success) {
    $("applicationList").innerHTML = `<div class="workspace-message" role="alert">投递记录加载失败，请稍后重试。</div>`;
    return;
  }
  const apps = data.success ? data.data : [];
  state.applications = apps;
  const canonicalStatuses = Array.isArray(data.canonical_statuses) ? data.canonical_statuses : [];
  state.applicationStatuses = canonicalStatuses;
  const previousStatus = $("appStatus").value;
  $("appStatus").innerHTML = canonicalStatuses.map((status) => (
    `<option value="${escapeHtml(status)}">${escapeHtml(status)}</option>`
  )).join("");
  $("appStatus").value = canonicalStatuses.includes(previousStatus)
    ? previousStatus
    : (canonicalStatuses.includes("已投递") ? "已投递" : canonicalStatuses[0] || "");
  if (!apps.length) {
    $("applicationList").innerHTML = `<div class="opportunity-empty"><strong>暂无投递</strong><span>添加第一条记录后，这里会按阶段自动成列。</span><button class="primary" onclick="jumpToModule('tracker','add')"><i data-lucide="plus"></i>新增投递</button></div>`;
    renderAgentCommandOpportunities();
    renderIcons();
    return;
  }
  const canonicalSet = new Set(canonicalStatuses);
  const unknownItems = apps.filter((item) => item.needs_status_review || !canonicalSet.has(item.status));
  const anchorIndexes = new Set([0, 2, 3]);
  const grouped = canonicalStatuses.map((stage, index) => ({
    stage,
    items: apps.filter((item) => item.status === stage),
    anchor: anchorIndexes.has(index) || stage === "Offer",
  })).filter((group) => group.items.length || group.anchor);
  if (unknownItems.length) grouped.unshift({ stage: "待确认", items: unknownItems, warning: true });
  $("applicationList").innerHTML = grouped.map((group) => `
    <section class="kanban-column${group.warning ? " needs-review" : ""}">
      <h4>${group.warning ? '<i data-lucide="triangle-alert" aria-hidden="true"></i>' : ""}${escapeHtml(group.stage)}<span>${group.items.length}</span></h4>
      ${group.warning ? '<p class="status-warning"><i data-lucide="triangle-alert" aria-hidden="true"></i>旧状态需要确认，请编辑后选择当前阶段。</p>' : ""}
      ${group.items.length ? group.items.map((item) => `
        <article class="kanban-card">
          <strong>${escapeHtml(item.company)}</strong>
          <span>${escapeHtml(item.job_title)}</span>
          <span class="status-text">阶段：${escapeHtml(item.needs_status_review ? `待确认（原状态：${item.status || "未设置"}）` : item.status)}</span>
          <em>${escapeHtml(item.city || "城市未填")}</em>
          <p>${escapeHtml(item.notes || "暂无备注，建议补充投递渠道、面试反馈或待办。")}</p>
          <button class="primary small details-command" onclick="openOpportunityWorkspace(${item.id})"><i data-lucide="panel-right-open"></i>打开详情</button>
          <div class="kanban-card-actions">
            <button class="ghost small" onclick="coachApplication(${item.id})">跟进建议</button>
            ${item.needs_status_review ? "" : `<button class="ghost small" onclick="advanceApplication(${item.id})">推进</button>`}
            <button class="ghost small" onclick="editApplication(${item.id})">编辑</button>
            <button class="ghost small danger" onclick="deleteApplication(${item.id})">删除</button>
          </div>
        </article>
      `).join("") : `<div class="kanban-empty"><span>暂无记录</span></div>`}
    </section>
  `).join("");
  renderAgentCommandOpportunities();
  renderIcons();
}

async function openOpportunityWorkspace(id, options = {}) {
  if (options.updateUrl !== false && document.activeElement instanceof HTMLElement) {
    state.opportunityOpener = document.activeElement;
  }
  const historyMode = options.historyMode || (options.updateUrl === false ? "none" : "push");
  return opportunityHistory.open(id, { historyMode });
}

async function loadOpportunityWorkspace(id, request = {}) {
  const opportunityId = Number(id);
  if (!Number.isInteger(opportunityId) || opportunityId <= 0) return false;
  const generation = ++state.opportunityLoadGeneration;
  const isCurrent = () => generation === state.opportunityLoadGeneration
    && state.currentOpportunityId === opportunityId
    && (!request.isCurrent || request.isCurrent());
  state.currentOpportunityId = opportunityId;
  const boardButton = document.querySelector('[data-section-filter="tracker:board"]');
  if (boardButton) filterModules("tracker", "board", boardButton);
  $("opportunityWorkspace").classList.remove("hidden");
  $("opportunityWorkspaceError").classList.add("hidden");
  $("opportunityWorkspaceTitle").textContent = "正在加载机会详情";
  $("opportunityWorkspaceSubtitle").textContent = "正在读取本地关联记录...";

  let workspace;
  try {
    workspace = await api(`/opportunities/${opportunityId}/workspace`);
  } catch (_error) {
    if (!isCurrent()) return { status: "superseded" };
    showOpportunityWorkspaceError(opportunityId, "网络连接失败，请检查连接后重试。");
    return { status: "retryable" };
  }
  if (!isCurrent()) return { status: "superseded" };
  if (!workspace.success) {
    if ([404, 410].includes(workspace.http_status)) return { status: "stale" };
    if (workspace.http_status === 403) return { status: "forbidden" };
    showOpportunityWorkspaceError(opportunityId, "机会详情暂时无法加载，请稍后重试。");
    return { status: "retryable" };
  }

  state.currentOpportunityWorkspace = workspace;
  renderOpportunityWorkspace(workspace);
  syncAgentContext();
  selectOpportunityTab($("opportunity-tab-overview"), false);
  $("opportunityWorkspace").scrollIntoView({ behavior: "smooth", block: "start" });
  return { status: "ok" };
}

function showOpportunityWorkspaceError(opportunityId, message) {
  $("opportunityWorkspaceTitle").textContent = "机会详情暂时不可用";
  $("opportunityWorkspaceSubtitle").textContent = "链接已保留，可直接重试。";
  const error = $("opportunityWorkspaceError");
  error.classList.remove("hidden");
  error.innerHTML = `${escapeHtml(message)}<button type="button" class="ghost" onclick="retryOpportunityWorkspace(${opportunityId})"><i data-lucide="refresh-cw"></i>重试</button>`;
  renderIcons();
}

function retryOpportunityWorkspace(opportunityId) {
  $("opportunityWorkspaceError").classList.add("hidden");
  return opportunityHistory.reload(opportunityId);
}

function resetOpportunityWorkspaceView(context = {}) {
  const wasOpen = state.currentOpportunityId !== null || !$("opportunityWorkspace").classList.contains("hidden");
  state.opportunityLoadGeneration += 1;
  state.currentOpportunityId = null;
  state.currentOpportunityWorkspace = null;
  syncAgentContext();
  $("opportunityWorkspace").classList.add("hidden");
  $("opportunityWorkspaceError").classList.add("hidden");
  if (!wasOpen) return;
  const opener = context.restoreFocus && state.opportunityOpener?.isConnected
    ? state.opportunityOpener
    : (context.page === "tracker" ? $("applicationBoardHeading") : $("pageTitle"));
  state.opportunityOpener = null;
  opener?.focus({ preventScroll: true });
}

function closeOpportunityWorkspace() {
  return opportunityHistory.close({ historyMode: "push", restoreFocus: true });
}

function selectOpportunityTab(selectedTab, moveFocus = true) {
  if (!selectedTab) return;
  document.querySelectorAll('.opportunity-tabs [role="tab"]').forEach((tab) => {
    const selected = tab === selectedTab;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    $(tab.getAttribute("aria-controls"))?.classList.toggle("hidden", !selected);
  });
  if (moveFocus) selectedTab.focus();
}

function handleOpportunityTabKeydown(event) {
  if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const tabs = [...document.querySelectorAll('.opportunity-tabs [role="tab"]')];
  const current = tabs.indexOf(event.currentTarget);
  let next = current;
  if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
  if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
  if (event.key === "Home") next = 0;
  if (event.key === "End") next = tabs.length - 1;
  selectOpportunityTab(tabs[next]);
}

function renderOpportunityWorkspace(workspace) {
  const opportunity = workspace.opportunity || {};
  $("opportunityWorkspaceError").classList.add("hidden");
  $("opportunityWorkspaceTitle").textContent = `${opportunity.company || "未命名公司"} / ${opportunity.job_title || "目标岗位"}`;
  $("opportunityWorkspaceSubtitle").textContent = `当前阶段：${opportunity.needs_status_review ? "待确认" : opportunity.status || "未设置"}`;
  renderOpportunityOverview(workspace);
  renderOpportunityMatch(workspace);
  renderOpportunityResume(workspace);
  renderOpportunityInterview(workspace);
  renderOpportunityTimeline(workspace);
  syncAgentContext();
  renderIcons();
}

function workspaceDate(value, fallback = "未设置") {
  return escapeHtml(value ? formatDate(value) : fallback);
}

function renderOpportunityOverview(workspace) {
  const opportunity = workspace.opportunity || {};
  const status = opportunity.needs_status_review
    ? `待确认（原状态：${opportunity.status || "未设置"}）`
    : opportunity.status || "未设置";
  $("opportunity-overview").innerHTML = `
    ${opportunity.needs_status_review ? '<p class="status-warning"><i data-lucide="triangle-alert"></i>这是旧版状态，请编辑并选择当前标准阶段。</p>' : ""}
    <dl class="opportunity-facts">
      <div><dt>公司</dt><dd>${escapeHtml(opportunity.company || "未填写")}</dd></div>
      <div><dt>岗位</dt><dd>${escapeHtml(opportunity.job_title || "未填写")}</dd></div>
      <div><dt>阶段</dt><dd>${escapeHtml(status)}</dd></div>
      <div><dt>城市</dt><dd>${escapeHtml(opportunity.city || "未填写")}</dd></div>
      <div><dt>优先级</dt><dd>${escapeHtml(opportunity.priority == null ? "未设置" : String(opportunity.priority))}</dd></div>
      <div><dt>下一步</dt><dd>${workspaceDate(opportunity.next_action_at)}</dd></div>
      <div><dt>面试时间</dt><dd>${workspaceDate(opportunity.interview_at)}</dd></div>
      <div><dt>投递时间</dt><dd>${workspaceDate(opportunity.applied_at || opportunity.created_at)}</dd></div>
    </dl>
    ${opportunity.notes ? `<div class="workspace-note"><b>备注</b><p>${escapeHtml(opportunity.notes)}</p></div>` : ""}
    <div class="workspace-primary-action"><button type="button" class="primary" onclick="editApplication(${opportunity.id})"><i data-lucide="pencil"></i>编辑机会</button></div>`;
}

function renderOpportunityMatch(workspace) {
  const matches = workspace.matches || [];
  const jd = workspace.opportunity?.jd_text || "";
  $("opportunity-match").innerHTML = `
    <section class="workspace-section"><h4>岗位 JD</h4>
      ${jd ? `<div class="workspace-long-text">${escapeHtml(workspace.opportunity.jd_text)}</div>` : '<div class="opportunity-empty"><b>尚未保存 JD</b><span>回到 JD 匹配区粘贴岗位描述，再生成匹配结果。</span></div>'}
    </section>
    <section class="workspace-section"><h4>最近匹配</h4>
      ${matches.length ? `<div class="workspace-list">${matches.map((match) => `
        <div class="workspace-row"><div><b>${escapeHtml(match.job_title || "目标岗位")}</b><span>${escapeHtml(match.resume_title || "关联简历")} · ${workspaceDate(match.created_at)}</span></div><strong>${escapeHtml(match.match_score == null ? "未评分" : `${match.match_score} 分`)}</strong>
        ${match.analysis ? `<p>${escapeHtml(match.analysis)}</p>` : ""}
        ${Object.keys(match.details || {}).length ? `<pre>${escapeHtml(JSON.stringify(match.details, null, 2))}</pre>` : ""}</div>`).join("")}</div>` : '<div class="opportunity-empty"><b>尚无匹配结果</b><span>使用这份 JD 和关联简历完成一次匹配。</span></div>'}
    </section>
    <div class="workspace-primary-action"><button type="button" class="primary" onclick="useWorkspaceJd()"><i data-lucide="scan-search"></i>${jd ? "用此 JD 重新匹配" : "前往 JD 匹配"}</button></div>`;
}

function useWorkspaceJd() {
  const opportunity = state.currentOpportunityWorkspace?.opportunity;
  if (!opportunity) return;
  state.matchOpportunityId = opportunity.id;
  renderMatchOpportunityNotice();
  $("jobTitleInput").value = opportunity.job_title || "";
  $("jdInput").value = opportunity.jd_text || "";
  if (opportunity.resume_id) $("tailorResumeSelect").value = String(opportunity.resume_id);
  jumpToModule("resume", "jd");
}

function renderOpportunityResume(workspace) {
  const resume = workspace.resume;
  $("opportunity-resume").innerHTML = resume ? `
    <div class="workspace-version">
      <i data-lucide="file-text"></i><div><b>${escapeHtml(resume.title || "未命名简历")}</b><span>${escapeHtml(resume.version_label || "已关联版本")} · ${workspaceDate(resume.updated_at || resume.created_at)}</span><small>${escapeHtml(resume.target_job_title || workspace.opportunity.job_title || "目标岗位")}</small></div>
    </div>
    <div class="workspace-primary-action"><button type="button" class="primary" onclick="openWorkspaceResume(${resume.id}, ${resume.has_original ? "true" : "false"})"><i data-lucide="external-link"></i>${resume.has_original ? "打开简历原件" : "查看简历版本"}</button></div>` : `
    <div class="opportunity-empty"><b>尚未关联简历版本</b><span>选择一份与该岗位匹配的简历，再从 JD 区新建机会。</span></div>
    <div class="workspace-primary-action"><button type="button" class="primary" onclick="jumpToModule('resume','input')"><i data-lucide="file-plus-2"></i>准备简历</button></div>`;
}

function openWorkspaceResume(resumeId, hasOriginal) {
  if (hasOriginal) return openOriginalResume(resumeId);
  jumpToModule("resume", "input");
  fillResume(resumeId);
}

function renderOpportunityInterview(workspace) {
  const interviews = workspace.interviews || [];
  const actions = workspace.actions || [];
  const interviewAction = actions.find((action) => ["interview", "interview_plan", "mock_interview"].includes(action.action_type) && ["pending", "in_progress"].includes(action.status));
  $("opportunity-interview").innerHTML = `
    <section class="workspace-section"><h4>面试记录</h4>
      ${interviews.length ? `<div class="workspace-list">${interviews.map((interview) => `
        <div class="workspace-row"><div><b>${escapeHtml(interview.job_title || "模拟面试")}</b><span>状态：${escapeHtml(interview.status || "未设置")} · 阶段：${escapeHtml(interview.current_stage || "未开始")}</span></div>${interview.score == null ? "" : `<strong>${escapeHtml(`${interview.score} 分`)}</strong>`}
          ${interview.feedback ? `<p>${escapeHtml(parseFeedbackSummary(interview.feedback) || interview.feedback)}</p>` : ""}
          ${interview.status === "active" ? `<button type="button" class="ghost" onclick="continueOpportunityInterview(${interview.id})"><i data-lucide="play"></i>继续面试</button>` : ""}</div>`).join("")}</div>` : '<div class="opportunity-empty"><b>尚无面试记录</b><span>从当前机会开始模拟面试，系统会保留机会和简历关联。</span></div>'}
    </section>
    <section class="workspace-section"><h4>准备行动</h4>
      ${actions.length ? `<div class="workspace-list">${actions.map((action) => `<div class="workspace-row"><div><b>${escapeHtml(action.title)}</b><span>${escapeHtml(action.status || "pending")} · ${workspaceDate(action.due_at, "无截止时间")}</span></div>${action.description ? `<p>${escapeHtml(action.description)}</p>` : ""}</div>`).join("")}</div>` : '<div class="opportunity-empty"><b>暂无准备行动</b><span>先开始一轮模拟面试，再根据反馈补充行动。</span></div>'}
    </section>
    <div class="workspace-primary-action"><button type="button" class="primary" onclick="prepareInterviewFromOpportunity(${interviewAction?.id || "null"})"><i data-lucide="messages-square"></i>开始新面试</button></div>`;
}

function prepareInterviewFromOpportunity(actionId = null) {
  const workspace = state.currentOpportunityWorkspace;
  if (!workspace?.opportunity) return;
  state.interviewOpportunityHandoff = buildInterviewHandoff({
    opportunityId: workspace.opportunity.id,
    resumeId: workspace.resume?.id,
    actionId,
    jobTitle: workspace.opportunity.job_title,
    jd: workspace.opportunity.jd_text,
  });
  if (!state.interviewOpportunityHandoff) return toast("请先为该机会关联简历");
  $("interviewJobTitle").value = workspace.opportunity.job_title || "";
  $("interviewJd").value = workspace.opportunity.jd_text || "";
  if (workspace.resume?.id) $("interviewResumeSelect").value = String(workspace.resume.id);
  jumpToModule("interview", "mock");
  toast("已关联机会和简历，可开始模拟面试");
}

async function continueOpportunityInterview(sessionId) {
  const data = await api(`/interview/sessions/${sessionId}`);
  if (!data.success) return toast(data.message || "面试记录无法继续");
  state.activeInterview = String(sessionId);
  state.pendingInterviewSubmission = null;
  state.interviewSubmitting = false;
  jumpToModule("interview", "mock");
  openInterviewRoom(data);
}

function renderOpportunityTimeline(workspace) {
  const events = workspace.timeline || [];
  $("opportunity-timeline").innerHTML = events.length ? `<ol class="workspace-timeline">${events.map((event) => `
    <li><i data-lucide="circle-dot"></i><div><b>${escapeHtml(event.event_type || "记录更新")}</b><span>${workspaceDate(event.occurred_at)} · ${escapeHtml(event.source || "system")}</span></div></li>`).join("")}</ol>` : `
    <div class="opportunity-empty"><b>暂无时间线事件</b><span>编辑阶段、添加行动或开始面试后，事件会显示在这里。</span></div>
    <div class="workspace-primary-action"><button type="button" class="primary" onclick="openOpportunityWorkspace(${workspace.opportunity.id}, { updateUrl: false })"><i data-lucide="refresh-cw"></i>刷新时间线</button></div>`;
}

async function advanceApplication(id) {
  const data = await api(`/applications/${id}/advance`, { method: "POST", body: { user_id: USER_ID } });
  if (!data.success) return toast(data.message || "推进失败");
  toast(`已推进到：${data.status}`);
  await loadApplications();
  await loadDashboard();
}

async function coachApplication(id) {
  const data = await withLoading(
    () => api(`/applications/${id}/coach`, { method: "POST", body: { user_id: USER_ID } }),
    "AI 正在整理投递跟进策略..."
  );
  jumpToModule("tracker", "board");
  const result = $("applicationCoachResult");
  result.classList.remove("hidden");
  result.innerHTML = `
    <h4>${escapeHtml(data.title || "投递跟进建议")}</h4>
    <div><b>下一步：</b>${escapeHtml(data.next_action || "")}</div>
    <div><b>风险点：</b>${escapeHtml(data.risk || "")}</div>
    <div><b>可发送话术：</b><br>${escapeHtml(data.message_template || "")}</div>
    ${data.ai_note ? `<div><b>AI 补充：</b><br>${renderText(data.ai_note)}</div>` : ""}
  `;
  result.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function evaluateSalary() {
  const data = await api("/salary/evaluate", {
    method: "POST",
    body: {
      job_type: $("salaryJob").value,
      experience: $("salaryExp").value,
      city: $("salaryCity").value,
      skills_count: Number($("salarySkills").value || 0),
    },
  });
  $("salaryResult").classList.remove("hidden");
  $("salaryResult").innerHTML = `<h4>${data.range.min} - ${data.range.max} / 月</h4><div>参考中位：${data.range.avg} / 月</div><div>${escapeHtml(data.advice)}</div>`;
}

async function loadDashboard() {
  const data = await api(`/dashboard/${USER_ID}`);
  if (!data.success) return;
  $("statResumes").textContent = data.stats.resumes;
  $("statInterviews").textContent = data.stats.interviews;
  $("statMatches").textContent = data.stats.matches;
  $("statApps").textContent = data.stats.applications;
  renderNextActions(data.next_actions || []);
  renderCareerPulse(data.career_pulse || {});
}

function renderCareerPulse(pulse) {
  if (!$("careerPulse")) return;
  $("readinessScore").textContent = pulse.score ?? 0;
  $("readinessLabel").textContent = pulse.label || "待启动";
  $("readinessSummary").textContent = pulse.summary || "系统会根据简历、JD 匹配、面试训练和投递进度，给出下一步最该做的动作。";
  $("pulseBlockers").innerHTML = (pulse.blockers || []).map((item) => `<span>${escapeHtml(item)}</span>`).join("");
  $("weeklyPlan").innerHTML = (pulse.weekly_plan || []).map((item, index) => `
    <button class="plan-step" onclick="jumpToModule('${item.page}', '${item.module}')">
      <b>${index + 1}</b>
      <span>${escapeHtml(item.title)}</span>
      <i data-lucide="arrow-right"></i>
    </button>
  `).join("");
  renderIcons();
}

function renderNextActions(actions) {
  const box = $("nextActions");
  if (!box) return;
  box.innerHTML = actions.length ? actions.map((action) => `
    <article class="next-action-card">
      <div>
        <b>${escapeHtml(action.title)}</b>
        <small>${escapeHtml(action.description)}</small>
      </div>
      <button class="ghost small" onclick="jumpToModule('${action.page}', '${action.module}')">${escapeHtml(action.cta || "去处理")}</button>
    </article>
  `).join("") : "";
}

function currentAgentResumeId() {
  if (state.currentOpportunityWorkspace?.resume?.id) return state.currentOpportunityWorkspace.resume.id;
  if (state.currentPage === "resume" && state.editingResumeId) return state.editingResumeId;
  const selectors = {
    "resume:analysis": "analysisResumeSelect",
    "resume:export": "exportResumeSelect",
    "resume:jd": "tailorResumeSelect",
    "resume:skills": "skillResumeSelect",
    "interview:mock": "interviewResumeSelect",
  };
  const id = selectors[`${state.currentPage}:${state.currentModule}`];
  return id ? Number($(id)?.value || 0) || null : null;
}

function syncAgentContext() {
  if (!window.ContextualAgent) return;
  agentContext.sync({
    module: state.currentModule ? `${state.currentPage}:${state.currentModule}` : state.currentPage,
    opportunityId: state.currentOpportunityId,
    resumeId: currentAgentResumeId(),
  });
  renderAgentContextChips();
}

function renderAgentContextChips() {
  const box = $("agentContextChips");
  if (!box) return;
  const context = agentContext.payload();
  const moduleLabels = {
    home: "项目总览", resume: "简历实验室", interview: "面试训练场",
    tracker: "投递看板", agent: "行动指挥台",
  };
  const values = [];
  if (context.module) {
    const [page, module] = context.module.split(":");
    const moduleButton = module && document.querySelector(`[data-section-filter="${page}:${module}"]`);
    values.push(["module", `模块：${moduleButton?.textContent?.trim() || moduleLabels[page] || page}`]);
  }
  if (context.opportunity_id) {
    const opportunity = state.currentOpportunityWorkspace?.opportunity
      || state.applications.find((item) => Number(item.id) === context.opportunity_id);
    values.push(["opportunity", `机会：${opportunity ? `${opportunity.company} / ${opportunity.job_title}` : `#${context.opportunity_id}`}`]);
  }
  if (context.resume_id) {
    const resume = state.resumes.find((item) => Number(item.id) === context.resume_id);
    values.push(["resume", `简历：${resume?.title || `#${context.resume_id}`}`]);
  }
  box.innerHTML = values.length ? values.map(([kind, label]) => `
    <span class="agent-context-chip">${escapeHtml(label)}<button type="button" data-remove-agent-context="${kind}" aria-label="移除${escapeAttr(label)}上下文" title="移除上下文"><i data-lucide="x"></i></button></span>
  `).join("") : '<span class="agent-context-empty">未附加上下文</span>';
  renderIcons();
}

function openAgentDrawer(event) {
  const drawer = $("agentDrawer");
  if (!drawer || drawer.getAttribute("aria-hidden") === "false") return;
  state.agentDrawerOpener = event?.currentTarget || document.activeElement;
  syncAgentContext();
  drawer.setAttribute("aria-hidden", "false");
  $("agentLauncher").setAttribute("aria-expanded", "true");
  $("agentDrawerBackdrop").classList.remove("hidden");
  document.body.classList.add("agent-drawer-open");
  requestAnimationFrame(() => {
    $("closeAgentDrawer")?.focus({ preventScroll: true });
  });
  loadAgentCommandCenter();
}

function closeAgentDrawer() {
  const drawer = $("agentDrawer");
  if (!drawer || drawer.getAttribute("aria-hidden") === "true") return;
  drawer.setAttribute("aria-hidden", "true");
  $("agentLauncher").setAttribute("aria-expanded", "false");
  $("agentDrawerBackdrop").classList.add("hidden");
  document.body.classList.remove("agent-drawer-open");
  const opener = state.agentDrawerOpener?.isConnected ? state.agentDrawerOpener : $("agentLauncher");
  state.agentDrawerOpener = null;
  opener?.focus({ preventScroll: true });
}

function handleAgentDrawerKeydown(event) {
  const drawer = $("agentDrawer");
  if (!drawer || drawer.getAttribute("aria-hidden") !== "false") return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeAgentDrawer();
    return;
  }
  if (event.key !== "Tab") return;
  const focusable = [...drawer.querySelectorAll('button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href]')]
    .filter((node) => node.offsetParent !== null);
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
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
      ...agentContext.payload(),
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
