# SDJ Editorial Portal — API Contract

**Project:** SDJ Editorial Portal — an editorial portal for the Science and Development
Journal (SDJ), published by the College of Basic and Applied Sciences, University of Ghana
**Author:** Roger Koranteng Obeng (22424140)
**Established:** 2026-08-12
**Status:** Authoritative. This document is the single source of truth for the HTTP boundary between the FastAPI backend (Plan 4) and the Next.js frontend (Plan 5). Where either plan's prose disagrees with this document, this document wins; the disagreement is a defect in the plan, to be corrected there, not here.

## How this document came to exist

Plan 4 (the editorial API) and Plan 5 (the frontend) were drafted concurrently, each against an assumed shape for the other. Plan 4 was written directly against the executed domain, persistence and authentication code from Plans 1–3, and is therefore authoritative on wire format. Plan 5's assumptions have been reconciled against it; this document records the settled contract both plans now point at, so a future change to either plan has one place to check rather than two plans to diff against each other.

---

## 1. Authentication mechanism

- **Scheme:** OAuth2-style bearer tokens. The backend issues a short-lived **access token** (a signed JWT, `HS256`, carrying `sub` and `exp`) and a longer-lived opaque **refresh token**, both minted by `ugjcs.infrastructure.security.tokens.JwtTokenService` (Plan 3).
- **Presentation:** every authenticated backend request carries `Authorization: Bearer <access_token>`. There is no cookie on the backend origin — the backend is a pure bearer-token API and holds no session state of its own beyond the persisted refresh-token record.
- **Token lifetimes:** configurable via `Settings.access_token_minutes` and `Settings.refresh_token_days`; the access token's own `exp` claim is the only wire-visible expiry — no response field states a lifetime in seconds.
- **Refresh rotation:** `POST /api/v1/auth/refresh` consumes the current refresh token and returns a new access/refresh pair. Plan 3 rotates the refresh token on every use and supports reuse detection (a replayed, already-rotated refresh token revokes its whole token family). Only one refresh token is ever live per session; a client must persist the rotated value before its next call.
- **Frontend session boundary:** the browser never sees a bearer token. The Next.js app is a Backend-For-Frontend: Route Handlers under `frontend/src/app/api/**` unseal a single **httpOnly, Secure (in production), SameSite=Lax cookie named `ugjcs_session`** (sealed with `iron-session`), attach the bearer token to the upstream backend call server-side, and reseal the cookie with any rotated tokens before responding. No Client Component, `localStorage`, `sessionStorage` or URL ever carries a token.
- **Frontend refresh flow:** `authedFetch` (the only function permitted to call the backend on behalf of an authenticated page) refreshes proactively when the stored `accessTokenExpiresAt` — decoded from the access token's own `exp` claim, since the response carries no `expires_in` — is within 5 seconds of expiry, and reactively once more on an unexpected `401`, to absorb clock skew between the two processes. `middleware.ts` enforces the `/author`, `/reviewer`, `/editor` prefixes as a routing-level gate in front of this; the backend's own authorisation check is what is actually authoritative.
- **Login response does not carry a user object.** `POST /auth/login` returns only `{access_token, refresh_token, token_type}`. The frontend derives the session's user by keeping the `email` from the request it already validated and calling `GET /auth/me` with the freshly issued access token for `{id, roles}`.

---

## 2. Naming convention

**snake_case everywhere on the wire** — every JSON field name and every enum value, on both requests and responses, exactly as Pydantic v2 serialises Python identifiers by default. There is **no camelCase translation layer anywhere** in either plan: `src/types/api.ts` on the frontend mirrors the backend's field names byte-for-byte, and `Role`, `ManuscriptStatus`, `Recommendation` and `DecisionType` are copied verbatim from `ugjcs.domain.enums` rather than re-spelled.

**Conversion point:** none exists, deliberately. This was a considered choice, not an oversight: introducing a camelCase boundary would mean maintaining a mapping layer with no behavioural payoff, since the frontend is the only consumer and TypeScript is equally happy with either casing. If a second, JavaScript-idiomatic API consumer is ever added, the conversion point would belong in `frontend/src/lib/backend.ts` and `frontend/src/lib/auth-fetch.ts` — the two functions every Route Handler is required to route backend calls through — and nowhere else.

---

## 3. Error format

Every error response, from every endpoint, is an **RFC 9457 Problem Details** JSON object served as `application/problem+json`:

| Field | Type | Notes |
|---|---|---|
| `type` | string | Always the literal `"about:blank"` in the current implementation — no per-error-class URIs are minted. |
| `title` | string | The raising exception's class name (e.g. `"IllegalTransitionError"`, `"AuthorizationDeniedError"`). This is what the frontend's `ProblemAlert` component renders as its headline. |
| `status` | integer | The HTTP status code, duplicated into the body. |
| `detail` | string, optional | A human-readable elaboration; present on validation failures and most domain errors. |
| `instance` | string, optional | The request path that produced the error. |

**Status code mapping** (`ugjcs.api.errors`, ordered by specificity — an unlisted `DomainError` subclass falls through to `400`):

| Exception | Status |
|---|---|
| `IllegalTransitionError` | 409 Conflict |
| `GuardViolationError` | 409 Conflict |
| `AuthorizationDeniedError` | 403 Forbidden |
| `AuthenticationError`, `InvalidTokenError` | 401 Unauthorized |
| `AccountError` | 400 Bad Request |
| Any other `DomainError` | 400 Bad Request |
| `RequestValidationError` (Pydantic body/query validation) | 422 Unprocessable Entity |
| `HTTPException` raised directly (e.g. not-found lookups) | whatever status it was raised with (typically 404) |

**Frontend contract:** every Route Handler relays this shape verbatim to the browser — `ProblemDetailsError` (`src/lib/backend.ts`, `src/lib/auth-fetch.ts`) carries the parsed `ProblemDetails` object and the status code together, and no Route Handler invents its own error shape. `ProblemDetails.type`/`title` are typed as plain `string`, not a narrower literal union, since the backend does not currently commit to a closed set of `type` values.

---

## 4. Manuscript status vocabulary

Copied verbatim from `ugjcs.domain.enums.ManuscriptStatus` (Plan 1) — the frontend must never invent its own spelling of a value the backend sends:

`draft`, `submitted`, `under_screening`, `desk_rejected`, `under_review`, `reviews_complete`, `revision_requested`, `resubmitted`, `accepted`, `rejected`, `scheduled`, `published`, `withdrawn`

Related vocabularies, equally verbatim:

- **`Role`** (`ugjcs.domain.enums.Role`): `author`, `reviewer`, `editor`, `editor_in_chief`, `administrator`
- **`Recommendation`** (`ugjcs.domain.enums.Recommendation`): `accept`, `minor_revision`, `major_revision`, `reject` — used only as `<select>` option values in the frontend's review form; `SubmitReviewRequest.recommendation` is an unvalidated `str` on the backend, so a value outside this list is a frontend bug, not a `422`.
- **`DecisionType`** (`ugjcs.domain.enums.DecisionType`): `desk_reject`, `send_to_review`, `request_revision`, `accept`, `reject`

---

## 5. Pagination

None, anywhere. Every list-returning endpoint returns a flat, unbounded JSON array. This is a deliberate scope decision for a 48-hour demonstration corpus, recorded in Plan 4; adding pagination later is an additive query parameter, not a redesign.

---

## 6. Endpoints

All paths below are relative to `/api/v1` unless marked **(unversioned)**. "Auth" states the bearer requirement and, where relevant, the role enforced by `ugjcs.domain.policies.Action` via `require(Action.…)`; "Ownership" marks the two actions (`RESUBMIT`, `WITHDRAW`) gated by `_OWNERSHIP_ACTIONS` — corresponding author only, checked a second time inside the handler once the manuscript is loaded.

### Operations

| Method | Path | Auth | Response | Status |
|---|---|---|---|---|
| GET | `/health` **(unversioned)** | none | `{}`-shaped liveness body | 200 |
| GET | `/ready` **(unversioned)** | none | readiness body | 200 |

### Authentication (`/auth`)

| Method | Path | Auth | Request body | Response | Status |
|---|---|---|---|---|---|
| POST | `/auth/login` | none | `{email, password}` | `{access_token, refresh_token, token_type}` | 200 / 401 (bad credentials) |
| POST | `/auth/refresh` | none (refresh token in body) | `{refresh_token}` | `{access_token, refresh_token, token_type}` | 200 / 401 (invalid/expired/reused) |
| POST | `/auth/logout` | none (refresh token in body) | `{refresh_token}` | *(empty)* | 204 |
| GET | `/auth/me` | Bearer | — | `{id, roles}` | 200 / 401 |

`GET /auth/me` serialises `Actor`, which carries only an id and a role set — **no `email`, no `name`**. `Account.full_name` exists in Plan 3's domain but nothing on the auth path threads it through to HTTP yet (§8, technical debt).

### Manuscripts (`/manuscripts`) — author-facing

| Method | Path | Auth | Request body | Response | Status |
|---|---|---|---|---|---|
| POST | `/manuscripts` | Bearer, role `author` | `{title, abstract, keywords, co_author_ids?}` (JSON — **not multipart**; no file upload exists anywhere in this domain) | `ManuscriptOut` | 201 |
| GET | `/manuscripts/mine` | Bearer, role `author` | — | `ManuscriptOut[]` | 200 |
| GET | `/manuscripts/{tracking_code}` | Bearer; visibility via `Action.VIEW` (`can()`: editor/EIC/administrator, or a listed author) | — | `ManuscriptOut` | 200 / 403 / 404 |
| POST | `/manuscripts/{tracking_code}/withdraw` | Bearer, **ownership** (`Action.WITHDRAW`; corresponding author only) | — | `ManuscriptOut` | 200 / 403 / 404 |

### Editorial (`/editorial`)

| Method | Path | Auth | Request body | Response | Status |
|---|---|---|---|---|---|
| GET | `/editorial/queue` | Bearer, role `editor`\|`editor_in_chief` (`Action.SCREEN`) | — | `ManuscriptOut[]` (hardcoded to `status == submitted`; no `?status=` filter) | 200 |
| POST | `/editorial/{tracking_code}/screen` | Bearer, `Action.SCREEN` | *(no body)* | `ManuscriptOut` | 200 / 404 |
| POST | `/editorial/{tracking_code}/decision` | Bearer, `Action.DECIDE` | `{decision: DecisionType, rationale}` | `ManuscriptOut` | 200 / 404 — a desk rejection is `decision: "desk_reject"` on this same endpoint; there is no separate "screen with a rejecting decision" call |
| POST | `/editorial/{tracking_code}/reviewers` | Bearer, `Action.ASSIGN_REVIEWER` | `{reviewer_id}` | *(empty)* | 204 / 404 — no `due_date`, no candidate-list endpoint; reviewer assignment is a persistence-only record (Plan 4 scope decision) |

### Reviews (`/reviews`)

| Method | Path | Auth | Request body | Response | Status |
|---|---|---|---|---|---|
| GET | `/reviews/mine` | Bearer, role `reviewer` (`Action.REVIEW`) | — | `BlindedManuscript[]` — the blinded manuscripts directly, not an assignment-summary wrapper; a manuscript's own `tracking_code` is the only handle on an assignment | 200 |
| POST | `/reviews/{tracking_code}/submit` | Bearer, `Action.REVIEW` | `{recommendation, comments}` — one free-text `recommendation` string, one free-text `comments` string; no per-criterion scores | *(empty)* | 204 / 403 (not assigned) |

### Public archive (`/archive`) — no authentication anywhere in this group

| Method | Path | Auth | Response | Status |
|---|---|---|---|---|
| GET | `/archive` | none | `ArchivePaperOut[]` — flat, unpaginated | 200 |
| GET | `/archive/{tracking_code}` | none | `ArchivePaperOut` | 200 / 404 (also 404 if the manuscript exists but is not `published`) |
| GET | `/archive/search?q=` | none | `ArchivePaperOut[]` — a flat array, **not** `{results, total}`; no `page` parameter | 200 |

Not exposed via HTTP in this plan: `Action.PUBLISH`/`Manuscript.schedule`/`Manuscript.publish` have no corresponding route — publication into the archive happens outside the HTTP boundary this plan builds. `Action.MANAGE_USERS` and `Action.VIEW_AUDIT` are likewise defined in the policy layer with no route exercising them yet.

---

## 7. Response shapes

### `TokenPairOut`
```json
{ "access_token": "string", "refresh_token": "string", "token_type": "bearer" }
```

### `ActorOut`
```json
{ "id": "uuid", "roles": ["author"] }
```

### `ManuscriptOut` — the one shape every manuscript route returns; no separate summary/detail variant
```json
{
  "tracking_code": "string",
  "title": "string",
  "abstract": "string",
  "keywords": ["string"],
  "author_ids": ["uuid"],
  "corresponding_author_id": "uuid",
  "status": "ManuscriptStatus",
  "version": 0,
  "minimum_reviews": 0,
  "submitted_reviews": 0
}
```
Deliberately absent: `id` (`tracking_code` is the only identifier on the wire), `submitted_at`/`updated_at` (no response anywhere in this API carries a timestamp), and any event/audit trail (no endpoint exposes one).

### `BlindedManuscript` — mirrors `ugjcs.domain.blinding.BlindedManuscript` field-for-field; **exactly these six fields, no more**
```json
{
  "tracking_code": "string",
  "title": "string",
  "abstract": "string",
  "keywords": ["string"],
  "version": 0,
  "status": "ManuscriptStatus"
}
```
No author field of any kind (`author_ids`, `corresponding_author_id`) exists on this type — a structural guarantee, not a filtered value: the type itself has nowhere to put one. Also absent: `id`, `document_url` (no document storage exists in this domain).

### `ArchivePaperOut` — the public shape; a byline a human or Google Scholar can read, never an account UUID
```json
{
  "tracking_code": "string",
  "title": "string",
  "abstract": "string",
  "keywords": ["string"],
  "author_names": ["string"],
  "status": "ManuscriptStatus",
  "version": 0
}
```
Deliberately absent: `published_at`, `doi`, `pdf_url`, `volume`, `number` — none exist anywhere in the domain built so far. There is no `/archive/issues` endpoint of any kind.

### Request bodies
```
SubmitManuscriptRequest   { title, abstract, keywords, co_author_ids? }
RecordDecisionRequest     { decision: DecisionType, rationale }
AssignReviewerRequest     { reviewer_id }
SubmitReviewRequest       { recommendation, comments }
LoginRequest               { email, password }
RefreshRequest             { refresh_token }
```

---

## 8. Known gaps carried into `docs/04-technical-debt-register.md`

- `GET /auth/me` cannot supply a display name — `SessionUser` on the frontend has only `{id, email, roles}`; `email` comes from the login form the BFF already validated, not from any backend response.
- No file upload, document storage, DOI minting or PDF export exists anywhere in the domain; `POST /manuscripts` is JSON-only.
- No pagination on any list endpoint.
- No event/audit-log endpoint, and no response anywhere carries a timestamp — the frontend's status displays cannot show a submission or decision date.
- Reviewer assignment has no invitation lifecycle, no conflict-of-interest check, and no candidate-listing endpoint (Plan 4's documented scope decision).
