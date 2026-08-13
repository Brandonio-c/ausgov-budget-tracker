import { readFileSync } from "node:fs";
import path from "node:path";
import { ExplorerShell } from "@/components/ExplorerShell";

// Deliberately not at /explorers/[family] (the plan's suggested literal
// path): the five already-completed family pages
// (/explorers/contracts, /explorers/pbs, /explorers/grants,
// /explorers/act-invoices, /explorers/vic-output-performance) already
// occupy those exact static slugs, and Next.js always prefers a static
// route over a same-path dynamic one - a [family] route living directly
// under /explorers would be permanently unreachable for every currently
// registered family until item 6.3's migration removes those pages. This
// path lets the shell be exercised against every real, registered family
// today without touching the not-yet-migrated pages.

// This site is a static export (next.config.ts: output: "export"), which
// requires every dynamic route's possible params to be known at build
// time. Rather than hard-coding a parallel family-id list here (the
// thing item 6.2 is meant to avoid), this reads the same registry file
// the backend loads (config/explorers/families.yaml) and extracts each
// `id:` - there is exactly one file that can add or remove a family, so
// the two cannot drift. A narrow, dependency-free regex is used instead
// of pulling in a YAML parser dependency, since this file's `- id: <value>`
// shape is simple, stable, and fully under this repo's own control.
export function generateStaticParams(): Array<{ family: string }> {
  const registryPath = path.join(
    process.cwd(),
    "..",
    "..",
    "config",
    "explorers",
    "families.yaml",
  );
  const text = readFileSync(registryPath, "utf-8");
  const ids = [...text.matchAll(/^\s*-\s*id:\s*(\S+)\s*$/gm)].map((m) => m[1]);
  if (ids.length === 0) {
    throw new Error(`generateStaticParams: found no family ids in ${registryPath}`);
  }
  return ids.map((family) => ({ family }));
}

export default async function ExplorerFamilyPage({
  params,
}: {
  params: Promise<{ family: string }>;
}) {
  const { family } = await params;
  return <ExplorerShell familyId={family} />;
}
