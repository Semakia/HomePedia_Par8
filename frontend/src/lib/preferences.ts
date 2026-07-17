// User preferences — single source of truth for the settings page (/parametres).
// Persisted to localStorage and applied to <html> (dark class + data-attributes)
// so the whole token-based UI can react. See preferences-provider.tsx.

import { COLOR_MODES, type ColorMode } from "./map-modes";

export type Theme = "light" | "dark" | "system";
export type Density = "comfortable" | "compact";

export type Preferences = {
  theme: Theme;
  density: Density;
  showBadge: boolean;
  mapColorMode: ColorMode;
  mapShowGares: boolean;
};

export const DEFAULT_PREFERENCES: Preferences = {
  theme: "system",
  density: "comfortable",
  showBadge: true,
  mapColorMode: "score",
  mapShowGares: false,
};

export const STORAGE_KEY = "homepedia:prefs";

export function loadPreferences(): Preferences {
  if (typeof window === "undefined") return DEFAULT_PREFERENCES;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFERENCES;
    const merged = {
      ...DEFAULT_PREFERENCES,
      ...(JSON.parse(raw) as Partial<Preferences>),
    };
    // Guard against stale/renamed enum values from older stored prefs: an unknown
    // mapColorMode flows into colorForCity(), whose switch has no default branch.
    if (!COLOR_MODES.some((m) => m.id === merged.mapColorMode)) {
      merged.mapColorMode = DEFAULT_PREFERENCES.mapColorMode;
    }
    return merged;
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function savePreferences(prefs: Preferences): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // localStorage unavailable (private mode, quota) — ignore.
  }
}

/** Resolve "system" to the effective light/dark using the OS preference. */
export function resolveTheme(theme: Theme): "light" | "dark" {
  if (theme !== "system") return theme;
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

/** Apply preferences to <html> — shared by the provider and the inline FOUC script. */
export function applyPreferences(prefs: Preferences): void {
  if (typeof document === "undefined") return;
  const el = document.documentElement;
  el.classList.toggle("dark", resolveTheme(prefs.theme) === "dark");
  el.dataset.density = prefs.density;
  el.dataset.badge = prefs.showBadge ? "on" : "off";
}
