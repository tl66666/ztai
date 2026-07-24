const assert = require("node:assert/strict");
const { test } = require("node:test");

test("Cloudflare worker proxies API requests and preserves Access identity", async () => {
  const worker = await import("../../frontend/cloudflare/worker.mjs");
  const request = new Request("https://ztai.kralai.tech/api/jobs?limit=10", {
    headers: { "Cf-Access-Jwt-Assertion": "signed-access-token" },
  });

  const upstream = worker.createUpstreamRequest(request);

  assert.equal(upstream.url, "https://api.ztai.kralai.tech/api/jobs?limit=10");
  assert.equal(upstream.headers.get("Cf-Access-Jwt-Assertion"), "signed-access-token");
});

test("Cloudflare worker leaves static requests with the Pages asset binding", async () => {
  const worker = (await import("../../frontend/cloudflare/worker.mjs")).default;
  const response = await worker.fetch(new Request("https://ztai.kralai.tech/css/style.css"), {
    ASSETS: { fetch: () => new Response("asset", { status: 200 }) },
  });

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "asset");
});
