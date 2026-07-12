const API = window.location.protocol === "file:" ? "http://localhost:5000/api" : "/api";
const USER_ID = 1;
const JOBHUNTER_AGENT_CONVERSATION = `jobhunter_agent_conversation_${USER_ID}`;

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
  mediaRecorder: null,
  audioChunks: [],
  audioBlob: null,
  audioMetrics: null,
  audioStartedAt: 0,
  recordingTarget: "answer",
  recorderFormat: null,
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
  await loadProviders();
  await Promise.all([loadResumes(), loadDashboard(), loadApplications(), loadQuestions(), loadTrainingRecords()]);
  await loadAgentConversations();
  await applyInitialRouteFromQuery();
  await loadAgentCommandCenter();
  await focusAgentResultFromQuery();
  syncAgentContext();
  lucide.createIcons();
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
    agent: "AI 教练",
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
  $("closeAgentDrawer")?.addEventListener("click", closeAgentDrawer);
  $("agentDrawerBackdrop")?.addEventListener("click", closeAgentDrawer);
  $("agentContextChips")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-agent-context]");
    if (!button) return;
    agentContext.remove(button.dataset.removeAgentContext);
    renderAgentContextChips();
  });
  $("chatLog")?.addEventListener("click", handleProposalClick);
  $("sendAgentBtn").addEventListener("click", sendAgentMessage);
  $("careerReportBtn").addEventListener("click", generateCareerReport);
  $("newAgentConversation")?.addEventListener("click", createAgentConversation);
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

async function api(path, options = {}) {
  const init = { method: "GET", ...options };
  if (init.body && !(init.body instanceof FormData)) {
    init.headers = { "Content-Type": "application/json", ...(init.headers || {}) };
    init.body = JSON.stringify(init.body);
  }
  const response = await fetch(`${API}${path}`, init);
  const type = response.headers.get("content-type") || "";
  if (type.includes("application/json")) {
    const payload = await response.json();
    if (response.ok || !payload || typeof payload !== "object") return payload;
    return { ...payload, http_status: response.status };
  }
  const payload = { success: response.ok, content: await response.text() };
  return response.ok ? payload : { ...payload, http_status: response.status };
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
  if (window.lucide) lucide.createIcons();
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
    .replace(/^## (.*)$/gm, "<h4>$1</h4>")
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
    toast(key ? `已切换到 ${data.provider} / ${data.model}` : "已切换模型；未填 Key 时使用本地兜底");
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
  const data = await api(`/resumes/${USER_ID}`);
  state.resumes = data.success ? data.data : [];
  $("resumeCount").textContent = state.resumes.length;
  $("resumeList").innerHTML = state.resumes.length
    ? state.resumes.map((resume) => `
      <article class="list-item" data-resume-id="${resume.id}" tabindex="-1">
        <b>${escapeHtml(resume.title)}</b>
        <small>${new Date(resume.updated_at || resume.created_at).toLocaleString()}${resume.file_type ? ` · 原件 ${escapeHtml(resume.file_type.toUpperCase())}` : ""}</small>
        <div class="list-actions">
          <button class="ghost small" onclick="fillResume(${resume.id})">编辑</button>
          <button class="ghost small" onclick="openOriginalResume(${resume.id})">打开原件</button>
          <label class="ghost small file-action">替换原件<input type="file" accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg" onchange="replaceOriginalResume(${resume.id}, this)"></label>
          <button class="ghost small" onclick="analyzeResume(${resume.id})">诊断</button>
          <button class="ghost small" onclick="deleteResume(${resume.id})">删除</button>
        </div>
      </article>
    `).join("")
    : `<div class="list-item"><b>暂无简历</b><small>先保存一份简历</small></div>`;
  updateResumeSelects();
  syncAgentContext();
  lucide.createIcons();
}

function updateResumeSelects() {
  const options = `<option value="">选择简历</option>` + state.resumes.map((resume) => `<option value="${resume.id}">${escapeHtml(resume.title)}</option>`).join("");
  ["tailorResumeSelect", "interviewResumeSelect", "exportResumeSelect", "analysisResumeSelect", "skillResumeSelect"].forEach((id) => $(id).innerHTML = options);
}

async function fillResume(id) {
  const data = await api(`/resumes/detail/${id}`);
  if (!data.success) return;
  $("resumeTitle").value = data.data.title;
  $("resumeContent").value = data.data.content;
  state.editingResumeId = id;
  $("saveResumeBtn").innerHTML = `<i data-lucide="save"></i>更新当前简历`;
  setResumeEditNotice(data.data.title);
  lucide.createIcons();
  jumpToModule("resume", "input");
  $("resumeTitle").focus();
  $("resumeContent").scrollTop = 0;
  toast(`正在编辑：${data.data.title}`);
}

function setResumeEditNotice(title = "") {
  const notice = $("editingResumeNotice");
  if (!notice) return;
  notice.classList.toggle("hidden", !state.editingResumeId);
  const text = $("editingResumeText");
  if (text) text.textContent = title ? `当前版本：${title}。修改后点击“更新当前简历”保存。` : "修改后点击“更新当前简历”保存。";
}

function cancelResumeEdit() {
  state.editingResumeId = null;
  $("resumeTitle").value = "";
  $("resumeContent").value = "";
  $("resumeFile").value = "";
  $("saveResumeBtn").innerHTML = `<i data-lucide="save"></i>保存简历`;
  setResumeEditNotice();
  lucide.createIcons();
  toast("已退出简历编辑模式");
}

function openOriginalResume(id) {
  window.open(`${API}/resumes/${id}/original`, "_blank");
}

async function replaceOriginalResume(id, input) {
  const file = input.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const data = await withLoading(
    () => api(`/resumes/${id}/replace-file`, { method: "POST", body: form }),
    "正在替换并解析原始简历..."
  );
  input.value = "";
  if (!data.success) return toast(data.message || "替换失败");
  toast("原文件已替换，文本内容已重新解析");
  await loadResumes();
  if (state.editingResumeId === id) {
    const detail = await api(`/resumes/detail/${id}`);
    $("resumeContent").value = detail.data.content || "";
  }
}

async function saveResume() {
  const file = $("resumeFile").files[0];
  const title = $("resumeTitle").value.trim();
  const content = $("resumeContent").value.trim();
  if (!title) return toast("请填写简历标题");
  let data;
  if (file) {
    const form = new FormData();
    form.append("file", file);
    form.append("user_id", USER_ID);
    form.append("title", title);
    data = await api("/resumes/upload", { method: "POST", body: form });
  } else if (state.editingResumeId) {
    if (!content) return toast("请粘贴简历内容或上传文件");
    data = await api(`/resumes/${state.editingResumeId}`, { method: "PUT", body: { title, content } });
  } else {
    if (!content) return toast("请粘贴简历内容或上传文件");
    data = await api("/resumes", { method: "POST", body: { user_id: USER_ID, title, content } });
  }
  if (data.success) {
    toast(state.editingResumeId ? "简历已更新" : "简历已保存");
    $("resumeFile").value = "";
    state.editingResumeId = null;
    $("saveResumeBtn").innerHTML = `<i data-lucide="save"></i>保存简历`;
    setResumeEditNotice();
    await loadResumes();
    await loadDashboard();
    lucide.createIcons();
  } else {
    toast(data.message || "保存失败");
  }
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
  return BrowserCapabilities.extensionForMime(mime);
}

function audioDownloadBase(filename = "interview-answer") {
  return filename.replace(/\.[^.]+$/, "") || "interview-answer";
}

async function blobToWav(blob) {
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) throw new Error("当前浏览器不支持音频解码");
  const ctx = new AudioContext();
  const buffer = await ctx.decodeAudioData(await blob.arrayBuffer());
  const channels = Math.min(2, buffer.numberOfChannels);
  const sampleRate = buffer.sampleRate;
  const samples = buffer.length;
  const bytesPerSample = 2;
  const blockAlign = channels * bytesPerSample;
  const dataSize = samples * blockAlign;
  const wav = new ArrayBuffer(44 + dataSize);
  const view = new DataView(wav);
  const writeString = (offset, text) => {
    for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i));
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, dataSize, true);
  const channelData = Array.from({ length: channels }, (_, index) => buffer.getChannelData(index));
  let offset = 44;
  for (let i = 0; i < samples; i += 1) {
    for (let channel = 0; channel < channels; channel += 1) {
      const sample = Math.max(-1, Math.min(1, channelData[channel][i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }
  }
  ctx.close?.();
  return new Blob([wav], { type: "audio/wav" });
}

async function downloadSavedAudio(filename, format = "wav") {
  if (!filename) return toast("没有可下载的音频文件");
  if (format === "wav") {
    try {
      const response = await fetch(`${API}/uploads/${encodeURIComponent(filename)}`);
      if (!response.ok) throw new Error("音频读取失败");
      const wavBlob = await blobToWav(await response.blob());
      downloadBlob(wavBlob, `${audioDownloadBase(filename)}.wav`);
      toast("WAV 音频已开始下载");
      return;
    } catch (error) {
      toast(`WAV 导出失败：${error.message}`);
      return;
    }
  }
  const response = await fetch(`${API}/uploads/${encodeURIComponent(filename)}/download/${format}`);
  await downloadResponse(response, `${audioDownloadBase(filename)}.${format === "original" ? audioExtensionFromMime("") : format}`);
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
  const resumeId = $("exportResumeSelect").value || selectedResumeId();
  if (!resumeId) return toast("请先选择要导出的简历");
  const response = await fetch(`${API}/resumes/${resumeId}/export/${format}`);
  await downloadResponse(response, format === "pdf" ? "resume.pdf" : "resume.docx");
}

async function convertDocument(route, inputId) {
  const input = $(inputId);
  const file = input.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API}/convert/${route}`, { method: "POST", body: form });
  await downloadResponse(response, route === "pdf-to-word" ? "converted.docx" : "converted.pdf");
  input.value = "";
}

async function generateResume() {
  const data = await api("/resume-generator", {
    method: "POST",
    body: {
      name: "唐乐",
      job_target: "软件测试工程师",
      skills: "Python, Flask, Selenium, Pytest, JMeter, Postman, MySQL",
    },
  });
  $("resumeTitle").value = "唐乐-软件测试工程师-项目版";
  $("resumeContent").value = data.resume_content;
  toast("已生成一份可继续修改的示例简历");
}

function renderResumeAuditResult(data) {
  $("resumeAuditResult").classList.remove("hidden");
  $("resumeAuditResult").innerHTML = `
    <h4>综合评分：${data.score}</h4>
    <div class="score-grid">
      ${Object.entries(data.section_scores || {}).map(([key, value]) => `<div><span>${escapeHtml(key)}</span><b>${value}</b></div>`).join("")}
    </div>
    <div><b>一句话定位</b><br>${escapeHtml(data.positioning)}</div>
    <div><b>优势证据</b><br>${(data.strengths || []).map((item) => `• ${escapeHtml(item)}`).join("<br>")}</div>
    <div><b>客观锐评</b><br>${(data.brutal_comments || []).map((item) => `• ${escapeHtml(item)}`).join("<br>")}</div>
    <div><b>HR 初筛风险</b><br>${(data.risks || []).map((item) => `• ${escapeHtml(item)}`).join("<br>")}</div>
    <div><b>证据缺口</b><br>${(data.evidence_gaps || []).map((item) => `• ${escapeHtml(item)}`).join("<br>")}</div>
    <div><b>优先修改项</b><br>${(data.actions || []).map((item) => `• ${escapeHtml(item)}`).join("<br>")}</div>
    <div><b>项目经历建议</b><br>${(data.project_suggestions || []).map((item) => `• ${escapeHtml(item)}`).join("<br>")}</div>
    <div class="result-actions">
      <button class="primary" onclick="improveSelectedResume()">生成优化版并保存</button>
      <button class="ghost" onclick="jumpToModule('resume','jd')">去做 JD 优化</button>
      <button class="ghost" onclick="jumpToModule('resume','skills')">看技能图谱</button>
      <button class="ghost" onclick="jumpToModule('interview','mock')">去模拟面试</button>
    </div>
  `;
}

async function analyzeResume(id) {
  const data = await withLoading(
    () => api(`/resumes/${id}/audit`, { method: "POST", body: { job_title: $("analysisJobTitle").value || $("jobTitleInput").value, jd: $("analysisJdInput").value || $("jdInput").value } }),
    "AI 正在诊断简历表达..."
  );
  $("analysisResumeSelect").value = String(id);
  jumpToModule("resume", "analysis");
  renderResumeAuditResult(data);
}

function selectedAnalysisResumeId() {
  return $("analysisResumeSelect").value || selectedResumeId();
}

async function auditSelectedResume() {
  const resumeId = selectedAnalysisResumeId();
  if (!resumeId) return toast("请先选择要分析的简历");
  const data = await withLoading(
    () => api(`/resumes/${resumeId}/audit`, {
      method: "POST",
      body: { job_title: $("analysisJobTitle").value, jd: $("analysisJdInput").value, career_profile: selectedCareerProfile() },
    }),
    "AI 正在做简历结构诊断..."
  );
  if (!data.success) return toast(data.message || "诊断失败");
  renderResumeAuditResult(data);
}

async function improveSelectedResume() {
  const resumeId = selectedAnalysisResumeId();
  if (!resumeId) return toast("请先选择要修改的简历");
  const data = await withLoading(
    () => api(`/resumes/${resumeId}/improve`, {
      method: "POST",
      body: {
        job_title: $("analysisJobTitle").value || $("jobTitleInput").value,
        jd: $("analysisJdInput").value || $("jdInput").value,
        career_profile: selectedCareerProfile(),
        save: true,
      },
    }),
    "AI 正在生成可投递优化版..."
  );
  if (!data.success) return toast(data.message || "优化失败");
  $("resumeAuditResult").classList.remove("hidden");
  $("resumeAuditResult").innerHTML = `
    <h4>已生成优化版：${escapeHtml(data.new_title || "新简历版本")}</h4>
    <div><b>改写策略</b><br>${(data.strategy || []).map((item) => `• ${escapeHtml(item)}`).join("<br>")}</div>
    <h4>优化内容预览</h4>${renderText(data.improved_resume || "")}
    <div class="result-actions">
      <button class="primary" onclick="jumpToModule('resume','manage')">查看我的简历</button>
      <button class="ghost" onclick="jumpToModule('resume','export')">导出新版本</button>
      <button class="ghost" onclick="prepareInterviewFromJd()">带入模拟面试</button>
    </div>
  `;
  await loadResumes();
  await loadDashboard();
}

async function deleteResume(id) {
  await api(`/resumes/${id}`, { method: "DELETE" });
  toast("简历已删除");
  loadResumes();
  loadDashboard();
}

function selectedResumeId() {
  return state.resumes[0]?.id;
}

function selectedTailorResumeId() {
  return $("tailorResumeSelect").value || state.resumes[0]?.id;
}

function selectedSkillResumeId() {
  return $("skillResumeSelect").value || state.resumes[0]?.id;
}

async function tailorResume() {
  const resumeId = selectedTailorResumeId();
  if (!resumeId) return toast("请先选择简历");
  const data = await withLoading(
    () => api(`/resumes/${resumeId}/tailor`, {
      method: "POST",
      body: { job_title: $("jobTitleInput").value, jd: $("jdInput").value, career_profile: selectedCareerProfile() },
    }),
    "AI 正在按 JD 优化简历..."
  );
  $("tailorResult").classList.remove("hidden");
  const focus = data.jd_focus || {};
  $("tailorResult").innerHTML = `
    <h4>匹配分：${data.match_score}</h4>
    <div class="score-grid">
      ${Object.entries(data.score_detail || {}).map(([key, value]) => `<div><span>${escapeHtml(key)}</span><b>${value}</b></div>`).join("")}
    </div>
    <div><b>候选人定位</b><br>${escapeHtml(data.positioning)}</div>
    <div><b>客观锐评</b><br>${(data.brutal_comments || []).map((item) => `• ${escapeHtml(item)}`).join("<br>")}</div>
    <div><b>JD 聚焦</b><br>
      硬技能：${escapeHtml((focus["硬技能"] || []).join("、") || "未明显出现")}<br>
      测试能力：${escapeHtml((focus["测试能力"] || []).join("、") || "未明显出现")}<br>
      AI 能力：${escapeHtml((focus["AI 能力"] || []).join("、") || "未明显出现")}
    </div>
    <div><b>已命中</b><br>${escapeHtml((data.matched_keywords || []).join("、") || "暂无")}</div>
    <div><b>待补齐</b><br>${escapeHtml((data.keyword_gaps || []).join("、") || "暂无")}</div>
    <div><b>面试讲述要点</b><br>${(data.interview_talking_points || []).map((item) => `• ${escapeHtml(item)}`).join("<br>")}</div>
    <h4>优化版本</h4>${renderText(data.ai_rewrite || data.tailored_resume)}
    <div class="result-actions">
      <button class="primary" onclick="prepareInterviewFromJd()">带入模拟面试</button>
      <button class="ghost" onclick="prepareApplicationFromJd()">新增投递记录</button>
      <button class="ghost" onclick="jumpToModule('resume','export')">去导出简历</button>
    </div>
  `;
}

async function matchResume() {
  const resumeId = selectedTailorResumeId();
  if (!resumeId) return toast("请先选择简历");
  const linkedOpportunityId = state.matchOpportunityId;
  const matchBody = buildMatchPayload({
    resume_id: Number(resumeId),
    job_title: $("jobTitleInput").value,
    jd: $("jdInput").value,
    job_requirements: $("jdInput").value,
    career_profile: selectedCareerProfile(),
  }, linkedOpportunityId);
  const data = await withLoading(
    () => api("/job-match", {
      method: "POST",
      body: matchBody,
    }),
    "AI 正在计算岗位匹配度..."
  );
  if (!data.success) return toast(data.message || "岗位匹配失败");
  clearMatchOpportunityLink();
  $("tailorResult").classList.remove("hidden");
  $("tailorResult").innerHTML = `<h4>岗位匹配：${data.match_score}</h4>${renderText(data.analysis)}<br><b>待补齐：</b>${escapeHtml((data.missing_keywords || []).join("、"))}
    <div class="result-actions">
      <button class="primary" onclick="prepareInterviewFromJd()">带入模拟面试</button>
      <button class="ghost" onclick="prepareApplicationFromJd()">新增投递记录</button>
    </div>`;
  await loadDashboard();
}

async function analyzeJdOnly() {
  const jd = $("jdInput").value.trim();
  if (!jd) return toast("请先粘贴岗位 JD");
  const data = await withLoading(
    () => api("/ai/analyze-jd", { method: "POST", body: { jd_content: jd, job_title: $("jobTitleInput").value, career_profile: selectedCareerProfile() } }),
    "AI 正在拆解 JD..."
  );
  $("tailorResult").classList.remove("hidden");
  const focus = data.focus || {};
  $("tailorResult").innerHTML = `
    <h4>JD 岗位画像</h4>
    <div><b>求职方向</b><br>${escapeHtml(data.profile?.label || careerProfileLabel())}</div>
    <div><b>核心关键词</b><br>${escapeHtml((data.keywords || []).join("、") || "暂无")}</div>
    <div><b>能力聚焦</b><br>
      ${Object.entries(focus).map(([key, value]) => `${escapeHtml(key)}：${escapeHtml((value || []).join("、") || "未明显出现")}`).join("<br>")}
    </div>
    <div><b>风险提示</b><br>${(data.risk_flags || []).map((item) => `• ${escapeHtml(item)}`).join("<br>") || "暂无明显风险词"}</div>
    ${renderText(data.content || "")}
    <div class="result-actions">
      <button class="primary" onclick="tailorResume()">用这份 JD 优化简历</button>
      <button class="ghost" onclick="prepareInterviewFromJd()">带入模拟面试</button>
    </div>
  `;
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
  const resumeId = selectedSkillResumeId();
  if (!resumeId) return toast("请先选择简历");
  const data = await api("/skills/radar", { method: "POST", body: { resume_id: Number(resumeId), career_profile: selectedCareerProfile(), job_title: $("analysisJobTitle").value || $("jobTitleInput").value } });
  const ctx = $("skillChart");
  if (state.skillChart) state.skillChart.destroy();
  state.skillChart = new Chart(ctx, {
    type: "radar",
    data: {
      labels: data.radar_data.map((item) => item.category),
      datasets: [{
        label: "能力值",
        data: data.radar_data.map((item) => item.score),
        backgroundColor: "rgba(255,122,182,0.18)",
        borderColor: "#ff7ab6",
        pointBackgroundColor: "#66dbc2",
      }],
    },
    options: { scales: { r: { min: 0, max: 10 } }, plugins: { legend: { display: false } } },
  });
  $("skillResult").classList.remove("hidden");
  $("skillResult").innerHTML = `
    <h4>技能图谱解读</h4>
    ${(data.radar_data || []).map((item) => `
      <div><b>${escapeHtml(item.category)}：${item.score}/10</b><br>
      已命中：${escapeHtml((item.matched || []).join("、") || "暂无")}<br>
      建议：${escapeHtml(item.suggestion || "补充真实项目证据，把技能写进项目过程和结果。")}</div>
    `).join("")}
    <div class="result-actions">
      <button class="primary" onclick="jumpToModule('resume','analysis')">去修改简历</button>
      <button class="ghost" onclick="jumpToModule('interview','professional')">按短板练专业面试</button>
    </div>
  `;
}

async function startInterview() {
  const handoff = state.interviewOpportunityHandoff;
  const resumeId = handoff?.resumeId || $("interviewResumeSelect").value || state.resumes[0]?.id;
  if (!resumeId) return toast("请先保存或选择简历");
  const baseBody = {
    user_id: USER_ID,
    resume_id: Number(resumeId),
    job_title: $("interviewJobTitle").value || "软件测试工程师",
    jd: $("interviewJd").value,
    career_profile: selectedCareerProfile(),
    mode: "campus",
  };
  const body = buildInterviewStartPayload(baseBody, handoff);
  const data = await api("/interview/sessions", {
    method: "POST",
    body,
  });
  if (!data.success) return toast(data.message || "面试创建失败");
  state.activeInterview = data.session_id;
  state.pendingInterviewSubmission = null;
  state.interviewSubmitting = false;
  state.interviewOpportunityHandoff = null;
  updateInterviewQuestion(data);
  $("interviewFeedback").classList.add("hidden");
  openInterviewRoom(data);
}

function updateInterviewQuestion(data) {
  state.interviewStageIndex = Math.max(0, Number(data.progress || 1) - 1);
  state.currentInterviewSession = data;
  $("currentQuestion").textContent = data.question;
  $("interviewStageLabel").textContent = stageName(data.stage);
  const progress = Math.min(100, (data.progress / data.total) * 100);
  $("interviewProgress").style.width = `${progress}%`;
  $("interviewProgress").parentElement.classList.toggle("has-progress", progress > 0);
  $("roomQuestion").textContent = data.question;
  $("roomStageLabel").textContent = stageName(data.stage);
  $("roomProgress").style.width = `${progress}%`;
}

function openInterviewRoom(data) {
  updateInterviewQuestion(data);
  $("roomAnswer").value = "";
  $("roomFeedback").classList.add("hidden");
  $("interviewRoom").classList.remove("hidden");
  lucide.createIcons();
}

function stageName(stage) {
  return {
    opening: "自我介绍",
    resume_deep_dive: "项目深挖",
    technical: "技术追问",
    professional: "专业追问",
    behavioral: "行为面",
    candidate_questions: "反问环节",
    finished: "面试结束",
  }[stage] || stage;
}

async function sendInterviewAnswer() {
  if (!state.activeInterview) return toast("请先开始模拟面试");
  if (state.interviewSubmitting) return;
  const answer = $("answerInput").value.trim();
  if (!answer) return toast("请先输入回答");
  const result = await InterviewSubmission.submitInterviewAnswer(state, answer, {
    createId: () => (
      globalThis.crypto && typeof globalThis.crypto.randomUUID === "function"
        ? globalThis.crypto.randomUUID()
        : `interview-${Date.now()}-${Math.random().toString(36).slice(2)}`
    ),
    send: (pending) => api(`/interview/sessions/${state.activeInterview}/answer`, {
      method: "POST",
      body: {
        answer: pending.answer,
        submission_id: pending.submissionId,
        expected_stage_index: pending.expectedStageIndex,
      },
    }),
    reload: () => api(`/interview/sessions/${state.activeInterview}`),
  });
  if (result.kind === "success") {
    const data = result.session;
    updateInterviewQuestion(data);
    $("answerInput").value = "";
    renderFeedback(data.feedback);
    if (data.stage === "finished") {
      loadDashboard();
      loadTrainingRecords();
    }
    return;
  }
  if (result.kind === "conflict_recovered") {
    updateInterviewQuestion(result.session);
    $("answerInput").value = "";
    toast("面试进度已同步，请回答当前问题");
    return;
  }
  if (result.kind !== "busy") toast("提交结果不确定，请重试");
}

async function sendRoomAnswer() {
  const roomAnswer = $("roomAnswer").value.trim();
  if (!roomAnswer) return toast("请先输入本轮回答");
  $("answerInput").value = roomAnswer;
  await sendInterviewAnswer();
  $("roomAnswer").value = "";
  $("roomFeedback").classList.remove("hidden");
  $("roomFeedback").innerHTML = $("interviewFeedback").innerHTML;
}

function renderFeedback(feedback) {
  $("interviewFeedback").classList.remove("hidden");
  $("interviewFeedback").innerHTML = renderFeedbackHtml(feedback);
}

function renderFeedbackHtml(feedback) {
  const dimensions = feedback.voice.dimension_scores || {};
  return `
    <h4>即时反馈：${feedback.score} 分</h4>
    <div>${escapeHtml(feedback.summary)}</div>
    <div>语速：${feedback.voice.estimated_speech_rate} 字/分钟（${feedback.voice.pace_label || "自然"}），口头禅：${feedback.voice.filler_count} 次，结构分：${feedback.voice.structure_score}</div>
    <div><b>维度分</b><br>${Object.entries(dimensions).map(([key, value]) => `${key}：${value}`).join("　")}</div>
    ${feedback.voice.audio_quality ? `<div><b>真实录音质量</b><br>${escapeHtml(feedback.voice.audio_quality)}</div>` : ""}
    ${feedback.answer_upgrade ? `<div><b>表达升级</b><br>${escapeHtml(feedback.answer_upgrade)}</div>` : ""}
    ${(feedback.suggestions || []).map((item) => `<div>• ${escapeHtml(item)}</div>`).join("")}
  `;
}

async function analyzeVoice() {
  const answer = $("answerInput").value.trim();
  if (!answer) return toast("请先输入或语音录入回答");
  const data = await api("/interview/analyze-voice", { method: "POST", body: { answer } });
  renderFeedback({ score: data.overall_score, summary: "表达分析完成", voice: data, suggestions: data.tips });
}

async function startAudioRecording(target = "answer") {
  const plan = BrowserCapabilities.audioInputPlan(window, navigator);
  if (!plan.canRecord) return toast("当前浏览器不能直接录音，请上传音频或使用文字回答");
  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    return toast("正在录音中，先停止当前录音");
  }
  let stream = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks = [];
    state.recordingTarget = target;
    state.audioStartedAt = Date.now();
    state.recorderFormat = plan.recorderFormat;
    const options = plan.recorderFormat ? { mimeType: plan.recorderFormat.mimeType } : undefined;
    state.mediaRecorder = options ? new MediaRecorder(stream, options) : new MediaRecorder(stream);
    state.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) state.audioChunks.push(event.data);
    };
    state.mediaRecorder.onerror = () => {
      stream.getTracks().forEach((track) => track.stop());
      toast("录音发生错误，请上传音频或使用文字回答");
    };
    state.mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      const mimeType = state.mediaRecorder.mimeType || state.recorderFormat?.mimeType || "audio/webm";
      state.audioBlob = new Blob(state.audioChunks, { type: mimeType });
      state.audioMetrics = await computeAudioMetrics(state.audioBlob);
      renderAudioPreview(target);
      toast("录音已生成，可以回放或分析");
    };
    state.mediaRecorder.start();
    toast(target === "room" ? "模拟面试录音开始" : "真实录音开始");
  } catch (error) {
    stream?.getTracks().forEach((track) => track.stop());
    state.mediaRecorder = null;
    toast(error?.name === "NotAllowedError"
      ? "未获得麦克风权限，请上传音频或使用文字回答"
      : "无法开始录音，请上传音频或使用文字回答");
  }
}

function stopAudioRecording() {
  if (!state.mediaRecorder || state.mediaRecorder.state !== "recording") return toast("当前没有正在录制的音频");
  state.mediaRecorder.stop();
}

async function handleAudioUpload() {
  const file = $("audioFileInput").files[0];
  if (!file) return;
  state.audioBlob = file;
  state.recordingTarget = "answer";
  state.audioMetrics = await computeAudioMetrics(file);
  renderAudioPreview("answer");
  toast("已载入上传音频，可以回放或分析");
}

async function computeAudioMetrics(blob) {
  const fallback = {
    duration_seconds: Math.max(1, Math.round((Date.now() - state.audioStartedAt) / 1000)),
    peak: 0,
    average_volume: 0,
    silence_ratio: 0,
    pause_count: 0,
    clipping_ratio: 0,
  };
  try {
    const arrayBuffer = await blob.arrayBuffer();
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return fallback;
    const ctx = new AudioContext();
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
    const data = audioBuffer.getChannelData(0);
    const step = Math.max(1, Math.floor(data.length / 24000));
    let sum = 0;
    let peak = 0;
    let silent = 0;
    let clipped = 0;
    let pauseCount = 0;
    let inPause = false;
    for (let i = 0; i < data.length; i += step) {
      const value = Math.abs(data[i]);
      sum += value * value;
      peak = Math.max(peak, value);
      if (value < 0.018) {
        silent += 1;
        if (!inPause) {
          pauseCount += 1;
          inPause = true;
        }
      } else {
        inPause = false;
      }
      if (value > 0.96) clipped += 1;
    }
    const samples = Math.ceil(data.length / step);
    await ctx.close?.();
    return {
      duration_seconds: Math.round(audioBuffer.duration),
      peak: Number(peak.toFixed(3)),
      average_volume: Number(Math.sqrt(sum / Math.max(1, samples)).toFixed(3)),
      silence_ratio: Number((silent / Math.max(1, samples)).toFixed(2)),
      pause_count: pauseCount,
      clipping_ratio: Number((clipped / Math.max(1, samples)).toFixed(3)),
    };
  } catch (error) {
    return fallback;
  }
}

function renderAudioPreview(target = "answer") {
  const playback = target === "room" ? $("roomAudioPlayback") : $("audioPlayback");
  const preview = target === "room" ? $("roomAudioMetricPreview") : $("audioMetricPreview");
  if (state.audioBlob) {
    if (playback.dataset.url) URL.revokeObjectURL(playback.dataset.url);
    const url = URL.createObjectURL(state.audioBlob);
    playback.src = url;
    playback.dataset.url = url;
  }
  const metrics = state.audioMetrics || {};
  preview.classList.remove("hidden");
  preview.innerHTML = `
    <span>时长 ${metrics.duration_seconds || 0}s</span>
    <span>音量 ${metrics.average_volume || 0}</span>
    <span>停顿 ${(metrics.silence_ratio || 0) * 100}%</span>
    <span>爆音 ${(metrics.clipping_ratio || 0) * 100}%</span>
  `;
}

async function analyzeRecordedAudio(target = "answer") {
  if (!state.audioBlob) return toast("请先录音或上传音频");
  const transcript = target === "room" ? $("roomAnswer").value.trim() : $("answerInput").value.trim();
  if (!transcript) return toast("请补充转写文本，AI 需要结合内容和声音一起分析");
  const form = new FormData();
  form.append("audio", state.audioBlob, `interview-answer.${audioExtensionFromMime(state.audioBlob.type)}`);
  form.append("user_id", USER_ID);
  form.append("transcript", transcript);
  form.append("duration_seconds", String(state.audioMetrics?.duration_seconds || 0));
  form.append("metrics", JSON.stringify(state.audioMetrics || {}));
  const data = await withLoading(
    () => api("/interview/analyze-audio", { method: "POST", body: form }),
    "AI 正在分析真实录音..."
  );
  if (!data.success) return toast(data.message || "录音分析失败");
  const feedback = { score: data.overall_score, summary: data.summary, voice: data, suggestions: data.tips };
  if (target === "room") {
    $("roomFeedback").classList.remove("hidden");
    $("roomFeedback").innerHTML = renderFeedbackHtml(feedback);
  } else {
    renderFeedback(feedback);
  }
  await loadTrainingRecords();
}

async function loadQuestions(category = "all") {
  const resolvedCategory = category === "career" ? selectedCareerProfile() : category;
  state.currentPracticeCategory = category;
  const data = await api(`/questions?category=${encodeURIComponent(resolvedCategory)}`);
  const questions = data.success ? data.data : [];
  $("questionList").innerHTML = questions.length
    ? questions.map((item, index) => `
      <article class="question-card">
        <b>${index + 1}. ${escapeHtml(item.question)}</b>
        <small>${categoryName(item.category)} · 点击“练习”后可输入自己的回答</small>
        <div class="list-actions">
          <button class="ghost small" onclick="selectQuestion('${escapeAttr(item.question)}', '${escapeAttr(category === "career" ? "career" : item.category)}')">练习</button>
          <button class="ghost small" onclick="showSampleAnswer('${escapeAttr(item.answer)}')">参考答案</button>
        </div>
      </article>
    `).join("")
    : `<article class="question-card"><b>暂无题目</b><small>换一个分类试试</small></article>`;
}

function escapeAttr(text = "") {
  return String(text).replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/\n/g, " ");
}

function categoryName(category) {
  return {
    general: "通用面试",
    career: "跟随求职方向",
    test: "软件测试",
    python: "Python / Flask",
    frontend: "前端基础",
    ai: "AI Agent",
    tech: "计算机 / 软件 / AI",
    ops: "运营 / 新媒体",
    marketing: "市场 / 销售",
    finance: "财务 / 会计",
    education: "教育 / 师范",
    hr: "行政 / 人事",
  }[category] || category;
}

function selectQuestion(question, category) {
  $("practiceQuestion").value = question;
  state.currentPracticeCategory = category;
  $("practiceAnswer").focus();
  toast("题目已放入练习区");
}

function showSampleAnswer(answer) {
  $("practiceResult").classList.remove("hidden");
  $("practiceResult").innerHTML = `<h4>参考答案</h4>${renderText(answer)}`;
}

async function loadTrainingRecords() {
  const box = $("trainingRecords");
  if (!box) return;
  const data = await api(`/training-records/${USER_ID}`);
  if (!data.success) return;
  const interviews = data.interviews || [];
  const practices = data.practices || [];
  const audios = data.audios || [];
  box.innerHTML = `
    ${renderRecordColumn("模拟面试", "interview", interviews, (item) => `
      <b>${escapeHtml(item.job_title || "模拟面试")}</b>
      <small>${formatDate(item.created_at)} · ${item.score ?? 0} 分</small>
      <p>${escapeHtml(parseFeedbackSummary(item.feedback) || "已完成一轮模拟面试。")}</p>
    `)}
    ${renderRecordColumn("答题练习", "practice", practices, (item) => `
      <b>${escapeHtml(categoryName(item.category))} · ${item.score ?? 0} 分</b>
      <small>${formatDate(item.created_at)}</small>
      <p>${escapeHtml(item.question || "")}</p>
    `)}
    ${renderRecordColumn("语音录音", "audio", audios, (item) => `
      <b>语音表达分析 · ${item.score ?? 0} 分</b>
      <small>${formatDate(item.created_at)}${item.audio_file ? " · 已保存音频" : ""}</small>
      <p>${escapeHtml((item.transcript || "").slice(0, 90))}</p>
    `)}
  `;
  lucide.createIcons();
}

function renderRecordColumn(title, type, items, bodyRenderer) {
  return `
    <section class="record-column">
      <h4>${escapeHtml(title)}<span>${items.length}</span></h4>
      ${items.length ? items.map((item) => `
        <article class="record-card">
          ${bodyRenderer(item)}
          <div class="record-actions">
            <button class="ghost small" onclick="viewTrainingRecord('${type}', ${item.id})">查看详情</button>
            <button class="ghost small danger" onclick="deleteTrainingRecord('${type}', ${item.id})">删除</button>
          </div>
        </article>
      `).join("") : `<article class="record-card"><b>暂无记录</b><small>完成训练后会自动出现在这里</small></article>`}
    </section>
  `;
}

async function viewTrainingRecord(type, id) {
  const data = await api(`/training-records/${USER_ID}`);
  if (!data.success) return toast("记录读取失败");
  const source = type === "interview" ? data.interviews : type === "practice" ? data.practices : data.audios;
  const item = (source || []).find((record) => Number(record.id) === Number(id));
  if (!item) return toast("记录不存在或已删除");
  const detail = $("recordDetail");
  detail.classList.remove("hidden");
  detail.innerHTML = renderRecordDetail(type, item);
  detail.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderRecordDetail(type, item) {
  const feedback = safeJson(item.feedback);
  const metrics = safeJson(item.metrics);
  if (type === "audio") {
    return `
      <h4>语音复盘详情：${item.score ?? 0} 分</h4>
      <div><b>时间</b><br>${formatDate(item.created_at)}</div>
      <div><b>转写文本</b><br>${escapeHtml(item.transcript || "暂无转写文本")}</div>
      <div><b>声音指标</b><br>时长 ${metrics.duration_seconds || 0}s，平均音量 ${metrics.average_volume || 0}，停顿占比 ${Math.round((metrics.silence_ratio || 0) * 100)}%，爆音占比 ${Math.round((metrics.clipping_ratio || 0) * 100)}%</div>
      ${item.audio_file ? `
        <audio controls src="${API}/uploads/${encodeURIComponent(item.audio_file)}"></audio>
        <div class="audio-downloads">
          <button class="ghost small" onclick="downloadSavedAudio('${escapeAttr(item.audio_file)}', 'wav')">下载 WAV</button>
          <button class="ghost small" onclick="downloadSavedAudio('${escapeAttr(item.audio_file)}', 'mp3')">下载 MP3</button>
          <button class="ghost small" onclick="downloadSavedAudio('${escapeAttr(item.audio_file)}', 'original')">下载原始音频</button>
        </div>
        <small>WAV 可由浏览器本地转换；MP3 由后端 ffmpeg 转码生成。</small>
      ` : ""}
      <div><b>AI 建议</b><br>${escapeHtml(feedback.summary || "")}</div>
      ${(feedback.tips || []).map((tip) => `<div>• ${escapeHtml(tip)}</div>`).join("")}
    `;
  }
  if (type === "practice") {
    return `
      <h4>答题记录详情：${item.score ?? 0} 分</h4>
      <div><b>时间</b><br>${formatDate(item.created_at)}</div>
      <div><b>题目</b><br>${escapeHtml(item.question || "")}</div>
      <div><b>我的回答</b><br>${escapeHtml(item.answer || "")}</div>
      <div><b>维度评分</b><br>${Object.entries(feedback.dimension_scores || {}).map(([key, value]) => `${escapeHtml(key)}：${escapeHtml(String(value))}`).join("　") || "暂无"}</div>
      ${(feedback.problems || []).map((problem) => `<div>• ${escapeHtml(problem)}</div>`).join("")}
      ${feedback.sample_answer ? `<h4>参考答案</h4>${renderText(feedback.sample_answer)}` : ""}
      ${feedback.upgrade ? `<h4>表达升级</h4><div>${escapeHtml(feedback.upgrade)}</div>` : ""}
    `;
  }
  return `
    <h4>模拟面试详情：${item.score ?? 0} 分</h4>
    <div><b>岗位</b><br>${escapeHtml(item.job_title || "模拟面试")}</div>
    <div><b>时间</b><br>${formatDate(item.created_at)}</div>
    <div><b>总体反馈</b><br>${escapeHtml(feedback.summary || parseFeedbackSummary(item.feedback) || "暂无总结")}</div>
    ${(feedback.suggestions || []).map((suggestion) => `<div>• ${escapeHtml(suggestion)}</div>`).join("")}
    <h4>面试对话</h4>
    ${renderConversation(item.conversation)}
  `;
}

function safeJson(value) {
  try {
    return JSON.parse(value || "{}");
  } catch {
    return {};
  }
}

function renderConversation(value) {
  const data = safeJson(value);
  const turns = Array.isArray(data) ? data : data.turns || data.conversation || [];
  if (!turns.length) return `<div>暂无完整对话记录。</div>`;
  return turns.map((turn) => {
    const role = turn.role || turn.speaker || "记录";
    const text = turn.content || turn.text || turn.question || turn.answer || "";
    return `<div class="conversation-line"><b>${escapeHtml(role)}</b><span>${escapeHtml(text)}</span></div>`;
  }).join("");
}

function parseFeedbackSummary(feedback) {
  try {
    const data = JSON.parse(feedback || "{}");
    return data.summary || "";
  } catch {
    return "";
  }
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "";
}

async function deleteTrainingRecord(type, id) {
  if (!confirm("确定删除这条训练记录吗？")) return;
  const data = await api(`/training-records/${type}/${id}`, { method: "DELETE" });
  if (!data.success) return toast(data.message || "删除失败");
  toast("训练记录已删除");
  await loadTrainingRecords();
  await loadDashboard();
}

async function clearTrainingRecords() {
  if (!confirm("确定清空所有面试、答题和语音记录吗？")) return;
  const data = await api(`/training-records/${USER_ID}/clear`, { method: "DELETE" });
  if (!data.success) return toast(data.message || "清空失败");
  toast("训练记录已清空");
  await loadTrainingRecords();
  await loadDashboard();
}

async function loadProfessionalPack() {
  const data = await withLoading(
    () => api("/interview/professional-pack", {
      method: "POST",
      body: {
        category: $("professionalCategory").value,
        career_profile: selectedCareerProfile(),
        level: $("professionalLevel").value,
        job_title: $("professionalJobTitle").value || $("interviewJobTitle").value || "目标岗位",
      },
    }),
    "AI 正在生成专业面试题组..."
  );
  if (!data.success) return toast(data.message || "题组生成失败");
  $("professionalPack").innerHTML = data.questions.map((item, index) => `
    <article class="question-card">
      <b>${index + 1}. ${escapeHtml(item.question)}</b>
      <small>${escapeHtml(item.focus)} · ${escapeHtml(item.difficulty)}</small>
      <div class="list-actions">
        <button class="ghost small" onclick="selectProfessionalQuestion('${escapeAttr(item.question)}')">作答</button>
        <button class="ghost small" onclick="showProfessionalReference('${escapeAttr(item.reference)}')">参考思路</button>
      </div>
    </article>
  `).join("");
}

function selectProfessionalQuestion(question) {
  $("professionalQuestion").value = question;
  $("professionalAnswer").focus();
  toast("专业问题已放入作答区");
}

function showProfessionalReference(reference) {
  $("professionalResult").classList.remove("hidden");
  $("professionalResult").innerHTML = `<h4>参考思路</h4>${renderText(reference)}`;
}

async function scoreProfessionalAnswer() {
  const question = $("professionalQuestion").value.trim();
  const answer = $("professionalAnswer").value.trim();
  if (!question || !answer) return toast("请先选择专业问题并填写回答");
  const data = await api("/interview/practice-feedback", {
    method: "POST",
    body: {
      question,
      answer,
      user_id: USER_ID,
      category: $("professionalCategory").value,
      career_profile: selectedCareerProfile(),
      job_title: $("professionalJobTitle").value || $("interviewJobTitle").value || "目标岗位",
    },
  });
  if (!data.success) return toast(data.message || "评分失败");
  $("professionalResult").classList.remove("hidden");
  $("professionalResult").innerHTML = `
    <h4>专业回答评分：${data.score} 分</h4>
    <div><b>维度分</b><br>${Object.entries(data.dimension_scores).map(([key, value]) => `${key}：${value}`).join("　")}</div>
    <div><b>命中关键词</b><br>${escapeHtml((data.hits || []).join("、") || "暂无")}</div>
    ${(data.problems || []).map((item) => `<div>• ${escapeHtml(item)}</div>`).join("")}
    <h4>参考答案</h4>${renderText(data.sample_answer)}
    <h4>追问建议</h4>${escapeHtml(data.follow_up || "把回答继续落到你的项目经历、测试工具和实际结果上。")}
  `;
  await loadTrainingRecords();
}

async function scorePractice() {
  const question = $("practiceQuestion").value.trim();
  const answer = $("practiceAnswer").value.trim();
  if (!question || !answer) return toast("请先填写题目和你的回答");
  const data = await api("/interview/practice-feedback", {
    method: "POST",
    body: { question, answer, category: state.currentPracticeCategory, career_profile: selectedCareerProfile(), job_title: $("interviewJobTitle").value || "目标岗位", user_id: USER_ID },
  });
  if (!data.success) return toast(data.message || "评分失败");
  $("practiceResult").classList.remove("hidden");
  $("practiceResult").innerHTML = `
    <h4>练习评分：${data.score} 分</h4>
    <div><b>维度分</b><br>${Object.entries(data.dimension_scores).map(([key, value]) => `${key}：${value}`).join("　")}</div>
    <div><b>命中关键词</b><br>${escapeHtml((data.hits || []).join("、") || "暂无")}</div>
    ${(data.problems || []).map((item) => `<div>• ${escapeHtml(item)}</div>`).join("")}
    <h4>参考答案</h4>${renderText(data.sample_answer)}
    <h4>表达升级</h4>${escapeHtml(data.upgrade)}
  `;
  await loadTrainingRecords();
}

function applyBrowserCapabilities() {
  const speech = BrowserCapabilities.speechRecognition(window);
  const audio = BrowserCapabilities.audioInputPlan(window, navigator);
  BrowserCapabilities.applyCapabilityUI(document, { speech, audio });
}

function resetSpeechRecognitionState() {
  state.recognizing = false;
  $("voiceBtn").classList.remove("recording");
}

function setupSpeechRecognition() {
  const speech = BrowserCapabilities.speechRecognition(window);
  if (!speech.Recognition) return;
  state.recognition = new speech.Recognition();
  state.recognition.lang = "zh-CN";
  state.recognition.continuous = true;
  state.recognition.interimResults = true;
  state.recognition.onresult = (event) => {
    let text = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      text += event.results[i][0].transcript;
    }
    $("answerInput").value = `${$("answerInput").value.replace(/\s*$/, "")}${text}`;
  };
  state.recognition.onend = () => {
    resetSpeechRecognitionState();
  };
  state.recognition.onerror = (event) => {
    resetSpeechRecognitionState();
    const denied = event?.error === "not-allowed" || event?.error === "service-not-allowed";
    toast(denied
      ? "未获得语音识别权限，请直接使用文字回答"
      : "语音识别暂时不可用，请直接使用文字回答");
  };
}

function toggleVoiceInput() {
  if (!state.recognition) return toast("当前浏览器不支持语音识别，可以使用 Chrome 尝试");
  if (state.recognizing) {
    try {
      state.recognition.stop();
    } catch (error) {
      resetSpeechRecognitionState();
    }
    return;
  }
  state.recognizing = true;
  $("voiceBtn").classList.add("recording");
  const result = BrowserCapabilities.startSpeechSafely(state.recognition);
  if (!result.ok) {
    resetSpeechRecognitionState();
    return toast("无法启动语音识别，请直接使用文字回答");
  }
  toast("正在语音录入");
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
    lucide.createIcons();
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
  lucide.createIcons();
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
    lucide.createIcons();
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
  lucide.createIcons();
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
  lucide.createIcons();
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
  lucide.createIcons();
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
  lucide.createIcons();
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
  if (window.lucide) lucide.createIcons();
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
  if (window.lucide) lucide.createIcons();
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
  if (window.lucide) lucide.createIcons();
}

function openAgentProposal(proposalId, opener = null) {
  openAgentDrawer({ currentTarget: opener || $("agentLauncher") });
  const existing = $("chatLog").querySelector(`[data-proposal-id="${Number(proposalId)}"]`);
  if (existing) return existing.scrollIntoView({ block: "center", behavior: "smooth" });
  const proposal = state.agentProposals.get(Number(proposalId));
  if (!proposal) return;
  appendMessage("这项操作需要你的确认。", "bot", { proposals: [proposal] });
}

async function sendAgentMessage() {
  const input = $("agentInput");
  const message = input.value.trim();
  if (!message) return;
  if (!state.agentConversationId) await createAgentConversation();
  const conversationId = state.agentConversationId;
  if (!conversationId) return;
  agentConversationEpoch.invalidate();
  appendMessage(message, "user");
  input.value = "";
  const chatRequest = {
    ...ContextualAgent.chatPayload(message, conversationId, agentContext.payload()),
    conversation_id: conversationId,
  };
  const data = await withLoading(
    () => api("/agent/chat", {
      method: "POST",
      body: chatRequest,
    }),
    "AI 教练正在读取上下文并处理任务..."
  );
  if (state.agentConversationId !== conversationId || (data.success && data.conversation_id !== conversationId)) return;
  if (!data.success) return toast(data.message || "AI 教练暂时不可用");
  localStorage.setItem(JOBHUNTER_AGENT_CONVERSATION, conversationId);
  const reply = data.reply || data.message || "我暂时没想好，换个问法试试。";
  appendMessage(reply, "bot", { proposals: data.action_proposals || [] });
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
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
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
  if (!confirm("确定清空当前 AI 教练会话吗？其他会话和求职数据不会受影响。")) return;
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
    appendMessage(message.content, message.role === "user" ? "user" : "bot", { proposals });
    if (message.role === "assistant") {
      renderAgentEvents(message.metadata?.events || [], message.metadata?.status || "completed");
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
  if (window.lucide) lucide.createIcons();
  return merged;
}

async function handleProposalClick(event) {
  const button = event.target.closest("[data-agent-action]");
  if (!button) return;
  const card = button.closest("[data-proposal-id]");
  const proposalId = Number(card?.dataset.proposalId);
  const actionName = button.dataset.agentAction;
  const proposal = state.agentProposals.get(proposalId);
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
    "你好，我是你的 AI 求职教练。把目标岗位、简历问题或面试难点发给我，我会结合已保存数据继续推进。",
    "bot"
  );
}

function renderAgentEvents(events, status = "completed") {
  if (!events.length && status === "completed") return;
  const labels = {
    list_resumes: "读取简历列表",
    get_resume: "读取简历正文",
    analyze_resume: "分析简历",
    match_job: "匹配目标岗位",
    analyze_jd: "解析岗位 JD",
    get_interview_question: "获取面试题",
    evaluate_answer: "评估面试回答",
    list_applications: "读取投递记录",
    get_dashboard: "读取求职看板",
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
  const statusText = status === "degraded" ? "本地模式" : status === "needs_input" ? "等待补充" : "任务记录";
  const node = $("chatLog").lastElementChild;
  node?.insertAdjacentHTML("beforeend", `<div class="agent-events"><small>${statusText}</small>${rows}</div>`);
  lucide.createIcons();
}

function renderAgentSuggestedActions(actions) {
  if (!actions.length) return;
  const node = $("chatLog").lastElementChild;
  const buttons = actions.map((action) => `
    <button type="button" onclick="closeAgentDrawer(); jumpToModule('${escapeAttr(action.page)}','${escapeAttr(action.module)}')">
      ${escapeHtml(action.label)}<i data-lucide="arrow-right"></i>
    </button>
  `).join("");
  node?.insertAdjacentHTML("beforeend", `<div class="agent-suggested-actions">${buttons}</div>`);
  lucide.createIcons();
}
