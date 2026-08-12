# UGJCS — Design Specification

**Project:** UGJCS — University of Ghana Journal of Computing Science
**Type:** Double-blind peer-reviewed academic journal management platform
**Context:** Advanced Software Engineering individual capstone, 48-hour constraint
**Date:** 2026-08-12
**Status:** Approved design, pending implementation plan

---

## 1. Problem statement

The Department of Computer Science, University of Ghana has no dedicated system for
managing scholarly publication. Where departmental or faculty journals exist in the
Ghanaian university context, the editorial process is typically conducted over email
and shared spreadsheets. That approach fails in four specific ways:

1. **Blinding is not enforceable.** Double-blind review depends on a human remembering
   to strip identifying information from a document before forwarding it. Author names
   routinely survive in PDF metadata even when removed from the visible text.
2. **There is no audit trail.** When a rejected author appeals, there is no
   authoritative, tamper-evident record of who decided what, when, and on what evidence.
3. **Reviewer assignment is ad hoc.** Editors assign from memory, which concentrates
   load on a few willing reviewers and misses expertise matches entirely.
4. **Published work is not discoverable.** Accepted papers end up as files on a shared
   drive rather than in a citable, indexable, harvestable archive.

UGJCS addresses all four as first-class system responsibilities rather than as
procedural guidance to users.

## 2. Aim and objectives

**Aim:** Deliver a deployed, production-quality platform that manages the complete
scholarly publishing lifecycle from submission to public archival, with double-blind
integrity and editorial auditability enforced by the system rather than by convention.

**Objectives:**

- O1. Enforce a guarded manuscript lifecycle in which no illegal state transition is
  reachable through any interface.
- O2. Guarantee double-blind integrity structurally, including at the document level.
- O3. Provide a tamper-evident editorial audit trail.
- O4. Assist reviewer assignment with expertise matching, conflict-of-interest
  exclusion and workload balancing, leaving final authority with the editor.
- O5. Publish accepted work to a public, searchable, citable and machine-harvestable
  archive.
- O6. Demonstrate disciplined engineering practice: estimation-driven scope, automated
  quality gates, infrastructure as code, and an explicit technical debt register.

## 3. Stakeholders and actors

| Actor | Type | Primary concerns |
|---|---|---|
| Author | Primary, authenticated | Submit work, track progress, respond to reviews |
| Reviewer | Primary, authenticated | Accept/decline invitations, submit structured reviews, remain anonymous |
| Editor | Primary, authenticated | Screen submissions, assign reviewers, record decisions |
| Editor-in-Chief | Primary, authenticated | Compose issues, publish, configure journal policy, final authority |
| Administrator | Secondary, authenticated | User accounts, role assignment, reviewer capacity |
| Reader | Primary, anonymous | Discover, read, cite and download published papers |
| Head of Department | Secondary | Editorial throughput and workload analytics |
| Indexing services | External system | Harvest metadata via OAI-PMH |

Non-human stakeholders: the AWS platform (cost and operability) and future maintainers
(the technical debt register is written for them).

## 4. Scope

### 4.1 In scope

The complete editorial pipeline: registration and authentication with role-based
access; manuscript submission with file upload; automated post-upload processing
(validation, anonymisation, text extraction, similarity screening); editorial
screening and desk rejection; assisted reviewer assignment; structured double-blind
reviewing; editorial decisions including revision rounds; issue composition and
publication; a public archive with full-text search, citation export and OAI-PMH; an
append-only editorial audit log; and administrative user management.

### 4.2 Out of scope (explicit)

Payment and article processing charges; copy-editing and typesetting workflow;
production-quality PDF galley generation; multi-journal tenancy; ORCID federation;
real DOI registration with Crossref (identifiers are DOI-*shaped* but not registered);
plagiarism detection against external corpora such as the open web (screening is
against the internal corpus only); and email deliverability beyond a single
transactional provider.

Each exclusion is recorded with a rationale so the boundary is a decision rather than
an omission.

## 5. Requirements

Priorities use MoSCoW. **M** items define the shippable core; **S** and **C** items are
built only if the estimate permits and otherwise enter the technical debt register with
a repayment plan.

### 5.1 Functional requirements

| ID | Requirement | Actor | Pri |
|---|---|---|---|
| FR-01 | Register an account and verify identity by email | Author, Reviewer | M |
| FR-02 | Authenticate and maintain a session; sessions expire and can be revoked | All authenticated | M |
| FR-03 | Assign and revoke roles; a user may hold several roles | Administrator | M |
| FR-04 | Create a submission with title, abstract, keywords, co-authors and a PDF | Author | M |
| FR-05 | Reject uploads that fail type, size or integrity validation, with a clear reason | System | M |
| FR-06 | Generate an anonymised copy of every submitted document | System | M |
| FR-07 | Screen a submission: send to review, request pre-review changes, or desk-reject | Editor | M |
| FR-08 | Recommend reviewers ranked by expertise match, excluding conflicts and respecting capacity | System | M |
| FR-09 | Invite reviewers; the editor may override any recommendation | Editor | M |
| FR-10 | Accept or decline a review invitation with a reason | Reviewer | M |
| FR-11 | Submit a structured review: criterion scores, recommendation, comments to author, confidential comments to editor | Reviewer | M |
| FR-12 | Record an editorial decision once the minimum review count is met | Editor | M |
| FR-13 | Submit a revised version with a response-to-reviewers letter | Author | M |
| FR-14 | View own submissions and their status timeline | Author | M |
| FR-15 | Compose an issue from accepted manuscripts and publish it | Editor-in-Chief | M |
| FR-16 | Browse issues and read published papers without authenticating | Reader | M |
| FR-17 | Full-text search across published papers with filters | Reader | M |
| FR-18 | Download a published paper's PDF | Reader | M |
| FR-19 | View the complete audit trail for a manuscript | Editor, EiC | M |
| FR-20 | Screen submissions for similarity against the internal corpus | System | S |
| FR-21 | Export citations as BibTeX and RIS | Reader | S |
| FR-22 | Expose an OAI-PMH endpoint serving Dublin Core | External system | S |
| FR-23 | Notify actors of events affecting them (in-app, and email where configured) | System | S |
| FR-24 | Editorial analytics: throughput, decision mix, reviewer load, time-to-decision | EiC, HoD | S |
| FR-25 | Withdraw a submission before a decision is recorded | Author | S |
| FR-26 | Configure journal policy: minimum reviews, review window, blinding model | EiC | C |
| FR-27 | Resolve a persistent identifier to its paper | Reader | C |
| FR-28 | Reviewer performance history and reliability indicators | EiC | C |

### 5.2 Non-functional requirements

| ID | Category | Requirement | Verification |
|---|---|---|---|
| NFR-01 | Security | Passwords hashed with Argon2id; no credential ever logged | Code review, unit test |
| NFR-02 | Security | Every endpoint authorised by explicit policy; deny by default | Integration test per role matrix |
| NFR-03 | Security | Reviewer-facing payloads contain no author-identifying data | Automated leak test over all reviewer endpoints |
| NFR-04 | Security | Documents served only via short-lived pre-signed URLs; buckets are private | Integration test, manual verification |
| NFR-05 | Security | Rate limiting on authentication and submission endpoints | Integration test |
| NFR-06 | Security | Dependencies scanned; no known high-severity vulnerability at release | `pip-audit`, `npm audit` in CI |
| NFR-07 | Integrity | Audit events are append-only and hash-chained | Property test; tamper-detection test |
| NFR-08 | Performance | Public archive pages respond within 500 ms at p95 under nominal load | k6 smoke test |
| NFR-09 | Performance | Search returns within 800 ms at p95 over the seeded corpus | k6 smoke test |
| NFR-10 | Reliability | Upload processing is idempotent and retried with backoff | Unit and integration test |
| NFR-11 | Availability | Service exposes liveness and readiness probes; unhealthy tasks are replaced | Deployment verification |
| NFR-12 | Usability | Responsive from 360 px; keyboard navigable; WCAG 2.1 AA contrast | Manual audit, automated axe check |
| NFR-13 | Maintainability | Domain layer imports no framework; enforced by an import-linter contract | CI gate |
| NFR-14 | Maintainability | Domain and application layers at or above 85% line coverage | CI coverage gate |
| NFR-15 | Observability | Structured JSON logs with correlation IDs; traces exported | Manual verification |
| NFR-16 | Portability | Entire infrastructure reproducible from code | `terraform apply` from clean state |
| NFR-17 | Compliance | Personal data minimised; audit log retains identity only where required | Design review |

## 6. Domain model

### 6.1 Aggregates and entities

`Manuscript` is the aggregate root. It owns its versions, review assignments and
decisions; nothing outside the aggregate mutates them. `User`, `Issue` and
`EditorialEvent` are separate aggregates referenced by identity.

- **User** — identity, credentials, roles, affiliation, expertise keywords, reviewer
  capacity, availability.
- **Manuscript** — tracking code (`UGJCS-2026-0042`), title, abstract, keywords,
  authorship list with a designated corresponding author, current status, current
  version.
- **ManuscriptVersion** — version number, original document reference, anonymised
  document reference, extracted text, similarity report, response-to-reviewers letter.
- **ReviewAssignment** — reviewer, due date, invitation state.
- **Review** — criterion scores (originality, rigour, clarity, significance),
  overall recommendation, comments to author, confidential comments to editor.
- **EditorialDecision** — decision type, deciding editor, rationale, timestamp.
- **Issue** — volume, number, year, title, publication date, ordered paper list.
- **EditorialEvent** — the append-only audit record described in §6.3.

### 6.2 Manuscript lifecycle

```
DRAFT ──submit──▶ SUBMITTED ──begin screening──▶ UNDER_SCREENING
                                                      │
                        ┌─────────────────────────────┼──────────────────┐
                        ▼                             ▼                  ▼
                 DESK_REJECTED                  UNDER_REVIEW      REVISION_REQUESTED
                                                      │                  │
                                              reviews complete       author resubmits
                                                      ▼                  ▼
                                              REVIEWS_COMPLETE ◀── RESUBMITTED
                                                      │
                          ┌───────────────────────────┼───────────────────┐
                          ▼                           ▼                   ▼
                  REVISION_REQUESTED             ACCEPTED             REJECTED
                                                      │
                                          assigned to issue
                                                      ▼
                                                 SCHEDULED ──issue published──▶ PUBLISHED
```

`WITHDRAWN` is reachable from `SUBMITTED`, `UNDER_SCREENING`, `UNDER_REVIEW`,
`REVIEWS_COMPLETE` and `REVISION_REQUESTED`. `DESK_REJECTED`, `REJECTED`, `PUBLISHED`
and `WITHDRAWN` are terminal.

Representative guards, each of which becomes a named unit test:

- Only an Editor or the Editor-in-Chief may begin screening.
- Reviewers may be assigned only in `UNDER_SCREENING` or `UNDER_REVIEW`.
- A decision requires submitted reviews at or above the configured minimum (default 2),
  except desk rejection, which requires none and is only legal in `UNDER_SCREENING`.
- Only the corresponding author of that manuscript may resubmit, and only from
  `REVISION_REQUESTED`.
- Publication requires `ACCEPTED` status *and* membership of an issue.
- No transition is permitted out of a terminal state.

### 6.3 Editorial event log — hybrid design

**Decision:** an append-only `editorial_events` table is the audit source of truth,
while current state is materialised on the manuscript row within the same transaction.

Each event stores sequence number, type, JSON payload, actor, timestamp, the previous
event's hash, and its own SHA-256 over `(prev_hash ‖ canonical payload)`. Any
retrospective edit breaks the chain and is detectable by a verification routine.

**Rationale.** Full event sourcing would require snapshotting and projection rebuilds —
real complexity and real risk inside 48 hours — for little additional credit. The
hybrid delivers the audit trail, replayability and tamper evidence that motivated event
sourcing, at a fraction of the cost. This is recorded as a justified architectural
trade-off, with full event sourcing listed under future evolution rather than as debt.

### 6.4 Double-blind integrity

Blinding is structural, not procedural, and is enforced at three levels:

1. **Projection level.** Reviewers receive a `BlindedManuscript` view object that has no
   author fields to leak — the data is absent from the type, not merely filtered.
2. **Document level.** Reviewers are only ever issued pre-signed URLs for the
   anonymised derivative, never the original.
3. **Reverse direction.** Author-facing review views omit reviewer identity and
   confidential editor comments entirely.

A dedicated test enumerates every reviewer-facing endpoint, serialises its response
against a fixture whose author names and affiliations are distinctive sentinels, and
asserts none of those sentinels appears in the output.

**Known limitation, documented rather than hidden:** metadata stripping cannot remove
author names printed in the visible body text of the PDF. The system therefore also
requires authors to confirm at submission that they have prepared an anonymised
manuscript, and flags detected name matches for the editor during screening. Full
in-document redaction is out of scope.

## 7. Architecture

### 7.1 Backend — hexagonal

```
backend/src/ugjcs/
├── domain/          entities, value objects, events, state machine, policies
│                    NO framework imports (enforced by import-linter in CI)
├── application/     use-case services, port protocols, DTOs, unit of work
├── infrastructure/  SQLAlchemy repositories, S3 storage, ARQ queue, email,
│                    security primitives, telemetry
└── api/             FastAPI routers, request/response schemas, dependencies
```

Dependencies point inwards only. Use-case services depend on port *protocols*; concrete
adapters are bound at composition root. The domain suite runs with no database, no
network and no framework, which is the demonstrable payoff of the structure.

### 7.2 Frontend — Next.js as Backend-For-Frontend

Public archive routes are statically rendered with incremental revalidation and call
the API directly — they are cacheable and carry no credentials.

All authenticated traffic is proxied through Next.js route handlers running
server-side. The browser holds an httpOnly, Secure, SameSite=Lax cookie scoped to the
Vercel origin; the route handler exchanges it for the bearer token attached to the
upstream call.

**Rationale.** Cookies between `*.vercel.app` and `*.cloudfront.net` are third-party and
are blocked by default in Safari and Brave — a defect that would surface on the
assessor's machine and nowhere else. The BFF makes the session cookie first-party,
keeps the access token out of reach of JavaScript, and hides the backend origin.

### 7.3 Infrastructure

```
Reader ─▶ Vercel (Next.js) ─┬─▶ CloudFront ─▶ ALB ─▶ ECS Fargate: api ─┬─▶ RDS Postgres
                            │                                          ├─▶ S3 (private)
                            └── (public pages, cached)                 └─▶ Redis ─▶ ECS Fargate: worker
```

CloudFront is architecturally necessary, not decorative: it supplies a trusted TLS
certificate on a `*.cloudfront.net` hostname, which is what permits an HTTPS frontend
to reach the backend without a registered domain. RDS and Redis sit in private subnets
with no public route. S3 blocks all public access; documents are reachable only through
short-lived pre-signed URLs.

### 7.4 Technology and justification

| Concern | Choice | Justification |
|---|---|---|
| Backend | FastAPI, Python 3.13 | Native async for I/O-bound work; Pydantic v2 gives validation and OpenAPI from one type definition |
| ORM | SQLAlchemy 2.0 + Alembic | Mature migrations; mapping style keeps domain classes framework-free |
| Database | PostgreSQL 16 | Native full-text search and JSONB remove the need for a search engine or document store |
| Queue | ARQ over Redis | Async-native and far lighter than Celery for this workload |
| Storage | S3 | Durable, private, pre-signed access |
| Frontend | Next.js 15, TypeScript, Tailwind | Static public pages for SEO plus server-side BFF in one deployment |
| Matching | scikit-learn + SciPy | TF-IDF and `linear_sum_assignment` are exactly the primitives needed |
| Similarity | `datasketch` MinHash + LSH | Sub-linear near-duplicate detection; appropriate to corpus scale |
| Tests | pytest, Hypothesis, testcontainers, Playwright, Schemathesis | Layer-appropriate verification |
| IaC | Terraform | Reproducible, reviewable, destroyable |

Python 3.13 is pinned deliberately: the host runs 3.14, which is ahead of some
scientific-stack wheels.

## 8. Data model

Principal tables: `users`, `roles`, `user_roles`, `manuscripts`,
`manuscript_versions`, `manuscript_authors`, `review_assignments`, `reviews`,
`editorial_decisions`, `issues`, `issue_papers`, `editorial_events`,
`similarity_reports`, `notifications`, `refresh_tokens`.

Design notes:

- `manuscripts.search_vector` is a generated weighted `tsvector` (title A, abstract B,
  keywords C, extracted text D) with a GIN index.
- `editorial_events` carries a unique constraint on `(manuscript_id, sequence)` and no
  UPDATE or DELETE path in application code.
- `refresh_tokens` stores hashes only, supporting rotation and revocation.
- Money and scores use exact types; timestamps are `timestamptz` in UTC throughout.

## 9. API surface

Versioned under `/api/v1`, documented automatically at `/docs`.

- `/auth` — register, verify, login, refresh, logout, me
- `/manuscripts` — create, list mine, retrieve, upload version, withdraw
- `/editorial` — screening queue, screen, reviewer recommendations, assign, decide
- `/reviews` — my invitations, respond, submit review
- `/issues` — compose, add or remove papers, publish
- `/archive` — public issues, papers, search, citation export
- `/admin` — users, roles, reviewer capacity, journal settings
- `/oai` — OAI-PMH verbs (`Identify`, `ListMetadataFormats`, `ListIdentifiers`,
  `ListRecords`, `GetRecord`)
- `/health`, `/ready` — probes

Errors follow RFC 9457 problem details with a stable `type` URI, so the frontend can
branch on machine-readable codes rather than message strings.

## 10. Advanced subsystems

### 10.1 Reviewer matching

1. Build a TF-IDF vocabulary over reviewer expertise profiles and the manuscript's
   title, abstract and keywords; suitability is cosine similarity.
2. Apply hard exclusions: the reviewer is an author, shares an affiliation with any
   author, has declined this manuscript before, is marked unavailable, or is already at
   capacity.
3. Expand each eligible reviewer into as many slots as their remaining capacity, build a
   cost matrix, and solve the assignment with the Hungarian algorithm
   (`scipy.optimize.linear_sum_assignment`) so load is balanced globally rather than
   greedily.
4. Present the ranked result to the editor **with the score and the reason for each
   exclusion**. The editor may override any recommendation.

Human-in-the-loop is a deliberate design position: the system advises, the editor
decides and is accountable.

### 10.2 Submission processing pipeline

Enqueued on upload, keyed by content checksum so retries are idempotent:

1. Verify the file by magic bytes rather than by extension or client-supplied MIME type;
   enforce size and page-count limits.
2. Extract text for search and similarity.
3. Produce the anonymised derivative by stripping XMP and DocInfo metadata.
4. Compute a MinHash signature and query the LSH index for near-duplicates in the
   internal corpus; persist a similarity report.
5. Write artefacts to S3 and advance the manuscript to `SUBMITTED`.

Failures are retried with exponential backoff and surfaced to the editor rather than
silently swallowed; a manuscript whose processing has failed is visibly flagged.

### 10.3 Scholarly interoperability

OAI-PMH 2.0 over Dublin Core with resumption tokens; DOI-shaped persistent identifiers
(`10.0000/ugjcs.v1i1.7` — explicitly documented as unregistered); BibTeX and RIS
export; `ScholarlyArticle` JSON-LD and Highwire Press meta tags on paper pages for
Google Scholar; and a generated `sitemap.xml`.

## 11. Security design

Argon2id password hashing. Short-lived access tokens with rotating, revocable refresh
tokens stored as hashes. Authorisation through a single `can(actor, action, resource)`
policy layer that denies by default, applied as a FastAPI dependency so no route can
omit it — with a test that walks the route table and fails if any route lacks a policy.
Strict CORS allowlist. Redis-backed rate limiting on authentication and submission.
Pydantic v2 strict schemas at every boundary. Private buckets with short-lived
pre-signed URLs. Security headers and a content security policy at the frontend.
Authorisation denials are audit-logged. Secrets live in AWS Secrets Manager, never in
the repository, and CI runs `bandit`, `pip-audit` and `npm audit` as gates.

An early action is to replace root AWS credentials with a least-privilege IAM deploy
user; the current use of root credentials is recorded as a critical-priority item in the
technical debt register until resolved.

## 12. Quality strategy

| Level | Scope | Tooling |
|---|---|---|
| Unit | State machine guards, policies, matching, blinding projections, hash chain | pytest |
| Property-based | Random legal event sequences preserve invariants | Hypothesis |
| Integration | Repositories, storage, queue, API per role | pytest, testcontainers |
| Contract | Responses conform to the published OpenAPI schema | Schemathesis |
| End-to-end | Submit → screen → review → decide → publish → read | Playwright |
| Security | Static analysis, dependency audit, baseline dynamic scan | bandit, pip-audit, OWASP ZAP |
| Performance | Archive and search under nominal load | k6 |
| Usability | Contrast, keyboard navigation, semantics | axe, manual audit |
| Acceptance | Scripted scenarios per role | Documented UAT script |

Invariants asserted by property tests: a manuscript never reaches `PUBLISHED` without a
preceding acceptance event; reviewer capacity is never exceeded; the blinded projection
never contains author data under any input; the event hash chain always verifies; no
transition leaves a terminal state.

## 13. Deployment and CI/CD

Pull requests run: ruff, mypy, import-linter, pytest with the coverage gate, bandit and
pip-audit for the backend; ESLint, `tsc --noEmit`, Vitest and a production build for the
frontend. Merges to `main` build and push the image to ECR, run migrations as a one-off
ECS task, update the api and worker services, then smoke-test the live health endpoint,
rolling back on failure. The frontend deploys through Vercel's Git integration.
Infrastructure changes are applied by `terraform apply` from `infra/`, reviewed as code.

Operating cost is roughly USD 35–55 per month with ALB, Fargate, RDS and Redis running.
The environment is kept live through assessment and destroyed afterwards with
`terraform destroy`; the figure is documented because cost awareness is an engineering
competence.

## 14. Effort estimation approach

**Use Case Points** as the primary technique, because the system is defined by actor
interactions with a stable use-case boundary — the situation UCP was designed for — and
because unadjusted use-case and actor weights can be derived directly from §5.1 rather
than guessed. **COCOMO II Early Design** serves as an independent cross-check from a
size-and-cost-driver perspective; agreement between two methods on different inputs is
stronger evidence than precision from one.

The estimate is computed *before* implementation and its output determines the MoSCoW
cut: requirements that do not fit the available hours are demoted rather than rushed,
and the demotion is recorded with its reason. Assumptions, technical and environmental
factors, productivity rate and the derived person-hours are documented in full, along
with a retrospective comparison of estimated against actual effort — the variance
analysis is itself assessable evidence.

## 15. Technical debt policy

Debt is recorded at the moment it is incurred, not reconstructed afterwards. Every
entry carries **Debt → Cause → Impact → Priority → Proposed resolution**, and is
classified as:

- **Critical** — must be resolved before real users are admitted (e.g. root AWS
  credentials, any authorisation gap).
- **Scheduled** — accepted now, with a named release for repayment.
- **Acceptable** — a conscious trade-off that may remain indefinitely, with the
  condition that would change that judgement stated explicitly.

Debt deliberately taken to meet the deadline is distinguished from debt arising from
inexperience or oversight, following Fowler's quadrant. Items are cross-referenced to
the requirements they affect and rolled into the maintenance plan as a repayment
schedule.

## 16. Assumptions and constraints

**Assumptions.** A single journal instance suffices. Reviewers are motivated to
participate without incentive mechanisms. Corpus scale is on the order of hundreds, not
millions, of papers, which justifies Postgres full-text search over a dedicated search
engine. Authors submit PDFs. Email delivery is available through one transactional
provider. Seed content is synthetic and clearly labelled.

**Constraints.** A 48-hour development window for one developer. AWS and Vercel free or
low-cost tiers. No registered domain, hence the CloudFront TLS strategy. No access to
real departmental data, hence synthetic seeding. The deployment must remain reachable
for assessment.

## 17. Future evolution

Full event sourcing with rebuildable projections; multi-journal tenancy so the platform
serves the wider faculty; ORCID authentication and real Crossref DOI registration;
similarity screening against external corpora; embedding-based reviewer matching to
replace TF-IDF; a production typesetting and galley pipeline; reviewer reputation and
reliability modelling; blue-green deployment; and read-replica scaling for the public
archive.

---

## Appendix A — Naming

The platform and the journal share the name **UGJCS** (University of Ghana Journal of
Computing Science). The codebase nonetheless separates journal-configuration data from
platform logic, so that multi-journal tenancy remains reachable without restructuring —
a deliberate seam, recorded here so that it is understood as design rather than
accident.
