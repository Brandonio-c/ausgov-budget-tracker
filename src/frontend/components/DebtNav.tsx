"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { appHref } from "@/lib/searchDisplay";

/** Deep links into debt-capable surfaces (mode=debt where applicable). */
const DEBT_LINKS = [
  { href: "/?mode=debt", label: "Breakdown", match: "/" },
  { href: "/combined?mode=debt", label: "Combined", match: "/combined" },
  { href: "/timeline?mode=debt", label: "Timeline", match: "/timeline" },
  { href: "/search?mode=debt&tab=advanced", label: "Corpus", match: "/search" },
  { href: "/explorers/contracts", label: "Contracts explorer", match: "/explorers/contracts" },
  { href: "/explorers/gfs?view=liabilities", label: "GFS explorer", match: "/explorers/gfs" },
  { href: "/legacy", label: "Phase 1 only", match: "/legacy" },
] as const;

function linkClass(active: boolean): string {
  return active
    ? "font-medium text-zinc-900 underline dark:text-zinc-50"
    : "text-zinc-600 underline hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-zinc-50";
}

export default function DebtNav() {
  const pathname = usePathname();

  return (
    <nav
      className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm"
      aria-label="Debt views"
    >
      <span className="flex flex-wrap gap-3">
        {DEBT_LINKS.slice(0, 4).map((view) => {
          const active =
            view.match === "/"
              ? pathname === "/" || pathname === ""
              : pathname === view.match || pathname.startsWith(`${view.match}/`);
          return (
            <Link key={view.href} href={appHref(view.href)} className={linkClass(active)}>
              {view.label}
            </Link>
          );
        })}
      </span>
      <span className="hidden text-zinc-300 sm:inline dark:text-zinc-600" aria-hidden>
        |
      </span>
      <span className="flex flex-wrap gap-3">
        {DEBT_LINKS.slice(4).map((item) => (
          <Link
            key={item.href}
            href={appHref(item.href)}
            className={linkClass(
              pathname === item.match || pathname.startsWith(`${item.match}/`),
            )}
          >
            {item.label}
          </Link>
        ))}
      </span>
    </nav>
  );
}
