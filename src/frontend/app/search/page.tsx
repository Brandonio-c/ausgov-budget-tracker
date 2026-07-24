"use client";

import { Suspense } from "react";
import SearchPageClient from "./SearchPageClient";

export default function SearchRoute() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen px-4 py-8 text-sm text-zinc-500">Loading search…</div>
      }
    >
      <SearchPageClient />
    </Suspense>
  );
}
