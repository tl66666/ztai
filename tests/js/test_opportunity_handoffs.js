const assert = require("node:assert/strict");
const {
  applicationPayloadForJob,
  buildApplicationHandoff,
  buildInterviewHandoff,
  buildInterviewStartPayload,
  buildMatchPayload,
  routeLeavesFlow,
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

assert.equal(typeof routeLeavesFlow, "function", "route cleanup must use a shared flow-boundary helper");
assert.equal(
  routeLeavesFlow({ page: "tracker", module: "add" }, { page: "resume", module: "input" }, "tracker", "add"),
  true,
  "Back or Forward away from the application flow must clear its whole handoff",
);
assert.equal(
  routeLeavesFlow({ page: "tracker", module: "board" }, { page: "tracker", module: "add" }, "tracker", "add"),
  false,
  "entering a flow must preserve the handoff prepared immediately before navigation",
);
assert.equal(
  routeLeavesFlow({ page: "interview", module: "mock" }, { page: "interview", module: "mock" }, "interview", "mock"),
  false,
  "re-activating the current operation must not clear it",
);
assert.equal(
  routeLeavesFlow({ page: "interview", module: "mock" }, { page: "interview", module: "practice" }, "interview", "mock"),
  true,
  "leaving the interview module must clear its handoff",
);
console.log("opportunity handoff behavior: ok");
