// Pure formatting helpers for the editorial analytics page and the assignment due
// chips. No React, no fetching — everything here is unit-tested directly.

/**
 * Acceptance rate for the KPI row. The backend serialises a plain `number`; a proportion
 * in [0, 1] is the expected shape, but a value already scaled to percent (> 1) is
 * displayed as-is rather than multiplied into nonsense like "4250%".
 */
export function formatPercent(rate: number | null): string {
  if (rate === null) return "—";
  const percent = rate > 1 ? rate : rate * 100;
  return `${trimDecimal(percent)}%`;
}

/** Day averages for the KPI row and reviewer table — one decimal, no trailing `.0`. */
export function formatDays(value: number | null): string {
  if (value === null) return "—";
  return `${trimDecimal(value)}`;
}

function trimDecimal(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

/** "2026-08" → "Aug 2026". Falls back to the raw string if the month is malformed. */
export function formatMonth(month: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(month);
  if (!match) return month;
  const [, year, mm] = match;
  const index = Number(mm) - 1;
  const NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  if (index < 0 || index > 11) return month;
  return `${NAMES[index]} ${year}`;
}

/** Calendar-day difference (local time): positive when `date` is in the future. */
function dayDiff(date: Date, now: Date): number {
  const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  return Math.round((startOf(date) - startOf(now)) / 86_400_000);
}

/** "today", "yesterday", "3 days ago", "2 months ago" — for the reviewer table's
 * last-activity column. Null (never active) renders an em-dash. */
export function relativeDate(iso: string | null, now: Date = new Date()): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const days = -dayDiff(date, now);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  if (days < 365) {
    const months = Math.floor(days / 30);
    return months === 1 ? "1 month ago" : `${months} months ago`;
  }
  const years = Math.floor(days / 365);
  return years === 1 ? "1 year ago" : `${years} years ago`;
}

export type DueTone = "ink" | "stamp" | "seal" | "verified" | "muted";

export interface DueChip {
  label: string;
  tone: DueTone;
}

/**
 * The one place a review deadline is turned into words and a tone, so the editor
 * queue's overdue chips and the detail page's assignment rows can never disagree.
 * `submitted` wins over everything — a submitted review is done, not overdue.
 */
export function dueChip(dueAt: string | null, submitted: boolean, now: Date = new Date()): DueChip {
  if (submitted) return { label: "Review submitted ✓", tone: "verified" };
  if (dueAt === null) return { label: "No deadline", tone: "muted" };
  const due = new Date(dueAt);
  if (Number.isNaN(due.getTime())) return { label: "No deadline", tone: "muted" };
  const days = dayDiff(due, now);
  if (days > 0) return { label: days === 1 ? "Due in 1 day" : `Due in ${days} days`, tone: "ink" };
  if (days === 0) return { label: "Due today", tone: "stamp" };
  const overdue = -days;
  return { label: overdue === 1 ? "1 day overdue" : `${overdue} days overdue`, tone: "seal" };
}
