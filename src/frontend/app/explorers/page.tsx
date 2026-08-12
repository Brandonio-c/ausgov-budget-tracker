import Link from "next/link";

export default function ExplorersIndex() {
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
    </main>
  );
}
