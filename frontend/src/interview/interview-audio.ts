import type { InterviewControllerDependencies } from "./interview-controller";

export interface InterviewAudioCallbacks {
  renderFeedback(feedback: any): void;
  renderFeedbackHtml(feedback: any): string;
  loadTrainingRecords(): Promise<void>;
}

export interface InterviewAudioController {
  extensionFromMime(mime?: string): string;
  downloadSaved(filename: string, format?: string): Promise<void>;
  getRecordingController(): any;
  startRecording(target?: string): Promise<void>;
  stopRecording(): void;
  handleUpload(): Promise<void>;
  computeMetrics(blob: Blob, source?: string, startedAt?: number): Promise<any>;
  renderPreview(target?: string): void;
  analyzeRecorded(target?: string): Promise<void>;
  applyCapabilities(): void;
  setupSpeechRecognition(): void;
  toggleVoiceInput(): void;
}

function required<T extends HTMLElement>(
  byId: InterviewControllerDependencies["byId"],
  id: string,
): T {
  const node = byId(id);
  if (!node) throw new Error(`Missing interview audio control: #${id}`);
  return node as T;
}

export function createInterviewAudioController(
  deps: InterviewControllerDependencies,
  callbacks: InterviewAudioCallbacks,
): InterviewAudioController {
  const {
    userId,
    state,
    request,
    byId,
    toast,
    withLoading,
    downloadBlob,
    downloadResponse,
    media,
    capabilities,
  } = deps;
  const previewUrls = media.createObjectUrlRegistry({
    create: (blob: Blob) => URL.createObjectURL(blob),
    revoke: (url: string) => URL.revokeObjectURL(url),
  });

  function extensionFromMime(mime = ""): string {
    return capabilities.extensionForMime(mime);
  }

  function downloadBase(filename = "interview-answer"): string {
    return filename.replace(/\.[^.]+$/, "") || "interview-answer";
  }

  async function blobToWav(blob: Blob): Promise<Blob> {
    const AudioContextClass = window.AudioContext
      || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) throw new Error("当前浏览器不支持音频解码");
    const buffer = await media.decodeAudioBlob(blob, AudioContextClass);
    const channels = Math.min(2, buffer.numberOfChannels);
    const sampleRate = buffer.sampleRate;
    const samples = buffer.length;
    const blockAlign = channels * 2;
    const dataSize = samples * blockAlign;
    const wav = new ArrayBuffer(44 + dataSize);
    const view = new DataView(wav);
    const writeString = (offset: number, text: string) => {
      for (let index = 0; index < text.length; index += 1) {
        view.setUint8(offset + index, text.charCodeAt(index));
      }
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
    const channelData = Array.from(
      { length: channels },
      (_, index) => buffer.getChannelData(index) as Float32Array,
    );
    let offset = 44;
    for (let index = 0; index < samples; index += 1) {
      for (let channel = 0; channel < channels; channel += 1) {
        const sample = Math.max(-1, Math.min(1, channelData[channel][index]));
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
        offset += 2;
      }
    }
    return new Blob([wav], { type: "audio/wav" });
  }

  async function downloadSaved(filename: string, format = "wav"): Promise<void> {
    if (!filename) {
      toast("没有可下载的音频文件");
      return;
    }
    if (!request.raw) throw new Error("ApiClient.raw is required for audio downloads");
    if (format === "wav") {
      try {
        const response = await request.raw(`/uploads/${encodeURIComponent(filename)}`);
        if (!response.ok) throw new Error("音频读取失败");
        downloadBlob(await blobToWav(await response.blob()), `${downloadBase(filename)}.wav`);
        toast("WAV 音频已开始下载");
      } catch (error) {
        toast(`WAV 导出失败：${(error as Error).message}`);
      }
      return;
    }
    const response = await request.raw(
      `/uploads/${encodeURIComponent(filename)}/download/${format}`,
    );
    const fallbackName = format === "original"
      ? capabilities.audioFileDescriptor({ name: filename, type: "" }).filename
      : `${downloadBase(filename)}.${format}`;
    await downloadResponse(response, fallbackName);
  }

  async function computeMetrics(
    blob: Blob,
    source = "upload",
    startedAt = 0,
  ): Promise<any> {
    return media.computeAudioMetrics(blob, {
      source,
      startedAt,
      AudioContext: window.AudioContext
        || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
        || null,
    });
  }

  function renderPreview(target = "answer"): void {
    const playback = required<HTMLAudioElement>(
      byId,
      target === "room" ? "roomAudioPlayback" : "audioPlayback",
    );
    const preview = required(byId, target === "room" ? "roomAudioMetricPreview" : "audioMetricPreview");
    const status = required(byId, target === "room" ? "roomAudioPlaybackStatus" : "audioPlaybackStatus");
    const download = required<HTMLAnchorElement>(
      byId,
      target === "room" ? "roomAudioDownloadLink" : "audioDownloadLink",
    );
    if (state.audioBlob) {
      const url = previewUrls.replace(target, state.audioBlob);
      const descriptor = capabilities.audioFileDescriptor(state.audioBlob);
      playback.src = url;
      playback.dataset.url = url;
      download.href = url;
      download.download = descriptor.filename;
      download.classList.remove("hidden");
      status.classList.remove("hidden", "is-warning");
      status.textContent = descriptor.mayNotPlay
        ? capabilities.audioPlaybackErrorMessage()
        : `已载入 ${descriptor.filename}，可回放或下载原文件。`;
      status.classList.toggle("is-warning", descriptor.mayNotPlay);
      playback.onerror = () => {
        status.textContent = capabilities.audioPlaybackErrorMessage();
        status.classList.remove("hidden");
        status.classList.add("is-warning");
        download.classList.remove("hidden");
      };
      playback.oncanplay = () => {
        if (!descriptor.mayNotPlay) status.classList.remove("is-warning");
      };
    }
    const metrics = state.audioMetrics || {};
    const duration = metrics.duration_seconds == null ? "未知" : `${metrics.duration_seconds}s`;
    preview.classList.remove("hidden");
    preview.innerHTML = `
      <span>时长 ${duration}</span>
      <span>音量 ${metrics.average_volume || 0}</span>
      <span>停顿 ${(metrics.silence_ratio || 0) * 100}%</span>
      <span>爆音 ${(metrics.clipping_ratio || 0) * 100}%</span>
    `;
  }

  function getRecordingController(): any {
    if (state.recordingController) return state.recordingController;
    state.recordingController = media.createRecordingController({
      acquireStream: () => navigator.mediaDevices.getUserMedia({ audio: true }),
      createRecorder: (stream: MediaStream, options?: MediaRecorderOptions) => (
        options ? new MediaRecorder(stream, options) : new MediaRecorder(stream)
      ),
      createBlob: (chunks: BlobPart[], options: BlobPropertyBag) => new Blob(chunks, options),
      computeMetrics,
      publish: ({ blob, metrics, target }: any) => {
        state.audioBlob = blob;
        state.audioMetrics = metrics;
        renderPreview(target);
        toast("录音已生成，可以回放或分析");
      },
      onError: (error: any) => {
        toast(error?.name === "NotAllowedError"
          ? "未获得麦克风权限，请上传音频或使用文字回答"
          : "录音发生错误，请上传音频或使用文字回答");
      },
    });
    return state.recordingController;
  }

  async function startRecording(target = "answer"): Promise<void> {
    const plan = capabilities.audioInputPlan(window, navigator);
    if (!plan.canRecord) {
      toast("当前浏览器不能直接录音，请上传音频或使用文字回答");
      return;
    }
    const result = await getRecordingController().start({
      target,
      format: plan.recorderFormat,
    });
    if (result.ok) {
      toast(target === "room" ? "模拟面试录音开始" : "真实录音开始");
    } else if (result.reason === "busy") {
      toast("正在启动或录制音频，请先停止当前录音");
    }
  }

  function stopRecording(): void {
    if (!getRecordingController().stop()) toast("当前没有正在录制的音频");
  }

  async function handleUpload(): Promise<void> {
    getRecordingController().invalidate();
    const file = required<HTMLInputElement>(byId, "audioFileInput").files?.[0];
    if (!file) return;
    state.audioBlob = file;
    state.audioMetrics = await computeMetrics(file, "upload");
    renderPreview("answer");
    toast("已载入上传音频，可以回放或分析");
  }

  async function analyzeRecorded(target = "answer"): Promise<void> {
    if (!state.audioBlob) {
      toast("请先录音或上传音频");
      return;
    }
    const transcript = required<HTMLTextAreaElement>(
      byId,
      target === "room" ? "roomAnswer" : "answerInput",
    ).value.trim();
    if (!transcript) {
      toast("请补充转写文本，AI 需要结合内容和声音一起分析");
      return;
    }
    const form = new FormData();
    const descriptor = capabilities.audioFileDescriptor(state.audioBlob);
    form.append("audio", state.audioBlob, descriptor.filename);
    form.append("user_id", String(userId));
    form.append("transcript", transcript);
    if (Number.isFinite(state.audioMetrics?.duration_seconds)) {
      form.append("duration_seconds", String(state.audioMetrics.duration_seconds));
    }
    form.append("metrics", JSON.stringify(state.audioMetrics || {}));
    const data = await withLoading(
      () => request("/interview/analyze-audio", { method: "POST", body: form }),
      "AI 正在分析真实录音...",
    );
    if (!data.success) {
      toast(data.message || "录音分析失败");
      return;
    }
    const feedback = {
      score: data.overall_score,
      summary: data.summary,
      voice: data,
      suggestions: data.tips,
    };
    if (target === "room") {
      const result = required(byId, "roomFeedback");
      result.classList.remove("hidden");
      result.innerHTML = callbacks.renderFeedbackHtml(feedback);
    } else {
      callbacks.renderFeedback(feedback);
    }
    await callbacks.loadTrainingRecords();
  }

  function applyCapabilities(): void {
    const speech = capabilities.speechRecognition(window);
    const audio = capabilities.audioInputPlan(window, navigator);
    capabilities.applyCapabilityUI(document, { speech, audio });
  }

  function setupSpeechRecognition(): void {
    const speech = capabilities.speechRecognition(window);
    if (!speech.Recognition) return;
    state.recognition = new speech.Recognition();
    state.recognition.lang = "zh-CN";
    state.recognition.continuous = true;
    state.recognition.interimResults = true;
    state.speechController = media.bindSpeechRecognition(state.recognition, {
      getText: () => required<HTMLTextAreaElement>(byId, "answerInput").value.replace(/\s*$/, ""),
      setText: (value: string) => {
        required<HTMLTextAreaElement>(byId, "answerInput").value = value;
      },
      setActive: (active: boolean) => {
        state.recognizing = active;
        required(byId, "voiceBtn").classList.toggle("recording", active);
      },
      onError: (event: any) => {
        const denied = event?.error === "not-allowed" || event?.error === "service-not-allowed";
        toast(denied
          ? "未获得语音识别权限，请直接使用文字回答"
          : "语音识别暂时不可用，请直接使用文字回答");
      },
    });
  }

  function toggleVoiceInput(): void {
    if (!state.recognition) {
      toast("当前浏览器不支持语音识别，可以使用 Chrome 尝试");
      return;
    }
    if (state.recognizing) {
      try {
        state.recognition.stop();
      } catch {
        state.speechController?.finish();
      }
      return;
    }
    state.speechController?.begin();
    const result = capabilities.startSpeechSafely(state.recognition);
    if (!result.ok) {
      state.speechController?.finish();
      toast("无法启动语音识别，请直接使用文字回答");
      return;
    }
    toast("正在语音录入");
  }

  return {
    extensionFromMime,
    downloadSaved,
    getRecordingController,
    startRecording,
    stopRecording,
    handleUpload,
    computeMetrics,
    renderPreview,
    analyzeRecorded,
    applyCapabilities,
    setupSpeechRecognition,
    toggleVoiceInput,
  };
}
