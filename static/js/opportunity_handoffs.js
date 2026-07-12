(function exposeOpportunityHandoffs(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.OpportunityHandoffs = api;
}(typeof globalThis !== "undefined" ? globalThis : this, function buildOpportunityHandoffs() {
  const validId = (value) => Number.isSafeInteger(Number(value)) && Number(value) > 0;
  const normalizedJob = (value) => String(value || "").trim().toLocaleLowerCase();

  function buildInterviewHandoff(values) {
    if (!validId(values?.opportunityId) || !validId(values?.resumeId)) return null;
    return Object.freeze({
      opportunityId: Number(values.opportunityId),
      resumeId: Number(values.resumeId),
      actionId: validId(values.actionId) ? Number(values.actionId) : null,
      jobTitle: String(values.jobTitle || "").trim(),
      jd: String(values.jd || ""),
    });
  }

  function buildInterviewStartPayload(base, handoff) {
    if (!handoff || !validId(handoff.opportunityId) || !validId(handoff.resumeId)) return { ...base };
    const payload = {
      ...base,
      application_id: handoff.opportunityId,
      resume_id: handoff.resumeId,
      job_title: handoff.jobTitle,
      jd: handoff.jd,
    };
    if (validId(handoff.actionId)) payload.action_id = handoff.actionId;
    return payload;
  }

  function buildApplicationHandoff(values) {
    if (!String(values?.jobTitle || "").trim()) return null;
    return Object.freeze({
      jobTitle: String(values.jobTitle).trim(),
      jd: String(values.jd || ""),
      resumeId: validId(values.resumeId) ? Number(values.resumeId) : null,
    });
  }

  function applicationPayloadForJob(handoff, currentJob) {
    if (!handoff || normalizedJob(handoff.jobTitle) !== normalizedJob(currentJob)) return {};
    const payload = {};
    if (handoff.jd) payload.jd_text = handoff.jd;
    if (validId(handoff.resumeId)) payload.resume_id = handoff.resumeId;
    return payload;
  }

  function buildMatchPayload(base, opportunityId) {
    const payload = { ...base };
    if (validId(opportunityId)) payload.application_id = Number(opportunityId);
    return payload;
  }

  function routeLeavesFlow(previous, next, page, module) {
    const wasInFlow = previous?.page === page && previous?.module === module;
    const remainsInFlow = next?.page === page && next?.module === module;
    return wasInFlow && !remainsInFlow;
  }

  return {
    applicationPayloadForJob,
    buildApplicationHandoff,
    buildInterviewHandoff,
    buildInterviewStartPayload,
    buildMatchPayload,
    routeLeavesFlow,
  };
}));
