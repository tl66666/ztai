import type { ApiRequest } from "../shared/api-client";
import type { RuntimeUi } from "../shared/runtime-ui";

interface ProviderModel {
  id: string;
  name: string;
}

interface Provider {
  id: string;
  name: string;
  models?: ProviderModel[];
  default_model?: string;
  model?: string;
}

interface CareerProfile {
  id: string;
  label: string;
}

export interface TopbarState {
  providers: Provider[];
  careerProfiles: CareerProfile[];
  careerProfile: string;
  theme: string;
  soundEnabled: boolean;
}

interface CareerFormPort {
  parseList(value: string): string[];
  loadProfile(options: Record<string, unknown>): Promise<any>;
  saveProfile(options: Record<string, unknown>): Promise<any>;
}

export interface TopbarControllerDependencies {
  state: TopbarState;
  request: ApiRequest;
  ui: RuntimeUi;
  careerForm: CareerFormPort;
  loadQuestions(category?: string): Promise<unknown>;
  afterCareerGoalSaved(): Promise<void>;
  storage?: Storage;
  documentObject?: Document;
}

export interface TopbarController {
  bind(): void;
  initialize(): Promise<void>;
  selectedCareerProfile(): string;
  careerProfileLabel(profileId?: string): string;
  applyTheme(theme: string): void;
}

const PROVIDER_LINKS: Record<string, Array<[string, string]>> = {
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

export function createTopbarController(
  deps: TopbarControllerDependencies,
): TopbarController {
  const {
    state,
    request,
    ui,
    careerForm,
    loadQuestions,
    afterCareerGoalSaved,
    storage = localStorage,
    documentObject = document,
  } = deps;
  const byId = <T extends HTMLElement = HTMLElement>(id: string): T | null => (
    ui.byId<T>(id)
  );
  let bound = false;

  function selectedCareerProfile(): string {
    return byId<HTMLSelectElement>("careerProfileSelect")?.value
      || state.careerProfile
      || "tech";
  }

  function careerProfileLabel(profileId = selectedCareerProfile()): string {
    return state.careerProfiles.find((item) => item.id === profileId)?.label
      || "计算机 / 软件 / AI";
  }

  function syncCareerProfileToForms(): void {
    const profile = selectedCareerProfile();
    const flowLabel = byId("flowProfileLabel");
    if (flowLabel) flowLabel.textContent = careerProfileLabel(profile);
    const examples: Record<string, string> = {
      tech: "软件测试工程师 / AI 应用测试",
      ops: "新媒体运营 / 用户运营",
      marketing: "市场专员 / 商务拓展",
      finance: "财务助理 / 会计实习生",
      education: "学科教师 / 教务助理",
      hr: "人事行政专员 / 招聘助理",
    };
    const placeholder = examples[profile] || examples.tech;
    for (const id of [
      "analysisJobTitle",
      "jobTitleInput",
      "interviewJobTitle",
      "professionalJobTitle",
    ]) {
      const element = byId<HTMLInputElement>(id);
      if (element) element.placeholder = `目标岗位，例如：${placeholder}`;
    }
    if (
      byId<HTMLSelectElement>("professionalCategory")?.value === "career"
      && byId<HTMLSelectElement>("questionCategory")?.value === "career"
    ) {
      void loadQuestions("career");
    }
  }

  async function loadCareerProfiles(): Promise<void> {
    const data = await request("/career/profiles");
    state.careerProfiles = data.success ? data.profiles : [];
    const select = byId<HTMLSelectElement>("careerProfileSelect");
    if (!select) return;
    select.innerHTML = state.careerProfiles
      .map((item) => `<option value="${item.id}">${ui.escapeHtml(item.label)}</option>`)
      .join("");
    select.value = state.careerProfiles.some((item) => item.id === state.careerProfile)
      ? state.careerProfile
      : (data.default || "tech");
    state.careerProfile = select.value;
    storage.setItem("jobhunter_career_profile", state.careerProfile);
    syncCareerProfileToForms();
  }

  async function loadCareerGoal(): Promise<void> {
    const result = await careerForm.loadProfile({
      request: () => request("/profile"),
      controls: {
        role: byId("careerGoalRole"),
        cities: byId("careerGoalCities"),
        salaryMin: byId("careerGoalSalaryMin"),
        salaryMax: byId("careerGoalSalaryMax"),
        skills: byId("careerGoalSkills"),
        direction: byId("careerProfileSelect"),
        status: byId("careerGoalStatus"),
        retry: byId("retryCareerGoalBtn"),
      },
      state,
    });
    if (result.ok && result.direction.matched) {
      storage.setItem("jobhunter_career_profile", state.careerProfile);
      syncCareerProfileToForms();
    }
  }

  function listInputValue(id: string): string[] {
    return careerForm.parseList(byId<HTMLInputElement>(id)?.value || "");
  }

  function optionalNumberValue(id: string): number | null {
    const value = byId<HTMLInputElement>(id)?.value.trim() || "";
    return value === "" ? null : Number(value);
  }

  async function saveCareerGoal(event: Event): Promise<void> {
    event.preventDefault();
    const role = byId<HTMLInputElement>("careerGoalRole");
    const targetRole = role?.value.trim() || "";
    const salaryMin = optionalNumberValue("careerGoalSalaryMin");
    const salaryMax = optionalNumberValue("careerGoalSalaryMax");
    const status = byId("careerGoalStatus");
    if (!targetRole) {
      if (status) status.textContent = "请填写目标岗位。";
      role?.focus();
      return;
    }
    if (salaryMin !== null && salaryMax !== null && salaryMin > salaryMax) {
      if (status) status.textContent = "薪资下限不能高于上限。";
      byId<HTMLInputElement>("careerGoalSalaryMin")?.focus();
      return;
    }
    await careerForm.saveProfile({
      request: (body: unknown) => request("/profile", { method: "PUT", body: body as any }),
      payload: {
        career_direction: selectedCareerProfile(),
        target_role: targetRole,
        cities: listInputValue("careerGoalCities"),
        salary: { min: salaryMin, max: salaryMax },
        confirmed_skills: listInputValue("careerGoalSkills"),
        source_metadata: { form: "career-goal-editor" },
      },
      status,
      onSuccess: async () => {
        ui.toast("求职目标档案已保存");
        await afterCareerGoalSaved();
      },
    });
  }

  function updateSoundButton(): void {
    const button = byId<HTMLButtonElement>("soundToggleBtn");
    if (!button) return;
    button.classList.toggle("is-off", !state.soundEnabled);
    button.title = state.soundEnabled ? "关闭界面音效" : "开启界面音效";
    button.innerHTML = `<i data-lucide="${state.soundEnabled ? "volume-2" : "volume-x"}"></i>`;
    ui.renderIcons();
  }

  function renderProviderLinks(providerId: string): void {
    const links = PROVIDER_LINKS[providerId] || [];
    const host = byId("providerLinkList");
    if (!host) return;
    host.innerHTML = links.map(([label, href]) => (
      `<a href="${href}" target="_blank" rel="noreferrer">${label}</a>`
    )).join("") || '<span class="muted-note">选择厂商后显示 API 获取入口。</span>';
  }

  function toggleCustomModelInput(): void {
    const input = byId<HTMLInputElement>("customModelInput");
    const select = byId<HTMLSelectElement>("modelSelect");
    if (!input || !select) return;
    const isCustom = select.value === "custom";
    input.classList.toggle("hidden", !isCustom);
    if (!isCustom) input.value = "";
  }

  function renderModelOptions(providerId: string, selectedModel = ""): void {
    const provider = state.providers.find((item) => item.id === providerId);
    const select = byId<HTMLSelectElement>("modelSelect");
    if (!select) return;
    if (!provider) {
      select.innerHTML = "";
      return;
    }
    const selected = selectedModel || provider.default_model || provider.model;
    select.innerHTML = (provider.models || []).map((model) => (
      `<option value="${model.id}" ${model.id === selected ? "selected" : ""}>${model.name}</option>`
    )).join("") + '<option value="custom">自定义模型 ID...</option>';
    toggleCustomModelInput();
  }

  async function loadProviders(): Promise<void> {
    const data = await request("/config/ai-status");
    if (!data.success) return;
    state.providers = data.providers || [];
    const providerSelect = byId<HTMLSelectElement>("providerSelect");
    if (providerSelect) {
      providerSelect.innerHTML = state.providers.map((provider) => (
        `<option value="${provider.id}" ${provider.id === data.provider ? "selected" : ""}>${provider.name}</option>`
      )).join("");
    }
    renderModelOptions(data.provider, data.selected_model || data.model);
    renderProviderLinks(data.provider);
    const providerName = byId("providerName");
    const providerModel = byId("providerModel");
    const agentModeLabel = byId("agentModeLabel");
    const agentModeDetail = byId("agentModeDetail");
    const providerDot = byId("providerDot");
    if (providerName) providerName.textContent = data.ai_enabled ? data.provider_name : "本地兜底";
    if (providerModel) providerModel.textContent = data.ai_enabled ? data.model : "规则引擎可用";
    if (agentModeLabel) {
      agentModeLabel.textContent = data.ai_enabled
        ? `${data.provider_name} 已连接`
        : "本地智能求职助手";
    }
    if (agentModeDetail) {
      agentModeDetail.textContent = data.ai_enabled
        ? "本地任务优先执行；开放问题由模型增强，写入仍需你确认。"
        : "本地任务可直接执行；开放问题与完整简历深度改写需配置模型。";
    }
    if (providerDot) {
      providerDot.style.background = data.ai_enabled ? "var(--mint)" : "var(--yellow)";
    }
  }

  async function saveProvider(): Promise<void> {
    const provider = byId<HTMLSelectElement>("providerSelect")?.value || "";
    const modelSelect = byId<HTMLSelectElement>("modelSelect");
    let model = modelSelect?.value || "";
    if (model === "custom") {
      model = byId<HTMLInputElement>("customModelInput")?.value.trim() || "";
      if (!model) {
        ui.toast("请输入自定义模型 ID，例如 deepseek-chat、kimi-k2.6");
        return;
      }
    }
    const keyInput = byId<HTMLInputElement>("apiKeyInput");
    const key = keyInput?.value.trim() || "";
    const data = await request("/config/ai-key", {
      method: "POST",
      body: { provider, model, api_key: key },
    });
    if (!data.success) return;
    if (keyInput) keyInput.value = "";
    ui.toast(key
      ? `已保存并启用 ${data.provider} / ${data.model}`
      : "已切换模型；未填 Key 时使用本地兜底");
    await loadProviders();
  }

  function applyTheme(theme: string): void {
    state.theme = theme;
    storage.setItem("jobhunter_theme", theme);
    documentObject.body.dataset.theme = theme;
    documentObject
      .querySelectorAll<HTMLElement>("[data-theme-choice]")
      .forEach((button) => {
        button.classList.toggle("active", button.dataset.themeChoice === theme);
      });
    const suffix = theme === "anime" ? "%20(2)" : "";
    const imageMap: Record<string, string> = {
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
    const positions: Record<string, string> = {
      resumeImage: "center 42%",
      interviewImage: "center 42%",
      trackImage: "center 72%",
      dashboardImage: "center",
    };
    Object.entries(imageMap).forEach(([id, src]) => {
      const node = byId<HTMLImageElement>(id);
      if (!node) return;
      node.src = src;
      if (id in positions) {
        node.parentElement?.style.setProperty("--asset-bg", `url("${src}")`);
        node.parentElement?.style.setProperty("--asset-pos", positions[id]);
      }
    });
    const loadingVideo = byId<HTMLVideoElement>("loadingVideo");
    if (loadingVideo) {
      loadingVideo.src = `/assets/images/loading${theme === "anime" ? "%20(2)" : ""}.mp4`;
    }
  }

  function bind(): void {
    if (bound) return;
    bound = true;
    updateSoundButton();
    byId("modelConfigBtn")?.addEventListener("click", () => {
      ui.playTone("tap");
      byId("modelConfigPanel")?.classList.toggle("hidden");
    });
    byId("soundToggleBtn")?.addEventListener("click", () => {
      state.soundEnabled = !state.soundEnabled;
      storage.setItem("jobhunter_sound", state.soundEnabled ? "on" : "off");
      updateSoundButton();
      if (state.soundEnabled) ui.playTone("success");
      ui.toast(state.soundEnabled ? "界面音效已开启" : "界面音效已关闭", { silent: true });
    });
    byId("closeModelPanel")?.addEventListener(
      "click",
      () => byId("modelConfigPanel")?.classList.add("hidden"),
    );
    byId("saveProviderBtn")?.addEventListener("click", () => void saveProvider());
    byId<HTMLSelectElement>("providerSelect")?.addEventListener("change", (event) => {
      const provider = (event.currentTarget as HTMLSelectElement).value;
      renderModelOptions(provider);
      renderProviderLinks(provider);
    });
    byId("modelSelect")?.addEventListener("change", toggleCustomModelInput);
    documentObject
      .querySelectorAll<HTMLElement>("[data-theme-choice]")
      .forEach((button) => {
        button.addEventListener("click", () => {
          ui.playTone("tap");
          applyTheme(button.dataset.themeChoice || "glass");
        });
      });
    byId<HTMLSelectElement>("careerProfileSelect")?.addEventListener("change", (event) => {
      state.careerProfile = (event.currentTarget as HTMLSelectElement).value || "tech";
      storage.setItem("jobhunter_career_profile", state.careerProfile);
      syncCareerProfileToForms();
      void loadQuestions(byId<HTMLSelectElement>("questionCategory")?.value || "general");
      ui.toast(`已切换求职方向：${careerProfileLabel(state.careerProfile)}`);
    });
    byId("careerGoalForm")?.addEventListener("submit", (event) => {
      void saveCareerGoal(event);
    });
    byId("retryCareerGoalBtn")?.addEventListener("click", () => void loadCareerGoal());
  }

  async function initialize(): Promise<void> {
    applyTheme(state.theme);
    await loadCareerProfiles();
    await loadCareerGoal();
    await loadProviders();
  }

  return {
    bind,
    initialize,
    selectedCareerProfile,
    careerProfileLabel,
    applyTheme,
  };
}
