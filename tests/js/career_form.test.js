const assert = require("node:assert/strict");
const test = require("node:test");

const CareerForm = require("../../frontend/src/career/career-form.mjs");

test("career lists accept Chinese and ASCII separators, trim, and deduplicate", () => {
  assert.deepEqual(
    CareerForm.parseList(" 杭州,上海，杭州、 深圳;苏州；上海\n北京 "),
    ["杭州", "上海", "深圳", "苏州", "北京"],
  );
});

test("serialized career lists round-trip without merging entries", () => {
  const values = ["Python", "接口测试", "Playwright"];
  assert.deepEqual(CareerForm.parseList(CareerForm.serializeList(values)), values);
});

test("known career direction restores while unknown direction preserves current selection", () => {
  assert.deepEqual(
    CareerForm.resolveDirection("software", ["tech", "software"], "tech"),
    { value: "software", matched: true, requested: "software" },
  );
  assert.deepEqual(
    CareerForm.resolveDirection("future-role", ["tech", "software"], "tech"),
    { value: "tech", matched: false, requested: "future-role" },
  );
});

test("profile hydration restores every field and synchronizes a known direction", () => {
  const controls = {
    role: { value: "" },
    cities: { value: "" },
    salaryMin: { value: "" },
    salaryMax: { value: "" },
    skills: { value: "" },
    direction: {
      value: "tech",
      options: [{ value: "tech" }, { value: "software" }],
    },
    status: { textContent: "" },
  };
  const state = { careerProfile: "tech" };
  const result = CareerForm.hydrateProfile({
    career_direction: "software",
    target_role: "测试开发工程师",
    cities: ["杭州", "上海"],
    salary: { min: 15, max: 25 },
    confirmed_skills: ["Python", "Playwright"],
  }, controls, state);

  assert.equal(controls.role.value, "测试开发工程师");
  assert.equal(controls.cities.value, "杭州；上海");
  assert.equal(controls.salaryMin.value, 15);
  assert.equal(controls.salaryMax.value, 25);
  assert.equal(controls.skills.value, "Python；Playwright");
  assert.equal(controls.direction.value, "software");
  assert.equal(state.careerProfile, "software");
  assert.equal(result.direction.matched, true);
});

test("unknown stored direction stays visible without overwriting current selection", () => {
  const controls = {
    role: { value: "" }, cities: { value: "" }, salaryMin: { value: "" },
    salaryMax: { value: "" }, skills: { value: "" },
    direction: { value: "tech", options: [{ value: "tech" }] },
    status: { textContent: "" },
  };
  const state = { careerProfile: "tech" };
  const result = CareerForm.hydrateProfile({ career_direction: "future-role" }, controls, state);

  assert.equal(controls.direction.value, "tech");
  assert.equal(state.careerProfile, "tech");
  assert.match(controls.status.textContent, /future-role/);
  assert.equal(result.direction.matched, false);
});

test("profile load network errors stay visible and preserve current fields", async () => {
  const controls = {
    role: { value: "未保存岗位" }, cities: { value: "杭州" }, salaryMin: { value: "15" },
    salaryMax: { value: "25" }, skills: { value: "Python" },
    direction: { value: "tech", options: [{ value: "tech" }] },
    status: { textContent: "" },
    retry: { hidden: true },
  };
  const state = { careerProfile: "tech" };
  const result = await CareerForm.loadProfile({
    request: async () => { throw new Error("offline"); }, controls, state,
  });

  assert.equal(result.ok, false);
  assert.equal(controls.role.value, "未保存岗位");
  assert.equal(controls.cities.value, "杭州");
  assert.match(controls.status.textContent, /加载失败.*重试/);
  assert.equal(controls.retry.hidden, false);
});

test("an empty profile starts onboarding instead of displaying a load failure", async () => {
  const controls = {
    role: { value: "" }, cities: { value: "" }, salaryMin: { value: "" },
    salaryMax: { value: "" }, skills: { value: "" },
    direction: { value: "tech", options: [{ value: "tech" }] },
    status: { textContent: "" }, retry: { hidden: false },
  };
  const result = await CareerForm.loadProfile({
    request: async () => ({ success: true, data: null }), controls,
    state: { careerProfile: "tech" },
  });

  assert.equal(result.ok, true);
  assert.equal(result.empty, true);
  assert.equal(result.direction.matched, false);
  assert.match(controls.status.textContent, /还没有目标档案/);
  assert.equal(controls.retry.hidden, true);
});

test("profile save failure preserves inputs and success alone runs follow-up", async () => {
  const fields = { role: { value: "测试开发" }, cities: { value: "杭州" } };
  const status = { textContent: "" };
  let successes = 0;
  const failed = await CareerForm.saveProfile({
    request: async () => ({ success: false, message: "服务暂不可用" }),
    payload: { target_role: "测试开发" },
    status,
    onSuccess: () => { successes += 1; },
  });
  assert.equal(failed.ok, false);
  assert.equal(fields.role.value, "测试开发");
  assert.match(status.textContent, /服务暂不可用.*重试/);
  assert.equal(successes, 0);

  const saved = await CareerForm.saveProfile({
    request: async () => ({ success: true, data: { target_role: "测试开发" } }),
    payload: { target_role: "测试开发" }, status,
    onSuccess: () => { successes += 1; },
  });
  assert.equal(saved.ok, true);
  assert.equal(successes, 1);
  assert.match(status.textContent, /已保存/);
});

test("profile save remains successful when a follow-up refresh fails", async () => {
  const status = { textContent: "" };
  const result = await CareerForm.saveProfile({
    request: async () => ({ success: true, data: { target_role: "测试开发" } }),
    payload: {}, status,
    onSuccess: async () => { throw new Error("dashboard unavailable"); },
  });

  assert.equal(result.ok, true);
  assert.match(status.textContent, /已保存/);
  assert.equal(result.followupError.message, "dashboard unavailable");
});
