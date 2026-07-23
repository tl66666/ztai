export function stageName(stage: string): string {
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

export function escapeAttr(text = ""): string {
  return String(text).replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/\n/g, " ");
}

export function categoryName(category: string): string {
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

export function safeJson(value: unknown): any {
  try {
    return JSON.parse(String(value || "{}"));
  } catch {
    return {};
  }
}

export function formatDate(value: unknown): string {
  return value ? new Date(String(value)).toLocaleString() : "";
}

export function parseFeedbackSummary(feedback: unknown): string {
  return safeJson(feedback).summary || "";
}
