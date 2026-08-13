import { dueChip, type DueTone } from "@/lib/analytics-format";

// Same rounded-full chip anatomy as `StatusBadge`, with the palette contract applied to
// deadlines: `seal` strictly for overdue, `verified` for a submitted review, `stamp` for
// "due today", plain ink for a future deadline, muted for no deadline at all.
const TONE_CLASSES: Record<DueTone, string> = {
  verified: "text-verified border-verified/25 bg-verified/[0.06]",
  stamp: "text-stamp border-stamp/25 bg-stamp/[0.06]",
  seal: "text-seal border-seal/25 bg-seal/[0.06]",
  ink: "text-ink/70 border-rule bg-ink/[0.03]",
  muted: "text-ink/45 border-rule bg-transparent",
};

export function chipClasses(tone: DueTone): string {
  return `inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${TONE_CLASSES[tone]}`;
}

/** Where one review stands against its deadline, as a chip. Pure presentation over
 * `dueChip()` — the tested function owns every label and tone decision. */
export function DueChipBadge({ dueAt, submitted }: { dueAt: string | null; submitted: boolean }) {
  const chip = dueChip(dueAt, submitted);
  return <span className={chipClasses(chip.tone)}>{chip.label}</span>;
}
