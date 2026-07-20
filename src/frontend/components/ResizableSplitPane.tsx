"use client";

import { KeyboardEvent, PointerEvent, ReactNode, useRef, useState } from "react";

interface Props {
  left: ReactNode;
  right: ReactNode;
}

const DEFAULT_LEFT_SHARE = 50;
const MIN_LEFT_SHARE = 40;
const DIVIDER_WIDTH_PX = 20;
const MIN_RIGHT_WIDTH_PX = 300;

export default function ResizableSplitPane({ left, right }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [leftShare, setLeftShare] = useState(DEFAULT_LEFT_SHARE);

  function clampShare(proposedShare: number) {
    const width = containerRef.current?.getBoundingClientRect().width ?? 0;
    const availableWidth = Math.max(1, width - DIVIDER_WIDTH_PX);
    const maxLeftShare = Math.max(
      MIN_LEFT_SHARE,
      ((availableWidth - MIN_RIGHT_WIDTH_PX) / availableWidth) * 100,
    );
    return Math.min(maxLeftShare, Math.max(MIN_LEFT_SHARE, proposedShare));
  }

  function resizeFromPointer(clientX: number) {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const availableWidth = Math.max(1, rect.width - DIVIDER_WIDTH_PX);
    const proposedShare = ((clientX - rect.left) / availableWidth) * 100;
    setLeftShare(clampShare(proposedShare));
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    resizeFromPointer(event.clientX);
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      resizeFromPointer(event.clientX);
    }
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setLeftShare((share) => clampShare(share - 2));
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      setLeftShare((share) => clampShare(share + 2));
    } else if (event.key === "Home") {
      event.preventDefault();
      setLeftShare(DEFAULT_LEFT_SHARE);
    }
  }

  return (
    <div ref={containerRef} className="grid items-start gap-5 lg:flex lg:items-stretch lg:gap-0">
      <div
        className="min-w-0 lg:sticky lg:top-[max(1.5rem,calc(50vh-17rem))] lg:self-start lg:shrink-0"
        style={{ flexBasis: `calc((100% - 1.25rem) * ${leftShare / 100})` }}
      >
        {left}
      </div>

      <div
        role="separator"
        aria-label="Resize chart and source viewer"
        aria-orientation="vertical"
        aria-valuemin={MIN_LEFT_SHARE}
        aria-valuemax={75}
        aria-valuenow={Math.round(leftShare)}
        tabIndex={0}
        title="Drag to resize; use left and right arrow keys for fine adjustment"
        onDoubleClick={() => setLeftShare(DEFAULT_LEFT_SHARE)}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onKeyDown={handleKeyDown}
        className="group hidden w-5 shrink-0 touch-none cursor-col-resize items-stretch justify-center outline-none lg:flex"
      >
        <div className="relative w-px bg-black/15 transition-colors group-hover:bg-blue-500 group-focus:bg-blue-500 dark:bg-white/15">
          <span className="absolute left-1/2 top-1/2 flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-black/15 bg-white text-sm font-semibold text-zinc-500 shadow-sm group-hover:border-blue-500 group-hover:text-blue-600 group-focus:border-blue-500 group-focus:text-blue-600 dark:border-white/20 dark:bg-zinc-800 dark:text-zinc-300">
            ↔
          </span>
        </div>
      </div>

      <div className="min-w-0 lg:min-w-[300px] lg:flex-1 xl:min-w-[320px]">{right}</div>
    </div>
  );
}
