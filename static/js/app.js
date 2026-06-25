const API = window.location.protocol === "file:" ? "http://localhost:5000/api" : "/api";
const USER_ID = 1;

const state = {
  resumes: [],
  providers: [],
  careerProfiles: [],
  careerProfile: localStorage.getItem("jobhunter_career_profile") || "tech",
  activeInterview: null,
  skillChart: null,
  recognition: null,
  recognizing: false,
  currentPracticeCategory: "general",
  theme: localStorage.getItem("jobhunter_theme") || "glass",
  editingResumeId: null,
  editingAppId: null,
  mediaRecorder: null,
  audioChunks: [],
  audioBlob: null,
  audioMetrics: null,
  audioStartedAt: 0,
  recordingTarget: "answer",
  soundEnabled: localStorage.getItem("jobhunter_sound") !== "off",
  audioContext: null,
};

const $ = (id) => document.getElementById(id);
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
  bindNavigation();
  bindActions();
  applyTheme(state.theme);
  setupSpeechRecognition();
  await loadCareerProfiles();
  await loadProviders();
  await Promise.all([loadResumes(), loadDashboard(), loadApplications(), loadQuestions(), loadTrainingRecords()]);
  applyInitialRouteFromQuery();
  lucide.createIcons();
});

function bindNavigation() {
  document.querySelectorAll("[data-page]").forEach((item) => {
    item.addEventListener("click", () => {
      playUiTone("jump");
      showPage(item.dataset.page);
    });
  });
}

function showPage(page) {
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
  activateCurrentPageDefaultModule(page);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function applyInitialRouteFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const page = params.get("page");
  const moduleName = params.get("module");
  const record = params.get("record");
  if (page) showPage(page);
  if (page && moduleName) {
    document.querySelector(`[data-section-filter="${page}:${moduleName}"]`)?.click();
  }
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
      filterModules(page, module, button);
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
  $("salaryBtn").addEventListener("click", evaluateSalary);
  $("sendAgentBtn").addEventListener("click", sendAgentMessage);
  $("careerReportBtn").addEventListener("click", generateCareerReport);
  $("agentInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") sendAgentMessage();
  });
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
  if (type.includes("application/json")) return response.json();
  return { success: response.ok, content: await response.text() };
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

function jumpToModule(page, module) {
  showPage(page);
  const button = document.querySelector(`[data-section-filter="${page}:${module}"]`);
  if (button) filterModules(page, module, button);
}

function activateCurrentPageDefaultModule(page) {
  const activeButton = document.querySelector(`[data-filter-page="${page}"] [data-section-filter].active`)
    || document.querySelector(`[data-filter-page="${page}"] [data-section-filter]`);
  if (!activeButton) return;
  const [, module] = activeButton.dataset.sectionFilter.split(":");
  filterModules(page, module, activeButton);
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
    brandLogo: `assets/images/logo${suffix}.png`,
    heroImage: `assets/images/hero-bg${suffix}.png`,
    dashboardImage: `assets/images/dashboard${suffix}.png`,
    resumeImage: `assets/images/resume-analysis${suffix}.png`,
    jobMatchImage: `assets/images/job-match${suffix}.png`,
    interviewImage: `assets/images/interview-scene${suffix}.png`,
    interviewAvatar: `assets/images/ai-avatar${suffix}.png`,
    trackImage: `assets/images/application-track${suffix}.png`,
    coachAvatar: `assets/images/ai-avatar${suffix}.png`,
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
  if (loadingVideo) loadingVideo.src = `assets/images/loading${theme === "anime" ? "%20(2)" : ""}.mp4`;
}

async function loadResumes() {
  const data = await api(`/resumes/${USER_ID}`);
  state.resumes = data.success ? data.data : [];
  $("resumeCount").textContent = state.resumes.length;
  $("resumeList").innerHTML = state.resumes.length
    ? state.resumes.map((resume) => `
      <article class="list-item">
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
  if (mime.includes("mp4") || mime.includes("m4a")) return "m4a";
  if (mime.includes("ogg")) return "ogg";
  if (mime.includes("mpeg") || mime.includes("mp3")) return "mp3";
  if (mime.includes("wav")) return "wav";
  return "webm";
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
  const data = await withLoading(
    () => api("/job-match", {
      method: "POST",
      body: { resume_id: resumeId, job_title: $("jobTitleInput").value, jd: $("jdInput").value, job_requirements: $("jdInput").value, career_profile: selectedCareerProfile() },
    }),
    "AI 正在计算岗位匹配度..."
  );
  $("tailorResult").classList.remove("hidden");
  $("tailorResult").innerHTML = `<h4>岗位匹配：${data.match_score}</h4>${renderText(data.analysis)}<br><b>待补齐：</b>${escapeHtml((data.missing_keywords || []).join("、"))}
    <div class="result-actions">
      <button class="primary" onclick="prepareInterviewFromJd()">带入模拟面试</button>
      <button class="ghost" onclick="prepareApplicationFromJd()">新增投递记录</button>
    </div>`;
  loadDashboard();
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
  $("interviewJobTitle").value = $("jobTitleInput").value || $("interviewJobTitle").value;
  $("interviewJd").value = $("jdInput").value || $("interviewJd").value;
  $("interviewResumeSelect").value = selectedTailorResumeId() || selectedResumeId() || "";
  jumpToModule("interview", "mock");
  toast("已把岗位信息带入模拟面试");
}

function prepareApplicationFromJd() {
  $("appJob").value = $("jobTitleInput").value || $("appJob").value;
  $("appNotes").value = $("jdInput").value ? `JD 摘要：${$("jdInput").value.slice(0, 180)}` : $("appNotes").value;
  jumpToModule("tracker", "add");
  toast("已带入岗位信息，补公司名后即可保存投递");
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
  const resumeId = $("interviewResumeSelect").value || state.resumes[0]?.id;
  if (!resumeId) return toast("请先保存或选择简历");
  const data = await api("/interview/sessions", {
    method: "POST",
    body: {
      user_id: USER_ID,
      resume_id: Number(resumeId),
      job_title: $("interviewJobTitle").value || "软件测试工程师",
      jd: $("interviewJd").value,
      career_profile: selectedCareerProfile(),
      mode: "campus",
    },
  });
  if (!data.success) return toast(data.message || "面试创建失败");
  state.activeInterview = data.session_id;
  updateInterviewQuestion(data);
  $("interviewFeedback").classList.add("hidden");
  openInterviewRoom(data);
}

function updateInterviewQuestion(data) {
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
  const answer = $("answerInput").value.trim();
  if (!answer) return toast("请先输入回答");
  const data = await api(`/interview/sessions/${state.activeInterview}/answer`, { method: "POST", body: { answer } });
  if (!data.success) return toast(data.message || "提交失败");
  updateInterviewQuestion(data);
  $("answerInput").value = "";
  renderFeedback(data.feedback);
  if (data.stage === "finished") {
    loadDashboard();
    loadTrainingRecords();
  }
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
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    return toast("当前浏览器不支持真实录音，建议使用最新版 Chrome 或 Edge");
  }
  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    return toast("正在录音中，先停止当前录音");
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  state.audioChunks = [];
  state.recordingTarget = target;
  state.audioStartedAt = Date.now();
  state.mediaRecorder = new MediaRecorder(stream);
  state.mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) state.audioChunks.push(event.data);
  };
  state.mediaRecorder.onstop = async () => {
    stream.getTracks().forEach((track) => track.stop());
    state.audioBlob = new Blob(state.audioChunks, { type: state.mediaRecorder.mimeType || "audio/webm" });
    state.audioMetrics = await computeAudioMetrics(state.audioBlob);
    renderAudioPreview(target);
    toast("录音已生成，可以回放或分析");
  };
  state.mediaRecorder.start();
  toast(target === "room" ? "模拟面试录音开始" : "真实录音开始");
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

function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;
  state.recognition = new SpeechRecognition();
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
    state.recognizing = false;
    $("voiceBtn").classList.remove("recording");
  };
}

function toggleVoiceInput() {
  if (!state.recognition) return toast("当前浏览器不支持语音识别，可以使用 Chrome 尝试");
  if (state.recognizing) {
    state.recognition.stop();
    return;
  }
  state.recognizing = true;
  $("voiceBtn").classList.add("recording");
  state.recognition.start();
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
  };
  const data = await api(state.editingAppId ? `/applications/${state.editingAppId}` : "/applications", {
    method: state.editingAppId ? "PUT" : "POST",
    body: payload,
  });
  if (data.success) {
    toast(state.editingAppId ? "投递记录已更新" : "投递记录已添加");
    state.editingAppId = null;
    $("saveAppBtn").innerHTML = `<i data-lucide="plus"></i>添加记录`;
    ["appCompany", "appJob", "appCity", "appNotes"].forEach((id) => $(id).value = "");
    loadApplications();
    loadDashboard();
    lucide.createIcons();
  }
}

async function editApplication(id) {
  const data = await api(`/applications/detail/${id}`);
  if (!data.success) return toast(data.message || "投递记录不存在");
  const item = data.data;
  state.editingAppId = id;
  $("appCompany").value = item.company || "";
  $("appJob").value = item.job_title || "";
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
  await loadApplications();
  await loadDashboard();
}

async function loadApplications() {
  const data = await api(`/applications/${USER_ID}`);
  const apps = data.success ? data.data : [];
  if (!apps.length) {
    $("applicationList").innerHTML = `<article class="kanban-card"><strong>暂无投递</strong><span>添加第一条记录后，这里会按阶段自动成列。</span></article>`;
    return;
  }
  const stages = ["已投递", "简历筛选", "笔试", "一面", "二面", "HR 面", "Offer", "已拒绝"];
  const grouped = stages.map((stage) => ({
    stage,
    items: apps.filter((item) => item.status === stage),
  })).filter((group) => group.items.length || ["已投递", "笔试", "一面", "Offer"].includes(group.stage));
  $("applicationList").innerHTML = grouped.map((group) => `
    <section class="kanban-column">
      <h4>${escapeHtml(group.stage)}<span>${group.items.length}</span></h4>
      ${group.items.length ? group.items.map((item) => `
        <article class="kanban-card">
          <strong>${escapeHtml(item.company)}</strong>
          <span>${escapeHtml(item.job_title)}</span>
          <em>${escapeHtml(item.city || "城市未填")}</em>
          <p>${escapeHtml(item.notes || "暂无备注，建议补充投递渠道、面试反馈或待办。")}</p>
          <button class="ghost small" onclick="coachApplication(${item.id})">生成跟进建议</button>
          <button class="ghost small" onclick="advanceApplication(${item.id})">推进到下一阶段</button>
          <button class="ghost small" onclick="editApplication(${item.id})">编辑</button>
          <button class="ghost small" onclick="deleteApplication(${item.id})">删除</button>
        </article>
      `).join("") : `<article class="kanban-card"><span>暂无记录</span></article>`}
    </section>
  `).join("");
  lucide.createIcons();
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

async function sendAgentMessage() {
  const input = $("agentInput");
  const message = input.value.trim();
  if (!message) return;
  appendMessage(message, "user");
  input.value = "";
  const data = await withLoading(
    () => api("/agent/chat", { method: "POST", body: { message } }),
    "AI 教练正在思考..."
  );
  appendMessage(data.reply || data.message || "我暂时没想好，换个问法试试。", "bot");
}

async function generateCareerReport() {
  const data = await withLoading(
    () => api(`/career/report/${USER_ID}`, { method: "POST" }),
    "AI 正在生成求职作战报告..."
  );
  if (!data.success) return toast(data.message || "报告生成失败");
  appendMessage("生成一份我的求职作战报告", "user");
  appendMessage(data.report, "bot");
}

function appendMessage(text, type) {
  const node = document.createElement("div");
  node.className = `message ${type}`;
  node.innerHTML = renderText(text);
  $("chatLog").appendChild(node);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}
