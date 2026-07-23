type UnknownRecord = Record<string, unknown>;

export interface ResumeSummary extends UnknownRecord {
  id: number;
  title: string;
  created_at?: string;
  updated_at?: string;
  file_type?: string;
}

export interface ResumeState {
  resumes: ResumeSummary[];
  editingResumeId: number | null;
  skillChart: { destroy(): void } | null;
  matchOpportunityId?: number | null;
}

export type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | UnknownRecord;
};

export type RequestClient = {
  (path: string, options?: RequestOptions): Promise<any>;
  raw?: (path: string, options?: RequestInit) => Promise<Response>;
};

export interface ResumeControllerDependencies {
  userId: number;
  apiBaseUrl: string;
  state: ResumeState;
  request: RequestClient;
  byId: (id: string) => HTMLElement | null;
  escapeHtml: (value: unknown) => string;
  renderText: (value: unknown) => string;
  toast: (message: string) => unknown;
  withLoading: <T>(task: () => Promise<T>, message?: string) => Promise<T>;
  renderIcons: () => unknown;
  syncAgentContext: () => unknown;
  jumpToModule: (page: string, module: string) => unknown;
  closeAgentDrawer: () => unknown;
  selectedCareerProfile: () => string;
  careerProfileLabel: () => string;
  loadDashboard: () => Promise<unknown>;
  clearMatchOpportunityLink: () => unknown;
  buildMatchPayload: (body: UnknownRecord, opportunityId?: number | null) => UnknownRecord;
  downloadResponse: (response: Response, fallbackName: string) => Promise<unknown>;
}

export interface ResumeController {
  load(): Promise<void>;
  updateSelects(): void;
  fill(id: number): Promise<void>;
  openUploadFromAgent(): void;
  fillTitleFromFile(): void;
  setEditNotice(title?: string): void;
  cancelEdit(): void;
  openOriginal(id: number): void;
  save(): Promise<void>;
  export(format: "pdf" | "word"): Promise<void>;
  convertDocument(route: "pdf-to-word" | "word-to-pdf", inputId: string): Promise<void>;
  generate(): Promise<void>;
  renderAudit(data: any): void;
  analyze(id: number): Promise<void>;
  selectedAnalysisId(): string | number | undefined;
  auditSelected(): Promise<void>;
  improveSelected(): Promise<void>;
  remove(id: number): Promise<void>;
  selectedResumeId(): number | undefined;
  selectedTailorId(): string | number | undefined;
  selectedSkillId(): string | number | undefined;
  tailor(): Promise<void>;
  match(): Promise<void>;
  analyzeJd(): Promise<void>;
  renderSkills(): Promise<void>;
  replaceOriginal(id: number, input: HTMLInputElement): Promise<void>;
}

function requiredElement<T extends HTMLElement>(
  byId: ResumeControllerDependencies["byId"],
  id: string,
): T {
  const node = byId(id);
  if (!node) throw new Error(`Missing resume control: #${id}`);
  return node as T;
}

export function createResumeController(deps: ResumeControllerDependencies): ResumeController {
  const {
    userId,
    state,
    request,
    byId,
    escapeHtml,
    toast,
    renderIcons,
    syncAgentContext,
    loadDashboard,
    downloadResponse,
    withLoading,
    jumpToModule,
    closeAgentDrawer,
    apiBaseUrl,
    renderText,
    selectedCareerProfile,
    careerProfileLabel,
    clearMatchOpportunityLink,
    buildMatchPayload,
  } = deps;

  function setEditNotice(title = ""): void {
    const notice = requiredElement(byId, "editingResumeNotice");
    notice.classList.toggle("hidden", !state.editingResumeId);
    const text = requiredElement(byId, "editingResumeText");
    text.textContent = title
      ? `当前版本：${title}。修改后点击“更新当前简历”保存。`
      : "修改后点击“更新当前简历”保存。";
  }

  function updateSelects(): void {
    const options = `<option value="">选择简历</option>${state.resumes
      .map((resume) => `<option value="${resume.id}">${escapeHtml(resume.title)}</option>`)
      .join("")}`;
    for (const id of [
      "tailorResumeSelect",
      "interviewResumeSelect",
      "exportResumeSelect",
      "analysisResumeSelect",
      "skillResumeSelect",
    ]) {
      requiredElement<HTMLSelectElement>(byId, id).innerHTML = options;
    }
  }

  async function load(): Promise<void> {
    const data = await request(`/resumes/${userId}`);
    state.resumes = data.success ? data.data : [];
    requiredElement(byId, "resumeCount").textContent = String(state.resumes.length);
    requiredElement(byId, "resumeList").innerHTML = state.resumes.length
      ? state.resumes.map((resume) => `
        <article class="list-item" data-resume-id="${resume.id}" tabindex="-1">
          <b>${escapeHtml(resume.title)}</b>
          <small>${new Date(resume.updated_at || resume.created_at || "").toLocaleString()}${resume.file_type ? ` · 原件 ${escapeHtml(resume.file_type.toUpperCase())}` : ""}</small>
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
    updateSelects();
    syncAgentContext();
    renderIcons();
  }

  async function fill(id: number): Promise<void> {
    const data = await request(`/resumes/detail/${id}`);
    if (!data.success) return;
    requiredElement<HTMLInputElement>(byId, "resumeTitle").value = data.data.title;
    const content = requiredElement<HTMLTextAreaElement>(byId, "resumeContent");
    content.value = data.data.content;
    state.editingResumeId = id;
    requiredElement(byId, "saveResumeBtn").innerHTML = `<i data-lucide="save"></i>更新当前简历`;
    setEditNotice(data.data.title);
    renderIcons();
    jumpToModule("resume", "input");
    requiredElement<HTMLInputElement>(byId, "resumeTitle").focus();
    content.scrollTop = 0;
    toast(`正在编辑：${data.data.title}`);
  }

  function openUploadFromAgent(): void {
    closeAgentDrawer();
    jumpToModule("resume", "input");
    const input = requiredElement<HTMLInputElement>(byId, "resumeFile");
    input.focus({ preventScroll: true });
    input.click();
  }

  function fillTitleFromFile(): void {
    const file = requiredElement<HTMLInputElement>(byId, "resumeFile").files?.[0];
    const title = requiredElement<HTMLInputElement>(byId, "resumeTitle");
    if (!file || title.value.trim()) return;
    title.value = file.name.replace(/\.[^.]+$/, "").slice(0, 300);
  }

  function cancelEdit(): void {
    state.editingResumeId = null;
    requiredElement<HTMLInputElement>(byId, "resumeTitle").value = "";
    requiredElement<HTMLTextAreaElement>(byId, "resumeContent").value = "";
    requiredElement<HTMLInputElement>(byId, "resumeFile").value = "";
    requiredElement(byId, "saveResumeBtn").innerHTML = `<i data-lucide="save"></i>保存简历`;
    setEditNotice();
    renderIcons();
    toast("已退出简历编辑模式");
  }

  function openOriginal(id: number): void {
    window.open(`${apiBaseUrl}/resumes/${id}/original`, "_blank");
  }

  async function save(): Promise<void> {
    const input = requiredElement<HTMLInputElement>(byId, "resumeFile");
    const file = input.files?.[0];
    const title = requiredElement<HTMLInputElement>(byId, "resumeTitle").value.trim();
    const content = requiredElement<HTMLTextAreaElement>(byId, "resumeContent").value.trim();
    if (!title) {
      toast("请填写简历标题");
      return;
    }

    let data;
    if (file) {
      const form = new FormData();
      form.append("file", file);
      form.append("user_id", String(userId));
      form.append("title", title);
      data = await request("/resumes/upload", { method: "POST", body: form });
    } else if (state.editingResumeId) {
      if (!content) {
        toast("请粘贴简历内容或上传文件");
        return;
      }
      data = await request(`/resumes/${state.editingResumeId}`, {
        method: "PUT",
        body: { title, content },
      });
    } else {
      if (!content) {
        toast("请粘贴简历内容或上传文件");
        return;
      }
      data = await request("/resumes", {
        method: "POST",
        body: { user_id: userId, title, content },
      });
    }

    if (!data.success) {
      toast(data.message || "保存失败");
      return;
    }
    toast(state.editingResumeId ? "简历已更新" : "简历已保存");
    input.value = "";
    state.editingResumeId = null;
    requiredElement(byId, "saveResumeBtn").innerHTML = `<i data-lucide="save"></i>保存简历`;
    setEditNotice();
    await load();
    await loadDashboard();
    renderIcons();
  }

  function selectedResumeId(): number | undefined {
    return state.resumes[0]?.id;
  }

  async function exportFile(format: "pdf" | "word"): Promise<void> {
    const selected = requiredElement<HTMLSelectElement>(byId, "exportResumeSelect").value;
    const resumeId = selected || selectedResumeId();
    if (!resumeId) {
      toast("请先选择要导出的简历");
      return;
    }
    if (!request.raw) throw new Error("ApiClient.raw is required for resume exports");
    const response = await request.raw(`/resumes/${resumeId}/export/${format}`);
    await downloadResponse(response, format === "pdf" ? "resume.pdf" : "resume.docx");
  }

  async function convertDocument(
    route: "pdf-to-word" | "word-to-pdf",
    inputId: string,
  ): Promise<void> {
    const input = requiredElement<HTMLInputElement>(byId, inputId);
    const file = input.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    if (!request.raw) throw new Error("ApiClient.raw is required for document conversion");
    const response = await request.raw(`/convert/${route}`, { method: "POST", body: form });
    await downloadResponse(response, route === "pdf-to-word" ? "converted.docx" : "converted.pdf");
    input.value = "";
  }

  async function generate(): Promise<void> {
    const data = await request("/resume-generator", {
      method: "POST",
      body: {
        name: "唐乐",
        job_target: "软件测试工程师",
        skills: "Python, Flask, Selenium, Pytest, JMeter, Postman, MySQL",
      },
    });
    requiredElement<HTMLInputElement>(byId, "resumeTitle").value = "唐乐-软件测试工程师-项目版";
    requiredElement<HTMLTextAreaElement>(byId, "resumeContent").value = data.resume_content;
    toast("已生成一份可继续修改的示例简历");
  }

  function renderAudit(data: any): void {
    const result = requiredElement(byId, "resumeAuditResult");
    result.classList.remove("hidden");
    result.innerHTML = `
      <h4>综合评分：${data.score}</h4>
      <div class="score-grid">
        ${Object.entries(data.section_scores || {}).map(([key, value]) => `<div><span>${escapeHtml(key)}</span><b>${value}</b></div>`).join("")}
      </div>
      <div><b>一句话定位</b><br>${escapeHtml(data.positioning)}</div>
      <div><b>优势证据</b><br>${(data.strengths || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>")}</div>
      <div><b>客观锐评</b><br>${(data.brutal_comments || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>")}</div>
      <div><b>HR 初筛风险</b><br>${(data.risks || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>")}</div>
      <div><b>证据缺口</b><br>${(data.evidence_gaps || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>")}</div>
      <div><b>优先修改项</b><br>${(data.actions || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>")}</div>
      <div><b>项目经历建议</b><br>${(data.project_suggestions || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>")}</div>
      <div class="result-actions">
        <button class="primary" onclick="improveSelectedResume()">生成优化版并保存</button>
        <button class="ghost" onclick="jumpToModule('resume','jd')">去做 JD 优化</button>
        <button class="ghost" onclick="jumpToModule('resume','skills')">看技能图谱</button>
        <button class="ghost" onclick="jumpToModule('interview','mock')">去模拟面试</button>
      </div>
    `;
  }

  async function analyze(id: number): Promise<void> {
    const data = await withLoading(
      () => request(`/resumes/${id}/audit`, {
        method: "POST",
        body: {
          job_title: requiredElement<HTMLInputElement>(byId, "analysisJobTitle").value
            || requiredElement<HTMLInputElement>(byId, "jobTitleInput").value,
          jd: requiredElement<HTMLTextAreaElement>(byId, "analysisJdInput").value
            || requiredElement<HTMLTextAreaElement>(byId, "jdInput").value,
        },
      }),
      "AI 正在诊断简历表达...",
    );
    requiredElement<HTMLSelectElement>(byId, "analysisResumeSelect").value = String(id);
    jumpToModule("resume", "analysis");
    renderAudit(data);
  }

  function selectedAnalysisId(): string | number | undefined {
    return requiredElement<HTMLSelectElement>(byId, "analysisResumeSelect").value
      || selectedResumeId();
  }

  async function auditSelected(): Promise<void> {
    const resumeId = selectedAnalysisId();
    if (!resumeId) {
      toast("请先选择要分析的简历");
      return;
    }
    const data = await withLoading(
      () => request(`/resumes/${resumeId}/audit`, {
        method: "POST",
        body: {
          job_title: requiredElement<HTMLInputElement>(byId, "analysisJobTitle").value,
          jd: requiredElement<HTMLTextAreaElement>(byId, "analysisJdInput").value,
          career_profile: selectedCareerProfile(),
        },
      }),
      "AI 正在做简历结构诊断...",
    );
    if (!data.success) {
      toast(data.message || "诊断失败");
      return;
    }
    renderAudit(data);
  }

  async function improveSelected(): Promise<void> {
    const resumeId = selectedAnalysisId();
    if (!resumeId) {
      toast("请先选择要修改的简历");
      return;
    }
    const data = await withLoading(
      () => request(`/resumes/${resumeId}/improve`, {
        method: "POST",
        body: {
          job_title: requiredElement<HTMLInputElement>(byId, "analysisJobTitle").value
            || requiredElement<HTMLInputElement>(byId, "jobTitleInput").value,
          jd: requiredElement<HTMLTextAreaElement>(byId, "analysisJdInput").value
            || requiredElement<HTMLTextAreaElement>(byId, "jdInput").value,
          career_profile: selectedCareerProfile(),
          save: true,
        },
      }),
      "AI 正在生成可投递优化版...",
    );
    if (!data.success) {
      toast(data.message || "优化失败");
      return;
    }
    const result = requiredElement(byId, "resumeAuditResult");
    result.classList.remove("hidden");
    result.innerHTML = `
      <h4>已生成优化版：${escapeHtml(data.new_title || "新简历版本")}</h4>
      <div><b>${data.ai_used ? "AI 深度改写：已通读完整简历并按目标岗位调整表达。" : "本地事实保真版：模型不可用时保留原始事实并完成结构整理。"}</b></div>
      <div><b>改写策略</b><br>${(data.strategy || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>")}</div>
      <h4>优化内容预览</h4>${renderText(data.improved_resume || "")}
      <div class="result-actions">
        <button class="primary" onclick="jumpToModule('resume','manage')">查看我的简历</button>
        <button class="ghost" onclick="jumpToModule('resume','export')">导出新版本</button>
        <button class="ghost" onclick="prepareInterviewFromJd()">带入模拟面试</button>
      </div>
    `;
    await load();
    await loadDashboard();
  }

  async function remove(id: number): Promise<void> {
    await request(`/resumes/${id}`, { method: "DELETE" });
    toast("简历已删除");
    await Promise.all([load(), loadDashboard()]);
  }

  function selectedTailorId(): string | number | undefined {
    return requiredElement<HTMLSelectElement>(byId, "tailorResumeSelect").value
      || selectedResumeId();
  }

  function selectedSkillId(): string | number | undefined {
    return requiredElement<HTMLSelectElement>(byId, "skillResumeSelect").value
      || selectedResumeId();
  }

  async function tailor(): Promise<void> {
    const resumeId = selectedTailorId();
    if (!resumeId) {
      toast("请先选择简历");
      return;
    }
    const data = await withLoading(
      () => request(`/resumes/${resumeId}/tailor`, {
        method: "POST",
        body: {
          job_title: requiredElement<HTMLInputElement>(byId, "jobTitleInput").value,
          jd: requiredElement<HTMLTextAreaElement>(byId, "jdInput").value,
          career_profile: selectedCareerProfile(),
        },
      }),
      "AI 正在按 JD 优化简历...",
    );
    const result = requiredElement(byId, "tailorResult");
    result.classList.remove("hidden");
    const focus = data.jd_focus || {};
    result.innerHTML = `
      <h4>匹配分：${data.match_score}</h4>
      <div class="score-grid">
        ${Object.entries(data.score_detail || {}).map(([key, value]) => `<div><span>${escapeHtml(key)}</span><b>${value}</b></div>`).join("")}
      </div>
      <div><b>候选人定位</b><br>${escapeHtml(data.positioning)}</div>
      <div><b>客观锐评</b><br>${(data.brutal_comments || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>")}</div>
      <div><b>JD 聚焦</b><br>
        硬技能：${escapeHtml((focus["硬技能"] || []).join("、") || "未明显出现")}<br>
        测试能力：${escapeHtml((focus["测试能力"] || []).join("、") || "未明显出现")}<br>
        AI 能力：${escapeHtml((focus["AI 能力"] || []).join("、") || "未明显出现")}
      </div>
      <div><b>已命中</b><br>${escapeHtml((data.matched_keywords || []).join("、") || "暂无")}</div>
      <div><b>待补齐</b><br>${escapeHtml((data.keyword_gaps || []).join("、") || "暂无")}</div>
      <div><b>面试讲述要点</b><br>${(data.interview_talking_points || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>")}</div>
      <h4>优化版本</h4>${renderText(data.ai_rewrite || data.tailored_resume)}
      <div class="result-actions">
        <button class="primary" onclick="prepareInterviewFromJd()">带入模拟面试</button>
        <button class="ghost" onclick="prepareApplicationFromJd()">新增投递记录</button>
        <button class="ghost" onclick="jumpToModule('resume','export')">去导出简历</button>
      </div>
    `;
  }

  async function match(): Promise<void> {
    const resumeId = selectedTailorId();
    if (!resumeId) {
      toast("请先选择简历");
      return;
    }
    const matchBody = buildMatchPayload({
      resume_id: Number(resumeId),
      job_title: requiredElement<HTMLInputElement>(byId, "jobTitleInput").value,
      jd: requiredElement<HTMLTextAreaElement>(byId, "jdInput").value,
      job_requirements: requiredElement<HTMLTextAreaElement>(byId, "jdInput").value,
      career_profile: selectedCareerProfile(),
    }, state.matchOpportunityId);
    const data = await withLoading(
      () => request("/job-match", { method: "POST", body: matchBody }),
      "AI 正在计算岗位匹配度...",
    );
    if (!data.success) {
      toast(data.message || "岗位匹配失败");
      return;
    }
    clearMatchOpportunityLink();
    const result = requiredElement(byId, "tailorResult");
    result.classList.remove("hidden");
    result.innerHTML = `<h4>岗位匹配：${data.match_score}</h4>${renderText(data.analysis)}<br><b>待补齐：</b>${escapeHtml((data.missing_keywords || []).join("、"))}
      <div class="result-actions">
        <button class="primary" onclick="prepareInterviewFromJd()">带入模拟面试</button>
        <button class="ghost" onclick="prepareApplicationFromJd()">新增投递记录</button>
      </div>`;
    await loadDashboard();
  }

  async function analyzeJd(): Promise<void> {
    const jd = requiredElement<HTMLTextAreaElement>(byId, "jdInput").value.trim();
    if (!jd) {
      toast("请先粘贴岗位 JD");
      return;
    }
    const data = await withLoading(
      () => request("/ai/analyze-jd", {
        method: "POST",
        body: {
          jd_content: jd,
          job_title: requiredElement<HTMLInputElement>(byId, "jobTitleInput").value,
          career_profile: selectedCareerProfile(),
        },
      }),
      "AI 正在拆解 JD...",
    );
    const result = requiredElement(byId, "tailorResult");
    result.classList.remove("hidden");
    const focus = data.focus || {};
    result.innerHTML = `
      <h4>JD 岗位画像</h4>
      <div><b>求职方向</b><br>${escapeHtml(data.profile?.label || careerProfileLabel())}</div>
      <div><b>核心关键词</b><br>${escapeHtml((data.keywords || []).join("、") || "暂无")}</div>
      <div><b>能力聚焦</b><br>
        ${Object.entries(focus).map(([key, value]) => `${escapeHtml(key)}：${escapeHtml((value as unknown[] || []).join("、") || "未明显出现")}`).join("<br>")}
      </div>
      <div><b>风险提示</b><br>${(data.risk_flags || []).map((item: unknown) => `• ${escapeHtml(item)}`).join("<br>") || "暂无明显风险词"}</div>
      ${renderText(data.content || "")}
      <div class="result-actions">
        <button class="primary" onclick="tailorResume()">用这份 JD 优化简历</button>
        <button class="ghost" onclick="prepareInterviewFromJd()">带入模拟面试</button>
      </div>
    `;
  }

  async function renderSkills(): Promise<void> {
    const resumeId = selectedSkillId();
    if (!resumeId) {
      toast("请先选择简历");
      return;
    }
    const data = await request("/skills/radar", {
      method: "POST",
      body: {
        resume_id: Number(resumeId),
        career_profile: selectedCareerProfile(),
        job_title: requiredElement<HTMLInputElement>(byId, "analysisJobTitle").value
          || requiredElement<HTMLInputElement>(byId, "jobTitleInput").value,
      },
    });
    const chartConstructor = (window as typeof window & {
      Chart?: new (target: HTMLElement, configuration: UnknownRecord) => { destroy(): void };
    }).Chart;
    if (state.skillChart) state.skillChart.destroy();
    state.skillChart = typeof chartConstructor === "function"
      ? new chartConstructor(requiredElement(byId, "skillChart"), {
          type: "radar",
          data: {
            labels: data.radar_data.map((item: any) => item.category),
            datasets: [{
              label: "能力值",
              data: data.radar_data.map((item: any) => item.score),
              backgroundColor: "rgba(255,122,182,0.18)",
              borderColor: "#ff7ab6",
              pointBackgroundColor: "#66dbc2",
            }],
          },
          options: {
            scales: { r: { min: 0, max: 10 } },
            plugins: { legend: { display: false } },
          },
        })
      : null;
    const result = requiredElement(byId, "skillResult");
    result.classList.remove("hidden");
    result.innerHTML = `
      <h4>技能图谱解读</h4>
      ${(data.radar_data || []).map((item: any) => `
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

  async function replaceOriginal(id: number, input: HTMLInputElement): Promise<void> {
    const file = input.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    const data = await withLoading(
      () => request(`/resumes/${id}/replace-file`, { method: "POST", body: form }),
      "正在替换并解析原始简历...",
    );
    input.value = "";
    if (!data.success) {
      toast(data.message || "替换失败");
      return;
    }
    toast("原文件已替换，文本内容已重新解析");
    await load();
    if (state.editingResumeId === id) {
      const detail = await request(`/resumes/detail/${id}`);
      requiredElement<HTMLTextAreaElement>(byId, "resumeContent").value = detail.data.content || "";
    }
  }

  return {
    load,
    updateSelects,
    fill,
    openUploadFromAgent,
    fillTitleFromFile,
    setEditNotice,
    cancelEdit,
    openOriginal,
    save,
    export: exportFile,
    convertDocument,
    generate,
    renderAudit,
    analyze,
    selectedAnalysisId,
    auditSelected,
    improveSelected,
    remove,
    selectedResumeId,
    selectedTailorId,
    selectedSkillId,
    tailor,
    match,
    analyzeJd,
    renderSkills,
    replaceOriginal,
  };
}
