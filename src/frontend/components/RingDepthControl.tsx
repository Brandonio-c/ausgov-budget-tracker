"use client";

interface Props {
  depth: number;
  maxDepth: number;
  onChange: (depth: number) => void;
  safeDepth?: number;
}

/** Depth stepper: − / value / + up to the tree’s available depth (no hard cap at 3). */
export default function RingDepthControl({
  depth,
  maxDepth,
  onChange,
  safeDepth = maxDepth,
}: Props) {
  const max = Math.max(1, maxDepth);
  const current = Math.min(Math.max(1, depth), max);

  function set(next: number) {
    onChange(Math.min(max, Math.max(1, next)));
  }

  return (
    <div
      className="flex overflow-hidden rounded-md border border-black/10 dark:border-white/10"
      role="group"
      aria-label="Ring depth"
    >
      <span className="px-2 py-2 text-xs text-zinc-500 dark:text-zinc-400">Safe levels</span>
      <button
        type="button"
        aria-label="Fewer rings"
        disabled={current <= 1}
        onClick={() => set(current - 1)}
        className="px-3 py-2 text-sm font-medium bg-white text-zinc-600 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
      >
        −
      </button>
      <input
        type="number"
        min={1}
        max={max}
        value={current}
        aria-label="Ring depth"
        onChange={(e) => {
          const n = Number(e.target.value);
          if (Number.isFinite(n)) set(n);
        }}
        className="w-12 border-x border-black/10 bg-zinc-900 px-1 py-2 text-center text-sm font-medium text-white dark:border-white/10 dark:bg-zinc-50 dark:text-zinc-900"
      />
      <button
        type="button"
        aria-label="More rings"
        disabled={current >= max}
        onClick={() => set(current + 1)}
        className="px-3 py-2 text-sm font-medium bg-white text-zinc-600 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
      >
        +
      </button>
      <span className="px-2 py-2 text-xs text-zinc-500 dark:text-zinc-400">
        of {max} · default {Math.min(max, Math.max(1, safeDepth))}
      </span>
      {current < max ? (
        <button
          type="button"
          onClick={() => set(max)}
          className="border-l border-black/10 bg-white px-3 py-2 text-xs font-medium text-blue-700 hover:bg-blue-50 dark:border-white/10 dark:bg-zinc-900 dark:text-blue-300 dark:hover:bg-zinc-800"
        >
          Show maximum
        </button>
      ) : null}
    </div>
  );
}
