import { describe, expect, it } from "vitest";

import {
  applicationPayloadForJob,
  buildApplicationHandoff,
  buildInterviewHandoff,
  buildInterviewStartPayload,
  buildMatchPayload,
  routeLeavesFlow,
} from "./opportunity-handoffs";

describe("opportunity handoffs", () => {
  it("builds interview context only from valid owned identifiers", () => {
    const handoff = buildInterviewHandoff({
      opportunityId: 12,
      resumeId: 7,
      actionId: 3,
      jobTitle: "AI 测试",
      jd: "Python",
    });
    expect(buildInterviewStartPayload({ user_id: 1 }, handoff)).toEqual({
      user_id: 1,
      application_id: 12,
      resume_id: 7,
      action_id: 3,
      job_title: "AI 测试",
      jd: "Python",
    });
    expect(buildInterviewHandoff({ opportunityId: 0, resumeId: 7 })).toBeNull();
  });

  it("keeps application and match context scoped to the current job", () => {
    const handoff = buildApplicationHandoff({
      jobTitle: "测试工程师",
      jd: "接口测试",
      resumeId: 8,
    });
    expect(applicationPayloadForJob(handoff, " 测试工程师 ")).toEqual({
      jd_text: "接口测试",
      resume_id: 8,
    });
    expect(applicationPayloadForJob(handoff, "产品经理")).toEqual({});
    expect(buildMatchPayload({ resume_id: 8 }, 12)).toEqual({
      resume_id: 8,
      application_id: 12,
    });
  });

  it("detects when navigation leaves a workflow", () => {
    expect(routeLeavesFlow(
      { page: "resume", module: "jd" },
      { page: "interview", module: "mock" },
      "resume",
      "jd",
    )).toBe(true);
  });
});
