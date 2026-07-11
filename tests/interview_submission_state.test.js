const assert = require("node:assert/strict");
const test = require("node:test");

const { submitInterviewAnswer } = require("../static/js/interview_submission.js");

function model() {
  return {
    activeInterview: "42",
    interviewStageIndex: 0,
    pendingInterviewSubmission: null,
    interviewSubmitting: false,
    currentInterviewSession: null,
  };
}

test("confirmed success clears pending submission and synchronizes stage", async () => {
  const state = model();
  const sent = [];
  const result = await submitInterviewAnswer(state, "answer", {
    createId: () => "submission-success",
    send: async (pending) => {
      sent.push({ ...pending });
      return { success: true, session_id: "42", stage: "resume_deep_dive", progress: 2, total: 6 };
    },
    reload: async () => assert.fail("reload should not run"),
  });

  assert.equal(result.kind, "success");
  assert.equal(state.pendingInterviewSubmission, null);
  assert.equal(state.interviewStageIndex, 1);
  assert.equal(state.currentInterviewSession.stage, "resume_deep_dive");
  assert.equal(sent[0].submissionId, "submission-success");
});

test("uncertain failure preserves and reuses submission identity", async () => {
  const state = model();
  const sentIds = [];
  const dependencies = {
    createId: () => "submission-retry",
    send: async (pending) => {
      sentIds.push(pending.submissionId);
      throw new Error("network uncertain");
    },
    reload: async () => assert.fail("reload should not run"),
  };

  const first = await submitInterviewAnswer(state, "answer", dependencies);
  const second = await submitInterviewAnswer(state, "answer", dependencies);

  assert.equal(first.kind, "uncertain_failure");
  assert.equal(second.kind, "uncertain_failure");
  assert.equal(state.pendingInterviewSubmission.submissionId, "submission-retry");
  assert.deepEqual(sentIds, ["submission-retry", "submission-retry"]);
});

test("stage conflict reloads persisted session before clearing obsolete pending", async () => {
  const state = model();
  let reloads = 0;
  const result = await submitInterviewAnswer(state, "stale answer", {
    createId: () => "submission-stale",
    send: async () => ({
      success: false,
      code: "interview_stage_conflict",
      http_status: 409,
    }),
    reload: async () => {
      reloads += 1;
      assert.equal(state.pendingInterviewSubmission.submissionId, "submission-stale");
      return {
        success: true,
        session_id: "42",
        stage: "professional",
        question: "Current persisted question",
        progress: 3,
        total: 6,
      };
    },
  });

  assert.equal(result.kind, "conflict_recovered");
  assert.equal(reloads, 1);
  assert.equal(state.pendingInterviewSubmission, null);
  assert.equal(state.interviewStageIndex, 2);
  assert.equal(state.currentInterviewSession.question, "Current persisted question");
});
