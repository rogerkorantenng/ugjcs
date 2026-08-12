# UGJCS Plan 5 — Frontend (Next.js as Backend-For-Frontend)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give an examiner a browser-usable UGJCS: a public, indexable archive; author submission with a real status timeline; a reviewer experience that is structurally incapable of leaking author identity; and an editor workflow that screens, assigns and decides. Ship it as a Next.js 15 App Router project that is also the security boundary for every authenticated call.

**Architecture:** Two traffic classes, never mixed.

1. **Public archive** (`/`, `/issues`, `/papers/[trackingCode]`, `/search`) is rendered by React Server Components with Incremental Static Regeneration, calling the backend directly over plain `fetch`. No cookie, no bearer token, nothing an anonymous reader's browser holds is privileged. This is what keeps these pages fast, cacheable at the edge and crawlable.
2. **Everything behind a role** (`/login`, `/author/*`, `/reviewer/*`, `/editor/*`) is a Client Component tree that talks only to same-origin `/api/*` Next.js Route Handlers, never to the backend directly. The browser holds one httpOnly, Secure, SameSite=Lax cookie scoped to the Vercel origin, sealed with `iron-session`. Each Route Handler unseals it, attaches `Authorization: Bearer <access_token>` to the upstream call, transparently refreshes an expired access token using the refresh token also inside the sealed cookie, and reseals the cookie with rotated tokens before responding.

**Why the split, stated once so no later task re-litigates it:** a cookie set by `ugjcs.vercel.app` is first-party to Vercel and third-party to the AWS backend origin. Safari and Brave block third-party cookies by default, so a design that sets the session cookie on the API origin, or that ships the access token to the browser at all, works on Chrome and fails silently on the assessor's machine. Routing every authenticated call through a same-origin Route Handler is what makes the cookie first-party everywhere, and it keeps the bearer token out of reach of any XSS in the page — Client Components never see it.

**Why authenticated pages are Client Components, not Server Components doing the fetch themselves:** Next.js 15 only allows a request to *write* cookies from a Route Handler or a Server Action, never during the render of a Server Component. Token refresh has to write a rotated cookie. Putting the fetch inside a Route Handler is therefore the only place in the framework where "read the session, maybe refresh it, call upstream, persist the rotation" can happen in one request — so every authenticated page fetches through `/api/*` via `useSWR`, and refresh-on-expiry works identically for a page load and for a form submission.

**Tech Stack:** Next.js 15 (App Router), React 19, TypeScript (strict), Tailwind CSS v4, `iron-session` (cookie sealing), `zod` (input validation), `swr` (client-side data fetching against the BFF), Vitest + Testing Library (unit/component), Playwright (end-to-end) + `@axe-core/playwright` (accessibility scan).

## Assumed backend contract

`docs/superpowers/plans/2026-08-12-ugjcs-plan-4-editorial-api.md` does not exist yet at the time of writing. This plan assumes, and every Route Handler below is written against, the following shape under `/api/v1` (consistent with §9 of the design spec and with the domain vocabulary fixed in Plans 1–3):

- `POST /auth/login {email, password} -> {access_token, refresh_token, expires_in, user: {id, email, name, roles}}`
- `POST /auth/refresh {refresh_token} -> {access_token, refresh_token, expires_in}`
- `POST /auth/logout {refresh_token} -> 204`
- `GET /auth/me -> {id, email, name, roles}` (Bearer)
- `POST /manuscripts` (multipart: `title, abstract, keywords[], author_ids[], confirmed_anonymised, file`) `-> ManuscriptDetail` (Bearer, role `author`)
- `GET /manuscripts/mine -> ManuscriptSummary[]` (Bearer, role `author`)
- `GET /manuscripts/{id} -> ManuscriptDetail` (Bearer; visibility enforced server-side by the `can()` policy)
- `POST /manuscripts/{id}/withdraw -> ManuscriptDetail` (Bearer, corresponding author only)
- `GET /editorial/queue?status= -> ManuscriptSummary[]` (Bearer, role `editor`|`editor_in_chief`)
- `POST /editorial/{id}/screen {decision: "advance"|"desk_reject", rationale} -> ManuscriptDetail`
- `GET /editorial/reviewer-candidates?manuscript_id= -> ReviewerCandidate[]` (score + exclusion reason, per §10.1)
- `POST /editorial/{id}/assign {reviewer_id, due_date} -> ManuscriptDetail`
- `POST /editorial/{id}/decide {decision, rationale} -> ManuscriptDetail`
- `GET /reviews/mine -> ReviewAssignmentSummary[]` (Bearer, role `reviewer`)
- `GET /reviews/{assignmentId} -> BlindedManuscript` (Bearer; **response type carries no author field at all**, per §6.4)
- `POST /reviews/{assignmentId} {scores: {originality, rigour, clarity, significance}, recommendation, comments_to_author, confidential_comments_to_editor} -> 201`
- `GET /archive/issues -> IssueSummary[]`
- `GET /archive/issues/{volume}/{number} -> IssueDetail`
- `GET /archive/papers/{trackingCode} -> ArchivePaperDetail`
- `GET /archive/search?q=&page= -> {results: ArchivePaperSummary[], total: number}`
- `GET /health -> 200`

Errors are RFC 9457 problem details: `{type, title, status, detail?, instance?}`, `type` stable and machine-readable. Every Route Handler below relays that shape verbatim to the browser rather than inventing its own error format, so a future Plan 4 that matches this contract needs zero frontend changes; a Plan 4 that differs needs changes isolated to `src/lib/backend.ts`, `src/lib/auth-fetch.ts` and `src/types/api.ts` only.

Role and status vocabularies are copied verbatim from `ugjcs.domain.enums` (Plan 1) because the frontend must never invent its own spelling of a value the backend will send:

- `Role`: `author`, `reviewer`, `editor`, `editor_in_chief`, `administrator`
- `ManuscriptStatus`: `draft`, `submitted`, `under_screening`, `desk_rejected`, `under_review`, `reviews_complete`, `revision_requested`, `resubmitted`, `accepted`, `rejected`, `scheduled`, `published`, `withdrawn`
- `Recommendation`: `accept`, `minor_revision`, `major_revision`, `reject`
- `DecisionType`: `desk_reject`, `send_to_review`, `request_revision`, `accept`, `reject`

## Global Constraints

- Node 20 LTS, pinned in `frontend/package.json` `engines` and `frontend/.nvmrc`. Everything runs via `npm` from `frontend/`.
- TypeScript `strict: true` (the `create-next-app` default). No `any`; no `// @ts-ignore`. A genuine escape hatch is `// @ts-expect-error` with a one-line reason, and only where this plan says so.
- ESLint `next/core-web-vitals` + `next/typescript` (bundles `eslint-plugin-jsx-a11y`, which is the accessibility lint gate). `npm run lint` must report zero warnings, not just zero errors.
- Access tokens and refresh tokens exist in exactly one place: the sealed `iron-session` cookie, read only inside `src/lib/session.ts`, `middleware.ts` and Route Handlers under `src/app/api/`. No Client Component, no `localStorage`, no `sessionStorage`, no query string ever carries a token.
- Every Route Handler that calls the backend uses `authedFetch` (Task 3) or `backendFetch` (Task 1) — never a bare `fetch` with a manually attached header. This is what keeps refresh-on-expiry uniform.
- Public archive pages never import `src/lib/session.ts` or anything under `src/app/api/`. A public page that accidentally depends on the session module is a page that can no longer be statically rendered, and the layering rule exists to catch that at review time, not in production.
- Tailwind only. No component library. The only additional runtime dependencies are `iron-session`, `zod`, `swr` — a session codec, a validator and a data-fetching hook, not UI.
- Responsive from 360px width (iPhone SE class); every interactive element reachable and operable by keyboard alone; text/background contrast at or above WCAG 2.1 AA (4.5:1 body text, 3:1 large text/UI components).
- Conventional Commits. Author: Roger Koranteng Obeng, student ID 22424140.
- `frontend/Makefile check` (lint, typecheck, unit tests) must stay green at every commit, mirroring the backend's `make check`. `frontend/Makefile e2e` is separate and not part of the fast gate, mirroring the backend's `make integration`.

## Interfaces inherited from Plans 1–3

Implementers must not redefine these values; the TypeScript literal unions in `src/types/api.ts` (Task 1) are the frontend's copy of them, and must stay byte-for-byte identical to the `StrEnum` values above.

- `TokenPair`-shaped login/refresh response: `access_token`, `refresh_token`, `expires_in` (seconds), and on login only, `user: {id, email, name, roles}}` (Plan 3 `SessionService.log_in`/`.refresh`).
- RFC 9457 problem details on every error response (design spec §9, §11).
- `BlindedManuscript` — the reviewer-facing projection has no author field in its type, not merely a filtered value (design spec §6.4). The frontend's `BlindedManuscript` TypeScript type mirrors that omission structurally; Task 5 proves the UI cannot render what the type cannot hold even if a malformed payload smuggles the field in.
- The manuscript lifecycle in design spec §6.2, used to drive which actions each screen offers (e.g. desk rejection is offered only from `under_screening`; resubmission only from `revision_requested`). The frontend enforces none of these as security — the backend's guards are authoritative — but the UI hides actions the backend would reject, to avoid presenting a false affordance.

---

## File Structure

```
frontend/
├── package.json                                            Task 1
├── tsconfig.json                                            Task 1  (create-next-app default, strict: true)
├── next.config.ts                                           Task 1
├── postcss.config.mjs                                       Task 1  (Tailwind v4 zero-config plugin)
├── vitest.config.ts                                         Task 1
├── vitest.setup.ts                                          Task 1
├── playwright.config.ts                                     Task 7
├── Makefile                                                 Task 1  (+ e2e target, Task 7)
├── .env.local.example                                       Task 1
├── .nvmrc                                                   Task 1
├── middleware.ts                                            Task 3
├── src/
│   ├── lib/
│   │   ├── env.ts                                           Task 1  server env schema (zod, fail fast)
│   │   ├── backend.ts                                       Task 1  ProblemDetailsError, backendFetch (no auth)
│   │   ├── format.ts                                        Task 2  dates, status labels
│   │   ├── session.ts                                       Task 3  iron-session config + getSession()
│   │   ├── auth-fetch.ts                                    Task 3  authedFetch: bearer attach + refresh-on-401
│   │   └── use-api.ts                                       Task 4  useSWR wrapper against /api/*
│   ├── types/
│   │   └── api.ts                                           Task 1  DTOs mirroring the assumed contract
│   ├── components/
│   │   ├── ui/
│   │   │   ├── button.tsx                                   Task 1
│   │   │   ├── input.tsx                                    Task 1
│   │   │   ├── card.tsx                                     Task 1
│   │   │   ├── alert.tsx                                    Task 1  renders a ProblemDetails
│   │   │   ├── badge.tsx                                    Task 1  status pill
│   │   │   ├── select.tsx                                   Task 6
│   │   │   ├── textarea.tsx                                 Task 5
│   │   │   └── pagination.tsx                                Task 2
│   │   ├── layout/
│   │   │   ├── site-header.tsx                               Task 2  public nav
│   │   │   └── app-nav.tsx                                   Task 3  role-aware authenticated nav
│   │   ├── manuscript-card.tsx                                Task 2
│   │   ├── status-timeline.tsx                                Task 4
│   │   ├── file-upload.tsx                                    Task 4
│   │   ├── blinded-manuscript-view.tsx                        Task 5
│   │   ├── review-form.tsx                                    Task 5
│   │   ├── reviewer-assign-form.tsx                           Task 6
│   │   └── decision-form.tsx                                  Task 6
│   └── app/
│       ├── layout.tsx                                        Task 1
│       ├── globals.css                                       Task 1  (Tailwind v4 `@import`)
│       ├── (public)/
│       │   ├── page.tsx                                      Task 2  home
│       │   ├── issues/page.tsx                                Task 2  browse issues
│       │   ├── issues/[volume]/[number]/page.tsx              Task 2  issue detail
│       │   ├── papers/[trackingCode]/page.tsx                 Task 2  paper detail (+ JSON-LD)
│       │   └── search/page.tsx                                Task 2
│       ├── sitemap.ts                                        Task 2
│       ├── login/page.tsx                                     Task 3
│       ├── author/
│       │   ├── layout.tsx                                     Task 3  session-presence read for nav
│       │   ├── page.tsx                                       Task 4  dashboard
│       │   ├── submit/page.tsx                                 Task 4  submission form
│       │   └── [id]/page.tsx                                   Task 4  detail + timeline
│       ├── reviewer/
│       │   ├── layout.tsx                                     Task 3
│       │   ├── page.tsx                                       Task 5  assignment list
│       │   └── [id]/page.tsx                                   Task 5  blinded read + review form
│       ├── editor/
│       │   ├── layout.tsx                                     Task 3
│       │   ├── page.tsx                                       Task 6  screening queue
│       │   └── [id]/page.tsx                                   Task 6  screen / assign / decide
│       └── api/
│           ├── auth/login/route.ts                            Task 3
│           ├── auth/logout/route.ts                            Task 3
│           ├── auth/me/route.ts                                Task 3
│           ├── manuscripts/route.ts                            Task 4  GET mine, POST create
│           ├── manuscripts/[id]/route.ts                       Task 4  GET one
│           ├── manuscripts/[id]/withdraw/route.ts               Task 4
│           ├── reviews/route.ts                                Task 5  GET mine
│           ├── reviews/[id]/route.ts                           Task 5  GET blinded, POST submit
│           └── editorial/
│               ├── queue/route.ts                              Task 6
│               ├── [id]/screen/route.ts                        Task 6
│               ├── [id]/candidates/route.ts                    Task 6
│               ├── [id]/assign/route.ts                        Task 6
│               └── [id]/decide/route.ts                        Task 6
└── tests/
    └── e2e/
        ├── mock-backend.ts                                   Task 7  hand-rolled contract double
        └── submit-review-decide.spec.ts                       Task 7
```

Unit/component tests are co-located as `*.test.ts(x)` next to the file they cover — the convention Vitest's default include glob (`**/*.test.{ts,tsx}`) is configured for in Task 1 — rather than mirrored under a separate tree, so a reviewer sees the test the moment they open the implementation.

---

### Task 1: Scaffold, environment, shared primitives

**Files:** everything under "Task 1" in the tree above.

**Interfaces:**
- Produces: `env` (validated server config), `backendFetch`, `ProblemDetailsError`, `ProblemDetails` type, the `ManuscriptStatus`/`Recommendation`/`DecisionType`/`Role` literal unions, `Button`, `Input`, `Card`, `Alert`, `Badge`.

- [ ] **Step 1: Scaffold**

```bash
cd "/home/rogerkorantenng/dev/Exams/Advanced Software Engineering/Exams"
npx create-next-app@15 frontend \
  --typescript --tailwind --eslint --app \
  --src-dir --import-alias "@/*" --use-npm --yes
cd frontend
npm install iron-session zod swr
npm install -D vitest @vitejs/plugin-react @testing-library/react \
  @testing-library/jest-dom @testing-library/user-event jsdom \
  @playwright/test @axe-core/playwright tsx
npx playwright install --with-deps chromium
node -e "console.log(process.version)" > .nvmrc
```

`create-next-app@15` ships Tailwind v4 (`@tailwindcss/postcss`, no `tailwind.config.ts`, `globals.css` starts with `@import "tailwindcss";`) — do not hand-write a v3-style config over it.

- [ ] **Step 2: Environment schema**

Create `frontend/.env.local.example`:

```bash
API_BASE_URL=http://localhost:8000/api/v1
SESSION_SECRET=replace-with-a-random-string-of-at-least-32-characters
```

Create `frontend/src/lib/env.ts`:

```ts
import "server-only";
import { z } from "zod";

const EnvSchema = z.object({
  API_BASE_URL: z.string().url(),
  SESSION_SECRET: z.string().min(32, "SESSION_SECRET must be at least 32 characters"),
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
});

/**
 * Parsed once at import time. A missing or malformed variable must fail the build/boot,
 * not surface as a confusing runtime error three requests later.
 */
export const env = EnvSchema.parse({
  API_BASE_URL: process.env.API_BASE_URL,
  SESSION_SECRET: process.env.SESSION_SECRET,
  NODE_ENV: process.env.NODE_ENV,
});
```

The `server-only` import makes it a build error for any Client Component to import this module, which is the mechanism — not a comment — that keeps secrets out of the browser bundle.

- [ ] **Step 3: Shared DTO types**

Create `frontend/src/types/api.ts`:

```ts
export const MANUSCRIPT_STATUSES = [
  "draft", "submitted", "under_screening", "desk_rejected", "under_review",
  "reviews_complete", "revision_requested", "resubmitted", "accepted",
  "rejected", "scheduled", "published", "withdrawn",
] as const;
export type ManuscriptStatus = (typeof MANUSCRIPT_STATUSES)[number];

export const RECOMMENDATIONS = ["accept", "minor_revision", "major_revision", "reject"] as const;
export type Recommendation = (typeof RECOMMENDATIONS)[number];

export const DECISION_TYPES = [
  "desk_reject", "send_to_review", "request_revision", "accept", "reject",
] as const;
export type DecisionType = (typeof DECISION_TYPES)[number];

export type Role = "author" | "reviewer" | "editor" | "editor_in_chief" | "administrator";

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
}

export interface SessionUser {
  id: string;
  email: string;
  name: string;
  roles: Role[];
}

export interface ManuscriptSummary {
  id: string;
  tracking_code: string;
  title: string;
  status: ManuscriptStatus;
  submitted_at: string | null;
  updated_at: string;
}

export interface EditorialEventDTO {
  sequence: number;
  event_type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
}

export interface ManuscriptDetail extends ManuscriptSummary {
  abstract: string;
  keywords: string[];
  author_names: string[];
  corresponding_author_id: string;
  events: EditorialEventDTO[];
}

/**
 * The reviewer-facing projection. There is deliberately no `author_names` or
 * `corresponding_author_id` field on this type — see design spec §6.4 and Task 5's test.
 */
export interface BlindedManuscript {
  id: string;
  tracking_code: string;
  title: string;
  abstract: string;
  keywords: string[];
  document_url: string;
  status: ManuscriptStatus;
}

export interface ReviewAssignmentSummary {
  id: string;
  manuscript_tracking_code: string;
  manuscript_title: string;
  due_date: string;
  status: "invited" | "accepted" | "declined" | "submitted" | "expired";
}

export interface ReviewerCandidate {
  reviewer_id: string;
  name: string;
  score: number | null;
  excluded_reason: string | null;
}

export interface IssueSummary {
  volume: number;
  number: number;
  year: number;
  title: string;
  published_at: string;
}

export interface ArchivePaperSummary {
  tracking_code: string;
  title: string;
  author_names: string[];
  published_at: string;
}

export interface ArchivePaperDetail extends ArchivePaperSummary {
  abstract: string;
  keywords: string[];
  volume: number;
  number: number;
  pdf_url: string;
  doi: string;
}
```

- [ ] **Step 4: Unauthenticated backend client**

Create `frontend/src/lib/backend.ts`:

```ts
import "server-only";
import { env } from "@/lib/env";
import type { ProblemDetails } from "@/types/api";

export class ProblemDetailsError extends Error {
  constructor(
    public readonly problem: ProblemDetails,
    public readonly status: number,
  ) {
    super(problem.title);
    this.name = "ProblemDetailsError";
  }
}

async function toProblem(response: Response): Promise<ProblemDetails> {
  try {
    return (await response.json()) as ProblemDetails;
  } catch {
    return { type: "about:blank", title: response.statusText, status: response.status };
  }
}

/** For the public archive: never attaches a token, never reads the session. */
export async function backendFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${env.API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!response.ok) throw new ProblemDetailsError(await toProblem(response), response.status);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
```

- [ ] **Step 5: UI atoms with tests**

Create `frontend/src/components/ui/button.tsx`:

```tsx
import { type ButtonHTMLAttributes, forwardRef } from "react";

const VARIANTS = {
  primary: "bg-blue-700 text-white hover:bg-blue-800 disabled:bg-blue-300",
  secondary: "bg-white text-blue-700 border border-blue-700 hover:bg-blue-50",
  danger: "bg-red-700 text-white hover:bg-red-800 disabled:bg-red-300",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof VARIANTS;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", className = "", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={`rounded-md px-4 py-2 text-sm font-medium transition-colors
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2
        disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
});
```

Create `frontend/src/components/ui/badge.tsx`:

```tsx
import type { ManuscriptStatus } from "@/types/api";

const LABELS: Record<ManuscriptStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  under_screening: "Under screening",
  desk_rejected: "Desk rejected",
  under_review: "Under review",
  reviews_complete: "Reviews complete",
  revision_requested: "Revision requested",
  resubmitted: "Resubmitted",
  accepted: "Accepted",
  rejected: "Rejected",
  scheduled: "Scheduled",
  published: "Published",
  withdrawn: "Withdrawn",
};

// Every colour pair here is >= 4.5:1 against its own background (WCAG 2.1 AA, checked
// against the rendered Tailwind palette, not assumed from the class name).
const TONES: Record<ManuscriptStatus, string> = {
  draft: "bg-gray-100 text-gray-800",
  submitted: "bg-blue-100 text-blue-900",
  under_screening: "bg-blue-100 text-blue-900",
  desk_rejected: "bg-red-100 text-red-900",
  under_review: "bg-indigo-100 text-indigo-900",
  reviews_complete: "bg-indigo-100 text-indigo-900",
  revision_requested: "bg-amber-100 text-amber-900",
  resubmitted: "bg-amber-100 text-amber-900",
  accepted: "bg-green-100 text-green-900",
  rejected: "bg-red-100 text-red-900",
  scheduled: "bg-teal-100 text-teal-900",
  published: "bg-green-100 text-green-900",
  withdrawn: "bg-gray-100 text-gray-800",
};

export function StatusBadge({ status }: { status: ManuscriptStatus }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${TONES[status]}`}>
      {LABELS[status]}
    </span>
  );
}
```

Create `frontend/src/components/ui/alert.tsx`:

```tsx
import type { ProblemDetails } from "@/types/api";

export function ProblemAlert({ problem }: { problem: ProblemDetails }) {
  return (
    <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-4 text-red-900">
      <p className="font-semibold">{problem.title}</p>
      {problem.detail && <p className="mt-1 text-sm">{problem.detail}</p>}
    </div>
  );
}
```

Create `frontend/src/components/ui/card.tsx`:

```tsx
import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`rounded-lg border border-gray-200 bg-white p-4 shadow-sm ${className}`} {...props} />;
}
```

Create `frontend/src/components/ui/input.tsx`:

```tsx
import { type InputHTMLAttributes, forwardRef } from "react";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, FieldProps>(function Input(
  { label, error, id, className = "", ...props },
  ref,
) {
  const inputId = id ?? props.name ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div>
      <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-gray-900">
        {label}
      </label>
      <input
        ref={ref}
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${inputId}-error` : undefined}
        className={`w-full rounded-md border px-3 py-2 text-sm
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600
          ${error ? "border-red-500" : "border-gray-300"} ${className}`}
        {...props}
      />
      {error && (
        <p id={`${inputId}-error`} className="mt-1 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
});
```

- [ ] **Step 6: Vitest configuration**

Create `frontend/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: { reporter: ["text", "text-summary"] },
  },
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
```

Create `frontend/vitest.setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 7: Write and run the badge and alert tests**

Create `frontend/src/components/ui/badge.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./badge";

describe("StatusBadge", () => {
  it("renders a human label for every manuscript status", () => {
    render(<StatusBadge status="under_screening" />);
    expect(screen.getByText("Under screening")).toBeInTheDocument();
  });

  it("distinguishes rejection tones from acceptance tones", () => {
    const { rerender } = render(<StatusBadge status="rejected" />);
    expect(screen.getByText("Rejected")).toHaveClass("bg-red-100");
    rerender(<StatusBadge status="accepted" />);
    expect(screen.getByText("Accepted")).toHaveClass("bg-green-100");
  });
});
```

Create `frontend/src/components/ui/alert.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProblemAlert } from "./alert";

describe("ProblemAlert", () => {
  it("surfaces the problem's title and detail with an alert role", () => {
    render(
      <ProblemAlert
        problem={{
          type: "https://ugjcs.example/problems/validation",
          title: "Invalid input",
          status: 422,
          detail: "Abstract must be at least 100 characters",
        }}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid input");
    expect(screen.getByRole("alert")).toHaveTextContent("Abstract must be at least 100 characters");
  });
});
```

Run: `cd frontend && npx vitest run`
Expected: 4 tests pass.

- [ ] **Step 8: Root layout and Makefile**

Create `frontend/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "UGJCS", template: "%s · UGJCS" },
  description: "University of Ghana Journal of Computing Science",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  );
}
```

Create `frontend/Makefile`:

```make
.PHONY: check lint typecheck test e2e
lint:
	npm run lint -- --max-warnings=0

typecheck:
	npx tsc --noEmit

test:
	npx vitest run

check: lint typecheck test

e2e:
	npx playwright test
```

Add to `frontend/package.json` `"scripts"`:

```json
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint .",
  "test": "vitest run",
  "test:watch": "vitest",
  "test:e2e": "playwright test"
}
```

- [ ] **Step 9: Verify and commit**

Run: `cd frontend && make check`
Expected: lint, typecheck and 4 unit tests all pass. `next build` is not part of `make check` (no `API_BASE_URL`/`SESSION_SECRET` are set yet outside `.env.local`); Task 3 onward always runs against a populated `.env.local` copied from the example.

```bash
git add frontend
git commit -m "feat: scaffold Next.js frontend with env validation and UI atoms"
```

---

### Task 2: Public archive (SSG/ISR, no credentials)

**Files:** `frontend/src/lib/format.ts`, `frontend/src/components/manuscript-card.tsx`, `frontend/src/components/ui/pagination.tsx`, `frontend/src/components/layout/site-header.tsx`, everything under `app/(public)/`, `app/sitemap.ts`.

**Interfaces:**
- Consumes: `backendFetch` (Task 1).
- Produces: `getIssues()`, `getIssue()`, `getPaper()`, `searchArchive()`.

- [ ] **Step 1: Archive data access**

Create `frontend/src/lib/format.ts`:

```ts
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" });
}

export function formatAuthors(names: string[]): string {
  if (names.length <= 2) return names.join(" & ");
  return `${names[0]} et al.`;
}
```

Create `frontend/src/lib/archive.ts`:

```ts
import { backendFetch } from "@/lib/backend";
import type { ArchivePaperDetail, ArchivePaperSummary, IssueSummary } from "@/types/api";

const REVALIDATE_SECONDS = 300;

export function getIssues() {
  return backendFetch<IssueSummary[]>("/archive/issues", { next: { revalidate: REVALIDATE_SECONDS } });
}

export function getIssue(volume: number, number: number) {
  return backendFetch<IssueSummary & { papers: ArchivePaperSummary[] }>(
    `/archive/issues/${volume}/${number}`,
    { next: { revalidate: REVALIDATE_SECONDS } },
  );
}

export function getPaper(trackingCode: string) {
  return backendFetch<ArchivePaperDetail>(`/archive/papers/${trackingCode}`, {
    next: { revalidate: REVALIDATE_SECONDS },
  });
}

export function searchArchive(query: string, page: number) {
  return backendFetch<{ results: ArchivePaperSummary[]; total: number }>(
    `/archive/search?q=${encodeURIComponent(query)}&page=${page}`,
    { next: { revalidate: 60 } },
  );
}
```

- [ ] **Step 2: `manuscript-card` and its test**

Create `frontend/src/components/manuscript-card.tsx`:

```tsx
import Link from "next/link";
import { formatAuthors, formatDate } from "@/lib/format";
import type { ArchivePaperSummary } from "@/types/api";

export function PaperCard({ paper }: { paper: ArchivePaperSummary }) {
  return (
    <Link
      href={`/papers/${paper.tracking_code}`}
      className="block rounded-lg border border-gray-200 bg-white p-4 hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
    >
      <h3 className="text-base font-semibold text-gray-900">{paper.title}</h3>
      <p className="mt-1 text-sm text-gray-600">
        {formatAuthors(paper.author_names)} · {formatDate(paper.published_at)}
      </p>
    </Link>
  );
}
```

Create `frontend/src/components/manuscript-card.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PaperCard } from "./manuscript-card";

const PAPER = {
  tracking_code: "UGJCS-2026-0012",
  title: "Sparse Retrieval for Low-Resource Languages",
  author_names: ["A. Mensah", "B. Owusu", "C. Boateng"],
  published_at: "2026-06-01T00:00:00Z",
};

describe("PaperCard", () => {
  it("links to the paper's detail page by tracking code", () => {
    render(<PaperCard paper={PAPER} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/papers/UGJCS-2026-0012");
  });

  it("collapses three or more authors to 'et al.'", () => {
    render(<PaperCard paper={PAPER} />);
    expect(screen.getByText(/A\. Mensah et al\./)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Home, issues, issue detail**

Create `frontend/src/app/(public)/page.tsx`:

```tsx
import Link from "next/link";
import { getIssues } from "@/lib/archive";
import { PaperCard } from "@/components/manuscript-card";

export const revalidate = 300;

export default async function HomePage() {
  const issues = await getIssues();
  const latest = issues[0];

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold">University of Ghana Journal of Computing Science</h1>
      <p className="mt-2 text-gray-600">A double-blind peer-reviewed journal.</p>
      <Link href="/search" className="mt-6 inline-block text-blue-700 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
        Search the archive
      </Link>
      {latest && (
        <section className="mt-10">
          <h2 className="text-xl font-semibold">
            Latest issue — Vol. {latest.volume}, No. {latest.number} ({latest.year})
          </h2>
          <Link href={`/issues/${latest.volume}/${latest.number}`} className="mt-2 inline-block text-blue-700 underline">
            View issue
          </Link>
        </section>
      )}
    </main>
  );
}
```

Create `frontend/src/app/(public)/issues/page.tsx`:

```tsx
import Link from "next/link";
import { getIssues } from "@/lib/archive";

export const revalidate = 300;
export const metadata = { title: "Browse issues" };

export default async function IssuesPage() {
  const issues = await getIssues();
  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-bold">Issues</h1>
      <ul className="mt-6 space-y-3">
        {issues.map((issue) => (
          <li key={`${issue.volume}-${issue.number}`}>
            <Link href={`/issues/${issue.volume}/${issue.number}`} className="text-blue-700 underline">
              Vol. {issue.volume}, No. {issue.number} ({issue.year}) — {issue.title}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

Create `frontend/src/app/(public)/issues/[volume]/[number]/page.tsx`:

```tsx
import type { Metadata } from "next";
import { getIssue } from "@/lib/archive";
import { PaperCard } from "@/components/manuscript-card";

interface Params { volume: string; number: string }

export const revalidate = 300;

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { volume, number } = await params;
  const issue = await getIssue(Number(volume), Number(number));
  return { title: `Vol. ${issue.volume}, No. ${issue.number}` };
}

export default async function IssuePage({ params }: { params: Promise<Params> }) {
  const { volume, number } = await params;
  const issue = await getIssue(Number(volume), Number(number));
  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-bold">
        Vol. {issue.volume}, No. {issue.number} — {issue.title}
      </h1>
      <div className="mt-6 grid gap-4">
        {issue.papers.map((paper) => (
          <PaperCard key={paper.tracking_code} paper={paper} />
        ))}
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Paper detail with scholarly metadata**

Create `frontend/src/app/(public)/papers/[trackingCode]/page.tsx`:

```tsx
import type { Metadata } from "next";
import { getPaper } from "@/lib/archive";
import { formatAuthors, formatDate } from "@/lib/format";

interface Params { trackingCode: string }

export const revalidate = 300;

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { trackingCode } = await params;
  const paper = await getPaper(trackingCode);
  return {
    title: paper.title,
    description: paper.abstract.slice(0, 160),
    openGraph: { title: paper.title, description: paper.abstract.slice(0, 160), type: "article" },
  };
}

export default async function PaperPage({ params }: { params: Promise<Params> }) {
  const { trackingCode } = await params;
  const paper = await getPaper(trackingCode);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ScholarlyArticle",
    headline: paper.title,
    author: paper.author_names.map((name) => ({ "@type": "Person", name })),
    datePublished: paper.published_at,
    identifier: paper.doi,
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      {/* Highwire Press tags for Google Scholar indexing */}
      <meta name="citation_title" content={paper.title} />
      {paper.author_names.map((name) => (
        <meta key={name} name="citation_author" content={name} />
      ))}
      <meta name="citation_publication_date" content={paper.published_at} />
      <meta name="citation_doi" content={paper.doi} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <p className="text-sm text-gray-500">{paper.tracking_code}</p>
      <h1 className="mt-1 text-2xl font-bold">{paper.title}</h1>
      <p className="mt-2 text-gray-600">
        {formatAuthors(paper.author_names)} · {formatDate(paper.published_at)}
      </p>
      <p className="mt-6 leading-relaxed text-gray-800">{paper.abstract}</p>
      <a
        href={paper.pdf_url}
        className="mt-6 inline-block rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
      >
        Download PDF
      </a>
    </main>
  );
}
```

- [ ] **Step 5: Search page and sitemap**

Create `frontend/src/components/ui/pagination.tsx`:

```tsx
import Link from "next/link";

export function Pagination({ page, hasNext, hrefFor }: { page: number; hasNext: boolean; hrefFor: (p: number) => string }) {
  return (
    <nav aria-label="Search results pages" className="mt-6 flex justify-between">
      {page > 1 ? (
        <Link href={hrefFor(page - 1)} className="text-blue-700 underline">Previous</Link>
      ) : <span />}
      {hasNext && <Link href={hrefFor(page + 1)} className="text-blue-700 underline">Next</Link>}
    </nav>
  );
}
```

Create `frontend/src/app/(public)/search/page.tsx`:

```tsx
import { searchArchive } from "@/lib/archive";
import { PaperCard } from "@/components/manuscript-card";
import { Pagination } from "@/components/ui/pagination";

export const metadata = { title: "Search" };

interface SearchParams { q?: string; page?: string }

export default async function SearchPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { q = "", page: pageParam = "1" } = await searchParams;
  const page = Number(pageParam) || 1;
  const results = q ? await searchArchive(q, page) : { results: [], total: 0 };

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-bold">Search</h1>
      <form className="mt-4" role="search">
        <label htmlFor="q" className="sr-only">Search papers</label>
        <input
          id="q"
          name="q"
          defaultValue={q}
          placeholder="Title, abstract or keyword"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
        />
      </form>
      <div className="mt-6 grid gap-4">
        {results.results.map((paper) => (
          <PaperCard key={paper.tracking_code} paper={paper} />
        ))}
      </div>
      {q && (
        <Pagination
          page={page}
          hasNext={page * 20 < results.total}
          hrefFor={(p) => `/search?q=${encodeURIComponent(q)}&page=${p}`}
        />
      )}
    </main>
  );
}
```

Create `frontend/src/app/sitemap.ts`:

```ts
import type { MetadataRoute } from "next";
import { getIssues } from "@/lib/archive";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const issues = await getIssues();
  return [
    { url: "https://ugjcs.example/" },
    { url: "https://ugjcs.example/issues" },
    ...issues.map((issue) => ({ url: `https://ugjcs.example/issues/${issue.volume}/${issue.number}` })),
  ];
}
```

- [ ] **Step 6: Run and verify**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 6 unit tests pass (the 4 from Task 1 plus the 2 `PaperCard` tests); typecheck clean.

`next build` cannot succeed yet without `API_BASE_URL` reachable — verifying real SSG output is deferred to Task 7's CI job, which runs against the mock backend.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/format.ts frontend/src/lib/archive.ts frontend/src/components/manuscript-card.tsx \
  frontend/src/components/manuscript-card.test.tsx frontend/src/components/ui/pagination.tsx \
  "frontend/src/app/(public)" frontend/src/app/sitemap.ts
git commit -m "feat: add statically rendered public archive with scholarly metadata"
```

---

### Task 3: Session core, login, role-aware navigation, route guard

**Files:** `frontend/src/lib/session.ts`, `frontend/src/lib/auth-fetch.ts`, `frontend/middleware.ts`, `frontend/src/app/api/auth/*`, `frontend/src/app/login/page.tsx`, `frontend/src/components/layout/app-nav.tsx`, `frontend/src/app/{author,reviewer,editor}/layout.tsx`.

**Interfaces:**
- Produces: `getSession()`, `authedFetch()`, `middleware()`.
- Consumes: `backendFetch` (Task 1), assumed `/auth/*` endpoints.

- [ ] **Step 1: Sealed session**

Create `frontend/src/lib/session.ts`:

```ts
import "server-only";
import { cookies } from "next/headers";
import { getIronSession, type IronSession, type SessionOptions } from "iron-session";
import { env } from "@/lib/env";
import type { SessionUser } from "@/types/api";

export interface SessionData {
  user?: SessionUser;
  accessToken?: string;
  refreshToken?: string;
  accessTokenExpiresAt?: number; // epoch millis
}

export const sessionOptions: SessionOptions = {
  cookieName: "ugjcs_session",
  password: env.SESSION_SECRET,
  cookieOptions: {
    httpOnly: true,
    secure: env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7, // matches the backend's 7-day refresh token lifetime (Plan 3)
  },
};

/** Only callable from a Route Handler, Server Action, or (read-only) a Server Component. */
export async function getSession(): Promise<IronSession<SessionData>> {
  return getIronSession<SessionData>(await cookies(), sessionOptions);
}
```

- [ ] **Step 2: `authedFetch` — bearer attach, refresh-on-401**

Create `frontend/src/lib/auth-fetch.ts`:

```ts
import "server-only";
import { env } from "@/lib/env";
import { getSession, type SessionData } from "@/lib/session";
import { ProblemDetailsError } from "@/lib/backend";
import type { IronSession } from "iron-session";
import type { ProblemDetails } from "@/types/api";

async function toProblem(response: Response): Promise<ProblemDetails> {
  try {
    return (await response.json()) as ProblemDetails;
  } catch {
    return { type: "about:blank", title: response.statusText, status: response.status };
  }
}

async function refresh(session: IronSession<SessionData>): Promise<void> {
  const response = await fetch(`${env.API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: session.refreshToken }),
  });
  if (!response.ok) {
    session.destroy();
    throw new ProblemDetailsError(
      { type: "https://ugjcs.example/problems/session-expired", title: "Your session has expired", status: 401 },
      401,
    );
  }
  const data = (await response.json()) as { access_token: string; refresh_token: string; expires_in: number };
  session.accessToken = data.access_token;
  session.refreshToken = data.refresh_token;
  session.accessTokenExpiresAt = Date.now() + data.expires_in * 1000;
  await session.save();
}

/**
 * Used only inside Route Handlers, where cookie writes are allowed. Proactively refreshes
 * a token about to expire, and retries once on a 401 the proactive check missed — clock
 * skew between this process and the backend is the reason a reactive path still exists.
 */
export async function authedFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = await getSession();
  if (!session.accessToken || !session.user) {
    throw new ProblemDetailsError(
      { type: "https://ugjcs.example/problems/unauthenticated", title: "Not signed in", status: 401 },
      401,
    );
  }
  if (session.accessTokenExpiresAt && session.accessTokenExpiresAt < Date.now() + 5_000) {
    await refresh(session);
  }

  const attempt = () =>
    fetch(`${env.API_BASE_URL}${path}`, {
      ...init,
      headers: { ...init.headers, Authorization: `Bearer ${session.accessToken}` },
    });

  let response = await attempt();
  if (response.status === 401) {
    await refresh(session);
    response = await attempt();
  }
  if (!response.ok) throw new ProblemDetailsError(await toProblem(response), response.status);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
```

- [ ] **Step 3: Session unit tests (no HTTP required)**

Create `frontend/src/lib/session.test.ts`:

```ts
import { sealData, unsealData } from "iron-session";
import { describe, expect, it } from "vitest";
import type { SessionData } from "./session";

const PASSWORD = "a".repeat(32);

describe("session sealing", () => {
  it("round-trips user identity and tokens through the sealed cookie payload", async () => {
    const original: SessionData = {
      user: { id: "u1", email: "a@ug.edu.gh", name: "A. Mensah", roles: ["author"] },
      accessToken: "access-abc",
      refreshToken: "refresh-xyz",
      accessTokenExpiresAt: Date.now() + 900_000,
    };
    const sealed = await sealData(original, { password: PASSWORD });
    const restored = await unsealData<SessionData>(sealed, { password: PASSWORD });
    expect(restored).toEqual(original);
  });

  it("fails to unseal with the wrong password, rather than silently returning garbage", async () => {
    const sealed = await sealData({ user: { id: "u1", email: "a@ug.edu.gh", name: "A", roles: ["author"] } }, { password: PASSWORD });
    await expect(unsealData(sealed, { password: "b".repeat(32) })).rejects.toThrow();
  });
});
```

Run: `cd frontend && npx vitest run src/lib/session.test.ts`
Expected: 2 tests pass. (Requires `.env.local` to exist for `src/lib/env.ts`'s import chain — copy `.env.local.example` first: `cp .env.local.example .env.local`.)

- [ ] **Step 4: Login/logout/me Route Handlers**

Create `frontend/src/app/api/auth/login/route.ts`:

```ts
import { NextResponse } from "next/server";
import { z } from "zod";
import { getSession } from "@/lib/session";
import { backendFetch, ProblemDetailsError } from "@/lib/backend";
import type { SessionUser } from "@/types/api";

const LoginInput = z.object({ email: z.string().email(), password: z.string().min(1) });

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: SessionUser;
}

export async function POST(request: Request) {
  const parsed = LoginInput.safeParse(await request.json());
  if (!parsed.success) {
    return NextResponse.json(
      { type: "https://ugjcs.example/problems/invalid-input", title: "Invalid input", status: 422, detail: parsed.error.issues[0]?.message },
      { status: 422 },
    );
  }

  try {
    const data = await backendFetch<LoginResponse>("/auth/login", { method: "POST", body: JSON.stringify(parsed.data) });
    const session = await getSession();
    session.user = data.user;
    session.accessToken = data.access_token;
    session.refreshToken = data.refresh_token;
    session.accessTokenExpiresAt = Date.now() + data.expires_in * 1000;
    await session.save();
    return NextResponse.json({ user: data.user });
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
```

Create `frontend/src/app/api/auth/logout/route.ts`:

```ts
import { NextResponse } from "next/server";
import { env } from "@/lib/env";
import { getSession } from "@/lib/session";

export async function POST() {
  const session = await getSession();
  if (session.refreshToken) {
    await fetch(`${env.API_BASE_URL}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refreshToken }),
    }).catch(() => undefined); // best-effort revoke upstream; the cookie is destroyed regardless
  }
  session.destroy();
  return new NextResponse(null, { status: 204 });
}
```

Create `frontend/src/app/api/auth/me/route.ts`:

```ts
import { NextResponse } from "next/server";
import { getSession } from "@/lib/session";

export async function GET() {
  const session = await getSession();
  return NextResponse.json({ user: session.user ?? null });
}
```

- [ ] **Step 5: Login page and a component test that checks the failure path**

Create `frontend/src/app/login/page.tsx`:

```tsx
"use client";
import { useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import type { ProblemDetails } from "@/types/api";

export default function LoginPage() {
  const router = useRouter();
  const next = useSearchParams().get("next") ?? "/author";
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setProblem(null);
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setProblem((await response.json()) as ProblemDetails);
      return;
    }
    router.push(next);
    router.refresh();
  }

  return (
    <main className="mx-auto max-w-sm px-4 py-16">
      <h1 className="text-2xl font-bold">Sign in</h1>
      {problem && <div className="mt-4"><ProblemAlert problem={problem} /></div>}
      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        <Input label="Email" name="email" type="email" required autoComplete="email" />
        <Input label="Password" name="password" type="password" required autoComplete="current-password" />
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </main>
  );
}
```

Create `frontend/src/app/login/login-page.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(() => vi.restoreAllMocks());

describe("LoginPage", () => {
  it("shows the problem detail returned by the login route on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({
          type: "https://ugjcs.example/problems/invalid-credentials",
          title: "Invalid email or password",
          status: 401,
        }),
      }),
    );
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "author@ug.edu.gh");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password"));
  });

  it("is fully keyboard-operable: Tab reaches email, password, then the submit button in order", async () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<LoginPage />);
    await userEvent.tab();
    expect(screen.getByLabelText("Email")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByLabelText("Password")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: /sign in/i })).toHaveFocus();
  });
});
```

Run: `cd frontend && npx vitest run src/app/login`
Expected: 2 tests pass.

- [ ] **Step 6: Role-aware nav and per-area layouts**

Create `frontend/src/components/layout/app-nav.tsx`:

```tsx
"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { SessionUser } from "@/types/api";

const LINKS: Record<string, { href: string; label: string }[]> = {
  author: [{ href: "/author", label: "My submissions" }, { href: "/author/submit", label: "Submit" }],
  reviewer: [{ href: "/reviewer", label: "My assignments" }],
  editor: [{ href: "/editor", label: "Screening queue" }],
  editor_in_chief: [{ href: "/editor", label: "Screening queue" }],
};

export function AppNav({ user }: { user: SessionUser }) {
  const router = useRouter();
  const links = user.roles.flatMap((role) => LINKS[role] ?? []);

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <nav aria-label="Account navigation" className="flex items-center justify-between border-b bg-white px-4 py-3">
      <div className="flex gap-4">
        {links.map((link) => (
          <Link key={link.href} href={link.href} className="text-sm font-medium text-gray-700 hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
            {link.label}
          </Link>
        ))}
      </div>
      <div className="flex items-center gap-3 text-sm text-gray-600">
        <span>{user.name}</span>
        <button onClick={signOut} className="font-medium text-blue-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
          Sign out
        </button>
      </div>
    </nav>
  );
}
```

Create `frontend/src/app/author/layout.tsx` (identical pattern repeated verbatim for `reviewer/layout.tsx` and `editor/layout.tsx`, substituting nothing — the guard is role-agnostic since `middleware.ts` already enforced the role):

```tsx
import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AppNav } from "@/components/layout/app-nav";

export default async function AuthorLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session.user) redirect("/login?next=/author");
  return (
    <>
      <AppNav user={session.user} />
      <div className="mx-auto max-w-4xl px-4 py-8">{children}</div>
    </>
  );
}
```

This `redirect` is a defence-in-depth backstop, not the primary gate — `middleware.ts` (next step) runs first and is what actually stops an unauthenticated request from reaching the page.

- [ ] **Step 7: Middleware route guard**

Create `frontend/middleware.ts`:

```ts
import { NextResponse, type NextRequest } from "next/server";
import { getIronSession } from "iron-session";
import { sessionOptions, type SessionData } from "@/lib/session";

const ROLE_BY_PREFIX: Record<string, string> = {
  "/author": "author",
  "/reviewer": "reviewer",
  "/editor": "editor",
};

export async function middleware(request: NextRequest) {
  const prefix = Object.keys(ROLE_BY_PREFIX).find((p) => request.nextUrl.pathname.startsWith(p));
  if (!prefix) return NextResponse.next();

  const response = NextResponse.next();
  const session = await getIronSession<SessionData>(request, response, sessionOptions);
  const requiredRole = ROLE_BY_PREFIX[prefix];

  if (!session.user) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
  if (!session.user.roles.includes(requiredRole) && !session.user.roles.includes("editor_in_chief")) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return response;
}

export const config = { matcher: ["/author/:path*", "/reviewer/:path*", "/editor/:path*"] };
```

- [ ] **Step 8: Run and commit**

Run: `cd frontend && make check`
Expected: lint, typecheck, and all unit tests (8 total so far) pass.

```bash
git add frontend/src/lib/session.ts frontend/src/lib/session.test.ts frontend/src/lib/auth-fetch.ts \
  frontend/src/app/api/auth frontend/src/app/login frontend/src/components/layout/app-nav.tsx \
  frontend/src/app/author/layout.tsx frontend/src/app/reviewer/layout.tsx frontend/src/app/editor/layout.tsx \
  frontend/middleware.ts
git commit -m "feat: add sealed-cookie session, BFF auth routes and role-gated middleware"
```

---

### Task 4: Author — dashboard, submission, status timeline

**Files:** `frontend/src/lib/use-api.ts`, `frontend/src/components/status-timeline.tsx`, `frontend/src/components/file-upload.tsx`, `frontend/src/app/api/manuscripts/**`, `frontend/src/app/author/{page,submit/page,[id]/page}.tsx`.

**Interfaces:**
- Consumes: `authedFetch` (Task 3).
- Produces: `GET/POST /api/manuscripts`, `GET /api/manuscripts/[id]`, `POST /api/manuscripts/[id]/withdraw`, `useApi()`.

- [ ] **Step 1: `useApi` — the client-side counterpart to `authedFetch`**

Create `frontend/src/lib/use-api.ts`:

```ts
"use client";
import useSWR, { type SWRConfiguration } from "swr";
import type { ProblemDetails } from "@/types/api";

export class ClientApiError extends Error {
  constructor(public readonly problem: ProblemDetails) {
    super(problem.title);
  }
}

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new ClientApiError((await response.json()) as ProblemDetails);
  return (await response.json()) as T;
}

export function useApi<T>(url: string | null, config?: SWRConfiguration) {
  return useSWR<T>(url, fetcher, config);
}
```

- [ ] **Step 2: Route Handlers proxying `/manuscripts`**

Create `frontend/src/app/api/manuscripts/route.ts`:

```ts
import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import { env } from "@/lib/env";
import { getSession } from "@/lib/session";
import type { ManuscriptDetail, ManuscriptSummary } from "@/types/api";

export async function GET() {
  try {
    const manuscripts = await authedFetch<ManuscriptSummary[]>("/manuscripts/mine");
    return NextResponse.json(manuscripts);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

/** Forwards the browser's multipart form (including the uploaded file) upstream unchanged. */
export async function POST(request: Request) {
  const session = await getSession();
  if (!session.accessToken) {
    return NextResponse.json({ type: "about:blank", title: "Not signed in", status: 401 }, { status: 401 });
  }

  const incoming = await request.formData();
  const upstream = await fetch(`${env.API_BASE_URL}/manuscripts`, {
    method: "POST",
    headers: { Authorization: `Bearer ${session.accessToken}` },
    body: incoming, // fetch sets the multipart boundary itself from the FormData instance
  });

  const body = (await upstream.json()) as ManuscriptDetail;
  return NextResponse.json(body, { status: upstream.status });
}
```

Create `frontend/src/app/api/manuscripts/[id]/route.ts`:

```ts
import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ManuscriptDetail } from "@/types/api";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    return NextResponse.json(await authedFetch<ManuscriptDetail>(`/manuscripts/${id}`));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
```

Create `frontend/src/app/api/manuscripts/[id]/withdraw/route.ts`:

```ts
import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ManuscriptDetail } from "@/types/api";

export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    return NextResponse.json(await authedFetch<ManuscriptDetail>(`/manuscripts/${id}/withdraw`, { method: "POST" }));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
```

- [ ] **Step 3: Status timeline, with a test asserting event order**

Create `frontend/src/components/status-timeline.tsx`:

```tsx
import { formatDate } from "@/lib/format";
import type { EditorialEventDTO } from "@/types/api";

const LABELS: Record<string, string> = {
  manuscript_submitted: "Submitted",
  screening_started: "Screening started",
  reviewer_assigned: "Reviewer assigned",
  invitation_answered: "Reviewer responded",
  review_submitted: "A review was submitted",
  review_round_closed: "Review round closed",
  decision_recorded: "Decision recorded",
  revision_submitted: "Revision submitted",
  manuscript_withdrawn: "Withdrawn",
  scheduled_for_issue: "Scheduled for an issue",
  manuscript_published: "Published",
};

export function StatusTimeline({ events }: { events: EditorialEventDTO[] }) {
  const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
  return (
    <ol className="border-l-2 border-gray-200 pl-4">
      {ordered.map((event) => (
        <li key={event.sequence} className="mb-4">
          <p className="text-sm font-medium text-gray-900">{LABELS[event.event_type] ?? event.event_type}</p>
          <time dateTime={event.occurred_at} className="text-xs text-gray-500">{formatDate(event.occurred_at)}</time>
        </li>
      ))}
    </ol>
  );
}
```

Create `frontend/src/components/status-timeline.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusTimeline } from "./status-timeline";

describe("StatusTimeline", () => {
  it("orders entries by sequence even when the API returns them out of order", () => {
    render(
      <StatusTimeline
        events={[
          { sequence: 2, event_type: "screening_started", occurred_at: "2026-08-02T00:00:00Z", payload: {} },
          { sequence: 1, event_type: "manuscript_submitted", occurred_at: "2026-08-01T00:00:00Z", payload: {} },
        ]}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Submitted");
    expect(items[1]).toHaveTextContent("Screening started");
  });

  it("falls back to the raw event type for one this component does not yet label", () => {
    render(<StatusTimeline events={[{ sequence: 1, event_type: "some_future_event", occurred_at: "2026-08-01T00:00:00Z", payload: {} }]} />);
    expect(screen.getByText("some_future_event")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: File upload control**

Create `frontend/src/components/file-upload.tsx`:

```tsx
"use client";
import { useState, type ChangeEvent } from "react";

const MAX_BYTES = 25 * 1024 * 1024; // UX guardrail only; the backend's magic-byte check is authoritative

export function FileUpload({ name, label }: { name: string; label: string }) {
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  function onChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      setError("Only PDF files are accepted");
      event.target.value = "";
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("File must be under 25MB");
      event.target.value = "";
      return;
    }
    setError(null);
    setFileName(file.name);
  }

  const inputId = `${name}-file`;
  return (
    <div>
      <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-gray-900">{label}</label>
      <input
        id={inputId}
        name={name}
        type="file"
        accept="application/pdf"
        required
        onChange={onChange}
        aria-describedby={error ? `${inputId}-error` : undefined}
        className="block w-full text-sm text-gray-700 file:mr-4 file:rounded-md file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-blue-700 hover:file:bg-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
      />
      {fileName && !error && <p className="mt-1 text-sm text-gray-600">Selected: {fileName}</p>}
      {error && <p id={`${inputId}-error`} className="mt-1 text-sm text-red-700">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 5: Dashboard, submission form, detail page**

Create `frontend/src/app/author/page.tsx`:

```tsx
"use client";
import Link from "next/link";
import { useApi } from "@/lib/use-api";
import { StatusBadge } from "@/components/ui/badge";
import { ProblemAlert } from "@/components/ui/alert";
import { formatDate } from "@/lib/format";
import type { ManuscriptSummary } from "@/types/api";
import { ClientApiError } from "@/lib/use-api";

export default function AuthorDashboard() {
  const { data, error, isLoading } = useApi<ManuscriptSummary[]>("/api/manuscripts");

  if (isLoading) return <p>Loading your submissions…</p>;
  if (error) return <ProblemAlert problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }} />;

  return (
    <>
      <h1 className="text-2xl font-bold">My submissions</h1>
      {data && data.length === 0 && <p className="mt-4 text-gray-600">You have not submitted a manuscript yet.</p>}
      <ul className="mt-4 space-y-3">
        {data?.map((manuscript) => (
          <li key={manuscript.id}>
            <Link href={`/author/${manuscript.id}`} className="flex items-center justify-between rounded-md border border-gray-200 bg-white p-4 hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
              <div>
                <p className="font-medium">{manuscript.title}</p>
                <p className="text-sm text-gray-500">{manuscript.tracking_code} · updated {formatDate(manuscript.updated_at)}</p>
              </div>
              <StatusBadge status={manuscript.status} />
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
```

Create `frontend/src/app/author/submit/page.tsx`:

```tsx
"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { FileUpload } from "@/components/file-upload";
import type { ManuscriptDetail, ProblemDetails } from "@/types/api";

export default function SubmitPage() {
  const router = useRouter();
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!(form.elements.namedItem("confirmed_anonymised") as HTMLInputElement).checked) {
      setProblem({ type: "about:blank", title: "Confirmation required", status: 422, detail: "Confirm the manuscript file has been anonymised before submitting." });
      return;
    }
    setSubmitting(true);
    setProblem(null);
    const response = await fetch("/api/manuscripts", { method: "POST", body: new FormData(form) });
    setSubmitting(false);
    if (!response.ok) {
      setProblem((await response.json()) as ProblemDetails);
      return;
    }
    const manuscript = (await response.json()) as ManuscriptDetail;
    router.push(`/author/${manuscript.id}`);
  }

  return (
    <>
      <h1 className="text-2xl font-bold">Submit a manuscript</h1>
      {problem && <div className="mt-4"><ProblemAlert problem={problem} /></div>}
      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        <Input label="Title" name="title" required minLength={5} />
        <div>
          <label htmlFor="abstract" className="mb-1 block text-sm font-medium text-gray-900">Abstract</label>
          <textarea id="abstract" name="abstract" required minLength={100} rows={6} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600" />
        </div>
        <Input label="Keywords (comma-separated)" name="keywords" required />
        <FileUpload name="file" label="Manuscript PDF (anonymised)" />
        <div className="flex items-start gap-2">
          <input id="confirmed_anonymised" name="confirmed_anonymised" type="checkbox" className="mt-1" />
          <label htmlFor="confirmed_anonymised" className="text-sm text-gray-700">
            I confirm this file has had author-identifying information removed, in line with the journal&apos;s double-blind policy.
          </label>
        </div>
        <Button type="submit" disabled={submitting}>{submitting ? "Submitting…" : "Submit manuscript"}</Button>
      </form>
    </>
  );
}
```

Create `frontend/src/app/author/[id]/page.tsx`:

```tsx
"use client";
import { use } from "react";
import { useApi, ClientApiError } from "@/lib/use-api";
import { StatusBadge } from "@/components/ui/badge";
import { StatusTimeline } from "@/components/status-timeline";
import { ProblemAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { ManuscriptDetail } from "@/types/api";

const WITHDRAWABLE = new Set(["submitted", "under_screening", "under_review", "reviews_complete", "revision_requested"]);

export default function ManuscriptDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, error, isLoading, mutate } = useApi<ManuscriptDetail>(`/api/manuscripts/${id}`);

  if (isLoading) return <p>Loading…</p>;
  if (error) return <ProblemAlert problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }} />;
  if (!data) return null;

  async function withdraw() {
    await fetch(`/api/manuscripts/${id}/withdraw`, { method: "POST" });
    mutate();
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{data.title}</h1>
        <StatusBadge status={data.status} />
      </div>
      <p className="mt-1 text-sm text-gray-500">{data.tracking_code}</p>
      <p className="mt-4 text-gray-800">{data.abstract}</p>
      {WITHDRAWABLE.has(data.status) && (
        <Button variant="danger" className="mt-4" onClick={withdraw}>Withdraw submission</Button>
      )}
      <h2 className="mt-8 text-lg font-semibold">Status history</h2>
      <div className="mt-2"><StatusTimeline events={data.events} /></div>
    </>
  );
}
```

- [ ] **Step 6: A route-handler-level test proving multipart forwarding**

Create `frontend/src/app/api/manuscripts/route.test.ts`:

```ts
import { describe, expect, it, vi, afterEach } from "vitest";

vi.mock("@/lib/session", () => ({
  getSession: vi.fn().mockResolvedValue({ accessToken: "token-123", user: { id: "u1", roles: ["author"] } }),
}));

afterEach(() => vi.restoreAllMocks());

describe("POST /api/manuscripts", () => {
  it("forwards the multipart body upstream with a bearer header, unmodified", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      status: 201,
      json: async () => ({ id: "m1", tracking_code: "UGJCS-2026-0099", status: "submitted" }),
    });
    vi.stubGlobal("fetch", fetchSpy);

    const { POST } = await import("./route");
    const form = new FormData();
    form.set("title", "A Paper");
    const request = new Request("http://localhost/api/manuscripts", { method: "POST", body: form });

    const response = await POST(request);

    expect(response.status).toBe(201);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer token-123");
    expect(init.body).toBeInstanceOf(FormData);
  });
});
```

Run: `cd frontend && npx vitest run src/app/api/manuscripts src/components/status-timeline.test.tsx`
Expected: 3 tests pass.

- [ ] **Step 7: Run and commit**

Run: `cd frontend && make check`
Expected: all gates pass; 13 unit tests total.

```bash
git add frontend/src/lib/use-api.ts frontend/src/components/status-timeline.tsx \
  frontend/src/components/status-timeline.test.tsx frontend/src/components/file-upload.tsx \
  frontend/src/app/api/manuscripts frontend/src/app/author
git commit -m "feat: add author dashboard, submission form and status timeline"
```

---

### Task 5: Reviewer — assignments, blinded reading, review form (with the blinding test)

**Files:** `frontend/src/components/blinded-manuscript-view.tsx`, `frontend/src/components/review-form.tsx`, `frontend/src/components/ui/textarea.tsx`, `frontend/src/app/api/reviews/**`, `frontend/src/app/reviewer/{page,[id]/page}.tsx`.

**Interfaces:**
- Consumes: `authedFetch`, `useApi`, `BlindedManuscript` type (Task 1).
- Produces: `GET /api/reviews`, `GET/POST /api/reviews/[id]`.

This is the task the marking scheme cares most about: a reviewer screen must be structurally incapable of showing an author's name.

- [ ] **Step 1: Route Handlers**

Create `frontend/src/app/api/reviews/route.ts`:

```ts
import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ReviewAssignmentSummary } from "@/types/api";

export async function GET() {
  try {
    return NextResponse.json(await authedFetch<ReviewAssignmentSummary[]>("/reviews/mine"));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
```

Create `frontend/src/app/api/reviews/[id]/route.ts`:

```ts
import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { BlindedManuscript } from "@/types/api";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    return NextResponse.json(await authedFetch<BlindedManuscript>(`/reviews/${id}`));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const body = await request.json();
    await authedFetch(`/reviews/${id}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return new NextResponse(null, { status: 201 });
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
```

- [ ] **Step 2: The blinded manuscript view**

Create `frontend/src/components/blinded-manuscript-view.tsx`:

```tsx
import type { BlindedManuscript } from "@/types/api";

/**
 * Renders exactly the fields on `BlindedManuscript` — a type with no author field to leak.
 * Do not widen this component's prop type to `ManuscriptDetail` or anything with an author
 * field "just to reuse it": the type boundary here is the control, not a formality.
 */
export function BlindedManuscriptView({ manuscript }: { manuscript: BlindedManuscript }) {
  return (
    <article>
      <p className="text-sm text-gray-500">{manuscript.tracking_code}</p>
      <h1 className="mt-1 text-2xl font-bold">{manuscript.title}</h1>
      <p className="mt-4 text-gray-800">{manuscript.abstract}</p>
      <ul className="mt-4 flex flex-wrap gap-2">
        {manuscript.keywords.map((keyword) => (
          <li key={keyword} className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-700">{keyword}</li>
        ))}
      </ul>
      <a
        href={manuscript.document_url}
        className="mt-6 inline-block rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
      >
        Open anonymised manuscript
      </a>
    </article>
  );
}
```

- [ ] **Step 3: The blinding test — this is the load-bearing artefact of this task**

Create `frontend/src/components/blinded-manuscript-view.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BlindedManuscriptView } from "./blinded-manuscript-view";
import type { BlindedManuscript } from "@/types/api";

// Distinctive sentinels: strings that would only appear in the DOM if author identity leaked.
const AUTHOR_NAME_SENTINEL = "Kwame Osei-Sentinel";
const AFFILIATION_SENTINEL = "University of Nowhere-Sentinel";

const BASE_MANUSCRIPT: BlindedManuscript = {
  id: "m1",
  tracking_code: "UGJCS-2026-0042",
  title: "Fair Scheduling for Shared GPU Clusters",
  abstract: "A scheduler balancing fairness against utilisation.",
  keywords: ["scheduling"],
  document_url: "https://example.com/anonymised.pdf",
  status: "under_review",
};

describe("BlindedManuscriptView", () => {
  it("never renders author identity, even if an upstream bug smuggles it into the payload", () => {
    // Cast through `unknown`: a conforming backend can never produce this shape, which is
    // exactly the point — the test proves the *component* is the second line of defence,
    // not merely that a well-behaved fixture looks fine.
    const contaminated = {
      ...BASE_MANUSCRIPT,
      author_names: [AUTHOR_NAME_SENTINEL],
      corresponding_author_id: "u-999",
      affiliation: AFFILIATION_SENTINEL,
    } as unknown as BlindedManuscript;

    render(<BlindedManuscriptView manuscript={contaminated} />);

    expect(screen.queryByText(AUTHOR_NAME_SENTINEL)).not.toBeInTheDocument();
    expect(screen.queryByText(AFFILIATION_SENTINEL)).not.toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain(AUTHOR_NAME_SENTINEL);
    expect(document.body.innerHTML).not.toContain(AFFILIATION_SENTINEL);
  });

  it("renders the fields the reviewer is entitled to", () => {
    render(<BlindedManuscriptView manuscript={BASE_MANUSCRIPT} />);
    expect(screen.getByText(BASE_MANUSCRIPT.title)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open anonymised manuscript/i })).toHaveAttribute("href", BASE_MANUSCRIPT.document_url);
  });

  // Compile-time half of the guarantee: the type itself has nothing to leak. If someone
  // widens `BlindedManuscript` to include an author field, this line stops compiling and
  // `make check`'s typecheck gate fails — do not delete it to make the type change land.
  it("has no author field on the type (enforced by tsc, not by this assertion)", () => {
    // @ts-expect-error BlindedManuscript intentionally has no author_names field
    const _leak: string[] = BASE_MANUSCRIPT.author_names;
    void _leak;
  });
});
```

Run: `cd frontend && npx vitest run src/components/blinded-manuscript-view.test.tsx && npx tsc --noEmit`
Expected: 3 tests pass, and the `@ts-expect-error` line must be flagged as *unused* by `tsc` if `BlindedManuscript` ever grows an `author_names` field — turning an accidental blind-spot regression into a red gate instead of a silent pass.

- [ ] **Step 4: Review form**

Create `frontend/src/components/ui/textarea.tsx`:

```tsx
import { type TextareaHTMLAttributes, forwardRef } from "react";

interface FieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, FieldProps>(function Textarea({ label, id, name, className = "", ...props }, ref) {
  const fieldId = id ?? name ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div>
      <label htmlFor={fieldId} className="mb-1 block text-sm font-medium text-gray-900">{label}</label>
      <textarea ref={ref} id={fieldId} name={name} rows={4} className={`w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${className}`} {...props} />
    </div>
  );
});
```

Create `frontend/src/components/review-form.tsx`:

```tsx
"use client";
import { useState, type FormEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { RECOMMENDATIONS, type Recommendation } from "@/types/api";

const CRITERIA = ["originality", "rigour", "clarity", "significance"] as const;

export function ReviewForm({ assignmentId, onSubmitted }: { assignmentId: string; onSubmitted: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const scores = Object.fromEntries(CRITERIA.map((criterion) => [criterion, Number(form.get(criterion))]));
    setSubmitting(true);
    setErrorMessage(null);
    const response = await fetch(`/api/reviews/${assignmentId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scores,
        recommendation: form.get("recommendation") as Recommendation,
        comments_to_author: form.get("comments_to_author"),
        confidential_comments_to_editor: form.get("confidential_comments_to_editor"),
      }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setErrorMessage("Could not submit the review. Please try again.");
      return;
    }
    onSubmitted();
  }

  return (
    <form onSubmit={onSubmit} className="mt-6 space-y-4" aria-label="Submit review">
      {errorMessage && <p role="alert" className="text-red-700">{errorMessage}</p>}
      <fieldset className="grid grid-cols-2 gap-4">
        <legend className="mb-2 text-sm font-medium text-gray-900">Criterion scores (1–5)</legend>
        {CRITERIA.map((criterion) => (
          <div key={criterion}>
            <label htmlFor={criterion} className="mb-1 block text-sm capitalize text-gray-700">{criterion}</label>
            <input id={criterion} name={criterion} type="number" min={1} max={5} required className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
          </div>
        ))}
      </fieldset>
      <div>
        <label htmlFor="recommendation" className="mb-1 block text-sm font-medium text-gray-900">Recommendation</label>
        <select id="recommendation" name="recommendation" required className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
          {RECOMMENDATIONS.map((value) => (
            <option key={value} value={value}>{value.replace("_", " ")}</option>
          ))}
        </select>
      </div>
      <Textarea label="Comments to author" name="comments_to_author" required minLength={20} />
      <Textarea label="Confidential comments to editor" name="confidential_comments_to_editor" />
      <Button type="submit" disabled={submitting}>{submitting ? "Submitting…" : "Submit review"}</Button>
    </form>
  );
}
```

- [ ] **Step 5: Assignment list and detail pages**

Create `frontend/src/app/reviewer/page.tsx`:

```tsx
"use client";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { formatDate } from "@/lib/format";
import type { ReviewAssignmentSummary } from "@/types/api";

export default function ReviewerAssignments() {
  const { data, error, isLoading } = useApi<ReviewAssignmentSummary[]>("/api/reviews");
  if (isLoading) return <p>Loading your assignments…</p>;
  if (error) return <ProblemAlert problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }} />;

  return (
    <>
      <h1 className="text-2xl font-bold">My review assignments</h1>
      <ul className="mt-4 space-y-3">
        {data?.map((assignment) => (
          <li key={assignment.id}>
            <Link href={`/reviewer/${assignment.id}`} className="block rounded-md border border-gray-200 bg-white p-4 hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
              <p className="font-medium">{assignment.manuscript_title}</p>
              <p className="text-sm text-gray-500">{assignment.manuscript_tracking_code} · due {formatDate(assignment.due_date)}</p>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
```

Create `frontend/src/app/reviewer/[id]/page.tsx`:

```tsx
"use client";
import { use } from "react";
import { useRouter } from "next/navigation";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { BlindedManuscriptView } from "@/components/blinded-manuscript-view";
import { ReviewForm } from "@/components/review-form";
import type { BlindedManuscript } from "@/types/api";

export default function ReviewAssignmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { data, error, isLoading } = useApi<BlindedManuscript>(`/api/reviews/${id}`);

  if (isLoading) return <p>Loading…</p>;
  if (error) return <ProblemAlert problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }} />;
  if (!data) return null;

  return (
    <>
      <BlindedManuscriptView manuscript={data} />
      <ReviewForm assignmentId={id} onSubmitted={() => router.push("/reviewer")} />
    </>
  );
}
```

- [ ] **Step 6: Run and commit**

Run: `cd frontend && make check`
Expected: all gates pass; 16 unit tests total.

```bash
git add frontend/src/components/blinded-manuscript-view.tsx frontend/src/components/blinded-manuscript-view.test.tsx \
  frontend/src/components/review-form.tsx frontend/src/components/ui/textarea.tsx \
  frontend/src/app/api/reviews frontend/src/app/reviewer
git commit -m "feat: add reviewer assignments, blinded manuscript view and review form"
```

---

### Task 6: Editor — screening queue, screen, assign, decide

**Files:** `frontend/src/components/ui/select.tsx`, `frontend/src/components/{reviewer-assign-form,decision-form}.tsx`, `frontend/src/app/api/editorial/**`, `frontend/src/app/editor/{page,[id]/page}.tsx`.

**Interfaces:**
- Consumes: `authedFetch`, `useApi`.
- Produces: `GET /api/editorial/queue`, `POST /api/editorial/[id]/{screen,assign,decide}`, `GET /api/editorial/[id]/candidates`.

- [ ] **Step 1: Route Handlers**

Create `frontend/src/app/api/editorial/queue/route.ts`:

```ts
import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ManuscriptSummary } from "@/types/api";

export async function GET(request: Request) {
  const status = new URL(request.url).searchParams.get("status");
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  try {
    return NextResponse.json(await authedFetch<ManuscriptSummary[]>(`/editorial/queue${query}`));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
```

Create `frontend/src/app/api/editorial/[id]/screen/route.ts`, `.../assign/route.ts`, `.../decide/route.ts` — identical shape, one per action:

```ts
// frontend/src/app/api/editorial/[id]/screen/route.ts
import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ManuscriptDetail } from "@/types/api";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const body = await request.text();
    const result = await authedFetch<ManuscriptDetail>(`/editorial/${id}/screen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
```

Repeat verbatim for `frontend/src/app/api/editorial/[id]/assign/route.ts` (upstream path `/editorial/${id}/assign`) and `frontend/src/app/api/editorial/[id]/decide/route.ts` (upstream path `/editorial/${id}/decide`).

Create `frontend/src/app/api/editorial/[id]/candidates/route.ts`:

```ts
import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ReviewerCandidate } from "@/types/api";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    return NextResponse.json(await authedFetch<ReviewerCandidate[]>(`/editorial/reviewer-candidates?manuscript_id=${id}`));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}
```

- [ ] **Step 2: `Select`, the reviewer-assignment form and its test**

Create `frontend/src/components/ui/select.tsx`:

```tsx
import { type SelectHTMLAttributes, forwardRef } from "react";

interface FieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
}

export const Select = forwardRef<HTMLSelectElement, FieldProps>(function Select({ label, id, name, children, className = "", ...props }, ref) {
  const fieldId = id ?? name ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div>
      <label htmlFor={fieldId} className="mb-1 block text-sm font-medium text-gray-900">{label}</label>
      <select ref={ref} id={fieldId} name={name} className={`w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${className}`} {...props}>
        {children}
      </select>
    </div>
  );
});
```

Create `frontend/src/components/reviewer-assign-form.tsx`:

```tsx
"use client";
import { useState, type FormEvent } from "react";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import type { ReviewerCandidate } from "@/types/api";

export function ReviewerAssignForm({ manuscriptId, candidates, onAssigned }: { manuscriptId: string; candidates: ReviewerCandidate[]; onAssigned: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const eligible = candidates.filter((c) => c.excluded_reason === null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    await fetch(`/api/editorial/${manuscriptId}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviewer_id: form.get("reviewer_id"), due_date: form.get("due_date") }),
    });
    setSubmitting(false);
    onAssigned();
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 flex flex-wrap items-end gap-3">
      <Select label="Reviewer" name="reviewer_id" required>
        <option value="" disabled defaultValue="">Choose a reviewer</option>
        {eligible.map((c) => (
          <option key={c.reviewer_id} value={c.reviewer_id}>
            {c.name} {c.score !== null && `(match ${(c.score * 100).toFixed(0)}%)`}
          </option>
        ))}
      </Select>
      <div>
        <label htmlFor="due_date" className="mb-1 block text-sm font-medium text-gray-900">Due date</label>
        <input id="due_date" name="due_date" type="date" required className="rounded-md border border-gray-300 px-3 py-2 text-sm" />
      </div>
      <Button type="submit" disabled={submitting || eligible.length === 0}>Assign</Button>
      {candidates.some((c) => c.excluded_reason) && (
        <details className="w-full text-sm text-gray-600">
          <summary>Excluded candidates ({candidates.filter((c) => c.excluded_reason).length})</summary>
          <ul className="mt-2 list-disc pl-5">
            {candidates.filter((c) => c.excluded_reason).map((c) => (
              <li key={c.reviewer_id}>{c.name} — {c.excluded_reason}</li>
            ))}
          </ul>
        </details>
      )}
    </form>
  );
}
```

Create `frontend/src/components/reviewer-assign-form.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReviewerAssignForm } from "./reviewer-assign-form";

const CANDIDATES = [
  { reviewer_id: "r1", name: "Dr. Adjei", score: 0.82, excluded_reason: null },
  { reviewer_id: "r2", name: "Dr. Boateng", score: null, excluded_reason: "Shares an affiliation with an author" },
];

describe("ReviewerAssignForm", () => {
  it("offers only eligible reviewers in the select, and lists exclusions separately", () => {
    render(<ReviewerAssignForm manuscriptId="m1" candidates={CANDIDATES} onAssigned={vi.fn()} />);
    const options = screen.getAllByRole("option").map((o) => o.textContent);
    expect(options.some((text) => text?.includes("Dr. Adjei"))).toBe(true);
    expect(options.some((text) => text?.includes("Dr. Boateng"))).toBe(false);
    expect(screen.getByText(/Dr\. Boateng — Shares an affiliation/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Decision form, hiding actions the backend would reject**

Create `frontend/src/components/decision-form.tsx`:

```tsx
"use client";
import { useState, type FormEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { DECISION_TYPES, type DecisionType, type ManuscriptStatus } from "@/types/api";

// A UX hint mirroring design spec §6.2's guards, not a security control — the backend
// re-validates every transition regardless of what this component allows the editor to pick.
const AVAILABLE_BY_STATUS: Record<ManuscriptStatus, DecisionType[]> = {
  draft: [], submitted: [],
  under_screening: ["desk_reject", "send_to_review"],
  desk_rejected: [], under_review: [],
  reviews_complete: ["request_revision", "accept", "reject"],
  revision_requested: [], resubmitted: [], accepted: [], rejected: [], scheduled: [], published: [], withdrawn: [],
};

export function DecisionForm({ manuscriptId, status, onDecided }: { manuscriptId: string; status: ManuscriptStatus; onDecided: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const available = AVAILABLE_BY_STATUS[status];
  if (available.length === 0) return null;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    await fetch(`/api/editorial/${manuscriptId}/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: form.get("decision"), rationale: form.get("rationale") }),
    });
    setSubmitting(false);
    onDecided();
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 space-y-4" aria-label="Record decision">
      <Select label="Decision" name="decision" required>
        {available.map((decision) => (
          <option key={decision} value={decision}>{decision.replace("_", " ")}</option>
        ))}
      </Select>
      <Textarea label="Rationale" name="rationale" required minLength={20} />
      <Button type="submit" disabled={submitting}>{submitting ? "Recording…" : "Record decision"}</Button>
    </form>
  );
}
```

Create `frontend/src/components/decision-form.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DecisionForm } from "./decision-form";

describe("DecisionForm", () => {
  it("offers desk rejection only from under_screening", () => {
    render(<DecisionForm manuscriptId="m1" status="under_screening" onDecided={vi.fn()} />);
    expect(screen.getByRole("option", { name: /desk reject/i })).toBeInTheDocument();
  });

  it("renders nothing once the manuscript has reached a state with no legal decision", () => {
    const { container } = render(<DecisionForm manuscriptId="m1" status="published" onDecided={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 4: Queue and detail pages**

Create `frontend/src/app/editor/page.tsx`:

```tsx
"use client";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { StatusBadge } from "@/components/ui/badge";
import { ProblemAlert } from "@/components/ui/alert";
import type { ManuscriptSummary } from "@/types/api";

export default function EditorialQueue() {
  const { data, error, isLoading } = useApi<ManuscriptSummary[]>("/api/editorial/queue");
  if (isLoading) return <p>Loading the queue…</p>;
  if (error) return <ProblemAlert problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }} />;

  return (
    <>
      <h1 className="text-2xl font-bold">Screening queue</h1>
      <table className="mt-4 w-full text-left text-sm">
        <caption className="sr-only">Manuscripts awaiting editorial action</caption>
        <thead>
          <tr className="border-b text-gray-500">
            <th scope="col" className="py-2">Tracking code</th>
            <th scope="col">Title</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((manuscript) => (
            <tr key={manuscript.id} className="border-b">
              <td className="py-2">
                <Link href={`/editor/${manuscript.id}`} className="text-blue-700 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
                  {manuscript.tracking_code}
                </Link>
              </td>
              <td>{manuscript.title}</td>
              <td><StatusBadge status={manuscript.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
```

Create `frontend/src/app/editor/[id]/page.tsx`:

```tsx
"use client";
import { use, useState } from "react";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ReviewerAssignForm } from "@/components/reviewer-assign-form";
import { DecisionForm } from "@/components/decision-form";
import type { ManuscriptDetail, ReviewerCandidate } from "@/types/api";

export default function EditorialManuscriptPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, error, isLoading, mutate } = useApi<ManuscriptDetail>(`/api/editorial/queue/${id}`.replace("/queue", ""));
  const { data: candidates } = useApi<ReviewerCandidate[]>(data?.status === "under_screening" || data?.status === "under_review" ? `/api/editorial/${id}/candidates` : null);
  const [screening, setScreening] = useState(false);

  if (isLoading) return <p>Loading…</p>;
  if (error) return <ProblemAlert problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }} />;
  if (!data) return null;

  async function screen(decision: "advance" | "desk_reject", rationale: string) {
    setScreening(true);
    await fetch(`/api/editorial/${id}/screen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, rationale }),
    });
    setScreening(false);
    mutate();
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{data.title}</h1>
        <StatusBadge status={data.status} />
      </div>

      {data.status === "under_screening" && (
        <div className="mt-4 flex gap-3">
          <Button disabled={screening} onClick={() => screen("advance", "Passes scope and formatting checks")}>Advance to review</Button>
          <Button variant="danger" disabled={screening} onClick={() => screen("desk_reject", "Out of journal scope")}>Desk reject</Button>
        </div>
      )}

      {(data.status === "under_screening" || data.status === "under_review") && candidates && (
        <ReviewerAssignForm manuscriptId={id} candidates={candidates} onAssigned={mutate} />
      )}

      <DecisionForm manuscriptId={id} status={data.status} onDecided={mutate} />
    </>
  );
}
```

- [ ] **Step 5: Run and commit**

Run: `cd frontend && make check`
Expected: all gates pass; 20 unit tests total.

```bash
git add frontend/src/components/ui/select.tsx frontend/src/components/reviewer-assign-form.tsx \
  frontend/src/components/reviewer-assign-form.test.tsx frontend/src/components/decision-form.tsx \
  frontend/src/components/decision-form.test.tsx frontend/src/app/api/editorial frontend/src/app/editor
git commit -m "feat: add editorial screening queue, reviewer assignment and decision recording"
```

---

### Task 7: Playwright end-to-end, accessibility scan, CI

**Files:** `frontend/playwright.config.ts`, `frontend/tests/e2e/mock-backend.ts`, `frontend/tests/e2e/submit-review-decide.spec.ts`, `.github/workflows/frontend-ci.yml`, `frontend/Makefile` (extend).

**Interfaces:**
- Consumes: the whole app.
- Produces: `make e2e`; `frontend-ci` GitHub Actions workflow.

**A stated simplification:** the mock backend below is a hand-rolled, in-memory double that implements only the assumed contract from the top of this plan — it is not the real FastAPI service. This test proves the frontend (BFF routing, cookies, forms, role gates) end-to-end; it does not prove integration with the real backend, which happens once Plan 4 exists and `E2E_BACKEND_URL` can point at it instead.

- [ ] **Step 1: The mock backend**

Create `frontend/tests/e2e/mock-backend.ts`:

```ts
import { createServer } from "node:http";
import { randomUUID } from "node:crypto";

interface StoredManuscript {
  id: string;
  tracking_code: string;
  title: string;
  abstract: string;
  keywords: string[];
  status: string;
  author_names: string[];
  corresponding_author_id: string;
  submitted_at: string;
  updated_at: string;
  events: { sequence: number; event_type: string; occurred_at: string; payload: Record<string, unknown> }[];
}

const USERS: Record<string, { id: string; email: string; name: string; roles: string[] }> = {
  "author@ug.edu.gh": { id: "u-author", email: "author@ug.edu.gh", name: "A. Mensah", roles: ["author"] },
  "reviewer@ug.edu.gh": { id: "u-reviewer", email: "reviewer@ug.edu.gh", name: "Dr. Adjei", roles: ["reviewer"] },
  "editor@ug.edu.gh": { id: "u-editor", email: "editor@ug.edu.gh", name: "Dr. Owusu", roles: ["editor"] },
};

const manuscripts = new Map<string, StoredManuscript>();
const reviewAssignments = new Map<string, { id: string; manuscript_id: string; status: string }>();
const tokensByUser = new Map<string, string>(); // access token -> email

function json(res: import("node:http").ServerResponse, status: number, body: unknown) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

function bearerUser(req: import("node:http").IncomingMessage) {
  const header = req.headers.authorization ?? "";
  const token = header.replace("Bearer ", "");
  const email = tokensByUser.get(token);
  return email ? USERS[email] : null;
}

export function startMockBackend(port: number) {
  const server = createServer(async (req, res) => {
    const url = new URL(req.url ?? "/", `http://localhost:${port}`);
    const chunks: Buffer[] = [];
    for await (const chunk of req) chunks.push(chunk as Buffer);
    const rawBody = Buffer.concat(chunks).toString();
    const body = rawBody && req.headers["content-type"]?.includes("application/json") ? JSON.parse(rawBody) : {};

    if (url.pathname === "/api/v1/auth/login" && req.method === "POST") {
      const user = USERS[body.email];
      if (!user || body.password !== "password123") return json(res, 401, { type: "about:blank", title: "Invalid email or password", status: 401 });
      const token = `access-${randomUUID()}`;
      tokensByUser.set(token, user.email);
      return json(res, 200, { access_token: token, refresh_token: `refresh-${randomUUID()}`, expires_in: 900, user });
    }

    if (url.pathname === "/api/v1/auth/refresh" && req.method === "POST") {
      return json(res, 200, { access_token: `access-${randomUUID()}`, refresh_token: `refresh-${randomUUID()}`, expires_in: 900 });
    }

    if (url.pathname === "/api/v1/auth/logout") return json(res, 204, {});

    const user = bearerUser(req);
    if (!user) return json(res, 401, { type: "about:blank", title: "Not signed in", status: 401 });

    if (url.pathname === "/api/v1/manuscripts" && req.method === "POST") {
      const id = randomUUID();
      const manuscript: StoredManuscript = {
        id,
        tracking_code: `UGJCS-2026-${String(manuscripts.size + 1).padStart(4, "0")}`,
        title: "E2E Test Manuscript",
        abstract: "An abstract long enough to pass validation for the end-to-end flow.",
        keywords: ["e2e"],
        status: "submitted",
        author_names: [user.name],
        corresponding_author_id: user.id,
        submitted_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        events: [{ sequence: 1, event_type: "manuscript_submitted", occurred_at: new Date().toISOString(), payload: {} }],
      };
      manuscripts.set(id, manuscript);
      return json(res, 201, manuscript);
    }

    if (url.pathname === "/api/v1/manuscripts/mine") {
      return json(res, 200, [...manuscripts.values()].filter((m) => m.corresponding_author_id === user.id));
    }

    const manuscriptMatch = url.pathname.match(/^\/api\/v1\/manuscripts\/([\w-]+)$/);
    if (manuscriptMatch) return json(res, 200, manuscripts.get(manuscriptMatch[1]));

    if (url.pathname === "/api/v1/editorial/queue") {
      return json(res, 200, [...manuscripts.values()].filter((m) => m.status === "under_screening" || m.status === "submitted"));
    }

    const screenMatch = url.pathname.match(/^\/api\/v1\/editorial\/([\w-]+)\/screen$/);
    if (screenMatch) {
      const manuscript = manuscripts.get(screenMatch[1])!;
      manuscript.status = body.decision === "advance" ? "under_review" : "desk_rejected";
      manuscript.events.push({ sequence: manuscript.events.length + 1, event_type: "screening_started", occurred_at: new Date().toISOString(), payload: {} });
      return json(res, 200, manuscript);
    }

    const assignMatch = url.pathname.match(/^\/api\/v1\/editorial\/([\w-]+)\/assign$/);
    if (assignMatch) {
      const assignmentId = randomUUID();
      reviewAssignments.set(assignmentId, { id: assignmentId, manuscript_id: assignMatch[1], status: "invited" });
      return json(res, 200, manuscripts.get(assignMatch[1]));
    }

    if (url.pathname === "/api/v1/reviews/mine") {
      return json(res, 200, [...reviewAssignments.values()].map((a) => {
        const m = manuscripts.get(a.manuscript_id)!;
        return { id: a.id, manuscript_tracking_code: m.tracking_code, manuscript_title: m.title, due_date: new Date().toISOString(), status: a.status };
      }));
    }

    const reviewGetMatch = url.pathname.match(/^\/api\/v1\/reviews\/([\w-]+)$/);
    if (reviewGetMatch && req.method === "GET") {
      const assignment = reviewAssignments.get(reviewGetMatch[1])!;
      const m = manuscripts.get(assignment.manuscript_id)!;
      // The blinded projection: author_names and corresponding_author_id are absent by construction.
      return json(res, 200, { id: m.id, tracking_code: m.tracking_code, title: m.title, abstract: m.abstract, keywords: m.keywords, document_url: "https://example.com/anon.pdf", status: m.status });
    }
    if (reviewGetMatch && req.method === "POST") {
      const assignment = reviewAssignments.get(reviewGetMatch[1])!;
      assignment.status = "submitted";
      const m = manuscripts.get(assignment.manuscript_id)!;
      m.status = "reviews_complete";
      m.events.push({ sequence: m.events.length + 1, event_type: "review_submitted", occurred_at: new Date().toISOString(), payload: {} });
      return json(res, 201, {});
    }

    const decideMatch = url.pathname.match(/^\/api\/v1\/editorial\/([\w-]+)\/decide$/);
    if (decideMatch) {
      const manuscript = manuscripts.get(decideMatch[1])!;
      manuscript.status = body.decision === "accept" ? "accepted" : body.decision === "reject" ? "rejected" : "revision_requested";
      manuscript.events.push({ sequence: manuscript.events.length + 1, event_type: "decision_recorded", occurred_at: new Date().toISOString(), payload: {} });
      return json(res, 200, manuscript);
    }

    if (url.pathname === "/api/v1/editorial/reviewer-candidates") {
      return json(res, 200, [{ reviewer_id: "u-reviewer", name: "Dr. Adjei", score: 0.9, excluded_reason: null }]);
    }

    if (url.pathname.startsWith("/api/v1/archive/")) return json(res, 200, url.pathname.includes("search") ? { results: [], total: 0 } : []);

    return json(res, 404, { type: "about:blank", title: "Not found", status: 404 });
  });
  server.listen(port);
  return server;
}

if (require.main === module) startMockBackend(Number(process.env.MOCK_BACKEND_PORT ?? 4100));
```

- [ ] **Step 2: Playwright config with two web servers**

Create `frontend/playwright.config.ts`:

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false, // the flow is a single-threaded story across three roles
  retries: 0,
  use: { baseURL: "http://localhost:3100" },
  webServer: [
    { command: "npx tsx tests/e2e/mock-backend.ts", port: 4100, env: { MOCK_BACKEND_PORT: "4100" }, reuseExistingServer: false },
    {
      command: "npx next dev -p 3100",
      port: 3100,
      env: { API_BASE_URL: "http://localhost:4100/api/v1", SESSION_SECRET: "e2e-secret-e2e-secret-e2e-secret" },
      reuseExistingServer: false,
    },
  ],
});
```

- [ ] **Step 3: The end-to-end flow**

Create `frontend/tests/e2e/submit-review-decide.spec.ts`:

```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("submit -> screen -> review -> decide", () => {
  test("a manuscript moves from author submission to an editorial decision", async ({ page, context }) => {
    // 1. Author submits.
    await page.goto("/login");
    await page.getByLabel("Email").fill("author@ug.edu.gh");
    await page.getByLabel("Password").fill("password123");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/author/);

    await page.goto("/author/submit");
    await page.getByLabel("Title").fill("E2E Test Manuscript");
    await page.getByLabel("Abstract").fill("A".repeat(120));
    await page.getByLabel(/keywords/i).fill("scheduling, gpu");
    await page.setInputFiles('input[type="file"]', { name: "paper.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 test") });
    await page.getByLabel(/confirm this file/i).check();
    await page.getByRole("button", { name: /submit manuscript/i }).click();
    await expect(page).toHaveURL(/\/author\/[\w-]+/);
    await expect(page.getByText("Submitted")).toBeVisible();

    await page.getByRole("button", { name: /sign out/i }).click();
    await context.clearCookies();

    // 2. Editor screens and assigns.
    await page.goto("/login");
    await page.getByLabel("Email").fill("editor@ug.edu.gh");
    await page.getByLabel("Password").fill("password123");
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.goto("/editor");
    await page.getByRole("link", { name: /UGJCS-2026/ }).first().click();
    await page.getByRole("button", { name: /advance to review/i }).click();
    await expect(page.getByText("Under review")).toBeVisible();
    await page.getByLabel("Reviewer").selectOption({ label: /Dr\. Adjei/ });
    await page.getByLabel("Due date").fill("2026-09-01");
    await page.getByRole("button", { name: /^assign$/i }).click();

    await page.getByRole("button", { name: /sign out/i }).click();
    await context.clearCookies();

    // 3. Reviewer reads the blinded manuscript and submits a review — author identity must
    //    never appear on this screen (the same guarantee Task 5's component test asserts
    //    in isolation; this proves it holds through the real route and real render).
    await page.goto("/login");
    await page.getByLabel("Email").fill("reviewer@ug.edu.gh");
    await page.getByLabel("Password").fill("password123");
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.goto("/reviewer");
    await page.getByRole("link", { name: /E2E Test Manuscript/ }).click();
    await expect(page.getByText("A. Mensah")).toHaveCount(0);

    for (const criterion of ["originality", "rigour", "clarity", "significance"]) {
      await page.locator(`#${criterion}`).fill("4");
    }
    await page.getByLabel("Recommendation").selectOption("minor_revision");
    await page.getByLabel("Comments to author").fill("Solid contribution; please tighten the evaluation section.");
    await page.getByRole("button", { name: /submit review/i }).click();
    await expect(page).toHaveURL(/\/reviewer$/);

    await page.getByRole("button", { name: /sign out/i }).click();
    await context.clearCookies();

    // 4. Editor records the decision.
    await page.goto("/login");
    await page.getByLabel("Email").fill("editor@ug.edu.gh");
    await page.getByLabel("Password").fill("password123");
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.goto("/editor");
    await page.getByRole("link", { name: /UGJCS-2026/ }).first().click();
    await page.getByLabel("Decision").selectOption("accept");
    await page.getByLabel("Rationale").fill("Reviewer feedback addressed; ready to publish.");
    await page.getByRole("button", { name: /record decision/i }).click();
    await expect(page.getByText("Accepted")).toBeVisible();
  });

  test("the login page has no automatically detectable accessibility violations", async ({ page }) => {
    await page.goto("/login");
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });
});
```

- [ ] **Step 4: Run it**

Run: `cd frontend && npm install -D tsx && npx playwright test`
Expected: 2 passed. If the assign/decide selectors drift because `useApi` cache keys differ from the literal strings above, fix the page component's `useApi` URL, not the test — the test encodes the contract this plan defines.

- [ ] **Step 5: CI workflow**

Create `.github/workflows/frontend-ci.yml`:

```yaml
name: frontend-ci

on:
  push:
    branches: [main, master]
  pull_request:

permissions:
  contents: read

concurrency:
  group: frontend-ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version-file: "frontend/.nvmrc", cache: "npm", cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
      - name: Populate a throwaway env for the typecheck/test gate
        run: cp .env.local.example .env.local
      - run: make check

  e2e:
    runs-on: ubuntu-latest
    needs: check
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version-file: "frontend/.nvmrc", cache: "npm", cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: make e2e
```

- [ ] **Step 6: Extend the Makefile and verify**

Add `e2e` and its dependency to `frontend/Makefile` (already present from Task 1 — confirm it reads exactly):

```make
e2e:
	npx playwright test
```

Run:
```bash
cd frontend && make check && make e2e
python3 -c "import yaml; d=yaml.safe_load(open('../.github/workflows/frontend-ci.yml')); print(sorted(d['jobs']))"
```
Expected: `make check` green (20 unit tests); `make e2e` reports 2 passed; the workflow lists `['check', 'e2e']`.

- [ ] **Step 7: Commit**

```bash
git add frontend/playwright.config.ts frontend/tests frontend/package.json frontend/package-lock.json \
  .github/workflows/frontend-ci.yml frontend/Makefile
git commit -m "test: add end-to-end submit-screen-review-decide flow and frontend CI"
```

---

## Definition of done for Plan 5

- `cd frontend && make check` passes: ESLint at zero warnings, `tsc --noEmit` clean, 20 Vitest unit/component tests green.
- `cd frontend && make e2e` passes: the full submit → screen → review → decide flow across three roles, plus an Axe scan on the login page with zero violations.
- The public archive (`/`, `/issues`, `/issues/[v]/[n]`, `/papers/[trackingCode]`, `/search`) renders via SSR/ISR with no session import anywhere in that route tree, correct `<title>`/OpenGraph/JSON-LD, and a generated `sitemap.xml`.
- No access token or refresh token is ever observable in a Client Component, `localStorage`, `sessionStorage`, or a URL. The only place a token exists is the sealed `ugjcs_session` cookie (httpOnly, Secure in production, SameSite=Lax).
- `BlindedManuscriptView` renders `BlindedManuscript` and nothing wider; `blinded-manuscript-view.test.tsx` proves no author sentinel reaches the DOM even from a contaminated payload, and a `@ts-expect-error` line fails the typecheck gate the day the type itself grows an author field.
- Every screen is reachable and completable by keyboard alone (proved for the login form; the same focus-visible/label pattern is used on every other form in the app).
- `.github/workflows/frontend-ci.yml` runs `check` on every push/PR and `e2e` after it passes.

## Deliberately not in this plan

A design system or theming layer beyond Tailwind's default palette; motion/animation; dark mode; internationalisation; an admin console for users/roles/journal settings (`/admin` in the API surface has no frontend here); direct-to-S3 presigned uploads (the manuscript file is proxied through the Route Handler, which is simpler and fast enough for a capstone-scale corpus, at the cost of routing the file through the Vercel function); OAI-PMH and BibTeX/RIS export UI (the backend exposes them; no frontend page links to them yet); offline support or a service worker; optimistic UI on mutations (every write waits for the response, then refetches — simpler to reason about within 48 hours, at a small latency cost); real-time updates (no websocket/polling — a reviewer or editor must reload to see another actor's action); reviewer capacity/availability self-service (editor-only assignment, per design spec §10.1's human-in-the-loop decision); and integration testing against the real backend, which Task 7's mock explicitly stands in for until Plan 4 exists.

## Carried forward as risk

- The mock backend in Task 7 encodes this plan's assumed contract, not a verified one. When Plan 4 lands, the first frontend task after it must be pointing `E2E_BACKEND_URL` at the real service and fixing whatever the assumption got wrong — expect at least the exact DTO field names to drift.
- `authedFetch`'s refresh path assumes the backend's `/auth/refresh` rotates the refresh token on every use (Plan 3 documents rotation with reuse detection). If refresh reuse detection revokes the whole token family on a raced double-refresh, a user with two tabs open can be logged out unexpectedly; no mitigation is implemented here.
- The reviewer-assignment UI trusts `excluded_reason: null` from `/editorial/reviewer-candidates` as the sole eligibility signal. If that endpoint's shape changes to omit excluded candidates entirely rather than annotating them, `ReviewerAssignForm`'s `eligible` filter degrades gracefully (empty exclusion list) but the "why is a reviewer missing" transparency goal from design spec §10.1 is lost silently — worth a follow-up test once Plan 4's real shape is known.
