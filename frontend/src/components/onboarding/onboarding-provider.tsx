"use client";

import { useSyncExternalStore } from "react";
import {
  DEFAULT_ONBOARDING,
  TOUR_STEPS,
  loadOnboarding,
  saveOnboarding,
  type OnboardingState,
  type TourStep,
} from "@/lib/onboarding";

// Module-level store, same SSR-safe pattern as preferences-provider.tsx: the
// server snapshot is the defaults, the client snapshot is the stored value, and
// React reconciles the two during hydration. The store survives client-side
// navigation (no full reload), so the tour traverses "/" → "/statistiques"
// naturally; localStorage covers a hard reload mid-tour.
let current: OnboardingState = DEFAULT_ONBOARDING;
let initialized = false;
const listeners = new Set<() => void>();

function getSnapshot(): OnboardingState {
  if (!initialized && typeof window !== "undefined") {
    current = loadOnboarding();
    initialized = true;
  }
  return current;
}

function getServerSnapshot(): OnboardingState {
  return DEFAULT_ONBOARDING;
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

function commit(next: OnboardingState): void {
  current = next;
  saveOnboarding(current);
  listeners.forEach((l) => l());
}

// Exported standalone so non-reactive callers (event handlers like the map's
// notify, or the settings "replay" button) can trigger the tour without
// subscribing their component to every store change via useOnboarding().
export function start(): void {
  commit({ seen: false, active: true, step: 0 });
}

function goTo(step: number): void {
  if (step >= TOUR_STEPS.length) {
    finish();
    return;
  }
  commit({ ...current, active: true, step: Math.max(0, step) });
}

function next(): void {
  goTo(current.step + 1);
}

function prev(): void {
  goTo(current.step - 1);
}

function skip(): void {
  commit({ ...current, active: false, seen: true });
}

function finish(): void {
  commit({ ...current, active: false, seen: true });
}

/** Advance only if the active step is action-driven and matches this event.
 *  Standalone export: callers fire this from event handlers without subscribing
 *  their (often heavy) component to the store. */
export function notify(event: string): void {
  if (!current.active) return;
  const step = TOUR_STEPS[current.step];
  if (step?.advanceOn === "action" && step.id === event) {
    next();
  }
}

export type OnboardingApi = {
  seen: boolean;
  active: boolean;
  stepIndex: number;
  step: TourStep | null;
  total: number;
  start: () => void;
  next: () => void;
  prev: () => void;
  skip: () => void;
  finish: () => void;
  notify: (event: string) => void;
};

export function useOnboarding(): OnboardingApi {
  const state = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return {
    seen: state.seen,
    active: state.active,
    stepIndex: state.step,
    step: state.active ? TOUR_STEPS[state.step] ?? null : null,
    total: TOUR_STEPS.length,
    start,
    next,
    prev,
    skip,
    finish,
    notify,
  };
}
