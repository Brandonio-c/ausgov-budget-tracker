"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import GlobalSearchBar from "@/components/GlobalSearchBar";

const VIEWS = [
  { href: "/", label: "Breakdown" },
  { href: "/combined", label: "Combined" },
  { href: "/timeline", label: "Timeline" },
] as const;

const EXPLORERS = [
  { href: "/explorers/contracts", label: "Contracts explorer" },
  { href: "/explorers/gfs", label: "GFS explorer" },
  { href: "/legacy", label: "Phase 1 only" },
] as const;

function linkClass(active: boolean): string {
  return active
    ? "font-medium text-zinc-900 underline dark:text-zinc-50"
    : "text-zinc-600 underline hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-zinc-50";
}

export default function DashboardNav() {
  const pathname = usePathname();

  return (
    <div className="mt-3 space-y-3">
      <GlobalSearchBar />
      <nav className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <span className="flex flex-wrap gap-3">
          {VIEWS.map((view) => {
            const active =
              view.href === "/"
                ? pathname === "/"
                : pathname === view.href || pathname.startsWith(`${view.href}/`);
            return (
              <Link key={view.href} href={view.href} className={linkClass(active)}>
                {view.label}
              </Link>
            );
          })}
          <Link
            href="/search"
            className={linkClass(pathname === "/search" || pathname.startsWith("/search/"))}
          >
            Corpus
          </Link>
        </span>
        <span className="hidden text-zinc-300 sm:inline dark:text-zinc-600" aria-hidden>
          |
        </span>
        <span className="flex flex-wrap gap-3">
          {EXPLORERS.map((item) => (
            <Link key={item.href} href={item.href} className={linkClass(pathname === item.href)}>
              {item.label}
            </Link>
          ))}
        </span>
      </nav>
    </div>
  );
}
