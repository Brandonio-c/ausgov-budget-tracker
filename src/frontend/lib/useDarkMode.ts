import { useSyncExternalStore } from "react";

function subscribe(listener: () => void) {
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  mediaQuery.addEventListener("change", listener);
  return () => mediaQuery.removeEventListener("change", listener);
}

function getSnapshot() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Tracks the OS color-scheme preference so canvas-rendered charts (which
 *  can't read CSS custom properties) get the right hex values. */
export function useDarkMode(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
