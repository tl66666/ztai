import { describe, expect, it, vi } from "vitest";

import {
  submitInterviewAnswer,
  type InterviewSubmissionState,
} from "./interview-submission";

function state(): InterviewSubmissionState {
  return {
    interviewStageIndex: 0,
    currentInterviewSession: null,
    pendingInterviewSubmission: null,
    interviewSubmitting: false,
  };
}

describe("interview submission", () => {
  it("clears a confirmed submission and synchronizes progress", async () => {
    const current = state();
    const result = await submitInterviewAnswer(current, "回答", {
      createId: () => "submission-1",
      send: vi.fn(async () => ({ success: true, progress: 2 })),
      reload: vi.fn(),
    });
    expect(result.kind).toBe("success");
    expect(current.interviewStageIndex).toBe(1);
    expect(current.pendingInterviewSubmission).toBeNull();
  });

  it("preserves submission identity after an uncertain failure", async () => {
    const current = state();
    const createId = vi.fn(() => "submission-1");
    const dependencies = {
      createId,
      send: vi.fn(async () => ({ success: false })),
      reload: vi.fn(),
    };
    await submitInterviewAnswer(current, "回答", dependencies);
    await submitInterviewAnswer(current, "回答", dependencies);
    expect(createId).toHaveBeenCalledOnce();
    expect(current.pendingInterviewSubmission?.submissionId).toBe("submission-1");
  });
});
