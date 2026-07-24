const API_ORIGIN = "https://api.ztai.kralai.tech";

export function isApiRequest(request) {
  return new URL(request.url).pathname.startsWith("/api/");
}

export function createUpstreamRequest(request) {
  const incoming = new URL(request.url);
  const upstream = new URL(`${incoming.pathname}${incoming.search}`, API_ORIGIN);
  return new Request(upstream, request);
}

export default {
  async fetch(request, env) {
    if (isApiRequest(request)) {
      return fetch(createUpstreamRequest(request));
    }
    return env.ASSETS.fetch(request);
  },
};
