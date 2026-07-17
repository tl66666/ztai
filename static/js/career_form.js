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

  async function loadProfile({ request, controls, state }) {
    if (controls.retry) controls.retry.hidden = true;
    try {
      const response = await request();
      if (!response?.success) {
        const message = response?.message || "目标档案加载失败";
        controls.status.textContent = `${message}，请重试。当前填写内容已保留。`;
        if (controls.retry) controls.retry.hidden = false;
        return { ok: false, response };
      }
      if (!response.data) {
        controls.status.textContent = "还没有目标档案，先填写目标岗位，Agent 才能给出更贴合的建议。";
        if (controls.retry) controls.retry.hidden = true;
        return {
          ok: true,
          empty: true,
          response,
          direction: {
            value: controls.direction?.value || state.careerProfile || "",
            matched: false,
            requested: "",
          },
        };
      }
      return { ok: true, response, ...hydrateProfile(response.data, controls, state) };
    } catch (error) {
      controls.status.textContent = "目标档案加载失败，请重试。当前填写内容已保留。";
      if (controls.retry) controls.retry.hidden = false;
      return { ok: false, error };
    }
  }

  async function saveProfile({ request, payload, status, onSuccess = () => {} }) {
    let response;
    try {
      response = await request(payload);
    } catch (error) {
      status.textContent = "目标档案保存失败，请重试。表单内容已保留。";
      return { ok: false, error };
    }
    if (!response?.success || !response.data) {
      const message = response?.message || "目标档案保存失败";
      status.textContent = `${message}，请重试。表单内容已保留。`;
      return { ok: false, response };
    }
    status.textContent = `目标档案已保存：${response.data.target_role || "未设置目标岗位"}`;
    try {
      await onSuccess(response.data);
      return { ok: true, response };
    } catch (followupError) {
      return { ok: true, response, followupError };
    }
  }

  return {
    parseList,
    serializeList,
    resolveDirection,
    hydrateProfile,
    loadProfile,
    saveProfile,
  };
});
