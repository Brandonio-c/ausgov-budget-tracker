"use client";

import { Suspense } from "react";
import HomeClient from "./HomeClient";

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen px-4 py-8 text-sm text-zinc-500">Loading…</div>
      }
    >
      <HomeClient />
    </Suspense>
  );
}
