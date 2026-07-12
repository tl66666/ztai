(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.CareerForm = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  function parseList(value) {
    const seen = new Set();
    return String(value || "")
      .split(/[,，、;；\n]/)
      .map((item) => item.trim())
      .filter((item) => {
        if (!item || seen.has(item)) return false;
        seen.add(item);
        return true;
      });
  }

  function serializeList(values) {
    return parseList(Array.isArray(values) ? values.join("；") : values).join("；");
  }

  function resolveDirection(requested, optionValues, current) {
    const normalized = String(requested || "").trim();
    const options = new Set((optionValues || []).map(String));
    const matched = Boolean(normalized && options.has(normalized));
    return {
      value: matched ? normalized : current,
      matched,
      requested: normalized,
    };
  }

  function hydrateProfile(profile, controls, state) {
    const direction = resolveDirection(
      profile.career_direction,
      Array.from(controls.direction?.options || [], (option) => option.value),
      controls.direction?.value || state.careerProfile,
    );
    controls.role.value = profile.target_role || "";
    controls.cities.value = serializeList(profile.cities || []);
    controls.salaryMin.value = profile.salary?.min ?? "";
    controls.salaryMax.value = profile.salary?.max ?? "";
    controls.skills.value = serializeList(profile.confirmed_skills || []);
    if (direction.matched) {
      controls.direction.value = direction.value;
      state.careerProfile = direction.value;
    }
    const role = profile.target_role || "未设置目标岗位";
    controls.status.textContent = direction.requested && !direction.matched
      ? `已载入目标档案：${role}（档案方向 ${direction.requested} 暂无可选项，保留当前方向）`
      : `已载入目标档案：${role}`;
    return { direction };
  }

  return {
    parseList,
    serializeList,
    resolveDirection,
    hydrateProfile,
  };
});
