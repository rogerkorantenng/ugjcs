"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import { Button } from "@/components/ui/button";

/**
 * A self-built onboarding tour — no library. Mounted once per dashboard page; on a user's
 * first visit (tracked per role in `localStorage`) it offers a short walkthrough, and the
 * AppNav's "Show me around" button can restart it any time via `TOUR_START_EVENT`.
 *
 * Highlighting works by the classic box-shadow cutout: one absolutely-positioned ring is
 * placed over the target with a 2px `stamp` outline and a huge dark spread shadow, so the
 * rest of the page dims while the target itself stays fully visible and unmoved. The ring
 * is repositioned from `getBoundingClientRect` on every resize and scroll, so it stays
 * glued to the target even while `scrollIntoView`'s smooth scroll is still in flight.
 */
export interface TourStep {
  /** Matches an element carrying `data-tour="<target>"`. Steps without a target render as
   * a centred card over the dimmed page — used for concepts (anonymity, editorial process)
   * that have no single on-screen anchor. */
  target?: string;
  title: string;
  body: string;
}

/** Dispatched on `window` by the AppNav "Show me around" button to (re)start the tour. */
export const TOUR_START_EVENT = "ugjcs:tour:start";

const RING_PADDING = 8;
const CARD_WIDTH = 336; // px — must match the card's w-[21rem]
const GUTTER = 16;
/** Rough card height used only to choose above/below placement — never for sizing. */
const CARD_CLEARANCE = 240;

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

function findTarget(step: TourStep): HTMLElement | null {
  if (!step.target) return null;
  return document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
}

function prefersReducedMotion() {
  // `matchMedia` is always present in browsers; the guard is for jsdom in tests.
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function Tour({ steps, storageKey }: { steps: TourStep[]; storageKey: string }) {
  const [phase, setPhase] = useState<"idle" | "prompt" | "active">("idle");
  // Steps whose target actually exists right now, resolved once at start — a stable list
  // keeps the "2 of 5" counter honest when an empty dashboard makes some anchors missing.
  const [activeSteps, setActiveSteps] = useState<TourStep[]>([]);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  const markSeen = useCallback(() => {
    try {
      window.localStorage.setItem(storageKey, "seen");
    } catch {
      // Storage unavailable (private mode) — the prompt may reappear, nothing worse.
    }
  }, [storageKey]);

  const begin = useCallback(() => {
    markSeen();
    const available = steps.filter((step) => !step.target || findTarget(step));
    if (available.length === 0) return;
    setActiveSteps(available);
    setIndex(0);
    setRect(null);
    setPhase("active");
  }, [steps, markSeen]);

  const dismiss = useCallback(() => {
    markSeen();
    setPhase("idle");
  }, [markSeen]);

  const end = useCallback(() => {
    setPhase("idle");
    setRect(null);
  }, []);

  // First-visit offer, gated behind an effect so the server render never flashes it.
  useEffect(() => {
    let seen: string | null = "seen";
    try {
      seen = window.localStorage.getItem(storageKey);
    } catch {
      // If storage is unreadable, err on the side of not nagging.
    }
    if (!seen) setPhase("prompt");
  }, [storageKey]);

  // The AppNav "Show me around" button restarts the tour from anywhere on this page.
  useEffect(() => {
    window.addEventListener(TOUR_START_EVENT, begin);
    return () => window.removeEventListener(TOUR_START_EVENT, begin);
  }, [begin]);

  // Track the current step's target: scroll it into view, then keep the highlight ring
  // glued to it through resize and scroll (including the smooth scroll itself).
  useEffect(() => {
    if (phase !== "active") return;
    const step = activeSteps[index];
    if (!step) return;
    const el = findTarget(step);
    if (!el) {
      // Target vanished mid-tour (e.g. a data refresh) — fall back to a centred card.
      setRect(null);
      return;
    }
    el.scrollIntoView?.({ block: "center", behavior: prefersReducedMotion() ? "auto" : "smooth" });
    const update = () => {
      const r = el.getBoundingClientRect();
      setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, { capture: true, passive: true });
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, { capture: true });
    };
  }, [phase, activeSteps, index]);

  const isLast = index >= activeSteps.length - 1;

  // Keyboard: Esc closes, arrows navigate.
  useEffect(() => {
    if (phase !== "active") return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        end();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        if (isLast) end();
        else setIndex((i) => i + 1);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        setIndex((i) => Math.max(0, i - 1));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, isLast, end]);

  // Move focus onto the step card so screen readers announce it and keys land somewhere sane.
  useEffect(() => {
    if (phase === "active") cardRef.current?.focus({ preventScroll: true });
  }, [phase, index]);

  if (phase === "prompt") {
    return (
      <div
        role="dialog"
        aria-labelledby="tour-prompt-title"
        className="fixed bottom-4 right-4 z-[90] w-[19rem] max-w-[calc(100vw-2rem)] rounded-[3px] border border-rule bg-surface p-4 shadow-[0_10px_24px_rgba(18,21,26,0.18)]"
      >
        <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-stamp">New here?</p>
        <h2 id="tour-prompt-title" className="mt-1 font-display-heading text-base font-semibold text-ink">
          Let us show you around.
        </h2>
        <p className="mt-1 text-sm text-ink/70">A short tour of this dashboard — what each part does and where to click first.</p>
        <div className="mt-3 flex items-center gap-4">
          <Button onClick={begin}>Start tour</Button>
          <button
            onClick={dismiss}
            className="rounded-[3px] text-sm font-medium text-ink/60 transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2"
          >
            Skip
          </button>
        </div>
      </div>
    );
  }

  if (phase !== "active" || activeSteps.length === 0) return null;

  const step = activeSteps[index];
  const targeted = Boolean(step.target) && rect !== null;

  let ringStyle: CSSProperties | undefined;
  let cardStyle: CSSProperties | undefined;
  if (targeted && rect) {
    ringStyle = {
      top: rect.top - RING_PADDING,
      left: rect.left - RING_PADDING,
      width: rect.width + RING_PADDING * 2,
      height: rect.height + RING_PADDING * 2,
      // The cutout: a stamp-violet ring plus a page-sized dark spread. One element does
      // both the highlight and the dimming, so the target itself is never covered.
      boxShadow: "0 0 0 2px var(--color-stamp), 0 0 0 9999px rgba(18, 21, 26, 0.55)",
    };
    const left = Math.min(Math.max(rect.left, GUTTER), Math.max(GUTTER, window.innerWidth - CARD_WIDTH - GUTTER));
    const spaceBelow = window.innerHeight - (rect.top + rect.height);
    cardStyle =
      spaceBelow >= CARD_CLEARANCE || rect.top < CARD_CLEARANCE
        ? { top: rect.top + rect.height + RING_PADDING + 12, left }
        : { bottom: window.innerHeight - rect.top + RING_PADDING + 12, left };
  }

  return (
    <div className="fixed inset-0 z-[100]">
      {targeted ? (
        <div aria-hidden="true" className="fixed rounded-[3px] transition-[top,left,width,height] duration-200 ease-out" style={ringStyle} />
      ) : (
        <div aria-hidden="true" className="fixed inset-0 bg-ink/55" />
      )}
      <div
        ref={cardRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-step-title"
        aria-describedby="tour-step-body"
        className={`fixed w-[21rem] max-w-[calc(100vw-2rem)] rounded-[3px] border border-rule bg-surface p-4 shadow-[0_10px_24px_rgba(18,21,26,0.25)] outline-none ${
          targeted ? "" : "left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
        }`}
        style={cardStyle}
      >
        <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-stamp">
          {index + 1} of {activeSteps.length}
        </p>
        <h2 id="tour-step-title" className="mt-1 font-display-heading text-base font-semibold text-ink">
          {step.title}
        </h2>
        <p id="tour-step-body" className="mt-1 text-sm text-ink/70">
          {step.body}
        </p>
        <div className="mt-4 flex items-center justify-between gap-3">
          <button
            onClick={end}
            className="rounded-[3px] text-xs font-medium text-ink/50 underline-offset-2 transition-colors hover:text-ink hover:underline focus-visible:outline-2 focus-visible:outline-offset-2"
          >
            Skip tour
          </button>
          <div className="flex items-center gap-2">
            {index > 0 && (
              <Button variant="secondary" onClick={() => setIndex((i) => Math.max(0, i - 1))}>
                Back
              </Button>
            )}
            <Button onClick={() => (isLast ? end() : setIndex((i) => i + 1))}>{isLast ? "Done" : "Next"}</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
