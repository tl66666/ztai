const assert = require("node:assert/strict");
const {
  applicationPayloadForJob,
  buildApplicationHandoff,
  buildInterviewHandoff,
  buildInterviewStartPayload,
  buildMatchPayload,
} = require("../../static/js/opportunity_handoffs.js");

const interview = buildInterviewHandoff({
  opportunityId: 11, resumeId: 101, actionId: 201, jobTitle: "Role A", jd: "JD A",
});
const mutableCurrentOpportunityId = 22;
const interviewPayload = buildInterviewStartPayload({ user_id: 1, mode: "campus" }, interview);
assert.equal(mutableCurrentOpportunityId, 22);
assert.deepEqual(interviewPayload, {
  user_id: 1, mode: "campus", application_id: 11, resume_id: 101,
  action_id: 201, job_title: "Role A", jd: "JD A",
});
assert.equal(Object.isFrozen(interview), true);

const application = buildApplicationHandoff({ jobTitle: "Role A", jd: "JD A", resumeId: 101 });
assert.deepEqual(applicationPayloadForJob(application, " Role A "), { jd_text: "JD A", resume_id: 101 });
assert.deepEqual(applicationPayloadForJob(application, "Role B"), {}, "changed jobs must not inherit stale context");
assert.deepEqual(applicationPayloadForJob(null, "Role A"), {}, "cleared handoff must stay empty");

assert.deepEqual(
  buildMatchPayload({ resume_id: 101, job_title: "Role A" }, 11),
  { resume_id: 101, job_title: "Role A", application_id: 11 },
);
assert.deepEqual(buildMatchPayload({ resume_id: 101 }, null), { resume_id: 101 });
console.log("opportunity handoff behavior: ok");
