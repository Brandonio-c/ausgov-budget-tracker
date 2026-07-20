// Serves the static Next.js export (./out) under vibefactory.app/ausgov-budget-tracker/*.
// Same path-stripping shape as dance-machine's asset-worker.js.
const ROUTE_PREFIX = "/ausgov-budget-tracker";

function stripRoutePrefix(url) {
  if (url.pathname === ROUTE_PREFIX) {
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
    const assetUrl = stripRoutePrefix(new URL(request.url));
    return env.ASSETS.fetch(new Request(assetUrl, request));
  },
};
