"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { explorerApi, ExplorerFamilySummary } from "@/lib/explorerApi";

export default function ExplorersIndex() {
  const [families, setFamilies] = useState<ExplorerFamilySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    explorerApi
      .list()
      .then((body) => setFamilies(body.families))
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">Explorers (preview)</h1>
      <p className="mt-2 text-sm opacity-80">
        New citation-bearing views backed by facts.db / API v2. Default home
        page remains the Phase 1 pie until M12 cutover.
      </p>
      <ul className="mt-6 list-disc space-y-2 pl-6">
        <li>
          <Link href="/explorers/contracts">Contracts explorer</Link>
        </li>
        <li>
          <Link href="/explorers/grants">Grants explorer</Link>
        </li>
        <li>
          <Link href="/explorers/act-invoices">ACT notifiable invoices</Link>
        </li>
        <li>
          <Link href="/explorers/pbs">PBS explorer</Link>
        </li>
        <li>
          <Link href="/explorers/gfs">GFS / jurisdiction explorer</Link>
        </li>
        <li>
          <Link href="/explorers/mfs">Monthly Financial Statements (MFS) explorer</Link>
        </li>
        <li>
          <Link href="/explorers/vic-output-performance">
            Victoria — Output Performance
          </Link>
        </li>
        <li>
          <Link href="/">Legacy default dashboard</Link>
        </li>
      </ul>

      <h2 className="mt-8 text-lg font-semibold">
        Generic explorer shell (item 6.2, preview)
      </h2>
      <p className="mt-2 text-sm opacity-80">
        A single registry-driven shell (<code>ExplorerShell.tsx</code>) rendering every
        family below through one implementation, reading its scope, estimate statuses and
        semantic disclosure from the family registry (<code>/v2/explorers</code>) rather
        than per-page hard-coded constants. Not yet the primary entry point for these
        families - the dedicated pages linked above remain the migrated, exit-gate-verified
        experience until item 6.3 moves them onto this shell.
      </p>
      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      {families === null && !error ? (
        <p className="mt-2 text-sm text-zinc-500">Loading registry…</p>
      ) : null}
      {families ? (
        <ul className="mt-4 list-disc space-y-2 pl-6">
          {families.map((f) => (
            <li key={f.id}>
              <Link href={`/explorers/family/${f.id}`}>{f.label}</Link>
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  );
}
