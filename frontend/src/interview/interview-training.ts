import type { InterviewControllerDependencies } from "./interview-controller";
import {
  categoryName,
  escapeAttr,
  formatDate,
  parseFeedbackSummary,
  safeJson,
} from "./interview-renderers";

export interface InterviewTrainingController {
  loadQuestions(category?: string): Promise<void>;
  selectQuestion(question: string, category: string): void;
  showSampleAnswer(answer: string): void;
  loadRecords(): Promise<void>;
  renderRecordColumn(
    title: string,
    type: string,
    items: any[],
    bodyRenderer: (item: any) => string,
  ): string;
  viewRecord(type: string, id: number): Promise<void>;
  renderRecordDetail(type: string, item: any): string;
  renderConversation(value: unknown): string;
  deleteRecord(type: string, id: number): Promise<void>;
  clearRecords(): Promise<void>;
  loadProfessionalPack(): Promise<void>;
  selectProfessionalQuestion(question: string): void;
  showProfessionalReference(reference: string): void;
  scoreProfessionalAnswer(): Promise<void>;
  scorePractice(): Promise<void>;
}

function required<T extends HTMLElement>(
  byId: InterviewControllerDependencies["byId"],
  id: string,
): T {
  const node = byId(id);
  if (!node) throw new Error(`Missing interview training control: #${id}`);
  return node as T;
}

export function createInterviewTrainingController(
  deps: InterviewControllerDependencies,
): InterviewTrainingController {
  const {
    userId,
    apiBaseUrl,
    state,
    request,
    byId,
    escapeHtml,
    renderText,
    toast,
    withLoading,
    renderIcons,
    selectedCareerProfile,
    loadDashboard,
    confirmAction,
  } = deps;

  async function loadQuestions(category = "all"): Promise<void> {
    const resolvedCategory = category === "career" ? selectedCareerProfile() : category;
    state.currentPracticeCategory = category;
    const data = await request(`/questions?category=${encodeURIComponent(resolvedCategory)}`);
    const questions = data.success ? data.data : [];
    required(byId, "questionList").innerHTML = questions.length
      ? questions.map((item: any, index: number) => `
        <article class="question-card">
          <b>${index + 1}. ${escapeHtml(item.question)}</b>
          <small>${categoryName(item.category)} · 点击“练习”后可输入自己的回答</small>
          <div class="list-actions">
            <button class="ghost small" data-command="interview-select-question" data-question="${escapeAttr(item.question)}" data-category="${escapeAttr(category === "career" ? "career" : item.category)}">练习</button>
            <button class="ghost small" data-command="interview-show-sample" data-answer="${escapeAttr(item.answer)}">参考答案</button>
          </div>
        </article>
      `).join("")
      : `<article class="question-card"><b>暂无题目</b><small>换一个分类试试</small></article>`;
  }

  function selectQuestion(question: string, category: string): void {
    required<HTMLTextAreaElement>(byId, "practiceQuestion").value = question;
    state.currentPracticeCategory = category;
    required<HTMLTextAreaElement>(byId, "practiceAnswer").focus();
    toast("题目已放入练习区");
  }

  function showSampleAnswer(answer: string): void {
    const result = required(byId, "practiceResult");
    result.classList.remove("hidden");
    result.innerHTML = `<h4>参考答案</h4>${renderText(answer)}`;
  }

  function renderRecordColumn(
    title: string,
    type: string,
    items: any[],
    bodyRenderer: (item: any) => string,
  ): string {
    return `
      <section class="record-column">
        <h4>${escapeHtml(title)}<span>${items.length}</span></h4>
        ${items.length ? items.map((item) => `
          <article class="record-card">
            ${bodyRenderer(item)}
            <div class="record-actions">
              <button class="ghost small" data-command="training-view" data-record-type="${escapeAttr(type)}" data-record-id="${item.id}">查看详情</button>
              <button class="ghost small danger" data-command="training-delete" data-record-type="${escapeAttr(type)}" data-record-id="${item.id}">删除</button>
            </div>
          </article>
        `).join("") : `<article class="record-card"><b>暂无记录</b><small>完成训练后会自动出现在这里</small></article>`}
      </section>
    `;
  }

  async function loadRecords(): Promise<void> {
    const box = byId("trainingRecords");
    if (!box) return;
    const data = await request(`/training-records/${userId}`);
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
    renderIcons();
  }

  async function viewRecord(type: string, id: number): Promise<void> {
    const data = await request(`/training-records/${userId}`);
    if (!data.success) {
      toast("记录读取失败");
      return;
    }
    const source = type === "interview"
      ? data.interviews
      : type === "practice" ? data.practices : data.audios;
    const item = (source || []).find((record: any) => Number(record.id) === Number(id));
    if (!item) {
      toast("记录不存在或已删除");
      return;
    }
    const detail = required(byId, "recordDetail");
    detail.classList.remove("hidden");
    detail.innerHTML = renderRecordDetail(type, item);
    detail.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderConversation(value: unknown): string {
    const data = safeJson(value);
    const turns = Array.isArray(data) ? data : data.turns || data.conversation || [];
    if (!turns.length) return `<div>暂无完整对话记录。</div>`;
    return turns.map((turn: any) => {
      const role = turn.role || turn.speaker || "记录";
      const text = turn.content || turn.text || turn.question || turn.answer || "";
      return `<div class="conversation-line"><b>${escapeHtml(role)}</b><span>${escapeHtml(text)}</span></div>`;
    }).join("");
  }

  function renderRecordDetail(type: string, item: any): string {
    const feedback = safeJson(item.feedback);
    const metrics = safeJson(item.metrics);
    if (type === "audio") {
      return `
        <h4>语音复盘详情：${item.score ?? 0} 分</h4>
        <div><b>时间</b><br>${formatDate(item.created_at)}</div>
        <div><b>转写文本</b><br>${escapeHtml(item.transcript || "暂无转写文本")}</div>
        <div><b>声音指标</b><br>时长 ${metrics.duration_seconds || 0}s，平均音量 ${metrics.average_volume || 0}，停顿占比 ${Math.round((metrics.silence_ratio || 0) * 100)}%，爆音占比 ${Math.round((metrics.clipping_ratio || 0) * 100)}%</div>
        ${item.audio_file ? `
          <audio controls src="${apiBaseUrl}/uploads/${encodeURIComponent(item.audio_file)}"></audio>
          <div class="audio-downloads">
            <button class="ghost small" data-command="training-audio-download" data-audio-file="${escapeAttr(item.audio_file)}" data-audio-format="wav">下载 WAV</button>
            <button class="ghost small" data-command="training-audio-download" data-audio-file="${escapeAttr(item.audio_file)}" data-audio-format="mp3">下载 MP3</button>
            <button class="ghost small" data-command="training-audio-download" data-audio-file="${escapeAttr(item.audio_file)}" data-audio-format="original">下载原始音频</button>
          </div>
          <small>WAV 可由浏览器本地转换；MP3 由后端 ffmpeg 转码生成。</small>
        ` : ""}
        <div><b>AI 建议</b><br>${escapeHtml(feedback.summary || "")}</div>
        ${(feedback.tips || []).map((tip: unknown) => `<div>• ${escapeHtml(tip)}</div>`).join("")}
      `;
    }
    if (type === "practice") {
      return `
        <h4>答题记录详情：${item.score ?? 0} 分</h4>
        <div><b>时间</b><br>${formatDate(item.created_at)}</div>
        <div><b>题目</b><br>${escapeHtml(item.question || "")}</div>
        <div><b>我的回答</b><br>${escapeHtml(item.answer || "")}</div>
        <div><b>维度评分</b><br>${Object.entries(feedback.dimension_scores || {}).map(([key, value]) => `${escapeHtml(key)}：${escapeHtml(String(value))}`).join("　") || "暂无"}</div>
        ${(feedback.problems || []).map((problem: unknown) => `<div>• ${escapeHtml(problem)}</div>`).join("")}
        ${feedback.sample_answer ? `<h4>参考答案</h4>${renderText(feedback.sample_answer)}` : ""}
        ${feedback.upgrade ? `<h4>表达升级</h4><div>${escapeHtml(feedback.upgrade)}</div>` : ""}
      `;
    }
    return `
      <h4>模拟面试详情：${item.score ?? 0} 分</h4>
      <div><b>岗位</b><br>${escapeHtml(item.job_title || "模拟面试")}</div>
      <div><b>时间</b><br>${formatDate(item.created_at)}</div>
      <div><b>总体反馈</b><br>${escapeHtml(feedback.summary || parseFeedbackSummary(item.feedback) || "暂无总结")}</div>
      ${(feedback.suggestions || []).map((suggestion: unknown) => `<div>• ${escapeHtml(suggestion)}</div>`).join("")}
      <h4>面试对话</h4>
      ${renderConversation(item.conversation)}
    `;
  }

  async function deleteRecord(type: string, id: number): Promise<void> {
    if (!confirmAction("确定删除这条训练记录吗？")) return;
    const data = await request(`/training-records/${type}/${id}`, { method: "DELETE" });
    if (!data.success) {
      toast(data.message || "删除失败");
      return;
    }
    toast("训练记录已删除");
    await Promise.all([loadRecords(), loadDashboard()]);
  }

  async function clearRecords(): Promise<void> {
    if (!confirmAction("确定清空所有面试、答题和语音记录吗？")) return;
    const data = await request(`/training-records/${userId}/clear`, { method: "DELETE" });
    if (!data.success) {
      toast(data.message || "清空失败");
      return;
    }
    toast("训练记录已清空");
    await Promise.all([loadRecords(), loadDashboard()]);
  }

  async function loadProfessionalPack(): Promise<void> {
    const data = await withLoading(
      () => request("/interview/professional-pack", {
        method: "POST",
        body: {
          category: required<HTMLSelectElement>(byId, "professionalCategory").value,
          career_profile: selectedCareerProfile(),
          level: required<HTMLSelectElement>(byId, "professionalLevel").value,
          job_title: required<HTMLInputElement>(byId, "professionalJobTitle").value
            || required<HTMLInputElement>(byId, "interviewJobTitle").value
            || "目标岗位",
        },
      }),
      "AI 正在生成专业面试题组...",
    );
    if (!data.success) {
      toast(data.message || "题组生成失败");
      return;
    }
    required(byId, "professionalPack").innerHTML = data.questions.map((item: any, index: number) => `
      <article class="question-card">
        <b>${index + 1}. ${escapeHtml(item.question)}</b>
        <small>${escapeHtml(item.focus)} · ${escapeHtml(item.difficulty)}</small>
        <div class="list-actions">
          <button class="ghost small" data-command="interview-select-professional" data-question="${escapeAttr(item.question)}">作答</button>
          <button class="ghost small" data-command="interview-show-professional-reference" data-reference="${escapeAttr(item.reference)}">参考思路</button>
        </div>
      </article>
    `).join("");
  }

  function selectProfessionalQuestion(question: string): void {
    required<HTMLTextAreaElement>(byId, "professionalQuestion").value = question;
    required<HTMLTextAreaElement>(byId, "professionalAnswer").focus();
    toast("专业问题已放入作答区");
  }

  function showProfessionalReference(reference: string): void {
    const result = required(byId, "professionalResult");
    result.classList.remove("hidden");
    result.innerHTML = `<h4>参考思路</h4>${renderText(reference)}`;
  }

  async function scoreProfessionalAnswer(): Promise<void> {
    const question = required<HTMLTextAreaElement>(byId, "professionalQuestion").value.trim();
    const answer = required<HTMLTextAreaElement>(byId, "professionalAnswer").value.trim();
    if (!question || !answer) {
      toast("请先选择专业问题并填写回答");
      return;
    }
    const data = await request("/interview/practice-feedback", {
      method: "POST",
      body: {
        question,
        answer,
        user_id: userId,
        category: required<HTMLSelectElement>(byId, "professionalCategory").value,
        career_profile: selectedCareerProfile(),
        job_title: required<HTMLInputElement>(byId, "professionalJobTitle").value
          || required<HTMLInputElement>(byId, "interviewJobTitle").value
          || "目标岗位",
      },
    });
    if (!data.success) {
      toast(data.message || "评分失败");
      return;
    }
    const result = required(byId, "professionalResult");
    result.classList.remove("hidden");
    result.innerHTML = `
      <h4>专业回答评分：${data.score} 分</h4>
      <div><b>维度分</b><br>${Object.entries(data.dimension_scores).map(([key, value]) => `${key}：${value}`).join("　")}</div>
      <div><b>命中关键词</b><br>${escapeHtml((data.hits || []).join("、") || "暂无")}</div>
      ${(data.problems || []).map((item: unknown) => `<div>• ${escapeHtml(item)}</div>`).join("")}
      <h4>参考答案</h4>${renderText(data.sample_answer)}
      <h4>追问建议</h4>${escapeHtml(data.follow_up || "把回答继续落到你的项目经历、测试工具和实际结果上。")}
    `;
    await loadRecords();
  }

  async function scorePractice(): Promise<void> {
    const question = required<HTMLTextAreaElement>(byId, "practiceQuestion").value.trim();
    const answer = required<HTMLTextAreaElement>(byId, "practiceAnswer").value.trim();
    if (!question || !answer) {
      toast("请先填写题目和你的回答");
      return;
    }
    const data = await request("/interview/practice-feedback", {
      method: "POST",
      body: {
        question,
        answer,
        category: state.currentPracticeCategory,
        career_profile: selectedCareerProfile(),
        job_title: required<HTMLInputElement>(byId, "interviewJobTitle").value || "目标岗位",
        user_id: userId,
      },
    });
    if (!data.success) {
      toast(data.message || "评分失败");
      return;
    }
    const result = required(byId, "practiceResult");
    result.classList.remove("hidden");
    result.innerHTML = `
      <h4>练习评分：${data.score} 分</h4>
      <div><b>维度分</b><br>${Object.entries(data.dimension_scores).map(([key, value]) => `${key}：${value}`).join("　")}</div>
      <div><b>命中关键词</b><br>${escapeHtml((data.hits || []).join("、") || "暂无")}</div>
      ${(data.problems || []).map((item: unknown) => `<div>• ${escapeHtml(item)}</div>`).join("")}
      <h4>参考答案</h4>${renderText(data.sample_answer)}
      <h4>表达升级</h4>${escapeHtml(data.upgrade)}
    `;
    await loadRecords();
  }

  return {
    loadQuestions,
    selectQuestion,
    showSampleAnswer,
    loadRecords,
    renderRecordColumn,
    viewRecord,
    renderRecordDetail,
    renderConversation,
    deleteRecord,
    clearRecords,
    loadProfessionalPack,
    selectProfessionalQuestion,
    showProfessionalReference,
    scoreProfessionalAnswer,
    scorePractice,
  };
}
