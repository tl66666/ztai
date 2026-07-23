import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createResumeController,
  type ResumeControllerDependencies,
  type ResumeState,
} from "./resume-controller";

function element(tag: string, id: string): HTMLElement {
  const node = document.createElement(tag);
  node.id = id;
  document.body.append(node);
  return node;
}

function dependencies(
  overrides: Partial<ResumeControllerDependencies> = {},
): ResumeControllerDependencies {
  const state: ResumeState = { resumes: [], editingResumeId: null, skillChart: null };
  return {
    userId: 1,
    apiBaseUrl: "/api",
    state,
    request: vi.fn().mockResolvedValue({ success: true, data: [] }),
    byId: (id) => document.getElementById(id),
    escapeHtml: (value) => String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;"),
    renderText: String,
    toast: vi.fn(),
    withLoading: (task) => task(),
    renderIcons: vi.fn(),
    syncAgentContext: vi.fn(),
    jumpToModule: vi.fn(),
    closeAgentDrawer: vi.fn(),
    selectedCareerProfile: () => "tech",
    careerProfileLabel: () => "计算机 / 软件 / AI",
    loadDashboard: vi.fn(),
    clearMatchOpportunityLink: vi.fn(),
    buildMatchPayload: (value) => value,
    downloadResponse: vi.fn(),
    ...overrides,
  };
}

describe("Resume controller", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    element("span", "resumeCount");
    element("div", "resumeList");
    for (const id of [
      "tailorResumeSelect",
      "interviewResumeSelect",
      "exportResumeSelect",
      "analysisResumeSelect",
      "skillResumeSelect",
    ]) {
      element("select", id);
    }
  });

  it("loads resumes through the shared client and renders every existing resume surface", async () => {
    const state = { resumes: [], editingResumeId: null, skillChart: null };
    const request = vi.fn().mockResolvedValue({
      success: true,
      data: [{
        id: 7,
        title: `<资深 "测试">`,
        file_type: "pdf",
        created_at: "2026-07-23T10:00:00Z",
      }],
    });
    const syncAgentContext = vi.fn();
    const renderIcons = vi.fn();
    const controller = createResumeController(dependencies({
      state,
      request,
      renderIcons,
      syncAgentContext,
    }));

    await controller.load();

    expect(request).toHaveBeenCalledWith("/resumes/1");
    expect(state.resumes).toHaveLength(1);
    expect(document.getElementById("resumeCount")?.textContent).toBe("1");
    expect(document.querySelector("#resumeList b")?.textContent).toBe(`<资深 "测试">`);
    expect(document.querySelector("#resumeList b")?.children).toHaveLength(0);
    expect(document.getElementById("resumeList")?.innerHTML).toContain("fillResume(7)");
    expect((document.getElementById("analysisResumeSelect") as HTMLSelectElement).options[1].value).toBe("7");
    expect(syncAgentContext).toHaveBeenCalledOnce();
    expect(renderIcons).toHaveBeenCalledOnce();
  });

  it("preserves file uploads through the shared client and refreshes dependent views", async () => {
    const title = element("input", "resumeTitle") as HTMLInputElement;
    const content = element("textarea", "resumeContent") as HTMLTextAreaElement;
    const input = element("input", "resumeFile") as HTMLInputElement;
    input.type = "file";
    element("button", "saveResumeBtn");
    element("div", "editingResumeNotice");
    element("span", "editingResumeText");
    title.value = "测试岗位版";
    content.value = "这段文本不会覆盖上传文件";
    const file = new File(["resume"], "resume.pdf", { type: "application/pdf" });
    Object.defineProperty(input, "files", { value: [file], configurable: true });

    const request = vi.fn()
      .mockResolvedValueOnce({ success: true })
      .mockResolvedValueOnce({ success: true, data: [] });
    const loadDashboard = vi.fn();
    const toast = vi.fn();
    const controller = createResumeController(dependencies({ request, loadDashboard, toast }));

    await controller.save();

    const upload = request.mock.calls[0];
    expect(upload[0]).toBe("/resumes/upload");
    expect(upload[1].method).toBe("POST");
    expect(upload[1].body).toBeInstanceOf(FormData);
    expect(upload[1].body.get("file")).toBe(file);
    expect(upload[1].body.get("user_id")).toBe("1");
    expect(upload[1].body.get("title")).toBe("测试岗位版");
    expect(request).toHaveBeenLastCalledWith("/resumes/1");
    expect(loadDashboard).toHaveBeenCalledOnce();
    expect(toast).toHaveBeenCalledWith("简历已保存");
  });

  it("exports binary files through the same client and centralized response handler", async () => {
    const response = new Response(new Blob(["pdf"]), {
      status: 422,
      headers: { "content-type": "application/json" },
    });
    const request = vi.fn() as unknown as ResumeControllerDependencies["request"];
    request.raw = vi.fn().mockResolvedValue(response);
    const downloadResponse = vi.fn();
    const toast = vi.fn();
    const controller = createResumeController(dependencies({
      state: {
        resumes: [{ id: 9, title: "项目版" }],
        editingResumeId: null,
        skillChart: null,
      },
      request,
      downloadResponse,
      toast,
    }));

    await controller.export("pdf");

    expect(request.raw).toHaveBeenCalledWith("/resumes/9/export/pdf");
    expect(downloadResponse).toHaveBeenCalledWith(response, "resume.pdf");
    expect(toast).not.toHaveBeenCalled();
  });

  it("replaces an original file without dropping FormData or the active edit session", async () => {
    const content = element("textarea", "resumeContent") as HTMLTextAreaElement;
    const input = document.createElement("input");
    input.type = "file";
    const file = new File(["updated"], "updated.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    Object.defineProperty(input, "files", { value: [file], configurable: true });
    const request = vi.fn()
      .mockResolvedValueOnce({ success: true })
      .mockResolvedValueOnce({
        success: true,
        data: [{ id: 12, title: "新版", created_at: "2026-07-23T10:00:00Z" }],
      })
      .mockResolvedValueOnce({ success: true, data: { content: "重新解析的文本" } });
    const controller = createResumeController(dependencies({
      state: { resumes: [], editingResumeId: 12, skillChart: null },
      request,
    }));

    await controller.replaceOriginal(12, input);

    expect(request.mock.calls[0][0]).toBe("/resumes/12/replace-file");
    expect(request.mock.calls[0][1].body).toBeInstanceOf(FormData);
    expect(request.mock.calls[0][1].body.get("file")).toBe(file);
    expect(request).toHaveBeenLastCalledWith("/resumes/detail/12");
    expect(content.value).toBe("重新解析的文本");
    expect(input.value).toBe("");
  });
});
