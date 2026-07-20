// Plain reverse-proxy Worker in front of the self-hosted FastAPI origin.
//
// Deliberately smaller than dance-machine's control-plane Worker: this API
// is stateless and fully public (no auth, no sessions, no secrets anywhere
// in this project — every row it serves is already public government data),
// so there's nothing here that needs to run at the edge — no Durable
// Objects, no KV, no shared-secret origin check. The Worker exists only to
// give the backend a stable vibefactory.app hostname in front of the
// tunneled self-hosted origin.

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "OPTIONS") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    const incoming = new URL(request.url);
    const originUrl = new URL(incoming.pathname + incoming.search, env.ORIGIN_BASE_URL);

    return fetch(new Request(originUrl, request));
  },
};
