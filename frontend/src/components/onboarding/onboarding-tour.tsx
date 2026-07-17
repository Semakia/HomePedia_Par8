"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { X } from "lucide-react";
import { loadOnboarding } from "@/lib/onboarding";
import { useOnboarding } from "./onboarding-provider";

// Padding (px) added around the spotlighted element so it isn't cut flush.
const PAD = 8;
// Bubble sizing used for placement maths.
const BUBBLE_W = 320;
const GAP = 16;

type Rect = { top: number; left: number; width: number; height: number };

export function OnboardingTour() {
  const { active, step, stepIndex, total, start, next, prev, skip, finish } =
    useOnboarding();
  const pathname = usePathname();
  const [rect, setRect] = useState<Rect | null>(null);

  // Auto-start the first time the user is on the map (the app root) — including
  // when they land elsewhere first and navigate to "/" later. Read the persisted
  // state directly (not the hook values, which on the first effect run still
  // hold the SSR snapshot where active=false) so we never clobber a tour resumed
  // mid-flow after a reload. start() only fires when not seen and not active, so
  // it can't re-trigger or reset an in-progress tour.
  useEffect(() => {
    if (pathname !== "/") return;
    const stored = loadOnboarding();
    if (!stored.seen && !stored.active) start();
  }, [pathname, start]);

  // Only render a step whose route matches where we currently are.
  const onRoute = step != null && step.route === pathname;
  const targetSel = onRoute ? step?.target : undefined;

  const measure = useCallback(() => {
    if (!targetSel) {
      setRect(null);
      return;
    }
    const el = document.querySelector<HTMLElement>(`[data-tour="${targetSel}"]`);
    setRect(el ? visibleRect(el) : null);
  }, [targetSel]);

  // Measure the target, retrying briefly because the element may mount on the
  // same render that advances the tour (e.g. the fiche appears when a city is
  // clicked). Re-measure on scroll/resize while the step is shown.
  useEffect(() => {
    if (!active || !onRoute || !targetSel) return;
    let raf = 0;
    let tries = 0;
    const tick = () => {
      const el = document.querySelector<HTMLElement>(
        `[data-tour="${targetSel}"]`,
      );
      if (el) {
        el.scrollIntoView({ block: "nearest", behavior: "smooth" });
        measure();
        return;
      }
      if (tries++ < 40) raf = requestAnimationFrame(tick);
    };
    // Defer the first measurement to a frame so we never setState synchronously
    // inside the effect body (and so the target has a chance to mount).
    raf = requestAnimationFrame(tick);

    const onChange = () => measure();
    window.addEventListener("scroll", onChange, true);
    window.addEventListener("resize", onChange);
    const ro = new ResizeObserver(onChange);
    const el = document.querySelector<HTMLElement>(`[data-tour="${targetSel}"]`);
    if (el) ro.observe(el);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onChange, true);
      window.removeEventListener("resize", onChange);
      ro.disconnect();
    };
  }, [active, onRoute, targetSel, measure, stepIndex]);

  if (!active || !step) return null;

  // The step belongs to another page (mid-tour navigation in flight): dim
  // nothing, just wait for that page to mount and render its own step.
  if (!onRoute) return null;

  const isLast = stepIndex === total - 1;
  const showNext = step.advanceOn === "next";
  const nextLabel = isLast ? "Terminer" : stepIndex === 0 ? "C'est parti" : "Suivant";

  const bubble = (
    <Bubble
      title={step.title}
      body={step.body}
      hint={step.advanceOn === "action" ? step.hint : undefined}
      stepIndex={stepIndex}
      total={total}
      canPrev={stepIndex > 0}
      onPrev={prev}
      onSkip={skip}
      showNext={showNext}
      nextLabel={nextLabel}
      onNext={isLast ? finish : next}
    />
  );

  // Targeted step with a measured element: spotlight (4 blurred panels + ring).
  if (targetSel && rect) {
    const r = inflate(rect, PAD);
    return (
      // The wrapper must not capture clicks over the spotlight hole, otherwise
      // the highlighted target isn't usable. Only the panels (block) and the
      // bubble re-enable pointer events.
      <div className="pointer-events-none fixed inset-0 z-[2000]" aria-live="polite">
        <Panels rect={r} />
        {/* Highlight ring — never intercepts clicks so the target stays usable. */}
        <div
          className="pointer-events-none fixed z-[2001] rounded-2xl outline outline-2 outline-primary"
          style={{ top: r.top, left: r.left, width: r.width, height: r.height }}
        />
        <PositionedBubble rect={r}>{bubble}</PositionedBubble>
      </div>
    );
  }

  // Modal step (welcome / end): it has a "Suivant"/"Terminer" button, so dim and
  // block the page behind the centered bubble.
  if (showNext) {
    return (
      <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
        <div className="w-full max-w-md">{bubble}</div>
      </div>
    );
  }

  // An action step whose target element isn't on the page (yet). It has no
  // button, so a blocking backdrop would trap the user (they could only skip).
  // Float the bubble without capturing clicks, so the page stays interactive and
  // the user can still perform the action that advances the tour.
  return (
    <div className="pointer-events-none fixed inset-0 z-[2000] flex items-center justify-center p-4">
      <div className="pointer-events-auto w-full max-w-md">{bubble}</div>
    </div>
  );
}

/** The visible box of `el`: its rect clipped by every scroll/overflow ancestor
 *  and the viewport. Without this, a target taller than its scrollable container
 *  (e.g. the criteria panel inside an overflow-y-auto card) would be spotlighted
 *  past the part the user can actually see. Returns null if fully clipped. */
function visibleRect(el: HTMLElement): Rect | null {
  const r = el.getBoundingClientRect();
  let { top, left } = r;
  let right = r.right;
  let bottom = r.bottom;
  for (let p = el.parentElement; p; p = p.parentElement) {
    const o = getComputedStyle(p);
    if (o.overflowX !== "visible" || o.overflowY !== "visible") {
      const pr = p.getBoundingClientRect();
      top = Math.max(top, pr.top);
      left = Math.max(left, pr.left);
      right = Math.min(right, pr.right);
      bottom = Math.min(bottom, pr.bottom);
    }
  }
  top = Math.max(top, 0);
  left = Math.max(left, 0);
  right = Math.min(right, window.innerWidth);
  bottom = Math.min(bottom, window.innerHeight);
  if (right <= left || bottom <= top) return null;
  return { top, left, width: right - left, height: bottom - top };
}

function inflate(r: Rect, pad: number): Rect {
  const top = Math.max(0, r.top - pad);
  const left = Math.max(0, r.left - pad);
  const right = Math.min(window.innerWidth, r.left + r.width + pad);
  const bottom = Math.min(window.innerHeight, r.top + r.height + pad);
  return { top, left, width: right - left, height: bottom - top };
}

/** Four blurred/dark panels around the spotlight rect. They capture clicks
 *  (block the surrounding UI); the rect itself is left uncovered = clickable. */
function Panels({ rect }: { rect: Rect }) {
  const panel = "pointer-events-auto fixed bg-black/40 backdrop-blur-sm";
  const right = rect.left + rect.width;
  const bottom = rect.top + rect.height;
  return (
    <>
      <div className={panel} style={{ top: 0, left: 0, width: "100vw", height: rect.top }} />
      <div className={panel} style={{ top: bottom, left: 0, width: "100vw", height: `calc(100vh - ${bottom}px)` }} />
      <div className={panel} style={{ top: rect.top, left: 0, width: rect.left, height: rect.height }} />
      <div className={panel} style={{ top: rect.top, left: right, width: `calc(100vw - ${right}px)`, height: rect.height }} />
    </>
  );
}

/** Places the bubble beside the rect: right → left → below → above. */
function PositionedBubble({
  rect,
  children,
}: {
  rect: Rect;
  children: React.ReactNode;
}) {
  const vw = typeof window !== "undefined" ? window.innerWidth : 1280;
  const vh = typeof window !== "undefined" ? window.innerHeight : 800;
  const right = rect.left + rect.width;
  const bottom = rect.top + rect.height;

  let style: React.CSSProperties;
  if (right + GAP + BUBBLE_W <= vw) {
    style = { top: clamp(rect.top, 8, vh - 220), left: right + GAP, width: BUBBLE_W };
  } else if (rect.left - GAP - BUBBLE_W >= 0) {
    style = { top: clamp(rect.top, 8, vh - 220), left: rect.left - GAP - BUBBLE_W, width: BUBBLE_W };
  } else if (bottom + GAP + 180 <= vh) {
    style = { top: bottom + GAP, left: clamp(rect.left, 8, vw - BUBBLE_W - 8), width: BUBBLE_W };
  } else {
    style = { top: clamp(rect.top - GAP - 200, 8, vh - 220), left: clamp(rect.left, 8, vw - BUBBLE_W - 8), width: BUBBLE_W };
  }

  return (
    <div className="pointer-events-auto fixed z-[2002]" style={style}>
      {children}
    </div>
  );
}

function clamp(v: number, min: number, max: number): number {
  return Math.min(Math.max(v, min), Math.max(min, max));
}

function Bubble({
  title,
  body,
  hint,
  stepIndex,
  total,
  canPrev,
  onPrev,
  onSkip,
  showNext,
  nextLabel,
  onNext,
}: {
  title: string;
  body: string;
  hint?: string;
  stepIndex: number;
  total: number;
  canPrev: boolean;
  onPrev: () => void;
  onSkip: () => void;
  showNext: boolean;
  nextLabel: string;
  onNext: () => void;
}) {
  return (
    <div className="relative rounded-2xl border border-line bg-card p-5 shadow-xl">
      <button
        type="button"
        onClick={onSkip}
        aria-label="Fermer le tutoriel"
        className="absolute right-3 top-3 text-muted hover:text-ink"
      >
        <X size={16} />
      </button>

      <p className="mb-1 text-xs font-medium text-muted">
        Étape {stepIndex + 1} / {total}
      </p>
      <h3 className="mb-1.5 pr-5 text-sm font-semibold text-ink">{title}</h3>
      <p className="text-sm text-muted">{body}</p>

      {hint && (
        <p className="mt-3 rounded-lg bg-primary-soft px-3 py-2 text-xs font-medium text-primary">
          {hint}
        </p>
      )}

      <div className="mt-4 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onSkip}
          className="text-xs font-medium text-muted hover:text-ink"
        >
          Passer le tutoriel
        </button>
        <div className="flex items-center gap-2">
          {canPrev && (
            <button
              type="button"
              onClick={onPrev}
              className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-muted hover:bg-bg"
            >
              Précédent
            </button>
          )}
          {showNext && (
            <button
              type="button"
              onClick={onNext}
              className="rounded-lg bg-primary px-4 py-1.5 text-xs font-medium text-white hover:opacity-90"
            >
              {nextLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
