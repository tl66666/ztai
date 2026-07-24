import { beforeEach, describe, expect, it, vi } from "vitest";

import { createInterviewController } from "./interview-controller";

function control(tag: string, id: string, value = ""): HTMLElement {
  const node = document.createElement(tag);
  node.id = id;
  if ("value" in node) (node as HTMLInputElement).value = value;
  document.body.append(node);
  return node;
}

describe("Interview controller", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    control("select", "interviewResumeSelect", "7");
    control("input", "interviewJobTitle", "测试工程师");
    control("textarea", "interviewJd", "岗位 JD");
    control("div", "currentQuestion");
    control("div", "interviewStageLabel");
    const progress = control("div", "interviewProgress");
    progress.append(document.createElement("span"));
    control("div", "roomQuestion");
    control("div", "roomStageLabel");
    control("div", "roomProgress");
    control("textarea", "roomAnswer");
    control("div", "roomFeedback");
    control("div", "interviewRoom");
    control("div", "interviewFeedback");
  });

  it("starts a persisted interview and updates both the page and room through one interface", async () => {
    const state: any = {
      resumes: [{ id: 7 }],
      activeInterview: null,
      interviewStageIndex: 0,
      pendingInterviewSubmission: null,
      interviewSubmitting: false,
      currentInterviewSession: null,
      interviewOpportunityHandoff: { opportunityId: 3, resumeId: 7 },
    };
    const request = vi.fn().mockResolvedValue({
      success: true,
      session_id: 42,
      stage: "technical",
      question: "如何设计回归测试？",
      progress: 2,
      total: 5,
    });
    const buildInterviewStartPayload = vi.fn((body, handoff) => ({
      ...body,
      opportunity_id: handoff.opportunityId,
    }));
    const controller = createInterviewController({
      userId: 1,
      apiBaseUrl: "/api",
      state,
      request,
      byId: (id) => document.getElementById(id),
      escapeHtml: String,
      renderText: String,
      toast: vi.fn(),
      withLoading: (task) => task(),
      renderIcons: vi.fn(),
      selectedCareerProfile: () => "tech",
      loadDashboard: vi.fn(),
      buildInterviewStartPayload,
      downloadBlob: vi.fn(),
      downloadResponse: vi.fn(),
      confirmAction: vi.fn(() => true),
      submission: {} as any,
      media: {
        createObjectUrlRegistry: () => ({ replace: vi.fn() }),
      } as any,
      capabilities: {} as any,
    });

    await controller.start();

    expect(request).toHaveBeenCalledWith("/interview/sessions", {
      method: "POST",
      body: expect.objectContaining({
        user_id: 1,
        resume_id: 7,
        job_title: "测试工程师",
        jd: "岗位 JD",
        career_profile: "tech",
        opportunity_id: 3,
      }),
    });
    expect(state.activeInterview).toBe(42);
    expect(state.interviewOpportunityHandoff).toBeNull();
    expect(document.getElementById("currentQuestion")?.textContent).toBe("如何设计回归测试？");
    expect(document.getElementById("roomStageLabel")?.textContent).toBe("技术追问");
    expect(document.getElementById("interviewRoom")?.classList.contains("hidden")).toBe(false);
  });

  it("retains the opportunity handoff when session creation fails", async () => {
    const handoff = { opportunityId: 3, resumeId: 7 };
    const state: any = {
      resumes: [{ id: 7 }],
      activeInterview: null,
      interviewOpportunityHandoff: handoff,
    };
    const toast = vi.fn();
    const controller = createInterviewController({
      userId: 1,
      apiBaseUrl: "/api",
      state,
      request: vi.fn().mockResolvedValue({ success: false, message: "创建失败" }),
      byId: (id) => document.getElementById(id),
      escapeHtml: String,
      renderText: String,
      toast,
      withLoading: (task) => task(),
      renderIcons: vi.fn(),
      selectedCareerProfile: () => "tech",
      loadDashboard: vi.fn(),
      buildInterviewStartPayload: (body) => body,
      downloadBlob: vi.fn(),
      downloadResponse: vi.fn(),
      confirmAction: vi.fn(() => true),
      submission: {} as any,
      media: {
        createObjectUrlRegistry: () => ({ replace: vi.fn() }),
      } as any,
      capabilities: {} as any,
    });

    await controller.start();

    expect(state.interviewOpportunityHandoff).toBe(handoff);
    expect(toast).toHaveBeenCalledWith("创建失败");
  });
});
