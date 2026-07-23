import { beforeEach, describe, expect, it, vi } from "vitest";

import { createOpportunityController } from "./opportunity-controller";

function control(tag: string, id: string): HTMLElement {
  const node = document.createElement(tag);
  node.id = id;
  document.body.append(node);
  return node;
}

describe("Opportunity controller", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    control("div", "applicationList");
    control("select", "appStatus");
  });

  it("keeps legacy statuses visible while building the canonical application board", async () => {
    const request = vi.fn().mockResolvedValue({
      success: true,
      canonical_statuses: ["已投递", "一面", "Offer"],
      data: [{
        id: 9,
        company: "示例公司",
        job_title: "测试工程师",
        status: "旧阶段",
        needs_status_review: true,
        city: "上海",
        notes: "",
      }],
    });
    const state: any = { applications: [], applicationStatuses: [] };
    const renderAgentCommandOpportunities = vi.fn();
    const controller = createOpportunityController({
      userId: 1,
      state,
      request,
      byId: (id) => document.getElementById(id),
      escapeHtml: String,
      renderText: String,
      toast: vi.fn(),
      withLoading: (task) => task(),
      renderIcons: vi.fn(),
      syncAgentContext: vi.fn(),
      jumpToModule: vi.fn(),
      filterModules: vi.fn(),
      renderAgentCommandOpportunities,
      applicationPayloadForJob: vi.fn(() => ({})),
      buildInterviewHandoff: vi.fn(),
      renderApplicationHandoffNotice: vi.fn(),
      clearApplicationHandoff: vi.fn(),
      renderMatchOpportunityNotice: vi.fn(),
      openOriginalResume: vi.fn(),
      fillResume: vi.fn(),
      openInterviewRoom: vi.fn(),
      parseFeedbackSummary: vi.fn(() => ""),
      confirmAction: vi.fn(() => true),
      history: {} as any,
    });

    await controller.loadApplications();

    expect(request).toHaveBeenCalledWith("/applications/1");
    expect(state.applicationStatuses).toEqual(["已投递", "一面", "Offer"]);
    expect(document.getElementById("applicationList")?.textContent).toContain("待确认");
    expect(document.getElementById("applicationList")?.textContent).toContain("原状态：旧阶段");
    expect(renderAgentCommandOpportunities).toHaveBeenCalledOnce();
  });
});
