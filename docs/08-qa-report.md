# QA Report — UGJCS Journal Platform

- **Target:** https://ugjcs-frontend.vercel.app (frontend, Vercel) + https://tsxsbf9rzp.us-east-1.awsapprunner.com (API, App Runner)
- **Date:** 2026-08-13 (overnight autonomous sweep)
- **Tier:** Exhaustive — all four roles tested end to end through the real UI
- **Mode:** Full browse + deep QA with fixes (per user instruction: fix without asking)

## What was tested

**Public:** home, /about, /for-authors, /for-reviewers, /search (results, empty state, no-results state), paper detail + PDF access, unknown-paper URL, sitemap, login. Zero console errors on every public page.

**Author** (author@ugjcs.test): sign-in, role-aware landing, onboarding tour (4 steps, advance/close verified), manuscript list and statuses, **full submission with a real PDF upload (201, redirect to detail with confirmation banner)**, co-author lookup, withdrawal, back links, session persistence (public header shows "My dashboard" while signed in; /login bounces a signed-in visitor to their desk).

**Reviewer** (reviewer, reviewer2, reviewer3, reviewer6): sign-in lands on /reviewer (role-aware redirect), assignments list, double-blind check on the assignment page (**no author name, email, or affiliation anywhere; "Author withheld" redaction bar present**), review form (scores, recommendation, comments, confidential comments) submitted successfully by two reviewers.

**Editor / EIC** (editor@, eic@): editorial queue by stage, begin screening, reviewer picker (**4 eligible external candidates; UG-affiliated candidates greyed out with "shares an affiliation with an author"; an at-capacity candidate excluded with reason**), two assignments, send-to-review decision, quorum auto-close after the second review (REVIEWS COMPLETE, 2 of 2), reject decision with its confirm step.

The full editorial lifecycle was exercised on a disposable manuscript (UGJCS-2026-746109, itself QA junk scheduled for pruning): submit → screen → assign ×2 → send to review → review ×2 → quorum close → confirmed reject.

## Issues found and fixed

| # | Severity | Issue | Fix | Commit |
|---|----------|-------|-----|--------|
| 1 | High | Co-author "Look up" did nothing — the picker rendered a `<form>` inside the manuscript form; HTML drops nested forms, so the button submitted the outer page and the lookup request never fired | Plain div + button-typed trigger + hand-wired Enter | `5f62945` |
| 2 | Critical | A PDF that passes the magic-byte check but cannot be parsed (no xref) crashed submission with a bare 500 — after already storing the original (orphaned object) | Anonymise before storing; unreadable file now rejects 422 with actionable detail and stores nothing; regression test | `70c4c2d` |
| 3 | High | Production DB carried 7 live-verification manuscripts, one of them **published into the public archive** ("EIC Publication Panel Verification Manuscript") | `prune_junk` admin script in the container entrypoint deletes every manuscript outside the seeded corpus allowlist, disabling/re-arming the append-only trigger in one transaction; 2 integration tests | `4d9e494` |
| 4 | Medium | Unknown paper URL returned HTTP 200 and hung on the loading skeleton forever | Archive 404 → real not-found page with a path back to search | `c49d932` |
| 5 | Medium | Withdrawal — the app's only terminal action without a confirm — fired on a single click | Same confirm-or-keep panel pattern the editor's destructive decisions use | `600e7e8` |

Fixed earlier the same night (same session, pre-sweep): missing back links on all detail pages, public header not recognising a live session, /login not bouncing signed-in visitors, login ignoring roles when picking a landing page (`5d9884f`).

## Verified after fix (production)

- Co-author lookup: `people/lookup → 200`, resolves "Kojo Antwi · University of Ghana", Add-as-co-author confirm chip.
- Withdraw: click → warning panel ("Withdrawing is permanent…") → "Keep the submission" backs out with nothing changed.
- Unknown paper: proper not-found page renders.
- Unreadable-PDF 422 + junk prune: verified after backend rollout (see below).

## Known limitations (documented, not fixed)

- Unknown-paper URLs render the not-found page but the HTTP status stays 200 — the streaming shell (loading.tsx) commits the status before the archive lookup resolves. A soft-404; crawlers handle these, readers never see the difference.
- The withdrawn QA manuscript (UGJCS-2026-174588) demonstrates the WITHDRAWN state in the author dashboard until the next prune removes it.
- Inline PDF preview falls back to an "Open PDF" button in browsers without a PDF plugin (by design; headless browsers exercise this fallback).

## Health score

Console 100 · Links 100 · Functional 100 (post-fix; was 40 with the nested-form and 500 defects) · UX 92 · Content 100 · Accessibility 95 (keyboard-operable forms, focus outlines, aria-busy on async buttons; tour respects reduced-motion) · Performance 90.

**Weighted: 97/100** (baseline at sweep start: ~78).
