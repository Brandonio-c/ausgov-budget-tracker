/** Ensure in-app paths keep a trailing slash before any query string. */
export function appHref(pathWithOptionalQuery: string): string {
  const raw = pathWithOptionalQuery || "/";
  const qIndex = raw.indexOf("?");
  const path = qIndex >= 0 ? raw.slice(0, qIndex) : raw;
  const query = qIndex >= 0 ? raw.slice(qIndex + 1) : "";
  let base = path || "/";
  if (!base.endsWith("/")) base += "/";
  return query ? `${base}?${query}` : base;
}

/**
 * Next.js basePath + trailingSlash can drop the slash on root (`/ausgov-budget-tracker?x`
 * instead of `/ausgov-budget-tracker/?x`). Force a hard navigation for root deep links.
 */
export function navigateApp(
  router: { push: (href: string) => void },
  pathWithOptionalQuery: string,
): void {
  const href = appHref(pathWithOptionalQuery);
  if (href === "/" || href.startsWith("/?")) {
    const base = (
      process.env.NEXT_PUBLIC_BASE_PATH || "/ausgov-budget-tracker"
    ).replace(/\/$/, "");
    const qs = href.includes("?") ? href.slice(href.indexOf("?")) : "";
    window.location.assign(`${base}/${qs}`);
    return;
  }
  router.push(href);
}

/** Render text that may contain «matched» markers from the search API. */
export function renderHighlighted(text: string): { __html: string } {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const html = escaped
    .replace(/«/g, '<mark class="rounded bg-amber-200/80 px-0.5 text-inherit dark:bg-amber-500/40">')
    .replace(/»/g, "</mark>");
  return { __html: html };
}
