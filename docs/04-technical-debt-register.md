# UGJCS — Technical Debt Register

**Project:** UGJCS — University of Ghana Journal of Computing Science
**Author:** Roger Koranteng Obeng (22424140)
**Opened:** 2026-08-12
**Status:** Live. Entries are added at the moment debt is incurred, not reconstructed afterwards.

## How this register is kept

Every entry records **Debt → Cause → Impact → Priority → Proposed resolution**, and is classified by
Fowler's distinction between debt taken *deliberately* to meet a constraint and debt arising from
*inadvertence*. Priority uses three levels:

- **Critical** — must be resolved before real users are admitted to the system.
- **Scheduled** — accepted now, with a named release for repayment.
- **Acceptable** — a conscious trade-off that may remain indefinitely. Each states the condition
  that would change that judgement.

An entry is only recorded here once the debt actually exists in the codebase. Consequences of work
not yet begun are forecasts, not debt, and are kept in the relevant implementation plan instead.

---

## Critical

### TD-01 — AWS access uses root account credentials

| | |
|---|---|
| **Debt** | The deployment toolchain authenticates to AWS as the account root user rather than a least-privilege IAM principal. |
| **Cause** | Deliberate. The account was configured before the project began, and replacing root credentials was not on the critical path to a working domain core. |
| **Impact** | Root credentials cannot be scoped, cannot be rotated per-service, and cannot be revoked without disrupting every other use of the account. Their compromise is unrecoverable within the account. |
| **Priority** | **Critical** — must be resolved before any infrastructure is provisioned, not merely before real users. |
| **Resolution** | Create an IAM deploy user restricted to ECR, ECS, RDS, S3 and CloudFront actions on this project's resources; store its credentials in GitHub Actions secrets; enable MFA on root and stop using it. |

### TD-02 — A reviewer may be authorised to review their own manuscript

| | |
|---|---|
| **Debt** | `Action.REVIEW` is granted on the `REVIEWER` role alone, with no per-manuscript predicate. An actor holding both `AUTHOR` and `REVIEWER` is not prevented by the policy layer from reviewing work they wrote. |
| **Cause** | Inadvertent, found by the final whole-branch review. `_OWNERSHIP_ACTIONS` covers `RESUBMIT` but the same reasoning was not applied to `REVIEW`. |
| **Impact** | The central conflict-of-interest failure for a double-blind journal. No exploit exists today because no HTTP surface calls the action, but the gap is real the moment one does. |
| **Priority** | **Critical before real users.** |
| **Resolution** | Introduce reviewer assignment as a first-class entity; make `REVIEW` an ownership-style action predicated on an accepted assignment, and exclude actors appearing in `author_ids`. Documented in `policies.py`'s module docstring so it cannot be forgotten. |

### TD-03 — Submitted reviews are counted, not identified

| | |
|---|---|
| **Debt** | `Manuscript.record_review` increments an integer counter and never checks the supplied `reviewer_id` against an assignment, against `author_ids`, or against reviewers who have already submitted. |
| **Cause** | Deliberate scope limitation — assignment tracking belongs with the reviewer-matching subsystem, which is not yet built. |
| **Impact** | One reviewer calling the method twice reaches the two-review quorum alone and closes the review round, so an editorial decision could rest on a single opinion. |
| **Priority** | **Critical before real users.** |
| **Resolution** | Replace `submitted_reviews: int` with `frozenset[UserId]` of reviewers who have submitted, and reject a submission from a reviewer without an accepted assignment. Documented in the method's docstring. |

---

## Scheduled

### TD-04 — The audit chain has no external anchor

| | |
|---|---|
| **Debt** | Hash chaining detects alteration, reordering and removal *within* the chain, but cannot detect truncation of the tail, a forged event appended through the legitimate API, or a wholly fabricated history rebuilt from the genesis hash. |
| **Cause** | Deliberate. An anchor is an operational concern outside the domain layer, and building one was not affordable in the available time. |
| **Impact** | An attacker with write access to the event store could truncate recent history, or replace it entirely, without the application detecting it. Partially mitigated: a PostgreSQL trigger rejects `UPDATE` and `DELETE` on the event table, and the foreign key refuses to delete a manuscript that has audit events. |
| **Priority** | **Scheduled** — next release after deployment. |
| **Resolution** | Publish a periodically signed checkpoint of the latest `event_hash` to storage the application cannot rewrite, and assert an expected event count at the persistence boundary. Stated explicitly in `hashchain.py`'s module docstring so no caller assumes more than the code provides. |

### TD-05 — Blinding does not scrub the manuscript body

| | |
|---|---|
| **Debt** | `BlindedManuscript` carries `title`, `abstract` and `keywords` verbatim. Self-identifying text — an author's name in the title, or an abstract reading "extending our earlier work in [Obeng 2025]" — reaches the reviewer unchanged. |
| **Cause** | Deliberate. Reliable text redaction is a research problem; a bad redaction that leaks one name would undermine the guarantee more thoroughly than not attempting it. |
| **Impact** | Double-blind integrity depends partly on author compliance rather than entirely on the system. |
| **Priority** | **Scheduled.** |
| **Resolution** | Screening surfaces detected author-name matches to the editor before reviewers are assigned; submission guidance requires authors to anonymise their own manuscript. Automated body-text redaction is recorded as future evolution, not as a near-term fix. |

### TD-06 — The editorial event log has no blinded projection

| | |
|---|---|
| **Debt** | Events carry `actor_id`, and decision events carry an editor's free-text rationale. There is no `BlindedEvent` type; the log is protected by authorisation policy alone (`VIEW_AUDIT` is editor-only). |
| **Cause** | Inadvertent — blinding was designed around the aggregate, and the event log was not considered as a second surface a reviewer might read. |
| **Impact** | None today, because no reviewer-facing path reads the log. The risk is that a future endpoint exposes editorial history without a projection to make the omission structural. |
| **Priority** | **Scheduled**, before any reviewer-facing audit view is built. |
| **Resolution** | Add a `BlindedEvent` projection following the same "omit the field from the type" principle as `BlindedManuscript`. Noted in `blinding.py`'s docstring. |

### TD-07 — No authorisation action maps to the blinded projection

| | |
|---|---|
| **Debt** | `blind()` exists and `policies.can()` exists, but no `Action` connects them. An adapter serving a reviewer must remember to call `blind()`; nothing enforces it. |
| **Cause** | Inadvertent. The two modules were specified independently and the seam between them was never designed. |
| **Impact** | The double-blind guarantee rests on adapter discipline rather than on a check the system can enforce — the exact weakness the structural approach was chosen to avoid. |
| **Priority** | **Scheduled**, alongside TD-02. |
| **Resolution** | Introduce an action representing "read as an assigned reviewer" whose only successful return path is the blinded projection. |

### TD-08 — The tail-append capability is unverified

| | |
|---|---|
| **Debt** | `hashchain.append` derives the expected sequence from the last link rather than the chain length, so it can append onto a chain tail. No test pins that capability; reverting to the older length-based form still passes the whole suite. |
| **Cause** | Inadvertent. The change was made to remove an O(n)-per-write coupling, and the test that would protect it was not added with it. |
| **Impact** | A future refactor could silently reintroduce whole-history loads on every write. |
| **Priority** | **Scheduled** — with the persistence work that first exploits tail-appending. |
| **Resolution** | A test appending onto a sliced tail whose last sequence exceeds its length, plus a repository that loads only the last link rather than the full chain. |

---

## Acceptable

### TD-09 — A hybrid event log rather than full event sourcing

| | |
|---|---|
| **Debt** | Current state is materialised on the manuscript row alongside the append-only event log, rather than being derived by replaying events. |
| **Cause** | Deliberate architectural trade-off, decided at design time and recorded in the specification. |
| **Impact** | Two representations of the same truth could in principle diverge. Mitigated by routing every state change through a single `_transition` method that writes both in one transaction; a grep confirms exactly one assignment to `status` in the entire aggregate. |
| **Priority** | **Acceptable.** |
| **Condition that would change this** | If projections multiply beyond the current single materialised view, or if replaying history to a past state becomes a requirement, full event sourcing with rebuildable projections becomes worth its cost. |

### TD-10 — The coverage gate sits at 85% while the code delivers 100%

| | |
|---|---|
| **Debt** | The CI gate fails below 85% line and branch coverage, well under what the branch actually achieves. |
| **Cause** | Deliberate. The gate is a floor that prevents regression, not a target. |
| **Impact** | Coverage could fall by fifteen points without CI objecting. |
| **Priority** | **Acceptable.** |
| **Condition that would change this** | Raising the floor is cheap and would be worthwhile if coverage ever drifts down. It is deliberately not set to 100%, because a gate at exactly the current figure makes any legitimate refactor fail the build for reasons unrelated to quality. |

### TD-12 — A timestamp representation reached the audit hash

| | |
|---|---|
| **Debt** | Resolved, recorded because the class of defect matters. `canonical_bytes()` hashed `occurred_at.isoformat()`, which includes the UTC offset, while PostgreSQL `timestamptz` normalises any offset to UTC on storage. An event recorded at a non-UTC offset would hash one way before persistence and differently after. |
| **Cause** | Inadvertent. Every test used a UTC datetime, so the suite was structurally blind to it. Four independent reviews of the in-memory code did not find it; it was found by reasoning about the database boundary. |
| **Impact** | `verify()` would have reported tampering on an event nobody touched. A false positive is worse than no check, because it destroys confidence in every genuine detection. |
| **Priority** | **Resolved** — `canonical_bytes()` now normalises to UTC, so the offset cannot reach the digest by construction. |
| **Resolution** | Done. The lesson stands: a value that crosses a storage boundary may return in a different representation than it went in, and only an integration test or explicit canonicalisation catches it. |

### TD-11 — Coverage is a weak signal, and this project has the evidence

| | |
|---|---|
| **Debt** | Not debt in the code, but a recorded limitation of the verification strategy that shapes how the other entries should be read. |
| **Cause** | Structural property of line and branch coverage. |
| **Impact** | Mutation testing during the final review found four mutations surviving a suite at 100% coverage — including deletion of the single line that makes the hash chain a chain, which left every test passing. Coverage measured that lines executed, not that behaviour was asserted. |
| **Priority** | **Acceptable** as a known limitation, provided it is compensated. |
| **Second illustration** | Coverage reported `Branch 0` for the mappers module despite branch coverage being enabled, because coverage.py does not treat an inline ternary as a branch point. "100% coverage, zero branches missed" therefore did not prove both arms of `IssueId(row.issue_id) if ... else None` had run — and the populated arm never had. |
| **Resolution** | Four gaps were closed by targeted tests once identified. Systematic mutation testing (for example `mutmut` or `cosmic-ray`) in CI is recorded as future evolution; it is the only automated technique that would have found these without a reviewer reading for intent. |

---

## Summary

| Priority | Count | Entries |
|---|---|---|
| Critical | 3 | TD-01, TD-02, TD-03 |
| Scheduled | 5 | TD-04 … TD-08 |
| Acceptable | 3 | TD-09, TD-10, TD-11 |
| Resolved, retained as a record | 1 | TD-12 |

**Repayment sequence.** TD-01 before any infrastructure is provisioned. TD-02, TD-03 and TD-07 are one
piece of work — they are all consequences of reviewer assignment not existing yet — and should be repaid
together in the release that introduces it. TD-04 follows deployment. TD-05, TD-06 and TD-08 are
independent and may be scheduled by convenience.

**How this register was produced.** Ten of these eleven entries were found by independent review of
work that had already passed every automated gate: linting, strict type checking, an architecture
contract, and a full test suite at 100% coverage. That is the register's most useful lesson, and it is
recorded here rather than only in the retrospective: automated gates establish a floor, and reading
code for what it *claims* is what finds the things above it.
