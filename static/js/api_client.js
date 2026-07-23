(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.JobHunterApiClient = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function create(options = {}) {
    const baseUrl = String(options.baseUrl || "").replace(/\/+$/, "");
    const transport = options.fetch
      || (typeof fetch === "function" ? fetch.bind(globalThis) : null);
    if (!transport) throw new Error("fetch implementation is required");

    function requestUrl(path) {
      return `${baseUrl}/${String(path || "").replace(/^\/+/, "")}`;
    }

    function requestInit(options = {}) {
      const init = { method: "GET", ...options };
      const bodyPrototype = init.body && typeof init.body === "object"
        ? Object.getPrototypeOf(init.body)
        : null;
      const isJsonBody = Array.isArray(init.body) || bodyPrototype === Object.prototype;
      if (isJsonBody) {
        init.headers = { "Content-Type": "application/json", ...(init.headers || {}) };
        init.body = JSON.stringify(init.body);
      }
      return init;
    }

    async function raw(path, options = {}) {
      return transport(requestUrl(path), requestInit(options));
    }

    async function request(path, options = {}) {
      let response;
      try {
        response = await raw(path, options);
      } catch {
        return {
          success: false,
          message: "网络请求失败，请检查连接后重试。",
          error_code: "network_error",
        };
      }
      if (response.status === 204) return { success: true };
      const type = response.headers.get("content-type") || "";
      if (type.includes("application/json")) {
        let payload;
        try {
          payload = await response.json();
        } catch {
          return {
            success: false,
            message: "服务器返回了无法解析的数据。",
            error_code: "invalid_response",
            http_status: response.status,
          };
        }
        if (response.ok || !payload || typeof payload !== "object") return payload;
        const detail = payload.detail;
        const detailMessage = typeof detail === "string"
          ? detail
          : (Array.isArray(detail) && detail[0]?.msg ? detail[0].msg : "");
        return {
          success: false,
          ...payload,
          message: payload.message || detailMessage || "请求处理失败。",
          http_status: response.status,
        };
      }
      const content = await response.text();
      const payload = {
        success: response.ok,
        content,
        ...(response.ok ? {} : { message: content || "请求处理失败。" }),
      };
      return response.ok ? payload : { ...payload, http_status: response.status };
    }

    request.raw = raw;
    return request;
  }

  return { create };
});
