import { describe, expect, it, vi } from "vitest";

import { createApiClient, resolveBaseUrl } from "./api-client";

describe("API client", () => {
  it("resolves local and Cloudflare origins consistently", () => {
    expect(resolveBaseUrl({
      location: { protocol: "https:" } as Location,
      runtimeConfig: { apiBaseUrl: "https://api.example.com/" },
    })).toBe("https://api.example.com/api");
    expect(resolveBaseUrl({
      location: { protocol: "file:" } as Location,
    })).toBe("http://localhost:5000/api");
  });

  it("serializes JSON and preserves structured errors", async () => {
    const transport = vi.fn(async () => new Response(
      JSON.stringify({ success: false, message: "conflict" }),
      { status: 409, headers: { "content-type": "application/json" } },
    ));
    const request = createApiClient({ baseUrl: "/api", fetch: transport });
    const result = await request("/profile", {
      method: "PUT",
      body: { target_role: "测试工程师" },
    });

    expect(transport).toHaveBeenCalledWith("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_role: "测试工程师" }),
    });
    expect(result).toEqual({
      success: false,
      message: "conflict",
      http_status: 409,
    });
  });

  it("returns one stable network error", async () => {
    const request = createApiClient({
      baseUrl: "/api",
      fetch: vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    });
    await expect(request("/profile")).resolves.toEqual({
      success: false,
      message: "网络请求失败，请检查连接后重试。",
      error_code: "network_error",
    });
  });
});
