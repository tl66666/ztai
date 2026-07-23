import { createInterviewAudioController } from "./interview-audio";
import {
  categoryName,
  escapeAttr,
  formatDate,
  parseFeedbackSummary,
  safeJson,
  stageName,
} from "./interview-renderers";
import { createInterviewTrainingController } from "./interview-training";

type RequestOptions = Omit<RequestInit, "body"> & { body?: BodyInit | Record<string, unknown> };
type RequestClient = {
  (path: string, options?: RequestOptions): Promise<any>;
  raw?: (path: string, options?: RequestInit) => Promise<Response>;
};

export interface InterviewControllerDependencies {
  userId: number;
  apiBaseUrl: string;
  state: any;
  request: RequestClient;
  byId: (id: string) => HTMLElement | null;
  escapeHtml: (value: unknown) => string;
  renderText: (value: unknown) => string;
  toast: (message: string) => unknown;
  withLoading: <T>(task: () => Promise<T>, message?: string) => Promise<T>;
  renderIcons: () => unknown;
  selectedCareerProfile: () => string;
  loadDashboard: () => Promise<unknown>;
  buildInterviewStartPayload: (body: any, handoff: any) => any;
  downloadBlob: (blob: Blob, filename: string) => unknown;
  downloadResponse: (response: Response, fallbackName: string) => Promise<unknown>;
  confirmAction: (message: string) => boolean;
  submission: any;
  media: any;
  capabilities: any;
}

export interface InterviewController {
  start(): Promise<void>;
  updateQuestion(data: any): void;
  openRoom(data: any): void;
  stageName(stage: string): string;
  sendAnswer(): Promise<void>;
  sendRoomAnswer(): Promise<void>;
  renderFeedback(feedback: any): void;
  renderFeedbackHtml(feedback: any): string;
  analyzeVoice(): Promise<void>;
  extensionFromMime(mime?: string): string;
  downloadSavedAudio(filename: string, format?: string): Promise<void>;
  getRecordingController(): any;
  startAudioRecording(target?: string): Promise<void>;
  stopAudioRecording(): void;
  handleAudioUpload(): Promise<void>;
  computeAudioMetrics(blob: Blob, source?: string, startedAt?: number): Promise<any>;
  renderAudioPreview(target?: string): void;
  analyzeRecordedAudio(target?: string): Promise<void>;
  applyBrowserCapabilities(): void;
  setupSpeechRecognition(): void;
  toggleVoiceInput(): void;
  loadQuestions(category?: string): Promise<void>;
  escapeAttr(text?: string): string;
  categoryName(category: string): string;
  selectQuestion(question: string, category: string): void;
  showSampleAnswer(answer: string): void;
  loadTrainingRecords(): Promise<void>;
  renderRecordColumn(title: string, type: string, items: any[], body: (item: any) => string): string;
  viewTrainingRecord(type: string, id: number): Promise<void>;
  renderRecordDetail(type: string, item: any): string;
  safeJson(value: unknown): any;
  renderConversation(value: unknown): string;
  parseFeedbackSummary(value: unknown): string;
  formatDate(value: unknown): string;
  deleteTrainingRecord(type: string, id: number): Promise<void>;
  clearTrainingRecords(): Promise<void>;
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
  if (!node) throw new Error(`Missing interview control: #${id}`);
  return node as T;
}

export function createInterviewController(
  deps: InterviewControllerDependencies,
): InterviewController {
  const {
    userId,
    state,
    request,
    byId,
    toast,
    renderIcons,
    selectedCareerProfile,
    buildInterviewStartPayload,
    escapeHtml,
    loadDashboard,
    submission,
  } = deps;

  function updateQuestion(data: any): void {
    state.interviewStageIndex = Math.max(0, Number(data.progress || 1) - 1);
    state.currentInterviewSession = data;
    required(byId, "currentQuestion").textContent = data.question;
    required(byId, "interviewStageLabel").textContent = stageName(data.stage);
    const progress = Math.min(100, (data.progress / data.total) * 100);
    const progressBar = required(byId, "interviewProgress");
    progressBar.style.width = `${progress}%`;
    progressBar.parentElement?.classList.toggle("has-progress", progress > 0);
    required(byId, "roomQuestion").textContent = data.question;
    required(byId, "roomStageLabel").textContent = stageName(data.stage);
    required(byId, "roomProgress").style.width = `${progress}%`;
  }

  function openRoom(data: any): void {
    updateQuestion(data);
    required<HTMLTextAreaElement>(byId, "roomAnswer").value = "";
    required(byId, "roomFeedback").classList.add("hidden");
    required(byId, "interviewRoom").classList.remove("hidden");
    renderIcons();
  }

  async function start(): Promise<void> {
    const handoff = state.interviewOpportunityHandoff;
    const resumeId = handoff?.resumeId
      || required<HTMLSelectElement>(byId, "interviewResumeSelect").value
      || state.resumes[0]?.id;
    if (!resumeId) {
      toast("请先保存或选择简历");
      return;
    }
    const body = buildInterviewStartPayload({
      user_id: userId,
      resume_id: Number(resumeId),
      job_title: required<HTMLInputElement>(byId, "interviewJobTitle").value || "软件测试工程师",
      jd: required<HTMLTextAreaElement>(byId, "interviewJd").value,
      career_profile: selectedCareerProfile(),
      mode: "campus",
    }, handoff);
    const data = await request("/interview/sessions", { method: "POST", body });
    if (!data.success) {
      toast(data.message || "面试创建失败");
      return;
    }
    state.activeInterview = data.session_id;
    state.pendingInterviewSubmission = null;
    state.interviewSubmitting = false;
    state.interviewOpportunityHandoff = null;
    updateQuestion(data);
    required(byId, "interviewFeedback").classList.add("hidden");
    openRoom(data);
  }

  function renderFeedbackHtml(feedback: any): string {
    const dimensions = feedback.voice.dimension_scores || {};
    return `
      <h4>即时反馈：${feedback.score} 分</h4>
      <div>${escapeHtml(feedback.summary)}</div>
      <div>语速：${feedback.voice.estimated_speech_rate} 字/分钟（${feedback.voice.pace_label || "自然"}），口头禅：${feedback.voice.filler_count} 次，结构分：${feedback.voice.structure_score}</div>
      <div><b>维度分</b><br>${Object.entries(dimensions).map(([key, value]) => `${key}：${value}`).join("　")}</div>
      ${feedback.voice.audio_quality ? `<div><b>真实录音质量</b><br>${escapeHtml(feedback.voice.audio_quality)}</div>` : ""}
      ${feedback.answer_upgrade ? `<div><b>表达升级</b><br>${escapeHtml(feedback.answer_upgrade)}</div>` : ""}
      ${(feedback.suggestions || []).map((item: unknown) => `<div>• ${escapeHtml(item)}</div>`).join("")}
    `;
  }

  function renderFeedback(feedback: any): void {
    const result = required(byId, "interviewFeedback");
    result.classList.remove("hidden");
    result.innerHTML = renderFeedbackHtml(feedback);
  }

  async function sendAnswer(): Promise<void> {
    if (!state.activeInterview) {
      toast("请先开始模拟面试");
      return;
    }
    if (state.interviewSubmitting) return;
    const input = required<HTMLTextAreaElement>(byId, "answerInput");
    const answer = input.value.trim();
    if (!answer) {
      toast("请先输入回答");
      return;
    }
    const result = await submission.submitInterviewAnswer(state, answer, {
      createId: () => (
        globalThis.crypto && typeof globalThis.crypto.randomUUID === "function"
          ? globalThis.crypto.randomUUID()
          : `interview-${Date.now()}-${Math.random().toString(36).slice(2)}`
      ),
      send: (pending: any) => request(`/interview/sessions/${state.activeInterview}/answer`, {
        method: "POST",
        body: {
          answer: pending.answer,
          submission_id: pending.submissionId,
          expected_stage_index: pending.expectedStageIndex,
        },
      }),
      reload: () => request(`/interview/sessions/${state.activeInterview}`),
    });
    if (result.kind === "success") {
      const data = result.session;
      updateQuestion(data);
      input.value = "";
      renderFeedback(data.feedback);
      if (data.stage === "finished") {
        await Promise.all([loadDashboard(), training.loadRecords()]);
      }
      return;
    }
    if (result.kind === "conflict_recovered") {
      updateQuestion(result.session);
      input.value = "";
      toast("面试进度已同步，请回答当前问题");
      return;
    }
    if (result.kind !== "busy") toast("提交结果不确定，请重试");
  }

  async function sendRoomAnswer(): Promise<void> {
    const roomInput = required<HTMLTextAreaElement>(byId, "roomAnswer");
    const roomAnswer = roomInput.value.trim();
    if (!roomAnswer) {
      toast("请先输入本轮回答");
      return;
    }
    required<HTMLTextAreaElement>(byId, "answerInput").value = roomAnswer;
    await sendAnswer();
    roomInput.value = "";
    const feedback = required(byId, "roomFeedback");
    feedback.classList.remove("hidden");
    feedback.innerHTML = required(byId, "interviewFeedback").innerHTML;
  }

  async function analyzeVoice(): Promise<void> {
    const answer = required<HTMLTextAreaElement>(byId, "answerInput").value.trim();
    if (!answer) {
      toast("请先输入或语音录入回答");
      return;
    }
    const data = await request("/interview/analyze-voice", {
      method: "POST",
      body: { answer },
    });
    renderFeedback({
      score: data.overall_score,
      summary: "表达分析完成",
      voice: data,
      suggestions: data.tips,
    });
  }

  const training = createInterviewTrainingController(deps);
  const audio = createInterviewAudioController(deps, {
    renderFeedback,
    renderFeedbackHtml,
    loadTrainingRecords: training.loadRecords,
  });

  return {
    start,
    updateQuestion,
    openRoom,
    stageName,
    sendAnswer,
    sendRoomAnswer,
    renderFeedback,
    renderFeedbackHtml,
    analyzeVoice,
    extensionFromMime: audio.extensionFromMime,
    downloadSavedAudio: audio.downloadSaved,
    getRecordingController: audio.getRecordingController,
    startAudioRecording: audio.startRecording,
    stopAudioRecording: audio.stopRecording,
    handleAudioUpload: audio.handleUpload,
    computeAudioMetrics: audio.computeMetrics,
    renderAudioPreview: audio.renderPreview,
    analyzeRecordedAudio: audio.analyzeRecorded,
    applyBrowserCapabilities: audio.applyCapabilities,
    setupSpeechRecognition: audio.setupSpeechRecognition,
    toggleVoiceInput: audio.toggleVoiceInput,
    loadQuestions: training.loadQuestions,
    escapeAttr,
    categoryName,
    selectQuestion: training.selectQuestion,
    showSampleAnswer: training.showSampleAnswer,
    loadTrainingRecords: training.loadRecords,
    renderRecordColumn: training.renderRecordColumn,
    viewTrainingRecord: training.viewRecord,
    renderRecordDetail: training.renderRecordDetail,
    safeJson,
    renderConversation: training.renderConversation,
    parseFeedbackSummary,
    formatDate,
    deleteTrainingRecord: training.deleteRecord,
    clearTrainingRecords: training.clearRecords,
    loadProfessionalPack: training.loadProfessionalPack,
    selectProfessionalQuestion: training.selectProfessionalQuestion,
    showProfessionalReference: training.showProfessionalReference,
    scoreProfessionalAnswer: training.scoreProfessionalAnswer,
    scorePractice: training.scorePractice,
  };
}
