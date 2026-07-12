const assert = require("node:assert/strict");
const test = require("node:test");

const CareerForm = require("../../static/js/career_form.js");

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
