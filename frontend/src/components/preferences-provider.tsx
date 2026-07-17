"use client";

import { useEffect, useSyncExternalStore } from "react";
import {
  DEFAULT_PREFERENCES,
  applyPreferences,
  loadPreferences,
  resolveTheme,
  savePreferences,
  type Preferences,
} from "@/lib/preferences";

// Module-level store. useSyncExternalStore reads it in an SSR-safe way: the
// server snapshot is the defaults, the client snapshot is the stored value, and
// React reconciles the two during hydration without a mismatch warning.
let current: Preferences = DEFAULT_PREFERENCES;
let initialized = false;
const listeners = new Set<() => void>();

function getSnapshot(): Preferences {
  if (!initialized && typeof window !== "undefined") {
    current = loadPreferences();
    initialized = true;
  }
  return current;
}

function getServerSnapshot(): Preferences {
  return DEFAULT_PREFERENCES;
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

function updatePreferences(patch: Partial<Preferences>): void {
  current = { ...current, ...patch };
  savePreferences(current);
  applyPreferences(current);
  listeners.forEach((l) => l());
}

export function usePreferences(): {
  prefs: Preferences;
  setPrefs: (patch: Partial<Preferences>) => void;
} {
  const prefs = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return { prefs, setPrefs: updatePreferences };
}

/** Tracks the effective dark state by observing the `dark` class on <html>.
 *  Works regardless of how it changed (manual toggle or live OS preference),
 *  which is what non-token consumers like the Leaflet tile layer need. */
export function useIsDark(): boolean {
  return useSyncExternalStore(
    (cb) => {
      const obs = new MutationObserver(cb);
      obs.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["class"],
      });
      return () => obs.disconnect();
    },
    () => document.documentElement.classList.contains("dark"),
    () => false,
  );
}

/** Mounts once near the root: keeps the DOM in sync with the live OS theme when
 *  the theme is set to "system". Pure DOM side-effect, no React state. */
export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const { prefs } = usePreferences();

  useEffect(() => {
    if (prefs.theme !== "system") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () =>
      document.documentElement.classList.toggle(
        "dark",
        resolveTheme("system") === "dark",
      );
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [prefs.theme]);

  return <>{children}</>;
}
