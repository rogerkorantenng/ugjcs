# Software Requirements Specification

<dl class="docmeta">
  <dt>Project</dt>
  <dd>SDJ Editorial Portal — an editorial portal for the Science and Development Journal (SDJ), published by the College of Basic and Applied Sciences (CBAS), University of Ghana</dd>
  <dt>Document</dt>
  <dd>02 — Software Requirements Specification</dd>
  <dt>Author</dt>
  <dd>Roger Koranteng Obeng, student ID 22424140</dd>
  <dt>Assessor</dt>
  <dd>Prof. Solomon Mensah</dd>
  <dt>Date</dt>
  <dd>2026-08-12</dd>
  <dt>Conformance</dt>
  <dd>Adapted from IEEE 830-1998 and ISO/IEC/IEEE 29148:2018</dd>
  <dt>Status</dt>
  <dd>Authoritative. Where this document and the implementation disagree, the implementation governs and the disagreement is recorded (section 4.1, section 7).</dd>
</dl>

**Naming.** The product specified here is the **SDJ Editorial Portal**. The repository
(`github.com/rogerkorantenng/ugjcs`), hosting URLs, package names and infrastructure resource
names retain the pilot's internal codename **UGJCS**; wherever `ugjcs` appears in a path, URL
or identifier, it is that codename, not a separate system. The deployed system is a prototype
built for an Advanced Software Engineering exam, not SDJ's official production system.

**Revision note (2026-08-12, post-implementation).** This document was originally authored
before the API and frontend existed, when only the domain layer and the database
persistence adapter were built. Section 2.1, section 2.4, section 4.3, section 5 and section 7 have since been revised against
the finished, deployed system — the live API (`https://tsxsbf9rzp.us-east-1.awsapprunner.com`,
confirmed against its own `/openapi.json`), the live frontend
(`https://ugjcs-frontend.vercel.app`), the backend source under `backend/src/ugjcs/api/` and
`frontend/src/app/`, the test suites under `backend/tests/`, and
Testing_Report.pdf. That first revision moved twelve requirements from planned to
implemented-and-tested, refined six to "partially implemented" with a named gap, and left
eleven genuinely not implemented.

A second revision on 2026-08-14 reconciled the document against two feature waves that
landed after the original build. It moved eight further lines to implemented-and-tested,
added six new requirements (FR-29 to FR-34) for capabilities the original set never
anticipated, and corrected several rows that had begun to understate the system rather
than overstate it. The current totals are in section 5. Requirement identifiers, MoSCoW
priorities and the sections neither revision touched are unchanged from the original.

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements of the SDJ Editorial
Portal, a double-blind peer-review and editorial management platform built for the Science
and Development Journal (SDJ), published by the College of Basic and Applied Sciences,
University of Ghana. It is written for three audiences: the assessor judging
requirements-engineering competence against this final project's rubric, a future maintainer
who needs to know what the system is contracted to do, and the author's own
implementation, which this document constrains. Requirements are stated so that each is
individually testable; no requirement is expressed as an unmeasurable quality goal.

### 1.2 Scope

The portal manages SDJ's complete scholarly publishing lifecycle: account registration and
role-based access; manuscript submission with file upload; automated post-upload
processing; editorial screening; assisted reviewer assignment; structured double-blind
review; editorial decisions and revision rounds; issue composition and publication; a
public archive with search, citation export and metadata harvesting; and a tamper-evident
editorial audit trail. Payment processing, copy-editing/typesetting, multi-journal
tenancy, ORCID federation, real DOI registration, and plagiarism screening against
external corpora are explicitly out of scope (design specification section 4.2). The full
functional boundary is enumerated in section 5 of that specification and restated as testable
requirements in section 3 of this document.

### 1.3 Definitions, acronyms and abbreviations

| Term | Meaning |
|---|---|
| SDJ | Science and Development Journal — the established CBAS journal this portal is built for |
| CBAS | College of Basic and Applied Sciences, University of Ghana — SDJ's publisher and the project's client |
| UGJCS | The pilot's internal codename for this system (see the naming note above) — survives only in package names, the repository name and hosting URLs |
| Double-blind | Neither author nor reviewer identity is disclosed to the other party during review |
| MoSCoW | Must/Should/Could/Won't — requirement prioritisation scheme |
| UCP | Use Case Points — the effort-estimation technique that produced the MoSCoW cut |
| FR / NFR | Functional requirement / non-functional requirement |
| UC | Use case, as enumerated in the effort-estimation document |
| RBAC | Role-based access control |
| COI | Conflict of interest |
| EiC | Editor-in-Chief |
| HoD | Head of Department — the design's shorthand for the college-leadership analytics consumer |
| BFF | Backend-for-Frontend — the Next.js server-side proxy pattern used for authenticated traffic |
| OAI-PMH | Open Archives Initiative Protocol for Metadata Harvesting |
| DOI | Digital Object Identifier (the portal issues DOI-*shaped* but unregistered identifiers — section 4.2) |
| TF-IDF | Term frequency–inverse document frequency, used for reviewer–manuscript matching |
| LSH | Locality-sensitive hashing, used for near-duplicate similarity screening |
| WCAG | Web Content Accessibility Guidelines |
| RFC 9457 | Problem Details for HTTP APIs — the platform's error-response format |
| Hash chain | The append-only audit mechanism: each event hashes over its predecessor's hash and its own payload |

### 1.4 References

- Design specification — the design specification
- Effort estimation — Effort_Estimation.pdf
- Technical debt register — Technical_Debt_Plan.pdf
- Domain implementation — `backend/src/ugjcs/domain/{transitions,enums,policies,blinding,manuscript,hashchain,events}.py`
- IEEE Std 830-1998, *Recommended Practice for Software Requirements Specifications*
- ISO/IEC/IEEE 29148:2018, *Systems and software engineering — Life cycle processes — Requirements engineering*

### 1.5 Overview

Section 2 describes the product, its user classes and its operating constraints. Section 3 states each
functional and non-functional requirement in testable form. Section 4 gives the manuscript
lifecycle as implemented, the actor/use-case mapping and the authorisation matrix. Section 5 is
the requirements traceability matrix, stated honestly for what is built versus planned.
Section 6 explains the MoSCoW prioritisation and how the effort estimate drove it. Section 7 states the
system's limitations plainly, cross-referenced to the technical debt register.

---

## 2. Overall description

### 2.1 Product perspective

The portal is a new, self-contained system built for the Science and Development Journal
(SDJ), published by the College of Basic and Applied Sciences; it replaces the journal's
current ad hoc process of email, shared drives and spreadsheets rather than integrating
with an existing editorial system. It is a
three-tier web application: a Next.js frontend (public archive, search, paper detail, and
author/reviewer/editor/Editor-in-Chief screens, with all authenticated traffic proxied
server-side as a Backend-For-Frontend), a FastAPI backend built as a hexagonal
architecture with a framework-free domain core, and PostgreSQL and S3 as its persistence
and document-storage infrastructure.

**This is no longer a forward-looking description.** The domain layer, the database
persistence adapter, the application use-case layer, the FastAPI API layer
(`/auth`, `/admin`, `/billing`, `/manuscripts`, `/editorial`, `/editorial-certificate`,
`/reviews`, `/archive`, `/people`, `/health`, `/ready`) and the Next.js frontend are all
built, tested and deployed: API at `https://tsxsbf9rzp.us-east-1.awsapprunner.com`,
frontend at `https://ugjcs-frontend.vercel.app`. Section 5's traceability matrix states,
requirement by requirement, which of these are implemented and tested, which are partially
built with a named gap, and which are not built at all.

Four things named in the original design remain unbuilt: OAI-PMH harvesting (FR-22),
similarity screening (FR-20), notifications of any kind, and asynchronous post-upload
processing. Redis and an ARQ worker were designed for that last one (design specification
Section 7) but are absent from the delivered codebase, and nothing in the current system depends
on them; FR-20 is the requirement that would have used them. Terraform-managed
ECS/ALB/CloudFront was the original deployment design, and the actual deployment target
differs (section 2.4, TD-14).

Six capabilities have no counterpart in the original requirement set, because they were
identified after it was written. They are added as FR-29 to FR-34: article processing
charges, the administrator console, decision certificates, anonymisation preflight, review
deadlines, and self-service author registration.

### 2.2 Product functions — summary

- Register, authenticate and authorise users under five roles, several of which one
  account may hold concurrently.
- Accept manuscript submissions, validate and process them asynchronously, and produce
  an anonymised derivative for reviewers.
- Screen submissions and route them to review, revision, or desk rejection.
- Recommend reviewers by expertise match, exclude conflicts, balance workload, and let
  the editor accept, reject or override every recommendation.
- Collect structured, double-blind reviews and aggregate them into an editorial
  decision once a quorum is met.
- Support revision rounds between author and editor.
- Compose issues from accepted manuscripts and publish them to a public archive.
- Serve the archive to anonymous readers with full-text search, citation export and
  OAI-PMH harvesting.
- Record every editorial event in a tamper-evident, append-only log.

- Bill and settle an article processing charge once a paper is accepted.
- Administer accounts, roles, reviewer capacity and activation from a console.
- Let anyone verify a published paper's editorial history against a tamper-evident chain.

*This list states intended product scope. It is not a claim that every bullet is built.
Section 5's traceability matrix is the authoritative, requirement-by-requirement account of what
is implemented today. Of the bullets above, asynchronous processing (section 2.1) and OAI-PMH
harvesting (FR-22) are the two that are not built.*

### 2.3 User classes and characteristics

| User class | Description | Frequency of use | Technical proficiency required |
|---|---|---|---|
| Author | Submits and tracks manuscripts, responds to review | Occasional, bursty around submission and revision | Low — web form and file upload only |
| Reviewer | Evaluates blinded manuscripts against structured criteria | Occasional, invitation-driven | Low |
| Editor | Screens submissions, assigns reviewers, records decisions | Regular, throughout each submission's lifecycle | Moderate — must interpret matching output and audit trail |
| Editor-in-Chief | All Editor capability plus issue composition, publication and policy configuration | Regular; final authority | Moderate |
| Administrator | Manages accounts, roles and reviewer capacity | Infrequent | Low |
| Reader | Anonymous; discovers, reads, cites and downloads published work | Frequent, unauthenticated | Low |
| CBAS college leadership (secondary) | Consumes editorial throughput analytics | Infrequent | Low |
| Indexing service (external system) | Harvests metadata via a defined API | Automated, scheduled | N/A — machine actor |

A single account may hold multiple roles simultaneously (design specification section 3); this
is a deliberate design choice with a direct security consequence recorded in section 4.3 and
Section 7 (an Author–Reviewer dual-role holder is not currently prevented from reviewing their
own manuscript).

### 2.4 Operating environment

**As deployed** (superseding the design specification's ECS/ALB/CloudFront topology —
see TD-14 for why, and for why no functional capability was lost by the substitution):
Backend: Python 3.13, FastAPI, PostgreSQL 16, deployed as a container on AWS App Runner,
reachable at `https://tsxsbf9rzp.us-east-1.awsapprunner.com` with a trusted TLS
certificate on App Runner's own `*.awsapprunner.com` hostname (no registered domain is
available, which is what the CloudFront design was originally solving; App Runner
supplies the same guarantee directly). Frontend: Next.js 15 / TypeScript / Tailwind,
deployed on Vercel at `https://ugjcs-frontend.vercel.app`. Storage: private S3 buckets,
documents reachable only via short-lived pre-signed URLs. Client environment: any
evergreen browser at 360 px width or above; readers require no account. Redis and an ARQ
worker, specified for asynchronous post-upload processing, are not present in the
delivered infrastructure — nothing currently deployed depends on them (section 2.1).

### 2.5 Design and implementation constraints

- A 48-hour solo development window (effort estimation section 8), which forced the MoSCoW
  cut in section 6 of this document.
- No registered domain — the CloudFront TLS strategy is not optional but architecturally
  necessary (design specification section 7.3).
- AWS and Vercel free/low-cost tiers; operating cost is targeted at USD 35–55/month.
- Domain layer must import no framework code, enforced by an import-linter contract in
  CI (NFR-13). **As delivered**, two contracts are enforced (`backend/.importlinter`):
  `domain-purity` (the constraint above) and `layers` (`api → infrastructure →
  application → domain`, dependencies point inward only) — both gate `make check` and
  therefore CI on every push and pull request.
- The domain layer is framework-free by construction; this is a testable constraint,
  not an aspiration.
- Synthetic seed data only — no real SDJ submissions or reviewer data are used.

### 2.6 Assumptions and dependencies

Assumptions (stated as assumptions — the project had no access to real SDJ operational
data): a single journal instance, SDJ itself, suffices; reviewers participate without
incentive mechanisms; SDJ's corpus scale is hundreds, not millions, of papers, justifying Postgres
full-text search over a dedicated search engine; authors submit PDFs; a single
transactional email provider is available. Dependencies: AWS managed services (ECS, RDS,
S3, CloudFront), Vercel, and a transactional email provider must remain available and
within free/low-cost tier limits for the system to operate as specified.

---

## 3. Specific requirements

Each functional requirement is stated as "the system shall …", is atomic (one testable
behaviour per identifier), and carries the preconditions that must hold before it may
fire, the postconditions guaranteed on success, and the acceptance criterion by which it
is verified. Identifiers are preserved unchanged from the design specification; no
requirement is renumbered. One requirement, **FR-25a**, is added beyond the original set
and is marked **NEW** — it was surfaced by comparing the implemented lifecycle guard
(`transitions.py`, which permits `WITHDRAWN` as a target state) against the implemented
authorisation layer (`policies.py`, which has no action gating who may invoke that
transition), a gap the original requirement (FR-25, which named the feature but not its
authorisation mechanism) did not anticipate.

### 3.1 Functional requirements

#### Group A — Identity and access

| ID | Statement | Actor | Pri | Preconditions | Postconditions | Acceptance criteria |
|---|---|---|---|---|---|---|
| FR-01 | The system shall let a person register an account and shall verify their email address before the account is usable. | Author, Reviewer | M | Email address not already registered | Account exists in an unverified state until the verification link is followed | Registration with a duplicate email is rejected; login is refused until verified |
| FR-02 | The system shall authenticate a registered user and maintain a session that expires and can be explicitly revoked. | All authenticated | M | Account verified | A valid session token is issued; revoked or expired tokens are rejected on every subsequent call | A revoked refresh token fails all further use; an expired access token is rejected without a valid session |
| FR-03 | The system shall let an Administrator assign and revoke roles, and a user may hold several roles concurrently. | Administrator | M | Target account exists | The account's role set reflects the change immediately | Assigning a second role does not remove the first; policy checks re-evaluate against the updated set on the next request |

#### Group B — Submission intake and processing

| ID | Statement | Actor | Pri | Preconditions | Postconditions | Acceptance criteria |
|---|---|---|---|---|---|---|
| FR-04 | The system shall let an Author create a submission comprising title, abstract, keywords, co-authors and a PDF file. | Author | M | Author is authenticated | Manuscript exists in `DRAFT`, then transitions to `SUBMITTED` | A manuscript with all required fields and a valid PDF reaches `SUBMITTED`; the transition is illegal from any other state |
| FR-05 | The system shall reject an uploaded file that fails type, size or integrity validation, and shall return a clear reason. | System | M | A file has been uploaded | Rejected files never reach persistent storage or a manuscript version | A renamed non-PDF file (validated by magic bytes, not extension) is rejected with a specific reason code |
| FR-06 | The system shall generate an anonymised copy of every submitted document, distinct from the original. | System | M | A manuscript version has been uploaded and validated | Two document references exist per version: original and anonymised | The anonymised derivative has XMP and DocInfo metadata stripped; reviewers are never issued the original |
| FR-20 | The system shall screen a submission for similarity against the internal corpus of previously submitted manuscripts. | System | S | Text has been extracted from the submission | A similarity report is persisted against the manuscript version | A near-duplicate submitted twice produces a report flagging the match; unrelated submissions produce no false positive on the seeded corpus |

#### Group C — Screening and reviewer assignment

| ID | Statement | Actor | Pri | Preconditions | Postconditions | Acceptance criteria |
|---|---|---|---|---|---|---|
| FR-07 | The system shall let an Editor or Editor-in-Chief screen a submission by sending it to review, requesting pre-review changes, or desk-rejecting it. | Editor | M | Manuscript is in `UNDER_SCREENING` | Manuscript moves to `UNDER_REVIEW`, `REVISION_REQUESTED` or `DESK_REJECTED` respectively | Any of the three legal targets is reachable only from `UNDER_SCREENING`; no other actor role can invoke it |
| FR-08 | The system shall recommend reviewers ranked by expertise match, excluding conflicts of interest and respecting reviewer capacity. | System | M | Manuscript is in `UNDER_SCREENING` or `UNDER_REVIEW` | A ranked candidate list is produced with a score and, for excluded reviewers, a stated reason | A reviewer sharing an author's affiliation, or already at capacity, never appears as a positive recommendation |
| FR-09 | The system shall let an Editor invite reviewers, and may override any system recommendation. | Editor | M | Manuscript is in `UNDER_SCREENING` or `UNDER_REVIEW` | A review assignment is created in the `INVITED` state | An editor-chosen reviewer outside the recommended list can still be invited |

#### Group D — Review and revision

| ID | Statement | Actor | Pri | Preconditions | Postconditions | Acceptance criteria |
|---|---|---|---|---|---|---|
| FR-10 | The system shall let an invited reviewer accept or decline the invitation, optionally with a reason. | Reviewer | M | Assignment is in `INVITED` | Assignment moves to `ACCEPTED` or `DECLINED` | A declined invitation frees the reviewer's capacity and is visible to the editor with its reason |
| FR-11 | The system shall let a reviewer with an accepted assignment submit a structured review: criterion scores, an overall recommendation, comments to the author, and confidential comments to the editor. | Reviewer | M | Assignment is `ACCEPTED`; manuscript is `UNDER_REVIEW` | A `Review` record is stored against the assignment; assignment moves to `SUBMITTED` | Confidential comments never appear in any author-facing view; a review cannot be submitted twice by the same reviewer for the same manuscript |
| FR-13 | The system shall let the corresponding author submit a revised version together with a response-to-reviewers letter. | Author | M | Manuscript is in `REVISION_REQUESTED`; actor is the corresponding author | Manuscript moves to `RESUBMITTED`, then to `UNDER_REVIEW` or `UNDER_SCREENING` at editorial discretion | A non-corresponding co-author's attempt to resubmit is denied; the letter is attached to the new version |

#### Group E — Editorial decision and withdrawal

| ID | Statement | Actor | Pri | Preconditions | Postconditions | Acceptance criteria |
|---|---|---|---|---|---|---|
| FR-12 | The system shall let an Editor or Editor-in-Chief record an editorial decision once the configured minimum number of reviews has been submitted. | Editor | M | Manuscript is `REVIEWS_COMPLETE` (or `UNDER_SCREENING` for desk rejection, which requires no reviews) | Manuscript moves to `ACCEPTED`, `REJECTED` or `REVISION_REQUESTED` | A decision attempted below quorum is refused with the current review count; desk rejection is legal only from `UNDER_SCREENING` |
| FR-25 | The system shall let the corresponding author withdraw a submission before a decision is recorded. | Author | S | Manuscript is in `SUBMITTED`, `UNDER_SCREENING`, `UNDER_REVIEW`, `REVIEWS_COMPLETE` or `REVISION_REQUESTED` | Manuscript moves to `WITHDRAWN`, a terminal state | A withdrawal attempted from `ACCEPTED` or any other non-listed state is refused |
| **FR-25a** *(NEW)* | The system shall authorise withdrawal only for the corresponding author of the manuscript being withdrawn, via a dedicated ownership-checked action equivalent to how `RESUBMIT` is checked. | Author | M *(elevated — closes a live authorisation gap)* | `Action.WITHDRAW` exists in the policy layer with the same ownership predicate as `Action.RESUBMIT` | An actor who is not the corresponding author, including a co-author, cannot invoke the transition regardless of role | A non-corresponding-author holder of the `AUTHOR` role attempting withdrawal is denied |

#### Group F — Publication and public archive

| ID | Statement | Actor | Pri | Preconditions | Postconditions | Acceptance criteria |
|---|---|---|---|---|---|---|
| FR-15 | The system shall let the Editor-in-Chief compose an issue from accepted manuscripts and publish it. | Editor-in-Chief | M | Manuscripts are `ACCEPTED`; actor holds `EDITOR_IN_CHIEF` | Manuscripts move `ACCEPTED → SCHEDULED → PUBLISHED`; the issue becomes publicly visible | An Editor without EiC role cannot publish; a manuscript not in `ACCEPTED` cannot be added to an issue |
| FR-16 | The system shall let an unauthenticated reader browse issues and read published papers. | Reader | M | Issue is `PUBLISHED` | Paper content and metadata are served without requiring login | Anonymous request to a published paper's page succeeds; request to an unpublished manuscript is refused |
| FR-17 | The system shall provide full-text search across published papers with filters. | Reader | M | At least one paper is published | Search returns ranked results within the performance bound of NFR-09 | A query on a distinctive term present only in one seeded paper returns that paper first |
| FR-18 | The system shall let a reader download a published paper's PDF. | Reader | M | Paper is published | The original (non-anonymised) PDF is served via the archive path | Download succeeds without authentication for any published paper |
| FR-21 | The system shall let a reader export a paper's citation as BibTeX and RIS. | Reader | S | Paper is published | A correctly formatted citation file is returned in the requested format | The exported BibTeX parses under a standard BibTeX parser without error |
| FR-22 | The system shall expose an OAI-PMH endpoint serving Dublin Core metadata for all published papers. | External system | S | At least one paper is published | `Identify`, `ListMetadataFormats`, `ListIdentifiers`, `ListRecords` and `GetRecord` all respond per OAI-PMH 2.0 | A harvest run against the seeded archive completes with resumption tokens honoured correctly |
| FR-27 | The system shall resolve a persistent identifier to its paper. | Reader | C | Identifier is DOI-shaped and assigned | Resolving the identifier returns (or redirects to) the paper | A well-formed but unassigned identifier returns a 404, not a server error |

#### Group G — Transparency and communication

| ID | Statement | Actor | Pri | Preconditions | Postconditions | Acceptance criteria |
|---|---|---|---|---|---|---|
| FR-14 | The system shall let an author view their own submissions and each one's status timeline. | Author | M | Actor is authenticated | Only manuscripts the actor authored are listed | An author cannot see another author's manuscript in this view, even by guessing its identifier |
| FR-19 | The system shall let an Editor or Editor-in-Chief view the complete audit trail for a manuscript. | Editor, EiC | M | Actor holds `EDITOR` or `EDITOR_IN_CHIEF` | The full, sequence-ordered event chain for the manuscript is returned | A Reviewer or Author role attempting this view is denied; the chain's hash verification passes |
| FR-23 | The system shall notify actors, in-app and by email where configured, of events affecting them. | System | S | An event affecting a specific actor has occurred | A notification record exists and, where email is configured, a message is queued for delivery | An editorial decision produces a notification visible to the affected author within the same request cycle |

#### Group H — Administration, configuration and analytics

| ID | Statement | Actor | Pri | Preconditions | Postconditions | Acceptance criteria |
|---|---|---|---|---|---|---|
| FR-24 | The system shall provide editorial analytics: throughput, decision mix, reviewer load and time-to-decision. | EiC, HoD | S | At least one full editorial cycle has completed | Aggregate figures are computed over the current dataset | Time-to-decision reported for a manuscript matches the difference between its submission and decision timestamps |
| FR-26 | The system shall let the Editor-in-Chief configure journal policy: minimum reviews, review window and blinding model. | EiC | C | Actor holds `EDITOR_IN_CHIEF` | Subsequent decisions and assignments respect the updated configuration | Lowering the minimum-review threshold takes effect for manuscripts not yet at decision, not retroactively |
| FR-28 | The system shall provide reviewer performance history and reliability indicators. | EiC | C | Reviewer has at least one completed or declined assignment | A per-reviewer summary (acceptance rate, on-time rate, average score deviation) is available | A reviewer who declines every invitation shows a 0% acceptance rate, not a null or error |
| FR-30 | The system shall let an Administrator manage accounts: grant and revoke roles, set reviewer capacity, and deactivate accounts. | Administrator | M | Actor holds `ADMINISTRATOR` | The account's roles, capacity or activation state are updated and visible on the next read | The administrator role itself cannot be granted or revoked through this interface, and an administrator cannot deactivate their own account |
| FR-33 | The system shall record a due date for each review assignment and mark an assignment overdue once that date passes without a submitted review. | Editor, EiC | S | A reviewer is assigned to a manuscript | The assignment carries a deadline and a server-computed overdue flag | A review submitted after its deadline is not flagged overdue; an assignment with no deadline is never flagged overdue |

#### Group I — Publication economics and scholarly record

| ID | Statement | Actor | Pri | Preconditions | Postconditions | Acceptance criteria |
|---|---|---|---|---|---|---|
| FR-29 | The system shall raise an article processing charge when a manuscript is accepted, and let the corresponding author settle it through a payment gateway. | Author, EiC | S | Manuscript is `ACCEPTED`, `SCHEDULED` or `PUBLISHED` | An invoice exists with a status of `pending`, `paid` or `waived` | No invoice exists before acceptance; a settled invoice cannot be waived, and a waived invoice cannot be verified |
| FR-31 | The system shall issue a signed-style decision certificate for a manuscript whose final decision is recorded. | Editor, EiC | C | An `accept` or `reject` decision exists in the manuscript's event chain | A PDF stating the decision, the tracking code and the audit chain's head hash is returned | Requesting a certificate before any final decision is a 409, not an empty document |
| FR-32 | The system shall report, at submission time, what the anonymiser removed from the uploaded document and what it could not remove. | Author | S | A document has been uploaded | The submission response carries a report of removed metadata keys and any author names still detectable in the body text | An author whose name appears in the manuscript body is told so at submission rather than after a reviewer sees it |
| FR-34 | The system shall let a member of the public register an author account without editorial-office involvement. | Reader | S | The email address is not already registered | An account exists holding exactly the `AUTHOR` role, signed in | Registration cannot grant reviewer, editor or administrator roles under any request body |

### 3.2 Non-functional requirements

Each non-functional requirement carries a stated **verification method** so that
"non-functional" does not collapse into "unverifiable."

#### Security

| ID | Requirement | Verification |
|---|---|---|
| NFR-01 | Passwords are hashed with Argon2id; no credential is ever written to a log. | Code review; unit test asserting the hashing algorithm and asserting no credential-shaped value appears in captured log output |
| NFR-02 | Every endpoint is authorised by an explicit policy; access is denied by default. | Integration test that walks the full route table and fails if any route lacks a policy check (design specification section 11) |
| NFR-03 | Reviewer-facing payloads contain no author-identifying data. | Automated leak test enumerating every reviewer-facing endpoint, serialising against a fixture with sentinel author names, asserting no sentinel appears in output |
| NFR-04 | Documents are served only via short-lived pre-signed URLs; storage buckets are private. | Integration test confirming direct bucket access is refused; manual verification of URL expiry |
| NFR-05 | Authentication and submission endpoints are rate-limited. | Integration test exceeding the configured limit and asserting a 429 response |
| NFR-06 | Dependencies are scanned; no known high-severity vulnerability is present at release. | `pip-audit` and `npm audit` as CI gates |

#### Integrity

| ID | Requirement | Verification |
|---|---|---|
| NFR-07 | Audit events are append-only and hash-chained; any retrospective edit is detectable. | Property test over random legal event sequences confirming the chain always verifies; a tamper-detection test that mutates a stored event and confirms verification fails. **Demonstrated in the current build** by `backend/tests/unit/domain/test_hashchain.py` and the integration tests `test_append_only.py` and `test_chain_persistence.py`, including a PostgreSQL trigger rejecting `UPDATE`/`DELETE`/`TRUNCATE` on the event table (technical debt register TD-13) |

#### Performance

| ID | Requirement | Verification |
|---|---|---|
| NFR-08 | Public archive pages respond within 500 ms at p95 under nominal load. | k6 smoke test against a deployed environment |
| NFR-09 | Search returns within 800 ms at p95 over the seeded corpus. | k6 smoke test |

#### Reliability

| ID | Requirement | Verification |
|---|---|---|
| NFR-10 | Upload processing is idempotent and retried with exponential backoff on failure. | Unit test on the retry policy; integration test replaying the same content checksum and asserting no duplicate side effect |

#### Availability

| ID | Requirement | Verification |
|---|---|---|
| NFR-11 | The service exposes liveness and readiness probes; unhealthy tasks are replaced automatically. | Deployment verification against the ECS service's health-check configuration |

#### Usability

| ID | Requirement | Verification |
|---|---|---|
| NFR-12 | The interface is responsive from 360 px width, keyboard-navigable, and meets WCAG 2.1 AA contrast. | Manual audit; automated `axe` accessibility check in CI |

#### Maintainability

| ID | Requirement | Verification |
|---|---|---|
| NFR-13 | The domain layer imports no framework code. | Import-linter contract enforced as a CI gate |
| NFR-14 | The domain and application layers hold at least 85% line coverage. | CI coverage gate. **The delivered domain and application layers report 90.03%** against the 85% gate, confirmed directly (`pytest -m "not integration" --cov=src/ugjcs/domain --cov=src/ugjcs/application`, run against this commit): 402 unit tests pass, and a separate run collects 84 integration tests against a real PostgreSQL container. Technical debt register TD-10 records the 85% figure as a floor, not a target, and TD-11 records that coverage alone is a weak signal — four mutations survived a 100%-covered suite until closed by targeted tests |

#### Observability

| ID | Requirement | Verification |
|---|---|---|
| NFR-15 | Structured JSON logs carry correlation IDs; traces are exported. | Manual verification against a deployed environment |

#### Portability

| ID | Requirement | Verification |
|---|---|---|
| NFR-16 | The entire infrastructure is reproducible from code. | `terraform apply` from a clean state, followed by `terraform destroy` |

#### Compliance

| ID | Requirement | Verification |
|---|---|---|
| NFR-17 | Personal data is minimised; the audit log retains identity only where required. | Design review against the data model (design specification section 8) |

---

## 4. System models

### 4.1 Manuscript lifecycle

The lifecycle below is transcribed directly from `backend/src/ugjcs/domain/transitions.py`
— the `LEGAL_TRANSITIONS` mapping is the executable, tested source of truth, not the
narrative description in the design specification.

#### 4.1.1 State table

| Source state | Legal target states | Terminal? |
|---|---|---|
| `DRAFT` | `SUBMITTED` | No |
| `SUBMITTED` | `UNDER_SCREENING`, `WITHDRAWN` | No |
| `UNDER_SCREENING` | `DESK_REJECTED`, `UNDER_REVIEW`, `REVISION_REQUESTED`, `WITHDRAWN` | No |
| `UNDER_REVIEW` | `REVIEWS_COMPLETE`, `WITHDRAWN` | No |
| `REVIEWS_COMPLETE` | `ACCEPTED`, `REJECTED`, `REVISION_REQUESTED`, `WITHDRAWN` | No |
| `REVISION_REQUESTED` | `RESUBMITTED`, `WITHDRAWN` | No |
| `RESUBMITTED` | `UNDER_REVIEW`, `UNDER_SCREENING` | No |
| `ACCEPTED` | `SCHEDULED` | No |
| `SCHEDULED` | `PUBLISHED` | No |
| `DESK_REJECTED` | *(none)* | **Yes** |
| `REJECTED` | *(none)* | **Yes** |
| `PUBLISHED` | *(none)* | **Yes** |
| `WITHDRAWN` | *(none)* | **Yes** |

No transition is legal out of a terminal state; this is asserted directly by
`assert_legal`, which raises `IllegalTransitionError` for any pair not present in
`LEGAL_TRANSITIONS`. `ACCEPTED` and `SCHEDULED` are deliberately excluded from the
withdrawable set: once a manuscript is accepted, undoing that is editorial retraction —
a different action, with its own notice obligations — and is not modelled as withdrawal.

#### 4.1.2 State diagram

<figure class="diagram"><svg id="my-svg" width="100%" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" class="statediagram" style="max-width: 1539.88px; background-color: transparent;" viewBox="0 0 1539.87890625 982" role="graphics-document document" aria-roledescription="stateDiagram"><style>#my-svg{font-family:"trebuchet ms",verdana,arial,sans-serif;font-size:16px;fill:#333;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#my-svg .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#my-svg .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#my-svg .error-icon{fill:#552222;}#my-svg .error-text{fill:#552222;stroke:#552222;}#my-svg .edge-thickness-normal{stroke-width:1px;}#my-svg .edge-thickness-thick{stroke-width:3.5px;}#my-svg .edge-pattern-solid{stroke-dasharray:0;}#my-svg .edge-thickness-invisible{stroke-width:0;fill:none;}#my-svg .edge-pattern-dashed{stroke-dasharray:3;}#my-svg .edge-pattern-dotted{stroke-dasharray:2;}#my-svg .marker{fill:#333333;stroke:#333333;}#my-svg .marker.cross{stroke:#333333;}#my-svg svg{font-family:"trebuchet ms",verdana,arial,sans-serif;font-size:16px;}#my-svg p{margin:0;}#my-svg defs [id$="-barbEnd"]{fill:#333333;stroke:#333333;}#my-svg g.stateGroup text{fill:#9370DB;stroke:none;font-size:10px;}#my-svg g.stateGroup text{fill:#333;stroke:none;font-size:10px;}#my-svg g.stateGroup .state-title{font-weight:bolder;fill:#131300;}#my-svg g.stateGroup rect{fill:#ECECFF;stroke:#9370DB;}#my-svg g.stateGroup line{stroke:#333333;stroke-width:1;}#my-svg .transition{stroke:#333333;stroke-width:1;fill:none;}#my-svg .stateGroup .composit{fill:white;border-bottom:1px;}#my-svg .stateGroup .alt-composit{fill:#e0e0e0;border-bottom:1px;}#my-svg .state-note{stroke:#aaaa33;fill:#fff5ad;}#my-svg .state-note text{fill:black;stroke:none;font-size:10px;}#my-svg .stateLabel .box{stroke:none;stroke-width:0;fill:#ECECFF;opacity:0.5;}#my-svg .edgeLabel .label rect{fill:#ECECFF;opacity:0.5;}#my-svg .edgeLabel{background-color:rgba(232,232,232, 0.8);text-align:center;}#my-svg .edgeLabel p{background-color:rgba(232,232,232, 0.8);}#my-svg .edgeLabel rect{opacity:0.5;background-color:rgba(232,232,232, 0.8);fill:rgba(232,232,232, 0.8);}#my-svg .edgeLabel .label text{fill:#333;}#my-svg .label div .edgeLabel{color:#333;}#my-svg .stateLabel text{fill:#131300;font-size:10px;font-weight:bold;}#my-svg .node circle.state-start{fill:#333333;stroke:#333333;}#my-svg .node .fork-join{fill:#333333;stroke:#333333;}#my-svg .node circle.state-end{fill:#9370DB;stroke:white;stroke-width:1.5;}#my-svg .end-state-inner{fill:white;stroke-width:1.5;}#my-svg .node rect{fill:#ECECFF;stroke:#9370DB;stroke-width:1px;}#my-svg .node polygon{fill:#ECECFF;stroke:#9370DB;stroke-width:1px;}#my-svg [id$="-barbEnd"]{fill:#333333;}#my-svg .statediagram-cluster rect{fill:#ECECFF;stroke:#9370DB;stroke-width:1px;}#my-svg .cluster-label,#my-svg .nodeLabel{color:#131300;}#my-svg .statediagram-cluster rect.outer{rx:5px;ry:5px;}#my-svg .statediagram-state .divider{stroke:#9370DB;}#my-svg .statediagram-state .title-state{rx:5px;ry:5px;}#my-svg .statediagram-cluster.statediagram-cluster .inner{fill:white;}#my-svg .statediagram-cluster.statediagram-cluster-alt .inner{fill:#f0f0f0;}#my-svg .statediagram-cluster .inner{rx:0;ry:0;}#my-svg .statediagram-state rect.basic{rx:5px;ry:5px;}#my-svg .statediagram-state rect.divider{stroke-dasharray:10,10;fill:#f0f0f0;}#my-svg .note-edge{stroke-dasharray:5;}#my-svg .statediagram-note rect{fill:#fff5ad;stroke:#aaaa33;stroke-width:1px;rx:0;ry:0;}#my-svg .statediagram-note rect{fill:#fff5ad;stroke:#aaaa33;stroke-width:1px;rx:0;ry:0;}#my-svg .statediagram-note text{fill:black;}#my-svg .statediagram-note .nodeLabel{color:black;}#my-svg .statediagram .edgeLabel{color:red;}#my-svg [id$="-dependencyStart"],#my-svg [id$="-dependencyEnd"]{fill:#333333;stroke:#333333;stroke-width:1;}#my-svg .statediagramTitleText{text-anchor:middle;font-size:18px;fill:#333;}#my-svg [data-look="neo"].statediagram-cluster rect{fill:#ECECFF;stroke:#9370DB;stroke-width:1;}#my-svg [data-look="neo"].statediagram-cluster rect.outer{rx:5px;ry:5px;filter:drop-shadow(1px 2px 2px rgba(185, 185, 185, 1));}#my-svg .node .neo-node{stroke:#9370DB;}#my-svg [data-look="neo"].node rect,#my-svg [data-look="neo"].cluster rect,#my-svg [data-look="neo"].node polygon{stroke:#9370DB;filter:drop-shadow(1px 2px 2px rgba(185, 185, 185, 1));}#my-svg [data-look="neo"].swimlane.cluster rect{filter:none;}#my-svg [data-look="neo"].node path{stroke:#9370DB;stroke-width:1px;}#my-svg [data-look="neo"].node .outer-path{filter:drop-shadow(1px 2px 2px rgba(185, 185, 185, 1));}#my-svg [data-look="neo"].node .neo-line path{stroke:#9370DB;filter:none;}#my-svg [data-look="neo"].node circle{stroke:#9370DB;filter:drop-shadow(1px 2px 2px rgba(185, 185, 185, 1));}#my-svg [data-look="neo"].node circle .state-start{fill:#000000;}#my-svg [data-look="neo"].icon-shape .icon{fill:#9370DB;filter:drop-shadow(1px 2px 2px rgba(185, 185, 185, 1));}#my-svg [data-look="neo"].icon-shape .icon-neo path{stroke:#9370DB;filter:drop-shadow(1px 2px 2px rgba(185, 185, 185, 1));}#my-svg :root{--mermaid-font-family:"trebuchet ms",verdana,arial,sans-serif;}</style><g><defs><marker id="my-svg_stateDiagram-barbEnd" refX="19" refY="7" markerWidth="20" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto"><path d="M 19,7 L9,13 L14,7 L9,1 Z"/></marker></defs><g class="root"><g class="clusters"/><g class="edgePaths"><path d="M1229.344,22L1229.344,26.167C1229.344,30.333,1229.344,38.667,1229.344,47C1229.344,55.333,1229.344,63.667,1229.344,67.833L1229.344,72" id="my-svg-edge0" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge0" data-points="W3sieCI6MTIyOS4zNDM3NSwieSI6MjJ9LHsieCI6MTIyOS4zNDM3NSwieSI6NDd9LHsieCI6MTIyOS4zNDM3NSwieSI6NzJ9XQ==" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M1229.344,112L1229.344,118.167C1229.344,124.333,1229.344,136.667,1229.344,149C1229.344,161.333,1229.344,173.667,1229.344,179.833L1229.344,186" id="my-svg-edge1" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge1" data-points="W3sieCI6MTIyOS4zNDM3NSwieSI6MTEyfSx7IngiOjEyMjkuMzQzNzUsInkiOjE0OX0seyJ4IjoxMjI5LjM0Mzc1LCJ5IjoxODZ9XQ==" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M1181.398,220.431L1157.826,227.526C1134.254,234.621,1087.109,248.81,1063.537,262.072C1039.965,275.333,1039.965,287.667,1039.965,293.833L1039.965,300" id="my-svg-edge2" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge2" data-points="W3sieCI6MTE4MS4zOTg0Mzc1LCJ5IjoyMjAuNDMwNzY2NjkyMTA2MTh9LHsieCI6MTAzOS45NjQ4NDM3NSwieSI6MjYzfSx7IngiOjEwMzkuOTY0ODQzNzUsInkiOjMwMH1d" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M1277.289,216.158L1314.137,223.965C1350.986,231.772,1424.682,247.386,1461.531,264.693C1498.379,282,1498.379,301,1498.379,320C1498.379,339,1498.379,358,1498.379,377C1498.379,396,1498.379,415,1498.379,434C1498.379,453,1498.379,472,1498.379,491C1498.379,510,1498.379,529,1498.379,548C1498.379,567,1498.379,586,1498.379,605C1498.379,624,1498.379,643,1498.379,662C1498.379,681,1498.379,700,1399.078,718.232C1299.777,736.463,1101.176,753.927,1001.875,762.659L902.574,771.39" id="my-svg-edge3" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge3" data-points="W3sieCI6MTI3Ny4yODkwNjI1LCJ5IjoyMTYuMTU4MDg4MDc1MTUyODJ9LHsieCI6MTQ5OC4zNzg5MDYyNSwieSI6MjYzfSx7IngiOjE0OTguMzc4OTA2MjUsInkiOjMyMH0seyJ4IjoxNDk4LjM3ODkwNjI1LCJ5IjozNzd9LHsieCI6MTQ5OC4zNzg5MDYyNSwieSI6NDM0fSx7IngiOjE0OTguMzc4OTA2MjUsInkiOjQ5MX0seyJ4IjoxNDk4LjM3ODkwNjI1LCJ5Ijo1NDh9LHsieCI6MTQ5OC4zNzg5MDYyNSwieSI6NjA1fSx7IngiOjE0OTguMzc4OTA2MjUsInkiOjY2Mn0seyJ4IjoxNDk4LjM3ODkwNjI1LCJ5Ijo3MTl9LHsieCI6OTAyLjU3NDIxODc1LCJ5Ijo3NzEuMzkwNDI4MjExNTg2OX1d" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M963.918,324.485L815.515,333.238C667.112,341.99,370.306,359.495,221.903,377.748C73.5,396,73.5,415,73.5,434C73.5,453,73.5,472,73.5,491C73.5,510,73.5,529,73.5,548C73.5,567,73.5,586,73.5,605C73.5,624,73.5,643,73.5,662C73.5,681,73.5,700,73.5,719C73.5,738,73.5,757,73.5,776C73.5,795,73.5,814,73.5,829.667C73.5,845.333,73.5,857.667,73.5,863.833L73.5,870" id="my-svg-edge4" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge4" data-points="W3sieCI6OTYzLjkxNzk2ODc1LCJ5IjozMjQuNDg1MDc5NzI0MzQ5NzZ9LHsieCI6NzMuNSwieSI6Mzc3fSx7IngiOjczLjUsInkiOjQzNH0seyJ4Ijo3My41LCJ5Ijo0OTF9LHsieCI6NzMuNSwieSI6NTQ4fSx7IngiOjczLjUsInkiOjYwNX0seyJ4Ijo3My41LCJ5Ijo2NjJ9LHsieCI6NzMuNSwieSI6NzE5fSx7IngiOjczLjUsInkiOjc3Nn0seyJ4Ijo3My41LCJ5Ijo4MzN9LHsieCI6NzMuNSwieSI6ODcwfV0=" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M963.918,336.954L933.979,343.628C904.04,350.302,844.163,363.651,814.224,376.492C784.285,389.333,784.285,401.667,784.285,407.833L784.285,414" id="my-svg-edge5" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge5" data-points="W3sieCI6OTYzLjkxNzk2ODc1LCJ5IjozMzYuOTUzNTI0NjEyNzA1MX0seyJ4Ijo3ODQuMjg1MTU2MjUsInkiOjM3N30seyJ4Ijo3ODQuMjg1MTU2MjUsInkiOjQxNH1d" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M1067.914,340L1076.532,346.167C1085.15,352.333,1102.386,364.667,1111.003,380.333C1119.621,396,1119.621,415,1119.621,434C1119.621,453,1119.621,472,1119.621,491C1119.621,510,1119.621,529,1119.621,548C1119.621,567,1119.621,586,1063.008,603.078C1006.395,620.156,893.168,635.313,836.555,642.891L779.941,650.469" id="my-svg-edge6" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge6" data-points="W3sieCI6MTA2Ny45MTQ0MDUxNTM1MDg4LCJ5IjozNDB9LHsieCI6MTExOS42MjEwOTM3NSwieSI6Mzc3fSx7IngiOjExMTkuNjIxMDkzNzUsInkiOjQzNH0seyJ4IjoxMTE5LjYyMTA5Mzc1LCJ5Ijo0OTF9LHsieCI6MTExOS42MjEwOTM3NSwieSI6NTQ4fSx7IngiOjExMTkuNjIxMDkzNzUsInkiOjYwNX0seyJ4Ijo3NzkuOTQxNDA2MjUsInkiOjY1MC40NjkyNzgwNDc4ODU1fV0=" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M1109.765,340L1131.286,346.167C1152.808,352.333,1195.851,364.667,1217.373,380.333C1238.895,396,1238.895,415,1238.895,434C1238.895,453,1238.895,472,1238.895,491C1238.895,510,1238.895,529,1238.895,548C1238.895,567,1238.895,586,1238.895,605C1238.895,624,1238.895,643,1238.895,662C1238.895,681,1238.895,700,1182.841,717.719C1126.788,735.438,1014.681,751.876,958.628,760.095L902.574,768.314" id="my-svg-edge7" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge7" data-points="W3sieCI6MTEwOS43NjQ3MzQxMDA4NzcxLCJ5IjozNDB9LHsieCI6MTIzOC44OTQ1MzEyNSwieSI6Mzc3fSx7IngiOjEyMzguODk0NTMxMjUsInkiOjQzNH0seyJ4IjoxMjM4Ljg5NDUzMTI1LCJ5Ijo0OTF9LHsieCI6MTIzOC44OTQ1MzEyNSwieSI6NTQ4fSx7IngiOjEyMzguODk0NTMxMjUsInkiOjYwNX0seyJ4IjoxMjM4Ljg5NDUzMTI1LCJ5Ijo2NjJ9LHsieCI6MTIzOC44OTQ1MzEyNSwieSI6NzE5fSx7IngiOjkwMi41NzQyMTg3NSwieSI6NzY4LjMxMzU1MTMxNzM0OTZ9XQ==" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M720.98,442.244L658.581,450.37C596.182,458.496,471.384,474.748,408.985,489.041C346.586,503.333,346.586,515.667,346.586,521.833L346.586,528" id="my-svg-edge8" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge8" data-points="W3sieCI6NzIwLjk4MDQ2ODc1LCJ5Ijo0NDIuMjQzOTQyNDkwNDczMX0seyJ4IjozNDYuNTg1OTM3NSwieSI6NDkxfSx7IngiOjM0Ni41ODU5Mzc1LCJ5Ijo1Mjh9XQ==" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M807.396,454L814.522,460.167C821.648,466.333,835.9,478.667,843.026,494.333C850.152,510,850.152,529,850.152,548C850.152,567,850.152,586,850.152,605C850.152,624,850.152,643,850.152,662C850.152,681,850.152,700,850.152,715.667C850.152,731.333,850.152,743.667,850.152,749.833L850.152,756" id="my-svg-edge9" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge9" data-points="W3sieCI6ODA3LjM5NjQ1MDEwOTY0OTEsInkiOjQ1NH0seyJ4Ijo4NTAuMTUyMzQzNzUsInkiOjQ5MX0seyJ4Ijo4NTAuMTUyMzQzNzUsInkiOjU0OH0seyJ4Ijo4NTAuMTUyMzQzNzUsInkiOjYwNX0seyJ4Ijo4NTAuMTUyMzQzNzUsInkiOjY2Mn0seyJ4Ijo4NTAuMTUyMzQzNzUsInkiOjcxOX0seyJ4Ijo4NTAuMTUyMzQzNzUsInkiOjc1Nn1d" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M307.688,568L295.694,574.167C283.701,580.333,259.714,592.667,247.72,605C235.727,617.333,235.727,629.667,235.727,635.833L235.727,642" id="my-svg-edge10" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge10" data-points="W3sieCI6MzA3LjY4NzkxMTE4NDIxMDUsInkiOjU2OH0seyJ4IjoyMzUuNzI2NTYyNSwieSI6NjA1fSx7IngiOjIzNS43MjY1NjI1LCJ5Ijo2NDJ9XQ==" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M356.948,568L360.143,574.167C363.338,580.333,369.727,592.667,372.922,608.333C376.117,624,376.117,643,376.117,662C376.117,681,376.117,700,376.117,719C376.117,738,376.117,757,376.117,776C376.117,795,376.117,814,376.117,829.667C376.117,845.333,376.117,857.667,376.117,863.833L376.117,870" id="my-svg-edge11" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge11" data-points="W3sieCI6MzU2Ljk0Nzc3OTYwNTI2MzIsInkiOjU2OH0seyJ4IjozNzYuMTE3MTg3NSwieSI6NjA1fSx7IngiOjM3Ni4xMTcxODc1LCJ5Ijo2NjJ9LHsieCI6Mzc2LjExNzE4NzUsInkiOjcxOX0seyJ4IjozNzYuMTE3MTg3NSwieSI6Nzc2fSx7IngiOjM3Ni4xMTcxODc1LCJ5Ijo4MzN9LHsieCI6Mzc2LjExNzE4NzUsInkiOjg3MH1d" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M384.086,568L395.648,574.167C407.211,580.333,430.336,592.667,467.9,605C505.464,617.333,557.468,629.667,583.469,635.833L609.471,642" id="my-svg-edge12" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge12" data-points="W3sieCI6Mzg0LjA4NTkzNzUsInkiOjU2OH0seyJ4Ijo0NTMuNDYwOTM3NSwieSI6NjA1fSx7IngiOjYwOS40NzEwMTE1MTMxNTc5LCJ5Ijo2NDJ9XQ==" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M411.224,568L431.154,574.167C451.084,580.333,490.944,592.667,510.875,608.333C530.805,624,530.805,643,530.805,662C530.805,681,530.805,700,575.292,717.441C619.78,734.881,708.755,750.762,753.243,758.703L797.73,766.643" id="my-svg-edge13" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge13" data-points="W3sieCI6NDExLjIyNDA5NTM5NDczNjgsInkiOjU2OH0seyJ4Ijo1MzAuODA0Njg3NSwieSI6NjA1fSx7IngiOjUzMC44MDQ2ODc1LCJ5Ijo2NjJ9LHsieCI6NTMwLjgwNDY4NzUsInkiOjcxOX0seyJ4Ijo3OTcuNzMwNDY4NzUsInkiOjc2Ni42NDMyNzkxNDU3MTk1fV0=" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M677.915,682L673.017,688.167C668.119,694.333,658.323,706.667,704.1,720.836C749.876,735.005,851.225,751.01,901.9,759.013L952.574,767.016" id="my-svg-edge14" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge14" data-points="W3sieCI6Njc3LjkxNTM2NDU4MzMzMzQsInkiOjY4Mn0seyJ4Ijo2NDguNTI3MzQzNzUsInkiOjcxOX0seyJ4Ijo5NTIuNTc0MjE4NzUsInkiOjc2Ny4wMTU3MTQyODU3MTQyfV0=" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M718.022,682L725.491,688.167C732.959,694.333,747.895,706.667,764.811,719C781.726,731.333,800.62,743.667,810.067,749.833L819.514,756" id="my-svg-edge15" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge15" data-points="W3sieCI6NzE4LjAyMjI3MjQ3ODA3MDEsInkiOjY4Mn0seyJ4Ijo3NjIuODMyMDMxMjUsInkiOjcxOX0seyJ4Ijo4MTkuNTEzNjM3NjA5NjQ5MSwieSI6NzU2fV0=" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M1006.266,756L1005.279,749.833C1004.293,743.667,1002.32,731.333,1001.334,715.667C1000.348,700,1000.348,681,1000.348,662C1000.348,643,1000.348,624,1000.348,605C1000.348,586,1000.348,567,1000.348,548C1000.348,529,1000.348,510,974.888,493.783C949.428,477.567,898.509,464.134,873.049,457.417L847.59,450.701" id="my-svg-edge16" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge16" data-points="W3sieCI6MTAwNi4yNjU4MzA1OTIxMDUzLCJ5Ijo3NTZ9LHsieCI6MTAwMC4zNDc2NTYyNSwieSI6NzE5fSx7IngiOjEwMDAuMzQ3NjU2MjUsInkiOjY2Mn0seyJ4IjoxMDAwLjM0NzY1NjI1LCJ5Ijo2MDV9LHsieCI6MTAwMC4zNDc2NTYyNSwieSI6NTQ4fSx7IngiOjEwMDAuMzQ3NjU2MjUsInkiOjQ5MX0seyJ4Ijo4NDcuNTg5ODQzNzUsInkiOjQ1MC43MDA1NzEzMDQ1OTkzNX1d" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M1066.355,767.374L1119.527,759.312C1172.699,751.249,1279.043,735.125,1332.215,717.562C1385.387,700,1385.387,681,1385.387,662C1385.387,643,1385.387,624,1385.387,605C1385.387,586,1385.387,567,1385.387,548C1385.387,529,1385.387,510,1385.387,491C1385.387,472,1385.387,453,1385.387,434C1385.387,415,1385.387,396,1340.491,379.091C1295.595,362.183,1205.803,347.366,1160.908,339.957L1116.012,332.549" id="my-svg-edge17" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge17" data-points="W3sieCI6MTA2Ni4zNTU0Njg3NSwieSI6NzY3LjM3MzgzMDk5ODc5NDZ9LHsieCI6MTM4NS4zODY3MTg3NSwieSI6NzE5fSx7IngiOjEzODUuMzg2NzE4NzUsInkiOjY2Mn0seyJ4IjoxMzg1LjM4NjcxODc1LCJ5Ijo2MDV9LHsieCI6MTM4NS4zODY3MTg3NSwieSI6NTQ4fSx7IngiOjEzODUuMzg2NzE4NzUsInkiOjQ5MX0seyJ4IjoxMzg1LjM4NjcxODc1LCJ5Ijo0MzR9LHsieCI6MTM4NS4zODY3MTg3NSwieSI6Mzc3fSx7IngiOjExMTYuMDExNzE4NzUsInkiOjMzMi41NDg5MjExNTYxOTQ4N31d" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M235.727,682L235.727,688.167C235.727,694.333,235.727,706.667,235.727,719C235.727,731.333,235.727,743.667,235.727,749.833L235.727,756" id="my-svg-edge18" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge18" data-points="W3sieCI6MjM1LjcyNjU2MjUsInkiOjY4Mn0seyJ4IjoyMzUuNzI2NTYyNSwieSI6NzE5fSx7IngiOjIzNS43MjY1NjI1LCJ5Ijo3NTZ9XQ==" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M235.727,796L235.727,802.167C235.727,808.333,235.727,820.667,235.727,833C235.727,845.333,235.727,857.667,235.727,863.833L235.727,870" id="my-svg-edge19" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge19" data-points="W3sieCI6MjM1LjcyNjU2MjUsInkiOjc5Nn0seyJ4IjoyMzUuNzI2NTYyNSwieSI6ODMzfSx7IngiOjIzNS43MjY1NjI1LCJ5Ijo4NzB9XQ==" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M73.5,910L73.5,914.167C73.5,918.333,73.5,926.667,111.08,936.007C148.66,945.348,223.82,955.696,261.401,960.87L298.981,966.044" id="my-svg-edge20" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge20" data-points="W3sieCI6NzMuNSwieSI6OTEwfSx7IngiOjczLjUsInkiOjkzNX0seyJ4IjoyOTguOTgwNzA3Nzg3MjgwMjcsInkiOjk2Ni4wNDQzMzU0MzE4MjE5fV0=" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M376.117,910L376.117,914.167C376.117,918.333,376.117,926.667,365.481,935.682C354.844,944.698,333.571,954.396,322.934,959.245L312.297,964.094" id="my-svg-edge21" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge21" data-points="W3sieCI6Mzc2LjExNzE4NzUsInkiOjkxMH0seyJ4IjozNzYuMTE3MTg3NSwieSI6OTM1fSx7IngiOjMxMi4yOTczMDQwNTM0NjI4LCJ5Ijo5NjQuMDkzNjI3NDQ1NDEwOH1d" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M235.727,910L235.727,914.167C235.727,918.333,235.727,926.667,246.363,935.682C257,944.698,278.273,954.396,288.91,959.245L299.546,964.094" id="my-svg-edge22" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge22" data-points="W3sieCI6MjM1LjcyNjU2MjUsInkiOjkxMH0seyJ4IjoyMzUuNzI2NTYyNSwieSI6OTM1fSx7IngiOjI5OS41NDY0NDU5NDY1MzcyLCJ5Ijo5NjQuMDkzNjI3NDQ1NDEwOH1d" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/><path d="M850.152,796L850.152,802.167C850.152,808.333,850.152,820.667,850.152,836.333C850.152,852,850.152,871,850.152,888C850.152,905,850.152,920,760.613,932.765C671.074,945.53,491.995,956.059,402.456,961.324L312.916,966.589" id="my-svg-edge23" class="edge-thickness-normal edge-pattern-solid transition" style="fill:none;;;fill:none" data-edge="true" data-et="edge" data-id="edge23" data-points="W3sieCI6ODUwLjE1MjM0Mzc1LCJ5Ijo3OTZ9LHsieCI6ODUwLjE1MjM0Mzc1LCJ5Ijo4MzN9LHsieCI6ODUwLjE1MjM0Mzc1LCJ5Ijo4OTB9LHsieCI6ODUwLjE1MjM0Mzc1LCJ5Ijo5MzV9LHsieCI6MzEyLjkxNjQ0MDk4NzUxODEsInkiOjk2Ni41ODg3MjkxNzkxNzU0fV0=" data-look="classic" marker-end="url(#my-svg_stateDiagram-barbEnd)"/></g><g class="edgeLabels"><g class="edgeLabel"><g class="label" data-id="edge0" transform="translate(0, 0)"><foreignObject width="0" height="0"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(1229.34375, 149)"><g class="label" data-id="edge1" transform="translate(-24.1640625, -12)"><foreignObject width="48.328125" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>submit</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(1039.96484375, 263)"><g class="label" data-id="edge2" transform="translate(-55.9765625, -12)"><foreignObject width="111.953125" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>begin screening</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(1498.37890625, 491)"><g class="label" data-id="edge3" transform="translate(-33.5, -12)"><foreignObject width="67" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>withdraw</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(73.5, 605)"><g class="label" data-id="edge4" transform="translate(-40.40625, -12)"><foreignObject width="80.8125" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>desk reject</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(784.28515625, 377)"><g class="label" data-id="edge5" transform="translate(-52.703125, -12)"><foreignObject width="105.40625" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>send to review</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(1119.62109375, 491)"><g class="label" data-id="edge6" transform="translate(-99.2734375, -12)"><foreignObject width="198.546875" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>request pre-review changes</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(1238.89453125, 548)"><g class="label" data-id="edge7" transform="translate(-33.5, -12)"><foreignObject width="67" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>withdraw</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(346.5859375, 491)"><g class="label" data-id="edge8" transform="translate(-58.484375, -12)"><foreignObject width="116.96875" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>quorum reached</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(850.15234375, 605)"><g class="label" data-id="edge9" transform="translate(-33.5, -12)"><foreignObject width="67" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>withdraw</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(235.7265625, 605)"><g class="label" data-id="edge10" transform="translate(-24.1171875, -12)"><foreignObject width="48.234375" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>accept</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(376.1171875, 719)"><g class="label" data-id="edge11" transform="translate(-21.90625, -12)"><foreignObject width="43.8125" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>reject</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(453.4609375, 605)"><g class="label" data-id="edge12" transform="translate(-57.34375, -12)"><foreignObject width="114.6875" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>request revision</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(530.8046875, 662)"><g class="label" data-id="edge13" transform="translate(-33.5, -12)"><foreignObject width="67" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>withdraw</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(777.21449, 739.32254)"><g class="label" data-id="edge14" transform="translate(-60.8046875, -12)"><foreignObject width="121.609375" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>author resubmits</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(762.83203125, 719)"><g class="label" data-id="edge15" transform="translate(-33.5, -12)"><foreignObject width="67" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>withdraw</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(1000.34765625, 605)"><g class="label" data-id="edge16" transform="translate(-82.90625, -12)"><foreignObject width="165.8125" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>editor routes to review</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(1385.38671875, 548)"><g class="label" data-id="edge17" transform="translate(-92.9921875, -12)"><foreignObject width="185.984375" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>editor routes to screening</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(235.7265625, 719)"><g class="label" data-id="edge18" transform="translate(-51.125, -12)"><foreignObject width="102.25" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>assign to issue</p></span></div></foreignObject></g></g><g class="edgeLabel" transform="translate(235.7265625, 833)"><g class="label" data-id="edge19" transform="translate(-54.2578125, -12)"><foreignObject width="108.515625" height="24"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"><p>issue published</p></span></div></foreignObject></g></g><g class="edgeLabel"><g class="label" data-id="edge20" transform="translate(0, 0)"><foreignObject width="0" height="0"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"></span></div></foreignObject></g></g><g class="edgeLabel"><g class="label" data-id="edge21" transform="translate(0, 0)"><foreignObject width="0" height="0"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"></span></div></foreignObject></g></g><g class="edgeLabel"><g class="label" data-id="edge22" transform="translate(0, 0)"><foreignObject width="0" height="0"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"></span></div></foreignObject></g></g><g class="edgeLabel"><g class="label" data-id="edge23" transform="translate(0, 0)"><foreignObject width="0" height="0"><div xmlns="http://www.w3.org/1999/xhtml" class="labelBkg" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="edgeLabel"></span></div></foreignObject></g></g></g><g class="nodes"><g class="node default" id="my-svg-state-root_start-0" data-look="classic" transform="translate(1229.34375, 15)"><circle class="state-start" r="7" width="14" height="14"/></g><g class="node  statediagram-state" id="my-svg-state-DRAFT-1" data-look="classic" transform="translate(1229.34375, 92)"><rect class="basic label-container" style="" rx="5" ry="5" x="-31.125" y="-20" width="62.25" height="40"/><g class="label" style="" transform="translate(-23.125, -12)"><rect/><foreignObject width="46.25" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>DRAFT</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-SUBMITTED-3" data-look="classic" transform="translate(1229.34375, 206)"><rect class="basic label-container" style="" rx="5" ry="5" x="-47.9453125" y="-20" width="95.890625" height="40"/><g class="label" style="" transform="translate(-39.9453125, -12)"><rect/><foreignObject width="79.890625" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>SUBMITTED</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-UNDER_SCREENING-17" data-look="classic" transform="translate(1039.96484375, 320)"><rect class="basic label-container" style="" rx="5" ry="5" x="-76.046875" y="-20" width="152.09375" height="40"/><g class="label" style="" transform="translate(-68.046875, -12)"><rect/><foreignObject width="136.09375" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>UNDER_SCREENING</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-WITHDRAWN-23" data-look="classic" transform="translate(850.15234375, 776)"><rect class="basic label-container" style="" rx="5" ry="5" x="-52.421875" y="-20" width="104.84375" height="40"/><g class="label" style="" transform="translate(-44.421875, -12)"><rect/><foreignObject width="88.84375" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>WITHDRAWN</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-DESK_REJECTED-20" data-look="classic" transform="translate(73.5, 890)"><rect class="basic label-container" style="" rx="5" ry="5" x="-65.5" y="-20" width="131" height="40"/><g class="label" style="" transform="translate(-57.5, -12)"><rect/><foreignObject width="115" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>DESK_REJECTED</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-UNDER_REVIEW-16" data-look="classic" transform="translate(784.28515625, 434)"><rect class="basic label-container" style="" rx="5" ry="5" x="-63.3046875" y="-20" width="126.609375" height="40"/><g class="label" style="" transform="translate(-55.3046875, -12)"><rect/><foreignObject width="110.609375" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>UNDER_REVIEW</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-REVISION_REQUESTED-15" data-look="classic" transform="translate(693.80078125, 662)"><rect class="basic label-container" style="" rx="5" ry="5" x="-86.140625" y="-20" width="172.28125" height="40"/><g class="label" style="" transform="translate(-78.140625, -12)"><rect/><foreignObject width="156.28125" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>REVISION_REQUESTED</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-REVIEWS_COMPLETE-13" data-look="classic" transform="translate(346.5859375, 548)"><rect class="basic label-container" style="" rx="5" ry="5" x="-80.59375" y="-20" width="161.1875" height="40"/><g class="label" style="" transform="translate(-72.59375, -12)"><rect/><foreignObject width="145.1875" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>REVIEWS_COMPLETE</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-ACCEPTED-18" data-look="classic" transform="translate(235.7265625, 662)"><rect class="basic label-container" style="" rx="5" ry="5" x="-44.875" y="-20" width="89.75" height="40"/><g class="label" style="" transform="translate(-36.875, -12)"><rect/><foreignObject width="73.75" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>ACCEPTED</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-REJECTED-21" data-look="classic" transform="translate(376.1171875, 890)"><rect class="basic label-container" style="" rx="5" ry="5" x="-43.6640625" y="-20" width="87.328125" height="40"/><g class="label" style="" transform="translate(-35.6640625, -12)"><rect/><foreignObject width="71.328125" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>REJECTED</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-RESUBMITTED-17" data-look="classic" transform="translate(1009.46484375, 776)"><rect class="basic label-container" style="" rx="5" ry="5" x="-56.890625" y="-20" width="113.78125" height="40"/><g class="label" style="" transform="translate(-48.890625, -12)"><rect/><foreignObject width="97.78125" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>RESUBMITTED</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-SCHEDULED-19" data-look="classic" transform="translate(235.7265625, 776)"><rect class="basic label-container" style="" rx="5" ry="5" x="-49.4921875" y="-20" width="98.984375" height="40"/><g class="label" style="" transform="translate(-41.4921875, -12)"><rect/><foreignObject width="82.984375" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>SCHEDULED</p></span></div></foreignObject></g></g><g class="node  statediagram-state" id="my-svg-state-PUBLISHED-22" data-look="classic" transform="translate(235.7265625, 890)"><rect class="basic label-container" style="" rx="5" ry="5" x="-46.7265625" y="-20" width="93.453125" height="40"/><g class="label" style="" transform="translate(-38.7265625, -12)"><rect/><foreignObject width="77.453125" height="24"><div xmlns="http://www.w3.org/1999/xhtml" style="display: table-cell; white-space: nowrap; line-height: 1.5; max-width: 200px; text-align: center;"><span class="nodeLabel markdown-node-label"><p>PUBLISHED</p></span></div></foreignObject></g></g><g class="node default" id="my-svg-state-root_end-23" data-look="classic" transform="translate(305.921875, 967)"><g class="outer-path"><path d="M7 0 C7 0.40517908122283747, 6.964012880168563 0.816513743121899, 6.893654271085456 1.2155372436685123 C6.823295662002349 1.6145607442151257, 6.716427752933756 2.013397210557766, 6.5778483455013586 2.394141003279681 C6.439268938068961 2.7748847960015954, 6.26476736710249 3.149104622578984, 6.062177826491071 3.4999999999999996 C5.859588285879653 3.8508953774210153, 5.622755194947063 4.189128084166967, 5.362311101832846 4.499513267805774 C5.10186700871863 4.809898451444582, 4.809898451444583 5.10186700871863, 4.499513267805775 5.362311101832846 C4.189128084166968 5.622755194947063, 3.8508953774210166 5.859588285879652, 3.500000000000001 6.06217782649107 C3.149104622578985 6.264767367102489, 2.7748847960015963 6.439268938068961, 2.3941410032796817 6.5778483455013586 C2.013397210557767 6.716427752933756, 1.6145607442151264 6.823295662002349, 1.2155372436685128 6.893654271085456 C0.8165137431218992 6.964012880168563, 0.4051790812228379 7, 4.286263797015736e-16 7 C-0.405179081222837 7, -0.8165137431218985 6.964012880168563, -1.2155372436685121 6.893654271085456 C-1.6145607442151257 6.823295662002349, -2.0133972105577667 6.716427752933756, -2.394141003279681 6.5778483455013586 C-2.774884796001595 6.439268938068961, -3.149104622578983 6.26476736710249, -3.4999999999999982 6.062177826491071 C-3.8508953774210135 5.859588285879653, -4.189128084166966 5.6227551949470636, -4.499513267805773 5.362311101832848 C-4.809898451444581 5.101867008718632, -5.101867008718628 4.809898451444586, -5.3623111018328435 4.499513267805779 C-5.622755194947059 4.189128084166971, -5.859588285879649 3.8508953774210206, -6.062177826491068 3.5000000000000053 C-6.264767367102486 3.14910462257899, -6.439268938068958 2.774884796001602, -6.577848345501356 2.394141003279688 C-6.716427752933754 2.0133972105577738, -6.823295662002347 1.614560744215134, -6.893654271085454 1.215537243668521 C-6.9640128801685615 0.816513743121908, -6.999999999999999 0.4051790812228472, -7 1.0183126166254463e-14 C-7.000000000000001 -0.40517908122282686, -6.964012880168565 -0.8165137431218878, -6.893654271085459 -1.215537243668501 C-6.823295662002352 -1.6145607442151142, -6.716427752933759 -2.0133972105577542, -6.577848345501363 -2.394141003279669 C-6.439268938068967 -2.7748847960015834, -6.264767367102496 -3.149104622578972, -6.062177826491078 -3.4999999999999876 C-5.859588285879661 -3.8508953774210033, -5.6227551949470715 -4.1891280841669545, -5.362311101832856 -4.499513267805763 C-5.10186700871864 -4.809898451444571, -4.809898451444594 -5.10186700871862, -4.499513267805787 -5.362311101832836 C-4.189128084166979 -5.622755194947053, -3.850895377421028 -5.859588285879643, -3.5000000000000133 -6.062177826491062 C-3.1491046225789985 -6.264767367102482, -2.774884796001611 -6.439268938068954, -2.3941410032796973 -6.577848345501353 C-2.0133972105577835 -6.716427752933752, -1.6145607442151435 -6.823295662002345, -1.2155372436685306 -6.893654271085453 C-0.8165137431219176 -6.9640128801685615, -0.40517908122285695 -6.999999999999999, -1.9937625952807352e-14 -7 C0.4051790812228171 -7.000000000000001, 0.8165137431218781 -6.964012880168565, 1.2155372436684913 -6.89365427108546 C1.6145607442151044 -6.823295662002354, 2.013397210557745 -6.716427752933763, 2.3941410032796595 -6.5778483455013665 C2.774884796001574 -6.43926893806897, 3.149104622578963 -6.2647673671025, 3.499999999999979 -6.062177826491083 C3.8508953774209953 -5.859588285879665, 4.189128084166947 -5.622755194947077, 4.499513267805756 -5.362311101832862 C4.809898451444564 -5.1018670087186475, 5.101867008718613 -4.809898451444602, 5.362311101832829 -4.499513267805796 C5.622755194947046 -4.189128084166989, 5.859588285879637 -3.8508953774210393, 6.062177826491056 -3.500000000000025 C6.2647673671024755 -3.1491046225790105, 6.439268938068949 -2.774884796001623, 6.577848345501348 -2.3941410032797092 C6.716427752933747 -2.0133972105577955, 6.823295662002342 -1.6145607442151562, 6.893654271085451 -1.2155372436685434 C6.96401288016856 -0.8165137431219307, 6.982275711847575 -0.2025895406114567, 7 -3.2800750208310675e-14 C7.017724288152425 0.2025895406113911, 7.017724288152424 -0.2025895406114242, 7 0" stroke="none" stroke-width="0" fill="#ECECFF" style=""/><path d="M7 0 C7 0.40517908122283747, 6.964012880168563 0.816513743121899, 6.893654271085456 1.2155372436685123 C6.823295662002349 1.6145607442151257, 6.716427752933756 2.013397210557766, 6.5778483455013586 2.394141003279681 C6.439268938068961 2.7748847960015954, 6.26476736710249 3.149104622578984, 6.062177826491071 3.4999999999999996 C5.859588285879653 3.8508953774210153, 5.622755194947063 4.189128084166967, 5.362311101832846 4.499513267805774 C5.10186700871863 4.809898451444582, 4.809898451444583 5.10186700871863, 4.499513267805775 5.362311101832846 C4.189128084166968 5.622755194947063, 3.8508953774210166 5.859588285879652, 3.500000000000001 6.06217782649107 C3.149104622578985 6.264767367102489, 2.7748847960015963 6.439268938068961, 2.3941410032796817 6.5778483455013586 C2.013397210557767 6.716427752933756, 1.6145607442151264 6.823295662002349, 1.2155372436685128 6.893654271085456 C0.8165137431218992 6.964012880168563, 0.4051790812228379 7, 4.286263797015736e-16 7 C-0.405179081222837 7, -0.8165137431218985 6.964012880168563, -1.2155372436685121 6.893654271085456 C-1.6145607442151257 6.823295662002349, -2.0133972105577667 6.716427752933756, -2.394141003279681 6.5778483455013586 C-2.774884796001595 6.439268938068961, -3.149104622578983 6.26476736710249, -3.4999999999999982 6.062177826491071 C-3.8508953774210135 5.859588285879653, -4.189128084166966 5.6227551949470636, -4.499513267805773 5.362311101832848 C-4.809898451444581 5.101867008718632, -5.101867008718628 4.809898451444586, -5.3623111018328435 4.499513267805779 C-5.622755194947059 4.189128084166971, -5.859588285879649 3.8508953774210206, -6.062177826491068 3.5000000000000053 C-6.264767367102486 3.14910462257899, -6.439268938068958 2.774884796001602, -6.577848345501356 2.394141003279688 C-6.716427752933754 2.0133972105577738, -6.823295662002347 1.614560744215134, -6.893654271085454 1.215537243668521 C-6.9640128801685615 0.816513743121908, -6.999999999999999 0.4051790812228472, -7 1.0183126166254463e-14 C-7.000000000000001 -0.40517908122282686, -6.964012880168565 -0.8165137431218878, -6.893654271085459 -1.215537243668501 C-6.823295662002352 -1.6145607442151142, -6.716427752933759 -2.0133972105577542, -6.577848345501363 -2.394141003279669 C-6.439268938068967 -2.7748847960015834, -6.264767367102496 -3.149104622578972, -6.062177826491078 -3.4999999999999876 C-5.859588285879661 -3.8508953774210033, -5.6227551949470715 -4.1891280841669545, -5.362311101832856 -4.499513267805763 C-5.10186700871864 -4.809898451444571, -4.809898451444594 -5.10186700871862, -4.499513267805787 -5.362311101832836 C-4.189128084166979 -5.622755194947053, -3.850895377421028 -5.859588285879643, -3.5000000000000133 -6.062177826491062 C-3.1491046225789985 -6.264767367102482, -2.774884796001611 -6.439268938068954, -2.3941410032796973 -6.577848345501353 C-2.0133972105577835 -6.716427752933752, -1.6145607442151435 -6.823295662002345, -1.2155372436685306 -6.893654271085453 C-0.8165137431219176 -6.9640128801685615, -0.40517908122285695 -6.999999999999999, -1.9937625952807352e-14 -7 C0.4051790812228171 -7.000000000000001, 0.8165137431218781 -6.964012880168565, 1.2155372436684913 -6.89365427108546 C1.6145607442151044 -6.823295662002354, 2.013397210557745 -6.716427752933763, 2.3941410032796595 -6.5778483455013665 C2.774884796001574 -6.43926893806897, 3.149104622578963 -6.2647673671025, 3.499999999999979 -6.062177826491083 C3.8508953774209953 -5.859588285879665, 4.189128084166947 -5.622755194947077, 4.499513267805756 -5.362311101832862 C4.809898451444564 -5.1018670087186475, 5.101867008718613 -4.809898451444602, 5.362311101832829 -4.499513267805796 C5.622755194947046 -4.189128084166989, 5.859588285879637 -3.8508953774210393, 6.062177826491056 -3.500000000000025 C6.2647673671024755 -3.1491046225790105, 6.439268938068949 -2.774884796001623, 6.577848345501348 -2.3941410032797092 C6.716427752933747 -2.0133972105577955, 6.823295662002342 -1.6145607442151562, 6.893654271085451 -1.2155372436685434 C6.96401288016856 -0.8165137431219307, 6.982275711847575 -0.2025895406114567, 7 -3.2800750208310675e-14 C7.017724288152425 0.2025895406113911, 7.017724288152424 -0.2025895406114242, 7 0" stroke="#333333" stroke-width="2" fill="none" stroke-dasharray="0 0" style=""/><g><path d="M2.5 0 C2.5 0.14470681472244193, 2.487147457203058 0.29161205111496386, 2.46201938253052 0.4341204441673258 C2.436891307857982 0.5766288372196877, 2.3987241974763416 0.7190704323420595, 2.3492315519647713 0.8550503583141718 C2.299738906453201 0.991030284286284, 2.2374169168223177 1.124680222349637, 2.165063509461097 1.2499999999999998 C2.092710102099876 1.3753197776503625, 2.0081268553382365 1.496117172916774, 1.915111107797445 1.6069690242163481 C1.8220953602566536 1.7178208755159223, 1.7178208755159226 1.8220953602566536, 1.6069690242163484 1.915111107797445 C1.4961171729167742 2.0081268553382365, 1.375319777650363 2.0927101020998755, 1.2500000000000002 2.1650635094610964 C1.1246802223496375 2.2374169168223172, 0.9910302842862845 2.2997389064532, 0.8550503583141721 2.349231551964771 C0.7190704323420597 2.3987241974763416, 0.576628837219688 2.436891307857982, 0.43412044416732604 2.46201938253052 C0.291612051114964 2.487147457203058, 0.14470681472244212 2.5, 1.5308084989341916e-16 2.5 C-0.1447068147224418 2.5, -0.2916120511149638 2.487147457203058, -0.43412044416732576 2.46201938253052 C-0.5766288372196877 2.436891307857982, -0.7190704323420595 2.3987241974763416, -0.8550503583141718 2.3492315519647713 C-0.991030284286284 2.299738906453201, -1.124680222349637 2.2374169168223177, -1.2499999999999996 2.165063509461097 C-1.375319777650362 2.092710102099876, -1.4961171729167733 2.008126855338237, -1.6069690242163475 1.9151111077974459 C-1.7178208755159217 1.8220953602566548, -1.822095360256653 1.7178208755159234, -1.9151111077974443 1.6069690242163495 C-2.0081268553382357 1.4961171729167755, -2.0927101020998746 1.3753197776503645, -2.1650635094610955 1.250000000000002 C-2.2374169168223164 1.1246802223496395, -2.2997389064531992 0.9910302842862865, -2.34923155196477 0.8550503583141743 C-2.3987241974763407 0.7190704323420621, -2.436891307857981 0.5766288372196907, -2.4620193825305194 0.434120444167329 C-2.487147457203058 0.29161205111496724, -2.5 0.14470681472244545, -2.5 3.636830773662308e-15 C-2.5 -0.14470681472243818, -2.4871474572030587 -0.2916120511149599, -2.4620193825305208 -0.4341204441673218 C-2.436891307857983 -0.5766288372196837, -2.398724197476343 -0.7190704323420553, -2.3492315519647726 -0.8550503583141675 C-2.2997389064532023 -0.9910302842862798, -2.23741691682232 -1.1246802223496328, -2.165063509461099 -1.2499999999999956 C-2.092710102099878 -1.3753197776503583, -2.00812685533824 -1.4961171729167695, -1.9151111077974488 -1.606969024216344 C-1.8220953602566576 -1.7178208755159183, -1.7178208755159263 -1.82209536025665, -1.6069690242163523 -1.9151111077974416 C-1.4961171729167784 -2.0081268553382334, -1.3753197776503672 -2.0927101020998724, -1.2500000000000047 -2.1650635094610937 C-1.1246802223496422 -2.237416916822315, -0.9910302842862897 -2.299738906453198, -0.8550503583141776 -2.3492315519647686 C-0.7190704323420656 -2.3987241974763394, -0.5766288372196942 -2.4368913078579806, -0.43412044416733236 -2.462019382530519 C-0.29161205111497057 -2.4871474572030574, -0.1447068147224489 -2.4999999999999996, -7.120580697431198e-15 -2.5 C0.14470681472243463 -2.5000000000000004, 0.29161205111495647 -2.487147457203059, 0.4341204441673183 -2.4620193825305217 C0.5766288372196802 -2.436891307857984, 0.7190704323420518 -2.3987241974763442, 0.8550503583141642 -2.349231551964774 C0.9910302842862766 -2.2997389064532037, 1.1246802223496295 -2.2374169168223212, 1.2499999999999925 -2.165063509461101 C1.3753197776503554 -2.0927101020998804, 1.4961171729167668 -2.008126855338242, 1.6069690242163412 -1.915111107797451 C1.7178208755159157 -1.82209536025666, 1.8220953602566472 -1.7178208755159294, 1.915111107797439 -1.6069690242163557 C2.0081268553382308 -1.496117172916782, 2.09271010209987 -1.3753197776503712, 2.1650635094610915 -1.2500000000000089 C2.237416916822313 -1.1246802223496466, 2.299738906453196 -0.9910302842862939, 2.3492315519647673 -0.855050358314182 C2.3987241974763385 -0.71907043234207, 2.4368913078579792 -0.5766288372196986, 2.462019382530518 -0.4341204441673369 C2.487147457203057 -0.29161205111497523, 2.4936698970884197 -0.07235340736123454, 2.5 -1.1714553645825241e-14 C2.5063301029115803 0.07235340736121111, 2.50633010291158 -0.07235340736122292, 2.5 0" stroke="none" stroke-width="0" fill="#9370DB" style=""/><path d="M2.5 0 C2.5 0.14470681472244193, 2.487147457203058 0.29161205111496386, 2.46201938253052 0.4341204441673258 C2.436891307857982 0.5766288372196877, 2.3987241974763416 0.7190704323420595, 2.3492315519647713 0.8550503583141718 C2.299738906453201 0.991030284286284, 2.2374169168223177 1.124680222349637, 2.165063509461097 1.2499999999999998 C2.092710102099876 1.3753197776503625, 2.0081268553382365 1.496117172916774, 1.915111107797445 1.6069690242163481 C1.8220953602566536 1.7178208755159223, 1.7178208755159226 1.8220953602566536, 1.6069690242163484 1.915111107797445 C1.4961171729167742 2.0081268553382365, 1.375319777650363 2.0927101020998755, 1.2500000000000002 2.1650635094610964 C1.1246802223496375 2.2374169168223172, 0.9910302842862845 2.2997389064532, 0.8550503583141721 2.349231551964771 C0.7190704323420597 2.3987241974763416, 0.576628837219688 2.436891307857982, 0.43412044416732604 2.46201938253052 C0.291612051114964 2.487147457203058, 0.14470681472244212 2.5, 1.5308084989341916e-16 2.5 C-0.1447068147224418 2.5, -0.2916120511149638 2.487147457203058, -0.43412044416732576 2.46201938253052 C-0.5766288372196877 2.436891307857982, -0.7190704323420595 2.3987241974763416, -0.8550503583141718 2.3492315519647713 C-0.991030284286284 2.299738906453201, -1.124680222349637 2.2374169168223177, -1.2499999999999996 2.165063509461097 C-1.375319777650362 2.092710102099876, -1.4961171729167733 2.008126855338237, -1.6069690242163475 1.9151111077974459 C-1.7178208755159217 1.8220953602566548, -1.822095360256653 1.7178208755159234, -1.9151111077974443 1.6069690242163495 C-2.0081268553382357 1.4961171729167755, -2.0927101020998746 1.3753197776503645, -2.1650635094610955 1.250000000000002 C-2.2374169168223164 1.1246802223496395, -2.2997389064531992 0.9910302842862865, -2.34923155196477 0.8550503583141743 C-2.3987241974763407 0.7190704323420621, -2.436891307857981 0.5766288372196907, -2.4620193825305194 0.434120444167329 C-2.487147457203058 0.29161205111496724, -2.5 0.14470681472244545, -2.5 3.636830773662308e-15 C-2.5 -0.14470681472243818, -2.4871474572030587 -0.2916120511149599, -2.4620193825305208 -0.4341204441673218 C-2.436891307857983 -0.5766288372196837, -2.398724197476343 -0.7190704323420553, -2.3492315519647726 -0.8550503583141675 C-2.2997389064532023 -0.9910302842862798, -2.23741691682232 -1.1246802223496328, -2.165063509461099 -1.2499999999999956 C-2.092710102099878 -1.3753197776503583, -2.00812685533824 -1.4961171729167695, -1.9151111077974488 -1.606969024216344 C-1.8220953602566576 -1.7178208755159183, -1.7178208755159263 -1.82209536025665, -1.6069690242163523 -1.9151111077974416 C-1.4961171729167784 -2.0081268553382334, -1.3753197776503672 -2.0927101020998724, -1.2500000000000047 -2.1650635094610937 C-1.1246802223496422 -2.237416916822315, -0.9910302842862897 -2.299738906453198, -0.8550503583141776 -2.3492315519647686 C-0.7190704323420656 -2.3987241974763394, -0.5766288372196942 -2.4368913078579806, -0.43412044416733236 -2.462019382530519 C-0.29161205111497057 -2.4871474572030574, -0.1447068147224489 -2.4999999999999996, -7.120580697431198e-15 -2.5 C0.14470681472243463 -2.5000000000000004, 0.29161205111495647 -2.487147457203059, 0.4341204441673183 -2.4620193825305217 C0.5766288372196802 -2.436891307857984, 0.7190704323420518 -2.3987241974763442, 0.8550503583141642 -2.349231551964774 C0.9910302842862766 -2.2997389064532037, 1.1246802223496295 -2.2374169168223212, 1.2499999999999925 -2.165063509461101 C1.3753197776503554 -2.0927101020998804, 1.4961171729167668 -2.008126855338242, 1.6069690242163412 -1.915111107797451 C1.7178208755159157 -1.82209536025666, 1.8220953602566472 -1.7178208755159294, 1.915111107797439 -1.6069690242163557 C2.0081268553382308 -1.496117172916782, 2.09271010209987 -1.3753197776503712, 2.1650635094610915 -1.2500000000000089 C2.237416916822313 -1.1246802223496466, 2.299738906453196 -0.9910302842862939, 2.3492315519647673 -0.855050358314182 C2.3987241974763385 -0.71907043234207, 2.4368913078579792 -0.5766288372196986, 2.462019382530518 -0.4341204441673369 C2.487147457203057 -0.29161205111497523, 2.4936698970884197 -0.07235340736123454, 2.5 -1.1714553645825241e-14 C2.5063301029115803 0.07235340736121111, 2.50633010291158 -0.07235340736122292, 2.5 0" stroke="#9370DB" stroke-width="2" fill="none" stroke-dasharray="0 0" style=""/></g></g></g></g></g></g><defs><filter id="my-svg-drop-shadow" height="130%" width="130%"><feDropShadow dx="4" dy="4" stdDeviation="0" flood-opacity="0.06" flood-color="#000000"/></filter></defs><defs><filter id="my-svg-drop-shadow-small" height="150%" width="150%"><feDropShadow dx="2" dy="2" stdDeviation="0" flood-opacity="0.06" flood-color="#000000"/></filter></defs></svg></figure>

#### 4.1.3 Spec-versus-code disagreement — RESUBMITTED routing

The design specification's section 6.2 diagram draws `RESUBMITTED` flowing directly into
`REVIEWS_COMPLETE` ("`RESUBMITTED` ◀── … ▶ `REVIEWS_COMPLETE`"), implying a resubmission
closes the review round automatically. The implemented `LEGAL_TRANSITIONS` table instead
routes `RESUBMITTED` to **either** `UNDER_REVIEW` **or** `UNDER_SCREENING`, at editorial
discretion — a resubmission may need fresh review, or may need re-screening first, but
never closes the review round by itself. **The code governs**, per this document's
instruction: FR-13's postcondition and the state diagram above are written to the
implemented behaviour, not the narrative diagram. This is a genuine, load-bearing
disagreement between the two documents and is recorded here rather than silently
resolved in one direction without comment.

### 4.2 Actor/use-case mapping

| Actor | Use cases (effort estimation section 3) |
|---|---|
| Author | UC1, UC2, UC4, UC9 (as respondent is Reviewer; Author has no UC9 role), UC12, UC13, UC19, UC21 (recipient), UC23 |
| Reviewer | UC1, UC2, UC9, UC10, UC21 (recipient) |
| Editor | UC2, UC3 (Administrator only, not Editor — see note), UC6, UC7, UC8, UC11, UC18, UC21 (recipient) |
| Editor-in-Chief | All Editor use cases, plus UC14, UC22, UC24 |
| Administrator | UC3 |
| Reader | UC15, UC16, UC17, UC19 (public export, distinct from FR-19's audit view), UC20 (indirectly, as the harvested party), UC25 |
| CBAS college leadership | UC22 (read-only consumer) |
| Indexing service | UC20 |
| System (no human actor) | UC5, UC7 (computation), UC21 (dispatch) |

*Note:* UC3 ("manage roles") is an Administrator-only use case per FR-03's actor
column; it is listed once and not duplicated against Editor.

### 4.3 Authorisation matrix

Derived directly from `backend/src/ugjcs/domain/policies.py` — `_ROLE_GRANTS` for
role-only actions, `_OWNERSHIP_ACTIONS` and `_can_view` for actions that also depend on
the actor's relationship to a specific manuscript, and the policy module's own docstring
for the one action (`REVIEW`) that is deliberately under-specified today.

| Action | Author | Reviewer | Editor | Editor-in-Chief | Administrator |
|---|---|---|---|---|---|
| `VIEW` | Own manuscripts only | — *(no dedicated action; see gap below)* | Yes | Yes | Yes |
| `SUBMIT` | Yes | — | — | — | — |
| `SCREEN` | — | — | Yes | Yes | — |
| `ASSIGN_REVIEWER` | — | — | Yes | Yes | — |
| `REVIEW` | — | Yes *(role-only — no conflict-of-interest predicate; TD-02)* | — | — | — |
| `DECIDE` | — | — | Yes | Yes | — |
| `RESUBMIT` | Corresponding author only | — | — | — | — |
| `PUBLISH` | — | — | — | Yes | — |
| `MANAGE_USERS` | — | — | — | — | Yes |
| `VIEW_AUDIT` | — | — | Yes | Yes | — *(role grant exists; no route reaches it — section 5, FR-19)* |
| `WITHDRAW` *(FR-25a)* | Corresponding author only — **implemented & tested** | — | — | — | — |

**FR-25a is closed.** `Action.WITHDRAW` now exists in `_OWNERSHIP_ACTIONS` alongside
`RESUBMIT` (`policies.py`), and `POST /manuscripts/{tracking_code}/withdraw`
(`manuscripts.py`) calls `authorize(actor, Action.WITHDRAW, manuscript)` before
withdrawing. `test_corresponding_author_may_withdraw_own_manuscript`,
`test_another_author_may_not_withdraw_someone_elses_manuscript` and
`test_a_listed_co_author_who_is_not_corresponding_may_not_withdraw`
(`test_policies.py`), plus `test_the_corresponding_author_can_withdraw` and
`test_a_co_author_who_is_not_corresponding_cannot_withdraw`
(`test_manuscripts_router.py`), cover it end to end. The gap this row previously
recorded — first noticed as a mismatch between `transitions.py` (which already
permitted `WITHDRAWN`) and `policies.py` (which had no gate for it) — is resolved, not
merely documented.

**Known gaps still open in this matrix, cross-referenced to the technical debt register:**

- `REVIEW` is granted to any actor holding the `REVIEWER` role with no check that they
  are not also an author of, or affiliated with, the manuscript in question (**TD-02** —
  critical, still open). The reviews API (`reviews.py`) adds one partial mitigation not
  present when this gap was first recorded: `_assigned_or_403` refuses a reviewer who
  was never assigned to the manuscript. It does **not** stop a reviewer who *was*
  assigned, and who also happens to be a listed author, from reviewing their own work —
  `assign_reviewer` (`editorial.py`) never checks `author_ids` before creating an
  assignment. Because `Manuscript.record_review` also does not check the submitting
  reviewer's identity against an accepted assignment or against reviewers who already
  submitted (**TD-03** — critical, still open), a reviewer with an existing assignment
  could in principle call `POST /reviews/{tracking_code}/submit` twice and reach the
  quorum alone. Neither gap has been closed by the API layer; both remain exactly as
  critical as the technical debt register states.
- There is no `Action` connecting `blinding.blind()` to `policies.can()` — a caller must
  remember to call `blind()` before serving a reviewer, and nothing in the authorisation
  layer enforces it (**TD-07** — scheduled). In the delivered code, `reviews.py`'s
  `my_assignments` handler does call `blind()` correctly, and `test_blinding_leak.py`
  proves no author identity leaks through it today — but that is adapter discipline
  holding, which is precisely the weakness TD-07 names, not the gap being closed.
- The editorial event log has no blinded projection and is protected by `VIEW_AUDIT`
  policy alone rather than by the type system (**TD-06** — scheduled). No reviewer-facing
  path reads the log in the delivered system, so the risk TD-06 describes remains
  theoretical, exactly as originally recorded.

---

## 5. Requirements traceability matrix

**Revised 2026-08-12 against the finished system** (see the revision note on p.1). Status
categories: **Implemented & tested** (the requirement's behaviour is reachable end to end
— domain rule, API route and, where the requirement names one, a frontend screen — and is
covered by an automated test in the delivered codebase); **Partially implemented** (some
layer of the requirement is built and tested but a named, specific piece is missing —
never "mostly done" without saying what the remainder is); **Not implemented** (no code
exists for this requirement's behaviour, stated as such rather than described euphemistically).

| FR | Use case | Module / endpoint | Test | Status |
|---|---|---|---|---|
| FR-01 | UC1 | `application/identity.py` (`RegistrationService`) — account creation, email verification token issue and redemption | `test_identity.py`: `test_registering_creates_an_unverified_account_and_sends_one_message`, `test_a_valid_verification_token_verifies_the_account`, `test_a_verification_token_cannot_be_replayed`, `test_registering_an_existing_email_raises_and_sends_no_second_message` | **Partially implemented.** The service layer is fully built and tested, including duplicate-email and replay handling. But no `/auth/register` route exists (absent from the live `/openapi.json`) and the frontend has no registration screen — only `/login`. Accounts in the deployed system are provisioned by seed data (the judge accounts in Testing_Report.pdf section 5), not self-registration. Missing: the API route and the frontend form that would call it. |
| FR-02 | UC2 | `api/routers/auth.py` (`/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`); `application/identity.py` (`SessionService`) | `test_auth_router.py` (unit, all four routes); integration `test_refresh_rotation.py`: `test_replaying_a_rotated_refresh_token_revokes_the_entire_family`, `test_roles_revoked_after_a_token_was_issued_take_effect_immediately`, `test_an_expired_refresh_token_is_refused` | **Implemented & tested.** Session issuance, explicit revocation (`/logout`), and expiry are all live and covered, including the security-sensitive case (stolen-refresh-token family revocation) against a real database. |
| FR-03 | UC3 | `domain/policies.py` (`Action.MANAGE_USERS`, granted to `Administrator`); `infrastructure/db/account_repository.py` (role grant/revoke persistence) | `test_policies.py` (grant); integration `test_account_repository.py`: `test_granting_a_role_and_saving_persists_it`, `test_revoking_a_role_and_saving_removes_it` | **Partially implemented.** The authorisation grant and the persistence of a role change are both implemented and tested against a real database. No `/admin` API route or frontend screen exists to let an Administrator invoke this — confirmed absent from `/openapi.json` and from `frontend/src/app/`, and stated explicitly in Testing_Report.pdf section 5: "no UI surface exists for this yet." |
| FR-04 | UC4 | `api/routers/manuscripts.py` (`POST /manuscripts`, multipart with `file`); `domain/manuscript.py`; `domain/transitions.py` (`DRAFT→SUBMITTED`); frontend `app/author/submit/page.tsx` | `test_manuscripts_router.py`: `test_an_author_can_submit_a_manuscript_with_a_pdf`; `test_transitions.py`, `test_manuscript.py` | **Implemented & tested**, end to end: route, upload, lifecycle guard and the author's submission form all exist and are exercised by the cited tests plus the live UAT pass in section 5 of the testing report. |
| FR-05 | UC4 | `application/documents.py` (`validate_document` — magic-byte check, independent of client-supplied `Content-Type`) | `test_documents.py`: `test_a_client_supplied_content_type_cannot_substitute_for_the_magic_number`, `test_content_exceeding_the_size_cap_is_rejected`; `test_manuscripts_router.py`: `test_a_non_pdf_upload_is_rejected_with_415`, `test_an_oversized_upload_is_rejected_with_413` | **Implemented & tested**, at the unit level (validation logic) and the API level (`415`/`413` responses). |
| FR-06 | UC5 | `infrastructure/storage/anonymize.py` (`strip_pdf_metadata`); wired into `manuscripts.py`'s `_store_document`, which writes both an original and an anonymised S3 key on every submit/resubmit | `test_anonymize.py`; `test_documents.py`: `test_original_and_anonymised_keys_differ_for_the_same_manuscript_and_version`, `test_keys_carry_no_title_or_author_identifying_text` | **Implemented & tested.** Every submitted document produces a metadata-stripped derivative, distinct from the original, before either reaches storage. **Note the scope of what "anonymised" means here** — see section 7: XMP/DocInfo metadata is stripped; visible body text (a title or abstract that names the author) is not touched, which is FR-06 as designed, not a shortfall against it. |
| FR-07 | UC6 | `api/routers/editorial.py` (`POST /editorial/{tracking_code}/screen` → `begin_screening`; `POST /editorial/{tracking_code}/decision` with `DESK_REJECT`/`SEND_TO_REVIEW`/`REQUEST_REVISION` → the three FR-07 outcomes); `domain/transitions.py`; `domain/policies.py` (`Action.SCREEN`, `Action.DECIDE`) | `test_editorial_router.py`: `test_an_editor_can_begin_screening`, `test_a_decision_moves_the_manuscript_to_review`, `test_a_reviewer_cannot_record_a_decision`; `test_transitions.py`, `test_policies.py` | **Implemented & tested.** The three-way screening outcome is reached through the same `/decision` route FR-12 uses (one action, `Action.DECIDE`, gates the post-screening and post-review decisions alike) rather than a dedicated `/screen`-outcome route; `/screen` itself only performs the `SUBMITTED→UNDER_SCREENING` intake step. This is a routing detail, not a missing behaviour — all three outcomes are reachable and tested. |
| FR-08 | UC7 | `api/routers/editorial.py` (`GET /editorial/{tracking_code}/reviewer-candidates`, `_match_score`); `domain/conflicts.py` (`exclusion_reason`); `api/schemas_analytics.py` (`RankedReviewerCandidateOut`); frontend reviewer-candidate picker | `test_editorial_router.py`: `test_reviewer_candidates_are_ranked_by_expertise_match_then_load`, `test_reviewer_candidates_lists_eligible_and_excluded_with_their_reasons`, `test_a_candidate_at_capacity_is_excluded`, `test_a_candidate_already_assigned_to_this_manuscript_is_excluded`, `test_reviewer_candidates_omits_unverified_inactive_and_non_reviewer_accounts`, `test_a_reviewer_cannot_see_reviewer_candidates` | **Implemented & tested.** A ranked candidate list exists: `match_score` counts the manuscript's keywords appearing in a reviewer's `expertise`, candidates sort by match then by load, and `exclusion_reason` (a pure function) marks shared affiliation, existing assignment on this manuscript, and capacity exhaustion. Excluded candidates are returned **with** their reason rather than filtered away, so an editor can see why an obvious name is unavailable. Matching is keyword overlap, not TF-IDF or an assignment-optimisation algorithm; that is a simpler mechanism than the design specification sketched, and it is a deliberate one, since the corpus is far too small for term weighting to mean anything. |
| FR-09 | UC8 | `api/routers/editorial.py` (`POST /editorial/{tracking_code}/reviewers`); `domain/policies.py` (`Action.ASSIGN_REVIEWER`) | `test_editorial_router.py`: `test_assigning_a_reviewer_records_it`, `test_assigning_a_reviewer_to_a_missing_manuscript_is_404`; integration `test_review_assignment_repository.py`: `test_an_assignment_is_visible_to_both_parties`, `test_assigning_the_same_reviewer_twice_is_rejected` | **Implemented & tested** for the invite mechanism itself. The "may override any system recommendation" clause is now genuinely exercised rather than vacuous: FR-08's ranked candidate list exists, marks excluded reviewers with a reason instead of hiding them, and the editor remains free to assign any `reviewer_id` regardless of what the ranking said. `assign_reviewer` still does not check the invited reviewer against `author_ids` (TD-02) before creating the assignment, so the exclusion is advisory at the candidate-list layer rather than enforced at the assignment layer. |
| FR-10 | UC9 | *(none)* | *(none)* | **Not implemented.** `AssignmentStatus` declares `INVITED`/`ACCEPTED`/`DECLINED`/`SUBMITTED`/`EXPIRED`, but the assignment repository writes the literal string `"assigned"` on creation (`assignment_repository.py`) — a value that is not even one of the enum's own members — and no route lets a reviewer accept or decline. A reviewer's assignment is usable immediately; there is no invitation-response step at all. |
| FR-11 | UC10 | `api/routers/reviews.py` (`POST /reviews/{tracking_code}/submit`); `api/schemas.py` (`SubmitReviewRequest`: four 1-5 criterion scores, `comments_to_author`, `confidential_comments_to_editor`; `ReviewOut`); `api/routers/editorial.py` (`GET /editorial/{tracking_code}/reviews`, the only route returning confidential comments); `domain/manuscript.py` (`record_review`, quorum counter) | `test_reviews_router.py`: `test_submitting_a_review_counts_it_and_records_the_content`, `test_a_score_outside_one_to_five_is_rejected`, `test_submitting_without_an_assignment_is_forbidden`; `test_editorial_router.py`: `test_an_editor_can_list_the_reviews_recorded_for_a_manuscript`, `test_an_editor_sees_the_confidential_comments_a_reviewer_wrote`; integration `test_review_assignment_repository.py`: `test_marking_submitted_records_the_review_content` | **Implemented & tested.** `SubmitReviewRequest` carries four criterion scores (originality, rigour, clarity, significance), each bounded 1 to 5 by Pydantic so an out-of-range score is a 422 before any handler runs, and the comment field is split into `comments_to_author` and `confidential_comments_to_editor`. The confidential channel is now enforced structurally rather than vacuously: `ReviewOut` is built by exactly one route, gated on `Action.DECIDE`, which no author-reachable or reviewer-reachable route carries. The quorum-counting defect (TD-03) is still unresolved; see section 4.3. |
| FR-12 | UC11 | `api/routers/editorial.py` (`POST /editorial/{tracking_code}/decision`); `domain/transitions.py`; `domain/policies.py` (`Action.DECIDE`) | `test_editorial_router.py`: `test_a_decision_moves_the_manuscript_to_review`, `test_a_reviewer_cannot_record_a_decision`; `test_transitions.py`, `test_manuscript.py`: `test_a_decision_requires_the_minimum_review_count` | **Implemented & tested.** Quorum enforcement and role gating both hold; quorum *correctness* still depends on the unresolved TD-03 defect in FR-11, which is a defect in what feeds the count, not in this requirement's own enforcement of it. |
| FR-13 | UC12 | `api/routers/manuscripts.py` (`POST /manuscripts/{tracking_code}/resubmit`, multipart with `response_to_reviewers`); `domain/policies.py` (`Action.RESUBMIT`, ownership-checked) | `test_manuscripts_router.py`: `test_the_corresponding_author_can_resubmit_with_a_revised_file`, `test_a_stranger_cannot_resubmit_someone_elses_manuscript`, `test_resubmitting_a_non_pdf_is_rejected`; `test_manuscript.py`: `test_resubmission_increments_the_version_and_resets_review_count` | **Implemented & tested**, including the response-to-reviewers letter and the ownership check. |
| FR-14 | UC13 | `api/routers/manuscripts.py` (`GET /manuscripts/mine`); `domain/policies.py` (`Action.VIEW`, `_can_view`); frontend `app/author/page.tsx`, `app/author/[trackingCode]/page.tsx` | `test_manuscripts_router.py`: `test_mine_lists_only_the_callers_manuscripts`, `test_retrieving_someone_elses_manuscript_is_forbidden`; live UAT (Testing_Report.pdf section 5): ten submissions listed with correct tracking codes and statuses | **Partially implemented.** An author's own-manuscripts list, correctly scoped and rendered, is implemented, tested and confirmed live. The **status timeline** clause is not met literally: `ManuscriptOut` carries only the manuscript's *current* `status`, not a history of transitions — the same underlying gap as FR-19 (no event/audit data is exposed on the wire at all, by the deliberate design recorded in `schemas.py`'s `ManuscriptOut` docstring). An author sees where a manuscript is now, not the sequence of states it passed through. |
| FR-15 | UC14 | `api/routers/editorial.py` (`POST /editorial/{tracking_code}/schedule`, `POST /editorial/{tracking_code}/publish`); `domain/transitions.py` (`ACCEPTED→SCHEDULED→PUBLISHED`); `domain/policies.py` (`Action.PUBLISH`, EiC-only) | `test_editorial_router.py`: `test_the_editor_in_chief_can_schedule_an_accepted_manuscript`, `test_the_editor_in_chief_can_publish_a_scheduled_manuscript`, `test_a_plain_editor_cannot_schedule`, `test_a_plain_editor_cannot_publish`, `test_publishing_without_scheduling_first_is_a_conflict`, `test_scheduling_the_same_volume_and_number_twice_yields_the_same_issue_id` | **Implemented & tested.** `Issue` is not a persisted aggregate — an `IssueId` is derived deterministically from `(volume, number)` (`domain/ids.py`, `mint_issue_id`) rather than looked up — a documented simplification, not a gap against this requirement's testable behaviour. Testing_Report.pdf section 4.5 records that these two routes, plus resubmission, were at one point fully domain-tested but reachable by no route at all; that gap is closed and is exactly what the cited tests now pin. |
| FR-16 | UC15 | `api/routers/archive.py` (`GET /archive`, `GET /archive/{tracking_code}` — no auth dependency); frontend `app/(public)/papers/[trackingCode]/page.tsx` | `test_archive_router.py`: `test_the_archive_requires_no_authentication`, `test_retrieving_a_published_paper_by_tracking_code`, `test_an_unpublished_manuscript_is_not_found_via_the_archive`; route audit `test_the_archive_prefix_genuinely_has_no_authorization_dependency` | **Implemented & tested**, including the negative case (an unpublished manuscript is not reachable through this path) and the route-audit proof that the entire `/archive` prefix is genuinely, not accidentally, public. |
| FR-17 | UC16 | `infrastructure/storage/fulltext.py` (PDF text extraction); `infrastructure/db/models.py` (stored `tsvector` column); `infrastructure/db/repository.py` (`search_published`, `websearch_to_tsquery` ranked by `ts_rank`, `ts_headline` snippets); `api/routers/archive.py` (`GET /archive/search`); `api/schemas_wave2.py` (`ArchiveSearchResultOut`); frontend `app/(public)/search/page.tsx` | `test_archive_search_fulltext.py`: `test_a_fulltext_match_carries_a_snippet_of_context`, `test_a_title_match_carries_a_null_snippet`, `test_a_keyword_match_is_found_with_a_null_snippet`, `test_no_match_anywhere_returns_an_empty_list`, `test_publishing_extracts_the_pdf_text_into_the_search_column`, `test_a_missing_or_unreadable_document_never_blocks_publishing`; integration `test_fulltext_search.py`, `test_archive_queries.py` | **Implemented & tested.** Search is PostgreSQL full-text over a stored `tsvector` covering title, abstract, keywords and the extracted body text of the published PDF, ranked by `ts_rank`, with `ts_headline` snippets returned when the match landed in the body. Body text is extracted at publication and a failed extraction never blocks the publish. Still not met: the "with filters" clause, since no keyword or date filter exists. NFR-09's 800 ms p95 bound remains unverified, because no load or performance test exists in this project (Testing_Report.pdf section 6). |
| FR-18 | UC17 | `api/routers/archive.py` (`GET /archive/{tracking_code}/document`, no auth dependency); `api/schemas.py` (`ArchivePaperOut.has_document`, `DocumentUrlOut`); frontend `app/(public)/papers/[trackingCode]/page.tsx` (inline PDF viewer) | `test_archive_router.py`: `test_a_published_papers_document_is_downloadable_without_authentication`, `test_archive_entries_report_whether_a_document_is_attached`, `test_downloading_a_missing_papers_document_is_404`, `test_downloading_when_no_document_was_ever_attached_is_404`; route audit `test_the_archive_prefix_genuinely_has_no_authorization_dependency` | **Implemented & tested.** A public, unauthenticated route serves a pre-signed URL for the original document of a published manuscript only. `has_document` on the archive shape lets a reader's page decide whether to render a viewer without first attempting a download. The route sits inside the `/archive` prefix, which the route audit proves carries no authorisation dependency anywhere. |
| FR-19 | UC18 | `domain/hashchain.py`; PostgreSQL append-only triggers (Alembic migration); `api/routers/archive.py` (`GET /archive/{tracking_code}/provenance`); `api/schemas_scholarly.py` (`ProvenanceOut`, `ProvenanceEventOut`); `api/routers/certificate.py` (decision certificate carrying the chain head) | `test_hashchain.py`; `test_provenance_router.py`: `test_an_intact_chain_verifies_and_reports_its_head_hash`, `test_a_tampered_interior_event_is_reported_as_not_intact`, `test_event_payloads_and_actor_ids_are_never_exposed`, `test_provenance_for_an_unpublished_manuscript_is_404`; integration `test_append_only.py`: `test_updating_an_event_is_rejected_by_the_database`, `test_truncating_the_event_log_is_rejected`; `test_chain_persistence.py` | **Implemented & tested.** The chain was already enforced at the database boundary; `GET /archive/{code}/provenance` now surfaces it, and goes further than the requirement asked by making verification public rather than editor-only: anyone can recompute a published paper's chain from genesis and see `intact`, the head hash, and each event's type, timestamp and 8-character hash prefix. Payloads and `actor_id` are deliberately withheld, because a `REVIEW_SUBMITTED` payload names its reviewer and a public endpoint must not hand out even a pseudonymous handle. What `intact` does **not** prove (tail truncation, a forged event appended through the normal path, a history rebuilt wholesale from genesis) is stated in TD-04 and in the endpoint's own contract. |
| FR-20 | UC5 | *(none)* | *(none)* | **Not implemented.** No similarity-screening, MinHash, or LSH code exists anywhere in the delivered backend. |
| FR-21 | UC19 | `application/scholarly.py` (`bibtex_citation`, `ris_citation`, `fake_doi`, `_citation_key`); `api/routers/archive.py` (`GET /archive/{tracking_code}/citation?format=`); frontend `components/paper-scholarly.tsx` (`CitationRow`) | `test_citation_router.py`: `test_a_bibtex_citation_is_well_formed_plain_text`, `test_a_ris_citation_is_a_jour_record_with_one_au_tag_per_author`, `test_archive_entries_carry_the_doi_shaped_identifier`, `test_an_unknown_citation_format_is_422`, `test_a_missing_citation_format_is_422`, `test_a_citation_for_an_unpublished_manuscript_is_404` | **Implemented & tested.** Both formats are served as `text/plain` from one route, with an unknown or missing `format` answered 422 rather than silently defaulting. Each paper also carries a DOI-shaped identifier derived from its tracking code. The identifier is **not registered**: `10.55555` is a documented fake registrant prefix (section 4.2) and resolving it at doi.org fails by design. Neither citation carries a publication date, because the domain stores none; that omission is the same underlying gap as FR-14's missing timeline. |
| FR-22 | UC20 | *(none)* | *(none)* | **Not implemented.** No OAI-PMH endpoint exists. |
| FR-23 | UC21 | `infrastructure/email/logging_sender.py` (`LoggingEmailSender`) | *(none beyond FR-01's registration tests, which exercise the logging stub incidentally)* | **Not implemented**, beyond a stub. `LoggingEmailSender` only logs a registration verification link — it does not send email, and there is no in-app notification record of any kind, no delivery for editorial events (decisions, assignments, publication), and no notification data model at all. Named explicitly in the design spec as future evolution; it remains that. |
| FR-24 | UC22 | `api/routers/editorial.py` (`GET /editorial/analytics`, gated on `Action.VIEW_AUDIT`); `api/schemas_analytics.py` (`EditorialAnalyticsOut`, `PipelineCounts`, `MonthlySubmissions`); frontend `app/editor/analytics/page.tsx` | `test_editorial_analytics.py`: `test_analytics_reports_pipeline_months_rate_and_averages`, `test_analytics_over_an_empty_desk_reports_zeros_and_nulls_not_zero_rates`, `test_a_reviewer_may_not_read_analytics`; integration `test_editorial_queries.py` | **Implemented & tested.** Throughput (pipeline counts by current status), decision mix (acceptance rate), and time-to-decision and review-turnaround averages are computed from the editorial event chain rather than from mutable manuscript rows, so the numbers derive from the same append-only record the audit guarantee covers. One rule governs every aggregate: an average or rate over an empty denominator is `null`, never `0`, so "no decisions yet" stays distinguishable from "decisions arrive instantly". The pipeline view drops `draft` (never reached the desk) and folds `desk_rejected` into `rejected`. |
| FR-25 | UC23 | `api/routers/manuscripts.py` (`POST /manuscripts/{tracking_code}/withdraw`); `domain/transitions.py` (`WITHDRAWN` reachable from five states); `domain/policies.py` (`Action.WITHDRAW`, ownership-checked — see FR-25a) | `test_manuscripts_router.py`: `test_the_corresponding_author_can_withdraw`, `test_a_co_author_who_is_not_corresponding_cannot_withdraw`, `test_withdrawing_a_missing_manuscript_is_404`; `test_transitions.py` | **Implemented & tested**, now including the authorisation half this line previously lacked — see FR-25a. |
| FR-25a | UC23 | `domain/policies.py` (`Action.WITHDRAW` in `_OWNERSHIP_ACTIONS`); `api/routers/manuscripts.py` (`authorize(actor, Action.WITHDRAW, manuscript)`) | `test_policies.py`: `test_corresponding_author_may_withdraw_own_manuscript`, `test_another_author_may_not_withdraw_someone_elses_manuscript`, `test_a_listed_co_author_who_is_not_corresponding_may_not_withdraw` | **Implemented & tested — this gap is closed.** The authorisation predicate this line was added to demand now exists, is wired into the live route, and is directly tested for both the positive case and two distinct negative cases (a stranger; a non-corresponding co-author). Section 4.3 records this as resolved rather than merely documented. |
| FR-26 | UC24 | *(none)* | *(none)* | **Not implemented.** Deferred (Could-have; effort estimation section 8.1) — no policy-configuration route or UI exists. |
| FR-29 | *(no dedicated UC — added after the original use-case set)* | `api/routers/billing.py` (all four routes); `api/schemas_wave2.py` (`ApcInvoiceOut`, `BillingInitializeOut`, `BillingVerifyOut`); `application/ports.py` (`PaymentGateway`, `ApcInvoiceRecord`); `infrastructure/config.py` (Paystack key, optional); frontend `components/apc-panel.tsx` | `test_billing_router.py`: `test_an_accept_decision_opens_a_pending_invoice_at_the_default_tariff`, `test_a_non_accept_decision_opens_no_invoice`, `test_a_repeated_accept_path_never_double_bills`, `test_the_corresponding_author_can_read_their_invoice`, `test_a_co_author_cannot_read_the_invoice`, `test_mock_mode_initialize_settles_the_invoice_and_says_so`, `test_real_mode_initialize_returns_the_checkout_url_and_stores_the_reference`, `test_only_the_corresponding_author_may_initialize`, `test_initializing_a_settled_invoice_is_a_conflict`; integration `test_invoice_repository.py` | **Implemented & tested.** An invoice opens automatically on an accept decision and only on an accept decision, at a default tariff, and the accept path is idempotent so a repeated transition never double-bills. Amounts are integer pesewas throughout, never floats. **Mock mode is the default**: with no Paystack secret key configured, `initialize` settles on the spot and answers `mock: true`, so the flow is demonstrable without a card; with a key configured it returns a real checkout URL and the charge is confirmed only by a later `verify`. Waiving is Editor-in-Chief only and is checked directly rather than by borrowing `Action.PUBLISH`, since waiving a charge and publishing a paper are different authorities that happen to sit with the same person. |
| FR-30 | *(no dedicated UC — added after the original use-case set)* | `api/routers/admin.py` (all four routes, gated on `Action.MANAGE_USERS`); `api/schemas_wave2.py` (`AdminAccountOut`, `RoleChangeRequest`, `CapacityChangeRequest`, `ActiveChangeRequest`); frontend `app/admin/page.tsx` | `test_admin_router.py`: `test_every_admin_route_is_forbidden_to_non_administrators`, `test_admin_routes_require_authentication`, `test_the_roster_lists_every_account_with_its_administrative_shape`, `test_granting_the_reviewer_role_adds_it`, `test_revoking_a_held_role_removes_it`, `test_the_administrator_role_can_be_neither_granted_nor_revoked`, `test_capacity_can_be_set_within_one_to_ten`, `test_capacity_outside_one_to_ten_is_a_422`, `test_an_administrator_can_deactivate_and_reactivate_another_account` | **Implemented & tested.** `Action.MANAGE_USERS` was defined in the policy layer from the start with no route exercising it; this closes that. Two refusals are enforced in the router rather than the domain because both protect the console from itself: the administrator role can be neither granted nor revoked through the API (403), and an administrator cannot deactivate their own account (409). Together they stop the last administrator locking everyone out. |
| FR-31 | *(no dedicated UC — added after the original use-case set)* | `api/routers/certificate.py` (`GET /editorial-certificate/{tracking_code}`, gated on `Action.DECIDE`); `infrastructure/storage/certificate_pdf.py` | `test_certificate_router.py`: `test_an_editor_receives_a_pdf_certificate`, `test_the_editor_in_chief_may_also_fetch_a_certificate`, `test_the_certificate_never_names_a_reviewer_or_leaks_confidential_comments`; `test_certificate_auth.py` | **Implemented & tested.** A generated PDF stating the final decision, the tracking code and the audit chain's head hash, so a decision can be attested outside the portal. Requesting one before any `accept` or `reject` decision is a 409 rather than an empty document. The certificate names no reviewer and carries no confidential comment, which is asserted directly rather than left to inspection. |
| FR-32 | *(no dedicated UC — added after the original use-case set)* | `infrastructure/storage/preflight.py` (`PdfInspection`); `api/schemas_scholarly.py` (`AnonymisationReport`, `ManuscriptSubmissionOut`); `api/routers/manuscripts.py` (`_submission_response`); frontend submission form | `test_submission_preflight.py`: `test_the_submission_response_reports_the_stripped_docinfo_keys`, `test_an_author_name_in_the_body_text_is_flagged`, `test_a_resubmission_also_carries_the_preflight_report`, `test_the_response_still_carries_every_manuscript_out_field` | **Implemented & tested.** This is the visible half of TD-05. Metadata stripping cannot remove a name printed in the body text, so rather than leave that silent, submission and resubmission now return what was removed (DocInfo keys, XMP) and which author names were still found in the extracted text. `author_names_in_body` is an honest partial detector: an empty list means nothing was found, never that the document is proven clean. The response is a subclass of `ManuscriptOut`, so every existing consumer keeps every field it relied on. |
| FR-33 | *(no dedicated UC — added after the original use-case set)* | `api/routers/editorial.py` (`GET /editorial/{tracking_code}/assignments`); `api/schemas_analytics.py` (`AssignmentDeadlineOut`); Alembic `due_at` migration; frontend editor assignments panel | `test_editorial_analytics.py`: `test_assignments_lists_deadlines_names_and_the_overdue_flag`, `test_an_assignment_before_its_deadline_is_not_overdue`, `test_assignments_for_a_missing_manuscript_is_404`; integration `test_due_at_migration.py` | **Implemented & tested.** `overdue` is computed server-side so every consumer agrees on one rule: not yet submitted, and `due_at` in the past. A review submitted late is never flagged overdue, and a null deadline never is either. The model carries `reviewer_name`, which is correct rather than a leak: the blind is author to reviewer, not editor to reviewer, and the route is gated on `Action.ASSIGN_REVIEWER`, which no author-reachable route carries. |
| FR-34 | *(no dedicated UC — added after the original use-case set)* | `api/routers/auth.py` (`POST /auth/register`, `RegisterRequest`); `application/registration.py` (`RegistrationService`); frontend `app/login/page.tsx` (sign-up tab) | `test_auth_router.py`: `test_registering_creates_a_verified_author_and_signs_in`, `test_registering_never_grants_an_editorial_role` | **Implemented & tested.** The route grants exactly `Role.AUTHOR` and ignores any role the request body might carry, which is asserted directly. Email delivery is mocked (`LoggingEmailSender` logs the verification link rather than sending it), so the account is verified immediately and signed in; that shortcut is honest about itself and is the same stub FR-23 records as unbuilt. Password policy is length-based, enforced in `RegistrationService`. |
| FR-27 | UC25 | *(none)* | *(none)* | **Not implemented.** Deferred (Could-have) — no persistent-identifier resolution route exists. |
| FR-28 | *(no dedicated UC — reporting over UC10/UC22 data, effort estimation section 3)* | `api/routers/editorial.py` (`GET /editorial/reviewer-performance`, gated on `Action.VIEW_AUDIT`); `api/schemas_analytics.py` (`ReviewerPerformanceOut`) | `test_editorial_analytics.py`: `test_reviewer_performance_reports_workload_and_turnaround_per_reviewer`, `test_a_reviewer_may_not_read_reviewer_performance` | **Implemented & tested.** Per reviewer: active assignments against capacity, reviews completed, average turnaround in days, and last activity. Turnaround and last activity are `null` until a first review completes, for the same reason the analytics aggregates are: an editor has to tell "new to the pool" apart from "turns reviews around instantly". The requirement's "acceptance rate" clause is not met, and cannot be, because FR-10's invitation lifecycle does not exist, so no reviewer has ever declined anything to compute a rate from. |

**Reading this matrix honestly.** Of the 35 requirement lines (FR-01 to FR-34 plus
FR-25a), **24 are implemented and tested end to end** (FR-02, FR-04, FR-05, FR-06, FR-07,
FR-08, FR-09, FR-11, FR-12, FR-13, FR-15, FR-16, FR-18, FR-19, FR-21, FR-24, FR-25,
FR-25a, FR-29 to FR-34), **5 are partially implemented with a specifically named
remainder** (FR-01, FR-03, FR-14, FR-17, FR-28), and **6 are genuinely not implemented**
(FR-10, FR-20, FR-22, FR-23, FR-26, FR-27).

FR-10, the reviewer invitation lifecycle, is the absence that propagates furthest: because
no reviewer can decline, FR-28 cannot report an acceptance rate, and an assignment takes
effect the moment it is created. The other five unbuilt requirements stand as the technical
debt register and the design specification's future-evolution section describe them.

---

## 6. Requirements prioritisation

Prioritisation uses MoSCoW, carried unchanged from the design specification (section 5) and
made authoritative by the effort estimation document's scope decision (section 8):

| Priority | Use cases | Decision |
|---|---|---|
| Must | UC1–UC18 | Implemented to production quality |
| Should | UC19–UC23 | Implemented only if Must-have work completes early |
| Could | UC24, UC25 | Deferred; recorded as technical debt with a repayment plan |

**How the estimate drove the cut.** Use Case Points sized the Must-have subset alone at
188 UUCP → 125.7 UCP → 2,514 person-hours (effort estimation section 6), against a 48-hour
development window — 1.9% of the Must-have estimate. COCOMO II Early Design, an
independent cross-check on different inputs (source lines of code and process/product
ratings rather than actor and transaction counts), priced the full system at
approximately 7,170 person-hours. The two methods disagree by roughly 2.2× on the exact
figure but agree on the order of magnitude: both place the full system in the
one-to-four-person-year range, nearly two orders of magnitude beyond the available
window (effort estimation section 7). That agreement, not either figure's precision, is what
forced a MoSCoW cut rather than an attempt to build everything thinly. Should-have items
are attempted only after every Must-have item reaches production quality; Could-have
items (FR-26, FR-27, FR-28) are not attempted within the window under any circumstance.

**Consequence for what exists today.** At the time this document was first written, the
domain layer was complete while the application, API and frontend layers were still
planned — consistent with, not contrary to, the MoSCoW cut: the cut governs *what* is
built, not the *order* in which layers within a use case are built, and a hexagonal
architecture's domain core is the natural first layer to complete and verify in isolation
(design specification section 7.1). That sequencing has since played out as intended: section 5's
revised traceability matrix shows the API and frontend layers have caught up for most of
the Must-have set (12 of 29 requirement lines implemented and tested end to end, domain
through frontend). Where a gap remains within the Must-have set — FR-08's reviewer
matching and FR-19's audit-trail route being the clearest examples — it is a gap in a
specific layer or route, not evidence that an entire layer was skipped; section 5 states each
one by name rather than folding them back into a single "still catching up" claim.

---

## 7. Constraints and limitations

This system does not guarantee everything its feature list might suggest. The following
limitations are stated plainly, each cross-referenced to Technical_Debt_Plan.pdf.

- **Double-blind review is not text-scrubbed — implemented as designed, with a limit
  that is now demonstrated in production, not merely anticipated.** Anonymisation
  strips XMP and DocInfo metadata from every submitted document (FR-06, live at
  `POST /manuscripts` and `POST /manuscripts/{tracking_code}/resubmit`,
  `infrastructure/storage/anonymize.py::strip_pdf_metadata`) and omits author fields
  from the `BlindedManuscript` type by construction (`blinding.py`), but `title`,
  `abstract` and `keywords` are copied to reviewers **verbatim**. An author who writes
  their own name into the title, or an abstract that says "extending our earlier work in
  [Obeng 2025]", reaches the reviewer unchanged. Double-blind integrity therefore depends
  partly on author compliance, not entirely on the system (**TD-05**, scheduled). This is
  unchanged by the API and frontend build — it was always the intended scope of FR-06, not
  a shortfall the implementation introduced.
- **The audit trail has no external anchor.** Hash chaining (NFR-07, `hashchain.py`)
  detects alteration, reordering and removal *within* the chain, and a PostgreSQL
  trigger blocks `UPDATE`, `DELETE` and `TRUNCATE` on the event table — both properties
  are proven against a real database by `test_append_only.py` and
  `test_chain_persistence.py`. But truncation of the tail, a forged event appended
  through the legitimate API, or a wholly fabricated history rebuilt from the genesis
  hash, are **undetectable by the application alone** — there is no periodically
  published, independently held checkpoint to compare against (**TD-04**, scheduled).
  Deployment did not change this: no checkpoint-publishing mechanism was added, and — see
  FR-19 above — there is currently no API route at all through which anyone could view
  the chain to notice tampering even if the chain itself remained sound.
- **A reviewer's conflict of interest is not checked by the authorisation layer — and
  this is now a live gap, not a theoretical one.** `Action.REVIEW` is granted to any
  actor holding the `REVIEWER` role, with no per-manuscript predicate excluding authors
  or affiliated actors (**TD-02**, critical). `POST /editorial/{tracking_code}/reviewers`
  creates an assignment without checking the reviewer against the manuscript's
  `author_ids`, and `POST /reviews/{tracking_code}/submit` counts a submission without
  checking it against reviewers who already submitted (**TD-03**, critical): a reviewer
  who also holds the `AUTHOR` role, or one who is assigned and calls submit twice, could
  in principle close a review round alone. Both routes are built and deployed today — the
  gap this bullet describes is no longer a forecast about what a future endpoint might do.
- **Withdrawal authorisation now exists and is enforced — this bullet previously
  recorded a gap that is closed.** The lifecycle permits `WITHDRAWN` from five states
  (`transitions.py`), and `Action.WITHDRAW` (`policies.py`) now gates
  `POST /manuscripts/{tracking_code}/withdraw` on the actor being the manuscript's
  corresponding author, exactly as FR-25a specified. See section 4.3 and section 5 (FR-25a) for the
  tests that prove it. This entry is retained here, rather than deleted, so the document's
  history — a gap identified, then closed — stays legible.
- **The editorial event log has no blinded view.** `EditorialEvent` carries `actor_id`
  and an editor's free-text rationale; there is no `BlindedEvent` projection, so a
  reviewer-facing audit view, if ever built, must not simply reuse `VIEW_AUDIT`'s
  current shape without one (**TD-06**, scheduled).
- **The current state is materialised, not derived by event replay.** The hybrid design
  (event log plus a materialised `status` column) is a deliberate trade-off against full
  event sourcing, mitigated by routing every state change through one `_transition`
  method. Two representations of the same fact could in principle diverge if that
  discipline is ever broken (**TD-09**, acceptable).
- **Coverage is a floor, not a proof of correctness.** The CI gate at 85% (NFR-14) is a
  regression floor, not a target (**TD-10**); `make check` reports **90.03%** on the
  current commit against that 85% gate — 402 unit tests pass, plus 84 integration tests
  against a real PostgreSQL container, run separately (confirmed directly against this
  commit; see NFR-14).
  Separately, mutation testing during final review found defects surviving a suite at
  100% line coverage — including deletion of the single line that makes the hash chain a
  chain — which coverage alone did not catch (**TD-11**, acceptable, provided compensated
  by targeted review; systematic mutation testing is recorded as future evolution, not
  yet in CI).
- **No reviewer accept/decline step exists (FR-10).** An assignment is usable by the
  reviewer immediately on creation; the `AssignmentStatus` vocabulary declares
  `INVITED`/`ACCEPTED`/`DECLINED`, but nothing in the delivered code writes or reads
  those states, and no route lets a reviewer decline. See section 5, FR-10.
- **A published paper cannot be downloaded by an anonymous reader (FR-18).** Document
  storage, upload, and authenticated download all exist (FR-04/FR-06), but no public,
  unauthenticated route serves a published manuscript's PDF, and the public paper page
  has no download link. This is the one gap this revision found that was not previously
  recorded anywhere in this project's documentation — see section 5, FR-18.
- **AWS access currently uses root credentials.** The toolchain authenticates as the AWS
  account root user rather than a least-privilege IAM principal (**TD-01**, critical).
  Deployment to App Runner, S3 and the rest of the live infrastructure has already
  happened under this arrangement, mitigated only by keeping the root keys off CI and
  used solely from the developer's own workstation (TD-01's full entry). That mitigation
  reduces exposure; it does not resolve the underlying debt, which remains the
  highest-priority item in the technical debt register.
- **Explicit out-of-scope items** (design specification section 4.2), restated here as hard
  limits rather than soft gaps: no copy-editing or typesetting workflow; no
  production-quality PDF galley generation; no multi-journal tenancy; no ORCID federation;
  identifiers are DOI-*shaped* but not registered with Crossref; similarity screening
  (FR-20, not implemented, see section 5) would in any case be against the internal corpus only,
  never the open web; email deliverability is not implemented at all today (FR-23), let
  alone guaranteed through a transactional provider; OAI-PMH (FR-22) is likewise not
  implemented. This list is not exhaustive of section 5's not-implemented rows, only a
  restatement of the ones the original specification called out as deliberately out of
  scope.
- **One item has left this list.** Article processing charges were originally declared out
  of scope and are now built (FR-29). The scope line that has *not* moved is the one that
  matters for anyone reading a charge on screen: the default configuration uses a mock
  gateway that settles an invoice without contacting Paystack, and a real Paystack
  integration is exercised only when a secret key is configured. No money has moved through
  this system, and the mock/real distinction is reported to the caller on every
  initialisation rather than inferred.
- **Requirements traceability reflects the finished system, not the pre-implementation
  build.** section 5 of this document, re-reconciled against the running code on 2026-08-14,
  shows 24 of 35 requirement lines implemented and tested end to end, 5 partially
  implemented with a named remainder, and 6 genuinely not implemented. The matrix has now
  been revised twice against the code rather than against intent, and both revisions moved
  lines in both directions: the second one had to correct rows that understated the system
  as much as the first corrected rows that overstated it. Section 5's closing paragraph is
  explicit that none of this is a claim of completeness.
