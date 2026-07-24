"use client";

import {
  createContext,
  useContext,
  KeyboardEvent,
  PointerEvent,
  ReactNode,
  useMemo,
  useRef,
  useState,
} from "react";

interface Props {
  left: ReactNode;
  right: ReactNode;
  leftLabel?: string;
  rightLabel?: string;
}

type CollapseSide = "none" | "left" | "right";

type SplitLayout = {
  collapse: CollapseSide;
  /** Chart pane is fullscreen (document minimized). */
  chartMaximized: boolean;
  /** Document pane is fullscreen (chart minimized). */
  viewerMaximized: boolean;
};

const SplitPaneLayoutContext = createContext<SplitLayout>({
  collapse: "none",
  chartMaximized: false,
  viewerMaximized: false,
});

export function useSplitPaneLayout(): SplitLayout {
  return useContext(SplitPaneLayoutContext);
}

const DEFAULT_LEFT_SHARE = 50;
const MIN_LEFT_SHARE = 28;
const MAX_LEFT_SHARE = 78;
const DIVIDER_WIDTH_PX = 20;
const MIN_RIGHT_WIDTH_PX = 280;
const COLLAPSE_THRESHOLD = 18;
const RAIL_CLASS =
  "flex w-9 shrink-0 flex-col items-center justify-center gap-2 self-stretch rounded-lg border border-black/10 bg-white py-3 dark:border-white/10 dark:bg-zinc-900";
const BTN_CLASS =
  "flex h-7 w-7 items-center justify-center rounded-full border border-black/15 bg-white text-xs font-semibold text-zinc-500 shadow-sm hover:border-blue-500 hover:text-blue-600 dark:border-white/20 dark:bg-zinc-800 dark:text-zinc-300";

function PaneControls({
  side,
  label,
  otherLabel,
  onMinimize,
  onMaximize,
}: {
  side: "left" | "right";
  label: string;
  otherLabel: string;
  onMinimize: () => void;
  onMaximize: () => void;
}) {
  const position =
    side === "left"
      ? "absolute right-2 top-3 z-20 hidden lg:flex"
      : "absolute left-2 top-3 z-20 hidden lg:flex";

  return (
    <div className={`${position} gap-1`} role="group" aria-label={`${label} layout`}>
      <button
        type="button"
        className={BTN_CLASS}
        aria-label={`Minimize ${label}`}
        title={`Minimize ${label}`}
        onClick={onMinimize}
      >
        {side === "left" ? "‹" : "›"}
      </button>
      <button
        type="button"
        className={BTN_CLASS}
        aria-label={`Maximize ${label} (hide ${otherLabel})`}
        title={`Maximize ${label}`}
        onClick={onMaximize}
      >
        ⛶
      </button>
    </div>
  );
}

export default function ResizableSplitPane({
  left,
  right,
  leftLabel = "Chart",
  rightLabel = "Document viewer",
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [leftShare, setLeftShare] = useState(DEFAULT_LEFT_SHARE);
  const [collapse, setCollapse] = useState<CollapseSide>("none");
  const restoreShare = useRef(DEFAULT_LEFT_SHARE);

  const layout = useMemo<SplitLayout>(
    () => ({
      collapse,
      chartMaximized: collapse === "right",
      viewerMaximized: collapse === "left",
    }),
    [collapse],
  );

  function clampShare(proposedShare: number) {
    const width = containerRef.current?.getBoundingClientRect().width ?? 0;
    const availableWidth = Math.max(1, width - DIVIDER_WIDTH_PX);
    const maxLeftShare = Math.min(
      MAX_LEFT_SHARE,
      Math.max(
        MIN_LEFT_SHARE,
        ((availableWidth - MIN_RIGHT_WIDTH_PX) / availableWidth) * 100,
      ),
    );
    return Math.min(maxLeftShare, Math.max(MIN_LEFT_SHARE, proposedShare));
  }

  function resizeFromPointer(clientX: number) {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const availableWidth = Math.max(1, rect.width - DIVIDER_WIDTH_PX);
    const proposedShare = ((clientX - rect.left) / availableWidth) * 100;

    if (proposedShare < COLLAPSE_THRESHOLD) {
      if (collapse !== "left") {
        restoreShare.current = leftShare;
        setCollapse("left");
      }
      return;
    }
    if (proposedShare > 100 - COLLAPSE_THRESHOLD) {
      if (collapse !== "right") {
        restoreShare.current = leftShare;
        setCollapse("right");
      }
      return;
    }

    if (collapse !== "none") setCollapse("none");
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

  function expandBoth(share = restoreShare.current) {
    setCollapse("none");
    setLeftShare(clampShare(share));
  }

  function collapseLeft() {
    restoreShare.current = leftShare;
    setCollapse("left");
  }

  function collapseRight() {
    restoreShare.current = leftShare;
    setCollapse("right");
  }

  function maximizeLeft() {
    restoreShare.current = leftShare;
    setCollapse("right");
  }

  function maximizeRight() {
    restoreShare.current = leftShare;
    setCollapse("left");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      if (collapse === "right") {
        expandBoth();
        return;
      }
      setLeftShare((share) => {
        const next = share - 3;
        if (next < COLLAPSE_THRESHOLD) {
          restoreShare.current = share;
          setCollapse("left");
          return share;
        }
        return clampShare(next);
      });
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      if (collapse === "left") {
        expandBoth();
        return;
      }
      setLeftShare((share) => {
        const next = share + 3;
        if (next > 100 - COLLAPSE_THRESHOLD) {
          restoreShare.current = share;
          setCollapse("right");
          return share;
        }
        return clampShare(next);
      });
    } else if (event.key === "Home") {
      event.preventDefault();
      expandBoth(DEFAULT_LEFT_SHARE);
    } else if (event.key === "[") {
      event.preventDefault();
      collapseLeft();
    } else if (event.key === "]") {
      event.preventDefault();
      collapseRight();
    } else if (event.key === "{") {
      event.preventDefault();
      maximizeLeft();
    } else if (event.key === "}") {
      event.preventDefault();
      maximizeRight();
    }
  }

  let body: ReactNode;

  if (collapse === "left") {
    body = (
      <div ref={containerRef} className="flex min-h-[calc(100dvh-8rem)] items-stretch gap-2">
        <button
          type="button"
          className={RAIL_CLASS}
          aria-label={`Restore split (show ${leftLabel})`}
          title={`Show ${leftLabel}`}
          onClick={() => expandBoth()}
        >
          <span className="text-lg font-semibold text-zinc-500 dark:text-zinc-300" aria-hidden>
            ›
          </span>
          <span
            className="text-[10px] font-medium uppercase tracking-wide text-zinc-400"
            style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
          >
            {leftLabel}
          </span>
        </button>
        <div className="relative min-h-full min-w-0 flex-1">
          {right}
          <button
            type="button"
            className={`${BTN_CLASS} absolute right-2 top-3 z-20 hidden lg:flex`}
            aria-label="Restore split view"
            title="Restore split view"
            onClick={() => expandBoth()}
          >
            ⧉
          </button>
        </div>
      </div>
    );
  } else if (collapse === "right") {
    body = (
      <div ref={containerRef} className="flex min-h-[calc(100dvh-8rem)] items-stretch gap-2">
        <div
          className="relative flex min-h-[calc(100dvh-8rem)] min-w-0 flex-1 flex-col"
          data-chart-maximized="true"
        >
          <div className="flex min-h-0 flex-1 flex-col [&_section]:flex [&_section]:min-h-[calc(100dvh-9rem)] [&_section]:flex-col [&_[data-chart-panel]]:min-h-0 [&_[data-chart-panel]]:flex-1">
            {left}
          </div>
          <button
            type="button"
            className={`${BTN_CLASS} absolute right-2 top-3 z-20 hidden lg:flex`}
            aria-label="Restore split view"
            title="Restore split view"
            onClick={() => expandBoth()}
          >
            ⧉
          </button>
        </div>
        <button
          type="button"
          className={RAIL_CLASS}
          aria-label={`Restore split (show ${rightLabel})`}
          title={`Show ${rightLabel}`}
          onClick={() => expandBoth()}
        >
          <span className="text-lg font-semibold text-zinc-500 dark:text-zinc-300" aria-hidden>
            ‹
          </span>
          <span
            className="text-[10px] font-medium uppercase tracking-wide text-zinc-400"
            style={{ writingMode: "vertical-rl" }}
          >
            {rightLabel}
          </span>
        </button>
      </div>
    );
  } else {
    body = (
      <div ref={containerRef} className="grid items-start gap-5 lg:flex lg:items-stretch lg:gap-0">
        <div
          className="relative min-w-0 lg:sticky lg:top-[max(1.5rem,calc(50vh-17rem))] lg:self-start lg:shrink-0"
          style={{ flexBasis: `calc((100% - 1.25rem) * ${leftShare / 100})` }}
        >
          {left}
          <PaneControls
            side="left"
            label={leftLabel}
            otherLabel={rightLabel}
            onMinimize={collapseLeft}
            onMaximize={maximizeLeft}
          />
        </div>

        <div
          role="separator"
          aria-label="Resize, minimize, or maximize chart and document viewer"
          aria-orientation="vertical"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(leftShare)}
          tabIndex={0}
          title="Drag to resize · ‹/› minimize · ⛶ maximize · Home restore split"
          onDoubleClick={() => expandBoth(DEFAULT_LEFT_SHARE)}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onKeyDown={handleKeyDown}
          className="group relative hidden w-5 shrink-0 touch-none cursor-col-resize items-stretch justify-center outline-none lg:flex"
        >
          <div className="relative w-px bg-black/15 transition-colors group-hover:bg-blue-500 group-focus:bg-blue-500 dark:bg-white/15">
            <span className="absolute left-1/2 top-1/2 flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-black/15 bg-white text-sm font-semibold text-zinc-500 shadow-sm group-hover:border-blue-500 group-hover:text-blue-600 group-focus:border-blue-500 group-focus:text-blue-600 dark:border-white/20 dark:bg-zinc-800 dark:text-zinc-300">
              ↔
            </span>
          </div>
        </div>

        <div className="relative min-w-0 lg:min-w-[280px] lg:flex-1 xl:min-w-[300px]">
          {right}
          <PaneControls
            side="right"
            label={rightLabel}
            otherLabel={leftLabel}
            onMinimize={collapseRight}
            onMaximize={maximizeRight}
          />
        </div>

        <div className="col-span-full flex flex-wrap gap-2 lg:hidden">
          <button
            type="button"
            className="rounded-md border border-black/10 px-3 py-1.5 text-xs font-medium text-zinc-600 dark:border-white/10 dark:text-zinc-300"
            onClick={collapseLeft}
          >
            Minimize {leftLabel}
          </button>
          <button
            type="button"
            className="rounded-md border border-black/10 px-3 py-1.5 text-xs font-medium text-zinc-600 dark:border-white/10 dark:text-zinc-300"
            onClick={maximizeLeft}
          >
            Maximize {leftLabel}
          </button>
          <button
            type="button"
            className="rounded-md border border-black/10 px-3 py-1.5 text-xs font-medium text-zinc-600 dark:border-white/10 dark:text-zinc-300"
            onClick={collapseRight}
          >
            Minimize {rightLabel}
          </button>
          <button
            type="button"
            className="rounded-md border border-black/10 px-3 py-1.5 text-xs font-medium text-zinc-600 dark:border-white/10 dark:text-zinc-300"
            onClick={maximizeRight}
          >
            Maximize {rightLabel}
          </button>
        </div>
      </div>
    );
  }

  return (
    <SplitPaneLayoutContext.Provider value={layout}>{body}</SplitPaneLayoutContext.Provider>
  );
}
