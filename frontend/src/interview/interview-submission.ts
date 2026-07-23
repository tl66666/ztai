export interface InterviewSubmissionState {
  interviewStageIndex: number;
  currentInterviewSession: unknown;
  pendingInterviewSubmission: PendingInterviewSubmission | null;
  interviewSubmitting: boolean;
}

export interface PendingInterviewSubmission {
  answer: string;
  submissionId: string;
  expectedStageIndex: number;
}

export interface InterviewSession {
  success?: boolean;
  progress?: number;
  code?: string;
  [key: string]: unknown;
}

export interface InterviewSubmissionDependencies {
  createId(): string;
  send(pending: PendingInterviewSubmission): Promise<InterviewSession>;
  reload(): Promise<InterviewSession>;
}

export function synchronizeSession(
  state: InterviewSubmissionState,
  session: InterviewSession,
): void {
  state.interviewStageIndex = Math.max(0, Number(session.progress || 1) - 1);
  state.currentInterviewSession = session;
}

export async function submitInterviewAnswer(
  state: InterviewSubmissionState,
  answer: string,
  dependencies: InterviewSubmissionDependencies,
): Promise<Record<string, unknown>> {
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
    if (response?.success) {
      synchronizeSession(state, response);
      state.pendingInterviewSubmission = null;
      return { kind: "success", session: response };
    }
    if (response?.code === "interview_stage_conflict") {
      const current = await dependencies.reload();
      if (current?.success) {
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
