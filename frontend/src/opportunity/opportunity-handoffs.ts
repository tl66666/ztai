type UnknownRecord = Record<string, unknown>;

export interface Route {
  page?: string | null;
  module?: string | null;
}

export interface InterviewHandoff {
  opportunityId: number;
  resumeId: number;
  actionId: number | null;
  jobTitle: string;
  jd: string;
}

export interface ApplicationHandoff {
  jobTitle: string;
  jd: string;
  resumeId: number | null;
}

const validId = (value: unknown): boolean => (
  Number.isSafeInteger(Number(value)) && Number(value) > 0
);
const normalizedJob = (value: unknown): string => (
  String(value || "").trim().toLocaleLowerCase()
);

export function buildInterviewHandoff(values: {
  opportunityId?: unknown;
  resumeId?: unknown;
  actionId?: unknown;
  jobTitle?: unknown;
  jd?: unknown;
}): Readonly<InterviewHandoff> | null {
  if (!validId(values?.opportunityId) || !validId(values?.resumeId)) return null;
  return Object.freeze({
    opportunityId: Number(values.opportunityId),
    resumeId: Number(values.resumeId),
    actionId: validId(values.actionId) ? Number(values.actionId) : null,
    jobTitle: String(values.jobTitle || "").trim(),
    jd: String(values.jd || ""),
  });
}

export function buildInterviewStartPayload(
  base: UnknownRecord,
  handoff?: InterviewHandoff | null,
): UnknownRecord {
  if (!handoff || !validId(handoff.opportunityId) || !validId(handoff.resumeId)) {
    return { ...base };
  }
  const payload: UnknownRecord = {
    ...base,
    application_id: handoff.opportunityId,
    resume_id: handoff.resumeId,
    job_title: handoff.jobTitle,
    jd: handoff.jd,
  };
  if (validId(handoff.actionId)) payload.action_id = handoff.actionId;
  return payload;
}

export function buildApplicationHandoff(values: {
  jobTitle?: unknown;
  jd?: unknown;
  resumeId?: unknown;
}): Readonly<ApplicationHandoff> | null {
  if (!String(values?.jobTitle || "").trim()) return null;
  return Object.freeze({
    jobTitle: String(values.jobTitle).trim(),
    jd: String(values.jd || ""),
    resumeId: validId(values.resumeId) ? Number(values.resumeId) : null,
  });
}

export function applicationPayloadForJob(
  handoff: ApplicationHandoff | null | undefined,
  currentJob: unknown,
): UnknownRecord {
  if (!handoff || normalizedJob(handoff.jobTitle) !== normalizedJob(currentJob)) return {};
  const payload: UnknownRecord = {};
  if (handoff.jd) payload.jd_text = handoff.jd;
  if (validId(handoff.resumeId)) payload.resume_id = handoff.resumeId;
  return payload;
}

export function buildMatchPayload(base: UnknownRecord, opportunityId: unknown): UnknownRecord {
  const payload = { ...base };
  if (validId(opportunityId)) payload.application_id = Number(opportunityId);
  return payload;
}

export function routeLeavesFlow(
  previous: Route,
  next: Route,
  page: string,
  module: string,
): boolean {
  const wasInFlow = previous?.page === page && previous?.module === module;
  const remainsInFlow = next?.page === page && next?.module === module;
  return wasInFlow && !remainsInFlow;
}
