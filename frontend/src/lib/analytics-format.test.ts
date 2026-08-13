import { describe, expect, it } from "vitest";
import { dueChip, formatDays, formatMonth, formatPercent, relativeDate } from "@/lib/analytics-format";

// A fixed "now" so every calendar-day assertion is deterministic regardless of when
// (or in which timezone) the suite runs. Midday avoids any midnight edge.
const NOW = new Date(2026, 7, 13, 12, 0, 0); // 2026-08-13 local

const daysFromNow = (days: number) => new Date(2026, 7, 13 + days, 9, 30).toISOString();

describe("dueChip", () => {
  it("marks a submitted review as done regardless of the deadline", () => {
    expect(dueChip(daysFromNow(-10), true, NOW)).toEqual({ label: "Review submitted ✓", tone: "verified" });
    expect(dueChip(null, true, NOW)).toEqual({ label: "Review submitted ✓", tone: "verified" });
  });

  it("renders a muted 'No deadline' when due_at is null", () => {
    expect(dueChip(null, false, NOW)).toEqual({ label: "No deadline", tone: "muted" });
  });

  it("counts down future deadlines in ink, singular and plural", () => {
    expect(dueChip(daysFromNow(4), false, NOW)).toEqual({ label: "Due in 4 days", tone: "ink" });
    expect(dueChip(daysFromNow(1), false, NOW)).toEqual({ label: "Due in 1 day", tone: "ink" });
  });

  it("stamps a deadline that falls today, even at a later hour", () => {
    const laterToday = new Date(2026, 7, 13, 23, 59).toISOString();
    expect(dueChip(laterToday, false, NOW)).toEqual({ label: "Due today", tone: "stamp" });
  });

  it("seals overdue deadlines, singular and plural", () => {
    expect(dueChip(daysFromNow(-1), false, NOW)).toEqual({ label: "1 day overdue", tone: "seal" });
    expect(dueChip(daysFromNow(-6), false, NOW)).toEqual({ label: "6 days overdue", tone: "seal" });
  });

  it("treats an unparseable date as no deadline rather than crashing", () => {
    expect(dueChip("not-a-date", false, NOW)).toEqual({ label: "No deadline", tone: "muted" });
  });
});

describe("formatPercent", () => {
  it("renders an em-dash when no decisions exist yet", () => {
    expect(formatPercent(null)).toBe("—");
  });

  it("scales a proportion in [0, 1] to percent", () => {
    expect(formatPercent(0.425)).toBe("42.5%");
    expect(formatPercent(0)).toBe("0%");
    expect(formatPercent(1)).toBe("100%");
  });

  it("leaves an already-scaled percentage alone", () => {
    expect(formatPercent(42.5)).toBe("42.5%");
  });
});

describe("formatDays", () => {
  it("renders an em-dash for null and trims trailing zeros otherwise", () => {
    expect(formatDays(null)).toBe("—");
    expect(formatDays(12)).toBe("12");
    expect(formatDays(12.04)).toBe("12");
    expect(formatDays(12.35)).toBe("12.4");
  });
});

describe("formatMonth", () => {
  it("turns an ISO year-month into a short label", () => {
    expect(formatMonth("2026-08")).toBe("Aug 2026");
    expect(formatMonth("2025-12")).toBe("Dec 2025");
  });

  it("falls back to the raw string for malformed input", () => {
    expect(formatMonth("garbage")).toBe("garbage");
    expect(formatMonth("2026-13")).toBe("2026-13");
  });
});

describe("relativeDate", () => {
  it("renders an em-dash for null or unparseable input", () => {
    expect(relativeDate(null, NOW)).toBe("—");
    expect(relativeDate("not-a-date", NOW)).toBe("—");
  });

  it("names today, yesterday, and recent day counts", () => {
    expect(relativeDate(daysFromNow(0), NOW)).toBe("today");
    expect(relativeDate(daysFromNow(-1), NOW)).toBe("yesterday");
    expect(relativeDate(daysFromNow(-12), NOW)).toBe("12 days ago");
  });

  it("rolls day counts up into months and years", () => {
    expect(relativeDate(daysFromNow(-70), NOW)).toBe("2 months ago");
    expect(relativeDate(daysFromNow(-800), NOW)).toBe("2 years ago");
  });
});
