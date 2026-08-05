// Serves the static Next.js export (./out) under vibefactory.app/ausgov-budget-tracker/*.
// Same path-stripping shape as dance-machine's asset-worker.js.
const ROUTE_PREFIX = "/ausgov-budget-tracker";

function stripRoutePrefix(url) {
  if (url.pathname === ROUTE_PREFIX || url.pathname === `${ROUTE_PREFIX}/`) {
    url.pathname = "/";
    return url;
  }
  if (url.pathname.startsWith(`${ROUTE_PREFIX}/`)) {
    url.pathname = url.pathname.slice(ROUTE_PREFIX.length) || "/";
  }
  return url;
}

export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);
    // Canonicalize bare /ausgov-budget-tracker(?…) → /ausgov-budget-tracker/(?…)
    // Query string is preserved by URL.toString().
    if (incoming.pathname === ROUTE_PREFIX) {
      incoming.pathname = `${ROUTE_PREFIX}/`;
      return Response.redirect(incoming.toString(), 308);
    }
    const assetUrl = stripRoutePrefix(new URL(request.url));
    // Static export uses trailingSlash: true — map /foo → /foo/ for asset lookup
    // when the request has no file extension (soft-nav / deep-link edge cases).
    if (
      assetUrl.pathname !== "/" &&
      !assetUrl.pathname.endsWith("/") &&
      !assetUrl.pathname.split("/").pop()?.includes(".")
    ) {
      assetUrl.pathname = `${assetUrl.pathname}/`;
    }
    const resp = await env.ASSETS.fetch(new Request(assetUrl, request));
    // The Assets binding's own Cache-Control ("public, max-age=0,
    // must-revalidate") was observed NOT preventing stale HTML from being
    // served for nested routes after a redeploy (confirmed via repeated,
    // consistent real-browser checks against the live domain - see
    // ops/reports/cloudflare-route-triage-*.md). must-revalidate still
    // permits a cache to store the response; no-store forbids it outright,
    // removing any ambiguity for HTML documents specifically (JS/CSS/font
    // chunks are content-hashed and safe to cache normally, so this only
    // touches text/html responses).
    const contentType = resp.headers.get("content-type") || "";
    if (contentType.includes("text/html")) {
      const headers = new Headers(resp.headers);
      headers.set("Cache-Control", "no-store");
      return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers });
    }
    return resp;
  },
};
