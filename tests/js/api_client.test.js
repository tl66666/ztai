const assert = require("node:assert/strict");
const test = require("node:test");

const ApiClient = require("../../static/js/api_client.js");

test("API client resolves one cross-platform backend origin for local and Cloudflare hosting", () => {
  assert.equal(ApiClient.resolveBaseUrl({
    location: { protocol: "https:" },
    runtimeConfig: { apiBaseUrl: "https://api.example.com/" },
  }), "https://api.example.com/api");
  assert.equal(ApiClient.resolveBaseUrl({
    location: { protocol: "https:" },
    runtimeConfig: {},
  }), "/api");
  assert.equal(ApiClient.resolveBaseUrl({
    location: { protocol: "file:" },
    runtimeConfig: {},
  }), "http://localhost:5000/api");
});


test("API client serializes JSON and preserves structured HTTP errors", async () => {
  const calls = [];
  const request = ApiClient.create({
    baseUrl: "/api",
    fetch: async (url, init) => {
      calls.push({ url, init });
      return {
        ok: false,
        status: 409,
        headers: { get: () => "application/json" },
        json: async () => ({ success: false, message: "conflict" }),
      };
    },
  });

  const result = await request("/profile", {
    method: "PUT",
    body: { target_role: "测试工程师" },
  });

  assert.deepEqual(calls, [{
    url: "/api/profile",
    init: {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_role: "测试工程师" }),
    },
  }]);
  assert.deepEqual(result, {
    success: false,
    message: "conflict",
    http_status: 409,
  });
});

test("API client exposes raw responses through the same configured transport", async () => {
  const calls = [];
  const response = { ok: true, blob: async () => Buffer.from("file") };
  const request = ApiClient.create({
    baseUrl: "https://api.example.com/api/",
    fetch: async (url, init) => {
      calls.push({ url, init });
      return response;
    },
  });

  const result = await request.raw("/exports/42");

  assert.equal(result, response);
  assert.deepEqual(calls, [{
    url: "https://api.example.com/api/exports/42",
    init: { method: "GET" },
  }]);
});

test("API client returns one stable error shape for transport failures", async () => {
  const request = ApiClient.create({
    baseUrl: "/api",
    fetch: async () => {
      throw new TypeError("Failed to fetch");
    },
  });

  const result = await request("/profile");

  assert.deepEqual(result, {
    success: false,
    message: "网络请求失败，请检查连接后重试。",
    error_code: "network_error",
  });
});

test("API client leaves binary and form payloads untouched", async () => {
  for (const body of [new Blob(["binary"]), new FormData(), "plain text"]) {
    let received;
    const request = ApiClient.create({
      baseUrl: "/api",
      fetch: async (_url, init) => {
        received = init;
        return {
          ok: true,
          status: 204,
          headers: { get: () => "" },
          text: async () => "",
        };
      },
    });

    await request("/upload", { method: "POST", body });

    assert.equal(received.body, body);
    assert.equal(received.headers, undefined);
  }
});

test("API client normalizes FastAPI details and empty responses", async () => {
  const responses = [
    {
      ok: false,
      status: 422,
      headers: { get: () => "application/json" },
      json: async () => ({ detail: "invalid profile" }),
    },
    {
      ok: true,
      status: 204,
      headers: { get: () => "" },
      text: async () => "",
    },
  ];
  const request = ApiClient.create({
    baseUrl: "/api",
    fetch: async () => responses.shift(),
  });

  assert.deepEqual(await request("/profile"), {
    success: false,
    detail: "invalid profile",
    message: "invalid profile",
    http_status: 422,
  });
  assert.deepEqual(await request("/profile", { method: "DELETE" }), {
    success: true,
  });
});
