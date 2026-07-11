(function exposeInterviewSubmission(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.InterviewSubmission = api;
}(typeof globalThis === "undefined" ? this : globalThis, function createInterviewSubmission() {
  function synchronizeSession(state, session) {
    state.interviewStageIndex = Math.max(0, Number(session.progress || 1) - 1);
    state.currentInterviewSession = session;
  }

  async function submitInterviewAnswer(state, answer, dependencies) {
    if (state.interviewSubmitting) return { kind: "busy" };

    let pending = state.pendingInterviewSubmission;
    if (
      !pending
      || pending.answer !== answer
      || pending.expectedStageIndex !== state.interviewStageIndex
    ) {
      pending = {
        answer,
        submissionId: dependencies.createId(),
        expectedStageIndex: state.interviewStageIndex,
      };
      state.pendingInterviewSubmission = pending;
    }

    state.interviewSubmitting = true;
    try {
      const response = await dependencies.send(pending);
      if (response && response.success) {
        synchronizeSession(state, response);
        state.pendingInterviewSubmission = null;
        return { kind: "success", session: response };
      }
      if (response && response.code === "interview_stage_conflict") {
        const current = await dependencies.reload();
        if (current && current.success) {
          synchronizeSession(state, current);
          state.pendingInterviewSubmission = null;
          return { kind: "conflict_recovered", session: current };
        }
        return { kind: "conflict_reload_failed", response, current };
      }
      return { kind: "uncertain_failure", response };
    } catch (error) {
      return { kind: "uncertain_failure", error };
    } finally {
      state.interviewSubmitting = false;
    }
  }

  return { submitInterviewAnswer, synchronizeSession };
}));
