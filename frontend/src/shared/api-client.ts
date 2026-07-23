export type ApiPayload = Record<string, unknown>;

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | ApiPayload | unknown[] | null;
};

export type ApiResponse = ApiPayload & {
  success?: boolean;
  message?: string;
  error_code?: string;
  http_status?: number;
};

export interface ApiRequest {
  (path: string, options?: ApiRequestOptions): Promise<any>;
  raw(path: string, options?: RequestInit): Promise<Response>;
}

export interface ApiClientOptions {
  baseUrl?: string;
  fetch?: typeof fetch;
}

export interface BaseUrlOptions {
  location?: Pick<Location, "protocol">;
  runtimeConfig?: { apiBaseUrl?: string };
}

export function resolveBaseUrl(options: BaseUrlOptions = {}): string {
  const location = options.location || { protocol: "" };
  const configured = String(options.runtimeConfig?.apiBaseUrl || "").replace(/\/+$/, "");
  if (configured) return configured.endsWith("/api") ? configured : `${configured}/api`;
  return location.protocol === "file:" ? "http://localhost:5000/api" : "/api";
}

function isJsonBody(body: unknown): body is ApiPayload | unknown[] {
  if (Array.isArray(body)) return true;
  if (!body || typeof body !== "object") return false;
  return Object.getPrototypeOf(body) === Object.prototype;
}

export function createApiClient(options: ApiClientOptions = {}): ApiRequest {
  const baseUrl = String(options.baseUrl || "").replace(/\/+$/, "");
  const transport = options.fetch || globalThis.fetch?.bind(globalThis);
  if (!transport) throw new Error("fetch implementation is required");

  function requestUrl(path: string): string {
    return `${baseUrl}/${String(path || "").replace(/^\/+/, "")}`;
  }

  function requestInit(options: ApiRequestOptions = {}): RequestInit {
    const init: ApiRequestOptions = { method: "GET", ...options };
    if (isJsonBody(init.body)) {
      init.headers = { "Content-Type": "application/json", ...(init.headers || {}) };
      init.body = JSON.stringify(init.body);
    }
    return init as RequestInit;
  }

  async function raw(path: string, options: ApiRequestOptions = {}): Promise<Response> {
    return transport(requestUrl(path), requestInit(options));
  }

  const request = async (path: string, options: ApiRequestOptions = {}): Promise<any> => {
    let response: Response;
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
      let payload: any;
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
  };

  return Object.assign(request, { raw });
}
