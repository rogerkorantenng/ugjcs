# UGJCS Plan 1 — Effort Estimation, Repository Foundation and Domain Core

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the effort estimation that governs project scope, scaffold the monorepo with automated quality gates, and build a fully tested, framework-free domain core containing the manuscript state machine, the hash-chained editorial event log, the authorisation policy layer and the double-blind projection.

**Architecture:** Hexagonal. This plan builds only the innermost hexagon — `backend/src/ugjcs/domain/` — which imports nothing from FastAPI, SQLAlchemy or any other framework. That constraint is mechanically enforced by an `import-linter` contract in CI, so the claim is verified rather than asserted. Every behaviour is driven out test-first.

**Tech Stack:** Python 3.13, `uv` for dependency management, pytest, Hypothesis, ruff, mypy (strict), import-linter, coverage.

## Global Constraints

- Python pinned to **3.13** (host runs 3.14, which is ahead of some scientific wheels).
- `backend/src/ugjcs/domain/` MUST NOT import `fastapi`, `sqlalchemy`, `pydantic`, `boto3`, `arq` or any I/O library. Standard library and `dataclasses` only.
- All timestamps are timezone-aware UTC (`datetime.now(UTC)`), never naive.
- Domain and application layers require **≥85% line coverage**; CI fails below.
- mypy runs in `strict` mode over `src/`; no `Any` escapes without an inline justification comment.
- Conventional Commits (`feat:`, `test:`, `docs:`, `chore:`, `refactor:`).
- Every file ends with a newline; ruff line length 100.
- The journal's canonical name is **UGJCS**; the Python package is `ugjcs`.
- Author: Roger Koranteng Obeng, student ID 22424140.

---

## File Structure

```
.
├── docs/
│   ├── 03-effort-estimation.md          Task 1
│   └── superpowers/{specs,plans}/
├── backend/
│   ├── pyproject.toml                   Task 2  deps, ruff, mypy, pytest, coverage config
│   ├── .python-version                  Task 2  pins 3.13
│   ├── Makefile                         Task 2  check target
│   ├── .importlinter                    Task 2  domain purity contract
│   ├── src/ugjcs/
│   │   ├── __init__.py                  Task 2
│   │   └── domain/
│   │       ├── __init__.py              Task 3
│   │       ├── errors.py                Task 3  domain exception hierarchy
│   │       ├── enums.py                 Task 3  Role, ManuscriptStatus, Recommendation, ...
│   │       ├── ids.py                   Task 3  typed identifiers, tracking codes
│   │       ├── transitions.py           Task 4  legal transition table + assert_legal
│   │       ├── events.py                Task 5  EditorialEvent + payload types
│   │       ├── hashchain.py             Task 6  canonical serialisation, chaining, verify
│   │       ├── manuscript.py            Task 7  Manuscript aggregate
│   │       ├── policies.py              Task 8  can(actor, action, resource)
│   │       └── blinding.py              Task 9  BlindedManuscript projection
│   └── tests/unit/domain/
│       ├── test_ids.py                  Task 3
│       ├── test_transitions.py          Task 4
│       ├── test_events.py               Task 5
│       ├── test_hashchain.py            Task 6
│       ├── test_manuscript.py           Task 7
│       ├── test_policies.py             Task 8
│       ├── test_blinding.py             Task 9
│       └── test_invariants.py           Task 10 Hypothesis property tests
└── .github/workflows/backend-ci.yml     Task 11
```

Files are split by responsibility rather than by type: the state machine table lives apart from the aggregate that consumes it, because the table is data that changes for policy reasons while the aggregate changes for behavioural reasons.

---

### Task 1: Effort estimation document

This task produces no code. It exists first because its output determines the MoSCoW cut for every subsequent plan, and because the assessment scheme awards 5 marks for it.

**Files:**
- Create: `docs/03-effort-estimation.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-08-12-ugjcs-journal-platform-design.md` §5.1 (the requirements table the use-case inventory is derived from).
- Produces: the ranked MoSCoW cut that Plans 2–6 treat as authoritative scope.

- [ ] **Step 1: Write the actor and use-case inventory**

Create `docs/03-effort-estimation.md` with the Use Case Points derivation. Actor weights follow Karner: Simple (another system through a defined API) = 1, Average (another system through a protocol, or a human through a text interface) = 2, Complex (a human through a graphical interface) = 3.

| Actor | Classification | Weight |
|---|---|---|
| Author | Complex — GUI | 3 |
| Reviewer | Complex — GUI | 3 |
| Editor | Complex — GUI | 3 |
| Editor-in-Chief | Complex — GUI | 3 |
| Administrator | Complex — GUI | 3 |
| Reader | Complex — GUI | 3 |
| Indexing service (OAI-PMH harvester) | Simple — defined API | 1 |
| **UAW** | | **19** |

Use case weights: Simple (≤3 transactions) = 5, Average (4–7) = 10, Complex (>7) = 15.

| # | Use case | FR | Class | Wt |
|---|---|---|---|---|
| UC1 | Register account | FR-01 | Average | 10 |
| UC2 | Authenticate and manage session | FR-02 | Average | 10 |
| UC3 | Manage roles | FR-03 | Simple | 5 |
| UC4 | Create submission | FR-04, FR-05 | Complex | 15 |
| UC5 | Process submission asynchronously | FR-06, FR-20 | Complex | 15 |
| UC6 | Screen submission | FR-07 | Average | 10 |
| UC7 | Recommend reviewers | FR-08 | Complex | 15 |
| UC8 | Invite and assign reviewers | FR-09 | Average | 10 |
| UC9 | Respond to review invitation | FR-10 | Simple | 5 |
| UC10 | Submit review | FR-11 | Average | 10 |
| UC11 | Record editorial decision | FR-12 | Average | 10 |
| UC12 | Submit revision | FR-13 | Average | 10 |
| UC13 | Track own submissions | FR-14 | Simple | 5 |
| UC14 | Compose and publish issue | FR-15 | Complex | 15 |
| UC15 | Browse archive | FR-16 | Simple | 5 |
| UC16 | Search papers | FR-17 | Average | 10 |
| UC17 | Download paper | FR-18 | Simple | 5 |
| UC18 | View audit trail | FR-19 | Simple | 5 |
| UC19 | Export citation | FR-21 | Simple | 5 |
| UC20 | Harvest metadata (OAI-PMH) | FR-22 | Complex | 15 |
| UC21 | Notify actors | FR-23 | Average | 10 |
| UC22 | View editorial analytics | FR-24 | Average | 10 |
| UC23 | Withdraw submission | FR-25 | Simple | 5 |
| UC24 | Configure journal policy | FR-26 | Simple | 5 |
| UC25 | Resolve persistent identifier | FR-27 | Simple | 5 |
| **UUCW** | | | **225** |

`UUCP = UAW + UUCW = 19 + 225 = 244`

- [ ] **Step 2: Write the technical and environmental factor tables**

| | Technical factor | Wt | Rating | Product | Justification |
|---|---|---|---|---|---|
| T1 | Distributed system | 2 | 4 | 8.0 | ECS, RDS, S3, Redis, CloudFront, Vercel |
| T2 | Performance objectives | 1 | 4 | 4.0 | p95 targets in NFR-08, NFR-09 |
| T3 | End-user efficiency | 1 | 3 | 3.0 | Editorial queues optimised for throughput |
| T4 | Complex internal processing | 1 | 5 | 5.0 | Hungarian assignment, MinHash LSH, hash chain |
| T5 | Reusability | 1 | 3 | 3.0 | Hexagonal seams; multi-journal deferred |
| T6 | Ease of installation | 0.5 | 3 | 1.5 | Terraform reproducible |
| T7 | Ease of use | 0.5 | 4 | 2.0 | Public archive serves non-technical readers |
| T8 | Portability | 2 | 3 | 6.0 | Containerised; adapters isolate vendors |
| T9 | Ease of change | 1 | 4 | 4.0 | Hexagonal architecture is the point |
| T10 | Concurrency | 1 | 4 | 4.0 | Async API plus worker pool |
| T11 | Special security objectives | 1 | 5 | 5.0 | Double-blind, RBAC, tamper-evident audit |
| T12 | Third-party direct access | 1 | 4 | 4.0 | OAI-PMH harvesting |
| T13 | User training facilities | 1 | 1 | 1.0 | User manual only |
| | **TFactor** | | | **50.5** | |

`TCF = 0.6 + (0.01 × 50.5) = 1.105`

| | Environmental factor | Wt | Rating | Product | Justification |
|---|---|---|---|---|---|
| E1 | Familiarity with process | 1.5 | 4 | 6.0 | Lifecycle taught this semester |
| E2 | Application experience | 0.5 | 3 | 1.5 | Scholarly publishing newly studied |
| E3 | Object-oriented experience | 1 | 4 | 4.0 | Strong |
| E4 | Lead analyst capability | 0.5 | 4 | 2.0 | Sole analyst |
| E5 | Motivation | 1 | 5 | 5.0 | Assessed capstone |
| E6 | Stable requirements | 2 | 5 | 10.0 | Self-defined and frozen at spec sign-off |
| E7 | Part-time staff | −1 | 0 | 0.0 | None |
| E8 | Difficult programming language | −1 | 2 | −2.0 | Python and TypeScript are familiar |
| | **EFactor** | | | **26.5** | |

`ECF = 1.4 + (−0.03 × 26.5) = 0.605`

- [ ] **Step 3: Compute and record the estimate**

```
UCP        = UUCP × TCF × ECF = 244 × 1.105 × 0.605 = 163.1
Effort     = UCP × PF         = 163.1 × 20 = 3,262 person-hours
                              ≈ 21.5 person-months (at 152 h/month)
                              ≈ 1.8 person-years
```

Karner's productivity factor of 20 h/UCP applies because the E1–E6 count below 3 plus the E7–E8 count above 3 equals zero, which is the documented condition for PF = 20.

Repeat the calculation for the Must-have subset (UC1–UC18, and the Simple indexing actor excluded): `UAW = 18`, `UUCW = 170`, `UUCP = 188`, `UCP = 125.7`, effort **2,514 person-hours**.

- [ ] **Step 4: Write the COCOMO II Early Design cross-check**

```
Size  = 12 KSLOC   (backend ~6, frontend ~5, infrastructure ~1)
Scale factors: PREC 3.72, FLEX 2.03, RESL 2.83, TEAM 1.10, PMAT 4.68  → ΣSF = 14.36
E     = 0.91 + 0.01 × 14.36 = 1.0536
Effort multipliers: RCPX 1.33, RUSE 1.00, PDIF 1.29, PERS 0.63,
                    PREX 0.87, FCIL 0.87, SCED 1.43              → ∏EM = 1.1699
PM    = 2.94 × 12^1.0536 × 1.1699 = 47.2 person-months ≈ 7,170 person-hours
```

Record the reconciliation explicitly: the two methods differ by roughly 2.2×. COCOMO II is calibrated on projects carrying formal verification, configuration management and management overhead that this project does not incur, and its `SCED = 1.43` penalty for extreme schedule compression compounds with high `RCPX` and `PDIF`. UCP counts externally visible transactions and is blind to platform work, which this project has a great deal of. Both bound the answer from the same side: **the full system is a one-to-four person-year effort.**

- [ ] **Step 5: Write the scope decision and the productivity reconciliation**

State the consequence plainly: 48 hours is 1.5% of the lower (UCP) estimate. Therefore the estimate governs scope in two ways.

First, the MoSCoW cut. Record this table as the authoritative scope for Plans 2–6:

| Priority | Use cases | Decision |
|---|---|---|
| Must | UC1–UC18 | Implemented to production quality |
| Should | UC19–UC23 | Implemented only if Plans 2–5 complete early |
| Could | UC24, UC25 | Deferred; entered in the technical debt register |

Second, the productivity reconciliation. The realised effort will be a small fraction of 2,514 hours because development is AI-assisted, which is a change of *method*, not merely of *pace*. Record that the productivity factor is a calibration parameter and must be re-derived whenever the method changes; report the locally realised PF once the build completes; note the sample size of one and that it does not generalise; and identify where the shortfall is repaid rather than eliminated — test depth below what 2,514 hours would buy, documentation formality, and security hardening. Cross-reference each of those to its entry in the technical debt register.

Acknowledge AI-assisted development here and in the references section, consistent with the requirement to acknowledge all external resources and tools.

- [ ] **Step 6: Record the assumptions, constraints and variance placeholder**

List the assumptions the estimate rests on (single developer; requirements frozen at spec sign-off; 12 KSLOC size estimate; managed AWS services rather than self-hosted equivalents; synthetic seed data) and the constraints (48-hour window; no registered domain; solo developer so `TEAM` is Very High and `E7` is zero).

Add a section headed "Estimated versus actual" that states the method now and is completed at the end of the project: actual hours per phase from the commit history, realised PF, the variance percentage, and an analysis of which factors were mis-rated with hindsight.

- [ ] **Step 7: Commit**

```bash
git add docs/03-effort-estimation.md
git commit -m "docs: effort estimation by Use Case Points with COCOMO II cross-check"
```

---

### Task 2: Backend scaffold with enforced quality gates

**Files:**
- Create: `backend/pyproject.toml`, `backend/.python-version`, `backend/.importlinter`, `backend/Makefile`, `backend/src/ugjcs/__init__.py`, `backend/src/ugjcs/domain/__init__.py`, `backend/tests/__init__.py`, `backend/tests/unit/__init__.py`, `backend/tests/unit/domain/__init__.py`

**Interfaces:**
- Produces: `make check` — the single command every later task runs before committing. It executes ruff, mypy strict, import-linter and pytest with coverage.

- [ ] **Step 1: Pin the interpreter and create the project**

```bash
cd backend
echo "3.13" > .python-version
uv init --bare --python 3.13
uv add --dev pytest pytest-cov hypothesis ruff mypy import-linter
```

- [ ] **Step 2: Write `pyproject.toml` configuration**

Append to `backend/pyproject.toml`:

```toml
[project]
name = "ugjcs"
version = "0.1.0"
requires-python = ">=3.13,<3.14"

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "A", "C4", "SIM", "RUF"]

[tool.mypy]
python_version = "3.13"
strict = true
files = ["src", "tests"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"

[tool.coverage.run]
source = ["src/ugjcs"]
branch = true

[tool.coverage.report]
fail_under = 85
show_missing = true

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ugjcs"]
```

- [ ] **Step 3: Write the domain purity contract**

Create `backend/.importlinter`:

```ini
[importlinter]
root_package = ugjcs

[importlinter:contract:domain-purity]
name = Domain layer imports no frameworks or I/O libraries
type = forbidden
source_modules = ugjcs.domain
forbidden_modules =
    fastapi
    sqlalchemy
    pydantic
    boto3
    arq
    redis
    httpx
```

- [ ] **Step 4: Write the Makefile**

Create `backend/Makefile`:

```make
.PHONY: check fmt test
fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests

check:
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy
	uv run lint-imports
	uv run pytest --cov --cov-report=term-missing

test:
	uv run pytest -q
```

- [ ] **Step 5: Create the package files**

Create empty `__init__.py` in `src/ugjcs/`, `src/ugjcs/domain/`, `tests/`, `tests/unit/`, `tests/unit/domain/`.

- [ ] **Step 6: Verify the gates run**

Run: `cd backend && make check`
Expected: ruff and mypy pass; import-linter reports the contract as KEPT; pytest reports no tests collected and coverage fails with "No data to report" or fails under 85. A coverage failure at this point is expected and is resolved by Task 3, which adds the first covered code. Confirm ruff, mypy and lint-imports specifically all pass.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "chore: scaffold backend with ruff, mypy strict, import-linter and coverage gates"
```

---

### Task 3: Domain primitives — errors, enums, identifiers

**Files:**
- Create: `backend/src/ugjcs/domain/errors.py`, `backend/src/ugjcs/domain/enums.py`, `backend/src/ugjcs/domain/ids.py`
- Test: `backend/tests/unit/domain/test_ids.py`

**Interfaces:**
- Produces:
  - `DomainError`, `IllegalTransitionError`, `GuardViolationError`, `AuthorizationDeniedError` (all in `errors.py`)
  - `Role`, `ManuscriptStatus`, `Recommendation`, `DecisionType`, `AssignmentStatus`, `EventType` (all `StrEnum`, in `enums.py`)
  - `UserId`, `ManuscriptId`, `ReviewId`, `IssueId` (`NewType` over `UUID`); `TrackingCode` with `TrackingCode.mint(year: int, sequence: int) -> TrackingCode` and `.value: str`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_ids.py`:

```python
import pytest

from ugjcs.domain.ids import TrackingCode


def test_tracking_code_formats_year_and_zero_padded_sequence() -> None:
    assert TrackingCode.mint(2026, 42).value == "UGJCS-2026-0042"


def test_tracking_code_pads_to_four_digits() -> None:
    assert TrackingCode.mint(2026, 7).value == "UGJCS-2026-0007"


def test_tracking_code_accepts_sequences_beyond_four_digits() -> None:
    assert TrackingCode.mint(2026, 12345).value == "UGJCS-2026-12345"


@pytest.mark.parametrize("sequence", [0, -1])
def test_tracking_code_rejects_non_positive_sequence(sequence: int) -> None:
    with pytest.raises(ValueError, match="sequence must be positive"):
        TrackingCode.mint(2026, sequence)


def test_tracking_code_parses_its_own_output() -> None:
    minted = TrackingCode.mint(2026, 42)
    assert TrackingCode.parse(minted.value) == minted


def test_tracking_code_rejects_malformed_input() -> None:
    with pytest.raises(ValueError, match="malformed tracking code"):
        TrackingCode.parse("UGJCS/2026/42")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_ids.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.domain.ids'`

- [ ] **Step 3: Write `errors.py`**

```python
"""Domain-level exceptions.

These carry no HTTP or framework semantics; adapters translate them at the boundary.
"""


class DomainError(Exception):
    """Base class for every domain rule violation."""


class IllegalTransitionError(DomainError):
    """A manuscript state transition that the lifecycle does not permit."""


class GuardViolationError(DomainError):
    """A transition is structurally legal but its precondition is unmet."""


class AuthorizationDeniedError(DomainError):
    """The actor may not perform this action on this resource."""
```

- [ ] **Step 4: Write `enums.py`**

```python
"""Closed vocabularies of the editorial domain."""

from enum import StrEnum


class Role(StrEnum):
    AUTHOR = "author"
    REVIEWER = "reviewer"
    EDITOR = "editor"
    EDITOR_IN_CHIEF = "editor_in_chief"
    ADMINISTRATOR = "administrator"


class ManuscriptStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_SCREENING = "under_screening"
    DESK_REJECTED = "desk_rejected"
    UNDER_REVIEW = "under_review"
    REVIEWS_COMPLETE = "reviews_complete"
    REVISION_REQUESTED = "revision_requested"
    RESUBMITTED = "resubmitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class Recommendation(StrEnum):
    ACCEPT = "accept"
    MINOR_REVISION = "minor_revision"
    MAJOR_REVISION = "major_revision"
    REJECT = "reject"


class DecisionType(StrEnum):
    DESK_REJECT = "desk_reject"
    SEND_TO_REVIEW = "send_to_review"
    REQUEST_REVISION = "request_revision"
    ACCEPT = "accept"
    REJECT = "reject"


class AssignmentStatus(StrEnum):
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


class EventType(StrEnum):
    MANUSCRIPT_SUBMITTED = "manuscript_submitted"
    SCREENING_STARTED = "screening_started"
    REVIEWER_ASSIGNED = "reviewer_assigned"
    INVITATION_ANSWERED = "invitation_answered"
    REVIEW_SUBMITTED = "review_submitted"
    REVIEW_ROUND_CLOSED = "review_round_closed"
    DECISION_RECORDED = "decision_recorded"
    REVISION_SUBMITTED = "revision_submitted"
    MANUSCRIPT_WITHDRAWN = "manuscript_withdrawn"
    SCHEDULED_FOR_ISSUE = "scheduled_for_issue"
    MANUSCRIPT_PUBLISHED = "manuscript_published"
```

- [ ] **Step 5: Write `ids.py`**

```python
"""Typed identifiers.

`NewType` gives compile-time separation between identifier kinds at zero runtime cost,
so a `UserId` can never be passed where a `ManuscriptId` is expected.
"""

import re
from dataclasses import dataclass
from typing import NewType, Self
from uuid import UUID

UserId = NewType("UserId", UUID)
ManuscriptId = NewType("ManuscriptId", UUID)
ReviewId = NewType("ReviewId", UUID)
IssueId = NewType("IssueId", UUID)

_TRACKING_PATTERN = re.compile(r"^UGJCS-(\d{4})-(\d{4,})$")


@dataclass(frozen=True, slots=True)
class TrackingCode:
    """The human-facing reference an author quotes in correspondence."""

    value: str

    @classmethod
    def mint(cls, year: int, sequence: int) -> Self:
        if sequence <= 0:
            raise ValueError("sequence must be positive")
        return cls(f"UGJCS-{year:04d}-{sequence:04d}")

    @classmethod
    def parse(cls, raw: str) -> Self:
        if not _TRACKING_PATTERN.match(raw):
            raise ValueError(f"malformed tracking code: {raw!r}")
        return cls(raw)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_ids.py -v`
Expected: PASS — 7 tests.

- [ ] **Step 7: Run the full gate**

Run: `cd backend && make check`
Expected: ruff, mypy, import-linter pass. Coverage may still fail below 85 because `enums.py` and `errors.py` have no direct tests; that is acceptable at this task and is resolved by Task 4. Confirm no lint or type errors.

- [ ] **Step 8: Commit**

```bash
git add backend/src/ugjcs/domain backend/tests/unit/domain/test_ids.py
git commit -m "feat: add domain primitives — errors, enums and typed identifiers"
```

---

### Task 4: Manuscript state machine

**Files:**
- Create: `backend/src/ugjcs/domain/transitions.py`
- Test: `backend/tests/unit/domain/test_transitions.py`

**Interfaces:**
- Consumes: `ManuscriptStatus` from `enums.py`; `IllegalTransitionError` from `errors.py`.
- Produces:
  - `TERMINAL_STATES: frozenset[ManuscriptStatus]`
  - `LEGAL_TRANSITIONS: Mapping[ManuscriptStatus, frozenset[ManuscriptStatus]]`
  - `is_legal(source: ManuscriptStatus, target: ManuscriptStatus) -> bool`
  - `assert_legal(source: ManuscriptStatus, target: ManuscriptStatus) -> None` raising `IllegalTransitionError`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_transitions.py`:

```python
import pytest

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.errors import IllegalTransitionError
from ugjcs.domain.transitions import (
    LEGAL_TRANSITIONS,
    TERMINAL_STATES,
    assert_legal,
    is_legal,
)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (S.DRAFT, S.SUBMITTED),
        (S.SUBMITTED, S.UNDER_SCREENING),
        (S.UNDER_SCREENING, S.DESK_REJECTED),
        (S.UNDER_SCREENING, S.UNDER_REVIEW),
        (S.UNDER_SCREENING, S.REVISION_REQUESTED),
        (S.UNDER_REVIEW, S.REVIEWS_COMPLETE),
        (S.REVIEWS_COMPLETE, S.ACCEPTED),
        (S.REVIEWS_COMPLETE, S.REJECTED),
        (S.REVIEWS_COMPLETE, S.REVISION_REQUESTED),
        (S.REVISION_REQUESTED, S.RESUBMITTED),
        (S.RESUBMITTED, S.UNDER_REVIEW),
        (S.ACCEPTED, S.SCHEDULED),
        (S.SCHEDULED, S.PUBLISHED),
        (S.SUBMITTED, S.WITHDRAWN),
        (S.UNDER_REVIEW, S.WITHDRAWN),
    ],
)
def test_lifecycle_permits_expected_transitions(source: S, target: S) -> None:
    assert is_legal(source, target)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (S.DRAFT, S.PUBLISHED),
        (S.SUBMITTED, S.ACCEPTED),
        (S.UNDER_SCREENING, S.PUBLISHED),
        (S.UNDER_REVIEW, S.ACCEPTED),
        (S.ACCEPTED, S.PUBLISHED),
        (S.REJECTED, S.ACCEPTED),
        (S.DRAFT, S.DRAFT),
    ],
)
def test_lifecycle_forbids_shortcut_transitions(source: S, target: S) -> None:
    assert not is_legal(source, target)


@pytest.mark.parametrize("terminal", sorted(TERMINAL_STATES))
def test_terminal_states_have_no_outgoing_transitions(terminal: S) -> None:
    assert LEGAL_TRANSITIONS[terminal] == frozenset()


def test_every_status_appears_in_the_table() -> None:
    assert set(LEGAL_TRANSITIONS) == set(S)


def test_assert_legal_is_silent_for_a_legal_transition() -> None:
    assert_legal(S.DRAFT, S.SUBMITTED)


def test_assert_legal_raises_naming_both_states() -> None:
    with pytest.raises(IllegalTransitionError, match=r"draft.*published"):
        assert_legal(S.DRAFT, S.PUBLISHED)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_transitions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.domain.transitions'`

- [ ] **Step 3: Write the implementation**

Create `backend/src/ugjcs/domain/transitions.py`:

```python
"""The manuscript lifecycle, expressed as data rather than as branching code.

Keeping the table separate from the aggregate means editorial policy can change
without touching aggregate behaviour, and the table can be exhaustively tested.
"""

from collections.abc import Mapping

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.errors import IllegalTransitionError

TERMINAL_STATES: frozenset[S] = frozenset(
    {S.DESK_REJECTED, S.REJECTED, S.PUBLISHED, S.WITHDRAWN}
)

_WITHDRAWABLE_FROM = (
    S.SUBMITTED,
    S.UNDER_SCREENING,
    S.UNDER_REVIEW,
    S.REVIEWS_COMPLETE,
    S.REVISION_REQUESTED,
)

LEGAL_TRANSITIONS: Mapping[S, frozenset[S]] = {
    S.DRAFT: frozenset({S.SUBMITTED}),
    S.SUBMITTED: frozenset({S.UNDER_SCREENING, S.WITHDRAWN}),
    S.UNDER_SCREENING: frozenset(
        {S.DESK_REJECTED, S.UNDER_REVIEW, S.REVISION_REQUESTED, S.WITHDRAWN}
    ),
    S.UNDER_REVIEW: frozenset({S.REVIEWS_COMPLETE, S.WITHDRAWN}),
    S.REVIEWS_COMPLETE: frozenset(
        {S.ACCEPTED, S.REJECTED, S.REVISION_REQUESTED, S.WITHDRAWN}
    ),
    S.REVISION_REQUESTED: frozenset({S.RESUBMITTED, S.WITHDRAWN}),
    S.RESUBMITTED: frozenset({S.UNDER_REVIEW, S.UNDER_SCREENING}),
    S.ACCEPTED: frozenset({S.SCHEDULED}),
    S.SCHEDULED: frozenset({S.PUBLISHED}),
    S.DESK_REJECTED: frozenset(),
    S.REJECTED: frozenset(),
    S.PUBLISHED: frozenset(),
    S.WITHDRAWN: frozenset(),
}


def is_legal(source: S, target: S) -> bool:
    """Whether the lifecycle permits moving from `source` to `target`."""
    return target in LEGAL_TRANSITIONS[source]


def assert_legal(source: S, target: S) -> None:
    """Raise `IllegalTransitionError` unless the move is permitted."""
    if not is_legal(source, target):
        raise IllegalTransitionError(
            f"cannot move manuscript from {source.value} to {target.value}"
        )
```

Note that `_WITHDRAWABLE_FROM` documents the withdrawal policy from the spec; it is asserted against the table by Task 10's property tests rather than being used to build the table, so that the table stays readable as a single literal.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_transitions.py -v`
Expected: PASS — all parametrised cases green.

- [ ] **Step 5: Run the full gate**

Run: `cd backend && make check`
Expected: all gates pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/ugjcs/domain/transitions.py backend/tests/unit/domain/test_transitions.py
git commit -m "feat: add guarded manuscript lifecycle state machine"
```

---

### Task 5: Editorial events

**Files:**
- Create: `backend/src/ugjcs/domain/events.py`
- Test: `backend/tests/unit/domain/test_events.py`

**Interfaces:**
- Consumes: `EventType` from `enums.py`; `ManuscriptId`, `UserId` from `ids.py`.
- Produces: `EditorialEvent` frozen dataclass with fields `manuscript_id: ManuscriptId`, `sequence: int`, `event_type: EventType`, `payload: Mapping[str, PayloadValue]`, `actor_id: UserId | None`, `occurred_at: datetime`, and method `canonical_bytes() -> bytes`. Also exports `type PayloadValue = str | int | float | bool | None`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_events.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ugjcs.domain.enums import EventType
from ugjcs.domain.events import EditorialEvent
from ugjcs.domain.ids import ManuscriptId, UserId


# Identity is pinned at module level: canonical_bytes() covers the identity fields as
# well as the payload, so a fixture that minted fresh UUIDs per call would make every
# event differ regardless of payload key order, and the determinism test would be vacuous.
MANUSCRIPT = ManuscriptId(uuid4())
ACTOR = UserId(uuid4())


def make_event(**overrides: object) -> EditorialEvent:
    defaults: dict[str, object] = {
        "manuscript_id": MANUSCRIPT,
        "sequence": 1,
        "event_type": EventType.MANUSCRIPT_SUBMITTED,
        "payload": {"title": "On Kente Pattern Recognition"},
        "actor_id": ACTOR,
        "occurred_at": datetime(2026, 8, 12, 9, 30, tzinfo=UTC),
    }
    return EditorialEvent(**(defaults | overrides))  # type: ignore[arg-type]


def test_event_is_immutable() -> None:
    event = make_event()
    with pytest.raises(AttributeError):
        event.sequence = 2  # type: ignore[misc]


def test_sequence_must_be_positive() -> None:
    with pytest.raises(ValueError, match="sequence must be positive"):
        make_event(sequence=0)


def test_occurred_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="occurred_at must be timezone-aware"):
        make_event(occurred_at=datetime(2026, 8, 12, 9, 30))


def test_canonical_bytes_are_stable_across_key_order() -> None:
    a = make_event(payload={"alpha": 1, "beta": 2})
    b = make_event(payload={"beta": 2, "alpha": 1})
    assert a.canonical_bytes() == b.canonical_bytes()


def test_canonical_bytes_change_when_payload_changes() -> None:
    a = make_event(payload={"alpha": 1})
    b = make_event(payload={"alpha": 2})
    assert a.canonical_bytes() != b.canonical_bytes()


def test_canonical_bytes_refuses_a_value_it_cannot_serialise_stably() -> None:
    """A set's str() follows iteration order, which varies with the process hash seed.

    Serialising it would produce different bytes for the same event in a different
    process, so the chain would report tampering that never happened. Refusing loudly
    is the only safe behaviour.
    """
    event = make_event(payload={"tags": {"a", "b"}})
    with pytest.raises(TypeError):
        event.canonical_bytes()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_events.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.domain.events'`

- [ ] **Step 3: Write the implementation**

Create `backend/src/ugjcs/domain/events.py`:

```python
"""Editorial events — the append-only record of everything that happened.

Canonical serialisation is separated from hashing so that the byte representation
is testable on its own and stays stable if the hash algorithm is ever replaced.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from ugjcs.domain.enums import EventType
from ugjcs.domain.ids import ManuscriptId, UserId

type PayloadValue = str | int | float | bool | None
"""Payload values are restricted to JSON-native scalars.

The hash chain in `hashchain.py` is only tamper-evident if equal events always
serialise to equal bytes. A `set` would serialise through its iteration order, which
varies with Python's per-process hash seed; an arbitrary object would fall back to a
`repr` containing a memory address. Either would make an untampered event fail
verification in a different process, which is a false tamper alert — worse than no
check at all. Restricting the type makes that unrepresentable.
"""


@dataclass(frozen=True, slots=True)
class EditorialEvent:
    manuscript_id: ManuscriptId
    sequence: int
    event_type: EventType
    payload: Mapping[str, PayloadValue]
    actor_id: UserId | None
    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise ValueError("sequence must be positive")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")

    def canonical_bytes(self) -> bytes:
        """A byte representation that is identical for equal events.

        Sorted keys and fixed separators make the encoding independent of dictionary
        insertion order, which is what allows the hash chain to be reproducible.
        """
        document = {
            "manuscript_id": str(self.manuscript_id),
            "sequence": self.sequence,
            "event_type": self.event_type.value,
            "payload": dict(self.payload),
            "actor_id": str(self.actor_id) if self.actor_id is not None else None,
            "occurred_at": self.occurred_at.isoformat(),
        }
        return json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_events.py -v`
Expected: PASS — 5 tests.

- [ ] **Step 5: Run the full gate**

Run: `cd backend && make check`
Expected: all gates pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/ugjcs/domain/events.py backend/tests/unit/domain/test_events.py
git commit -m "feat: add editorial event with canonical serialisation"
```

---

### Task 6: Tamper-evident hash chain

**Files:**
- Create: `backend/src/ugjcs/domain/hashchain.py`
- Test: `backend/tests/unit/domain/test_hashchain.py`

**Interfaces:**
- Consumes: `EditorialEvent` from `events.py`.
- Produces:
  - `GENESIS_HASH: str` — 64 zero characters
  - `chain_hash(event: EditorialEvent, previous_hash: str) -> str`
  - `ChainedEvent` frozen dataclass wrapping `event: EditorialEvent`, `previous_hash: str`, `event_hash: str`
  - `append(chain: Sequence[ChainedEvent], event: EditorialEvent) -> ChainedEvent`
  - `verify(chain: Sequence[ChainedEvent]) -> None` raising `ChainBrokenError` (a `DomainError` subclass defined in this module)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_hashchain.py`:

```python
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ugjcs.domain.enums import EventType
from ugjcs.domain.events import EditorialEvent, PayloadValue
from ugjcs.domain.hashchain import (
    GENESIS_HASH,
    ChainBrokenError,
    ChainedEvent,
    append,
    chain_hash,
    verify,
)
from ugjcs.domain.ids import ManuscriptId, UserId

MANUSCRIPT = ManuscriptId(uuid4())


def event(sequence: int, **payload: PayloadValue) -> EditorialEvent:
    return EditorialEvent(
        manuscript_id=MANUSCRIPT,
        sequence=sequence,
        event_type=EventType.DECISION_RECORDED,
        payload=payload or {"note": "ok"},
        actor_id=UserId(uuid4()),
        occurred_at=datetime(2026, 8, 12, 10, sequence, tzinfo=UTC),
    )


def build_chain(length: int) -> list[ChainedEvent]:
    chain: list[ChainedEvent] = []
    for sequence in range(1, length + 1):
        chain.append(append(chain, event(sequence)))
    return chain


def test_hash_is_sixty_four_hex_characters() -> None:
    digest = chain_hash(event(1), GENESIS_HASH)
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


def test_first_event_chains_from_genesis() -> None:
    chain = build_chain(1)
    assert chain[0].previous_hash == GENESIS_HASH


def test_each_event_chains_to_its_predecessor() -> None:
    chain = build_chain(3)
    assert chain[1].previous_hash == chain[0].event_hash
    assert chain[2].previous_hash == chain[1].event_hash


def test_identical_payloads_at_different_positions_hash_differently() -> None:
    chain = build_chain(2)
    assert chain[0].event_hash != chain[1].event_hash


def test_verify_accepts_an_untampered_chain() -> None:
    verify(build_chain(4))


def test_verify_accepts_an_empty_chain() -> None:
    verify([])


def test_verify_detects_a_modified_payload() -> None:
    chain = build_chain(3)
    chain[1] = replace(chain[1], event=event(2, note="tampered"))
    with pytest.raises(ChainBrokenError, match="sequence 2"):
        verify(chain)


def test_verify_detects_a_removed_event() -> None:
    chain = build_chain(3)
    del chain[1]
    with pytest.raises(ChainBrokenError):
        verify(chain)


def test_verify_detects_a_spliced_chain() -> None:
    """Two internally consistent chains joined together must not verify.

    Every link here reconciles with its own recorded predecessor hash, so the payload
    and sequence checks both pass. Only the link-to-predecessor check catches it. This
    is the splice attack: take a real prefix, graft a different history onto it.
    """
    original = build_chain(2)
    forged = build_chain(2)
    spliced = [original[0], forged[1]]
    with pytest.raises(ChainBrokenError, match="broken link at sequence 2"):
        verify(spliced)


def test_append_rejects_a_non_consecutive_sequence() -> None:
    chain = build_chain(1)
    with pytest.raises(ChainBrokenError, match="expected sequence 2"):
        append(chain, event(5))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_hashchain.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.domain.hashchain'`

- [ ] **Step 3: Write the implementation**

Create `backend/src/ugjcs/domain/hashchain.py`:

```python
"""Tamper-evident chaining over the editorial event log.

Each event's hash covers its predecessor's hash, so altering, reordering or removing an
event in the interior of the chain invalidates every hash after it. This detects
tampering; it does not prevent it, which is why the database also denies UPDATE and
DELETE on the event table.

What this construction cannot detect on its own, stated plainly so no caller assumes
more than it provides:

- Truncation of the tail. Any prefix of a valid chain is itself a valid chain.
- A forged event appended through `append`, which is indistinguishable from a genuine one.
- A wholly fabricated history rebuilt from the genesis hash using these same functions.

All three need an external anchor the forger cannot reproduce: a periodically published
or signed checkpoint of the latest `event_hash`, plus an expected event count asserted at
the persistence boundary. That anchor is out of scope for the domain layer and is
recorded in the technical debt register.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from ugjcs.domain.errors import DomainError
from ugjcs.domain.events import EditorialEvent

GENESIS_HASH = "0" * 64


class ChainBrokenError(DomainError):
    """The event chain does not verify against its recorded hashes."""


@dataclass(frozen=True, slots=True)
class ChainedEvent:
    event: EditorialEvent
    previous_hash: str
    event_hash: str


def chain_hash(event: EditorialEvent, previous_hash: str) -> str:
    """SHA-256 over the predecessor hash followed by the event's canonical bytes."""
    digest = hashlib.sha256()
    digest.update(previous_hash.encode("ascii"))
    digest.update(event.canonical_bytes())
    return digest.hexdigest()


def append(chain: Sequence[ChainedEvent], event: EditorialEvent) -> ChainedEvent:
    """Link `event` onto the end of `chain`, enforcing consecutive sequencing."""
    expected_sequence = len(chain) + 1
    if event.sequence != expected_sequence:
        raise ChainBrokenError(
            f"expected sequence {expected_sequence}, received {event.sequence}"
        )
    previous_hash = chain[-1].event_hash if chain else GENESIS_HASH
    return ChainedEvent(
        event=event,
        previous_hash=previous_hash,
        event_hash=chain_hash(event, previous_hash),
    )


def verify(chain: Sequence[ChainedEvent]) -> None:
    """Raise `ChainBrokenError` at the first link that does not reconcile."""
    previous_hash = GENESIS_HASH
    for position, link in enumerate(chain, start=1):
        if link.event.sequence != position:
            raise ChainBrokenError(
                f"expected sequence {position}, found {link.event.sequence}"
            )
        if link.previous_hash != previous_hash:
            raise ChainBrokenError(f"broken link at sequence {link.event.sequence}")
        if chain_hash(link.event, previous_hash) != link.event_hash:
            raise ChainBrokenError(f"hash mismatch at sequence {link.event.sequence}")
        previous_hash = link.event_hash
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_hashchain.py -v`
Expected: PASS — 9 tests.

- [ ] **Step 5: Run the full gate**

Run: `cd backend && make check`
Expected: all gates pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/ugjcs/domain/hashchain.py backend/tests/unit/domain/test_hashchain.py
git commit -m "feat: add tamper-evident hash chain over editorial events"
```

---

### Task 7: Manuscript aggregate

**Files:**
- Create: `backend/src/ugjcs/domain/manuscript.py`
- Test: `backend/tests/unit/domain/test_manuscript.py`

**Interfaces:**
- Consumes: `assert_legal` from `transitions.py`; `EditorialEvent` from `events.py`; enums, ids and errors.
- Produces: `Manuscript` with fields `id`, `tracking_code`, `title`, `abstract`, `keywords`, `author_ids`, `corresponding_author_id`, `status`, `version`, `minimum_reviews`, `submitted_reviews`, `issue_id`, and mutating methods `submit`, `begin_screening`, `record_review`, `record_decision`, `resubmit`, `schedule`, `publish`, `withdraw`, each returning the `EditorialEvent` it emitted. `pending_events` accumulates emitted events; `pull_events()` drains them.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_manuscript.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ugjcs.domain.enums import DecisionType, EventType, ManuscriptStatus as S
from ugjcs.domain.errors import GuardViolationError, IllegalTransitionError
from ugjcs.domain.ids import IssueId, ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript

AUTHOR = UserId(uuid4())
EDITOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 11, 0, tzinfo=UTC)


def status_of(manuscript: Manuscript) -> S:
    """Read status through a call so mypy cannot narrow the attribute in place.

    Asserting `manuscript.status is S.X` inline narrows the attribute to that literal for
    the rest of the function. mypy cannot see that a later method call mutates it, so a
    second assertion against a different status is rejected as a non-overlapping identity
    check. Reading through a call yields a fresh `S` each time.
    """
    return manuscript.status


def draft() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 1),
        title="Adinkra Symbol Classification with Vision Transformers",
        abstract="We evaluate transformer architectures on Adinkra symbol recognition.",
        keywords=("computer vision", "cultural heritage"),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


def submitted() -> Manuscript:
    manuscript = draft()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    return manuscript


def under_review() -> Manuscript:
    manuscript = submitted()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="In scope",
        occurred_at=NOW,
    )
    return manuscript


def test_new_manuscript_starts_in_draft() -> None:
    assert draft().status is S.DRAFT


def test_submit_moves_to_submitted_and_emits_an_event() -> None:
    manuscript = draft()
    event = manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    assert manuscript.status is S.SUBMITTED
    assert event.event_type is EventType.MANUSCRIPT_SUBMITTED
    assert event.sequence == 1


def test_events_are_sequenced_consecutively() -> None:
    manuscript = submitted()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    assert [event.sequence for event in manuscript.pending_events] == [1, 2]


def test_pull_events_drains_the_buffer() -> None:
    manuscript = submitted()
    assert len(manuscript.pull_events()) == 1
    assert manuscript.pending_events == ()


def test_cannot_submit_twice() -> None:
    manuscript = submitted()
    with pytest.raises(IllegalTransitionError):
        manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)


def test_desk_rejection_requires_no_reviews() -> None:
    manuscript = submitted()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.DESK_REJECT, actor_id=EDITOR,
        rationale="Out of scope", occurred_at=NOW,
    )
    assert manuscript.status is S.DESK_REJECTED


def test_desk_rejection_is_illegal_once_under_review() -> None:
    manuscript = under_review()
    with pytest.raises(IllegalTransitionError):
        manuscript.record_decision(
            decision=DecisionType.DESK_REJECT, actor_id=EDITOR,
            rationale="Too late", occurred_at=NOW,
        )


def test_acceptance_requires_the_minimum_review_count() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    with pytest.raises(GuardViolationError, match="requires 2 reviews, has 1"):
        manuscript.record_decision(
            decision=DecisionType.ACCEPT, actor_id=EDITOR,
            rationale="Strong", occurred_at=NOW,
        )


def test_review_quorum_closes_the_review_round() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    assert status_of(manuscript) is S.UNDER_REVIEW
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    assert status_of(manuscript) is S.REVIEWS_COMPLETE


def test_acceptance_succeeds_once_the_minimum_is_met() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.ACCEPT, actor_id=EDITOR,
        rationale="Strong contribution", occurred_at=NOW,
    )
    assert manuscript.status is S.ACCEPTED


def test_only_the_corresponding_author_may_resubmit() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.REQUEST_REVISION, actor_id=EDITOR,
        rationale="Clarify method", occurred_at=NOW,
    )
    with pytest.raises(GuardViolationError, match="corresponding author"):
        manuscript.resubmit(actor_id=UserId(uuid4()), occurred_at=NOW)


def test_resubmission_increments_the_version_and_resets_review_count() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.REQUEST_REVISION, actor_id=EDITOR,
        rationale="Clarify method", occurred_at=NOW,
    )
    manuscript.resubmit(actor_id=AUTHOR, occurred_at=NOW)
    assert manuscript.version == 2
    assert manuscript.submitted_reviews == 0


def test_publication_requires_an_issue() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.ACCEPT, actor_id=EDITOR,
        rationale="Strong", occurred_at=NOW,
    )
    with pytest.raises(IllegalTransitionError):
        manuscript.publish(actor_id=EDITOR, occurred_at=NOW)


def test_withdrawal_is_permitted_before_a_decision() -> None:
    manuscript = under_review()
    manuscript.withdraw(actor_id=AUTHOR, occurred_at=NOW)
    assert manuscript.status is S.WITHDRAWN


def accepted() -> Manuscript:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.ACCEPT, actor_id=EDITOR,
        rationale="Strong contribution", occurred_at=NOW,
    )
    return manuscript


def test_accepted_manuscript_can_be_scheduled_then_published() -> None:
    """The terminal path. Everything else is preparation for this happening."""
    manuscript = accepted()
    issue_id = IssueId(uuid4())
    scheduled = manuscript.schedule(issue_id=issue_id, actor_id=EDITOR, occurred_at=NOW)
    assert status_of(manuscript) is S.SCHEDULED
    assert manuscript.issue_id == issue_id
    assert scheduled.event_type is EventType.SCHEDULED_FOR_ISSUE
    published = manuscript.publish(actor_id=EDITOR, occurred_at=NOW)
    assert status_of(manuscript) is S.PUBLISHED
    assert published.event_type is EventType.MANUSCRIPT_PUBLISHED


def test_reviews_are_refused_outside_the_review_stage() -> None:
    manuscript = submitted()
    with pytest.raises(GuardViolationError, match="only while under review"):
        manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)


def test_revision_may_be_requested_at_screening_without_any_reviews() -> None:
    """FR-07: an editor may return a manuscript for pre-review changes."""
    manuscript = submitted()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.REQUEST_REVISION, actor_id=EDITOR,
        rationale="Anonymise the manuscript before review", occurred_at=NOW,
    )
    assert manuscript.status is S.REVISION_REQUESTED


def test_closing_the_review_round_emits_a_distinct_event_type() -> None:
    """Counting REVIEW_SUBMITTED must not include the event that closes the round."""
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    submitted_count = sum(
        1 for event in manuscript.pending_events
        if event.event_type is EventType.REVIEW_SUBMITTED
    )
    assert submitted_count == 2
    assert manuscript.pending_events[-1].event_type is EventType.REVIEW_ROUND_CLOSED


def test_sequence_numbers_continue_after_the_buffer_is_drained() -> None:
    """hashchain.append demands consecutive sequences across the manuscript's whole life.

    Draining the buffer is how a repository persists events, so numbering that restarts
    at 1 after a drain would collide with an event already in the chain.
    """
    manuscript = submitted()
    manuscript.pull_events()
    event = manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    assert event.sequence == 2


def test_decision_payload_carries_the_decision_and_rationale() -> None:
    """Payload keys are hashed into the audit chain, so their names are part of the contract."""
    manuscript = accepted()
    decision = manuscript.pending_events[-1]
    assert decision.payload["decision"] == "accept"
    assert decision.payload["rationale"] == "Strong contribution"
    assert decision.payload["status"] == "accepted"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_manuscript.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.domain.manuscript'`

- [ ] **Step 3: Write the implementation**

Create `backend/src/ugjcs/domain/manuscript.py`:

```python
"""The manuscript aggregate.

Every state change goes through `_transition`, which checks the lifecycle table and
emits exactly one event. There is no other write path, so the event log cannot drift
out of step with the materialised state.
"""

from dataclasses import dataclass, field
from datetime import datetime

from ugjcs.domain.enums import DecisionType, EventType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.errors import GuardViolationError
from ugjcs.domain.events import EditorialEvent, PayloadValue
from ugjcs.domain.ids import IssueId, ManuscriptId, TrackingCode, UserId
from ugjcs.domain.transitions import assert_legal

_DECISION_TARGETS: dict[DecisionType, S] = {
    DecisionType.DESK_REJECT: S.DESK_REJECTED,
    DecisionType.SEND_TO_REVIEW: S.UNDER_REVIEW,
    DecisionType.REQUEST_REVISION: S.REVISION_REQUESTED,
    DecisionType.ACCEPT: S.ACCEPTED,
    DecisionType.REJECT: S.REJECTED,
}

# Only these need a quorum. REQUEST_REVISION is deliberately absent: FR-07 lets an editor
# return a manuscript for pre-review changes during screening, when no reviews exist yet.
# Post-review revision is already gated by the table, which reaches REVISION_REQUESTED from
# REVIEWS_COMPLETE and nowhere else after review begins.
_DECISIONS_REQUIRING_REVIEWS = frozenset({DecisionType.ACCEPT, DecisionType.REJECT})


@dataclass(slots=True)
class Manuscript:
    id: ManuscriptId
    tracking_code: TrackingCode
    title: str
    abstract: str
    keywords: tuple[str, ...]
    author_ids: tuple[UserId, ...]
    corresponding_author_id: UserId
    status: S = S.DRAFT
    version: int = 1
    minimum_reviews: int = 2
    submitted_reviews: int = 0
    issue_id: IssueId | None = None
    _sequence: int = 0
    _events: list[EditorialEvent] = field(default_factory=list, repr=False)

    @property
    def pending_events(self) -> tuple[EditorialEvent, ...]:
        return tuple(self._events)

    def pull_events(self) -> tuple[EditorialEvent, ...]:
        """Return buffered events and clear the buffer, for the caller to persist.

        `_sequence` is deliberately NOT reset. Sequence numbers must stay monotonic across
        the whole lifetime of the manuscript, not just the current buffer, because
        `hashchain.append` requires each event to follow its predecessor consecutively.
        A repository rehydrating this aggregate must seed `_sequence` from the last
        persisted event, otherwise the next event collides with one already in the chain.
        """
        drained = tuple(self._events)
        self._events.clear()
        return drained

    def submit(self, *, actor_id: UserId, occurred_at: datetime) -> EditorialEvent:
        return self._transition(
            S.SUBMITTED, EventType.MANUSCRIPT_SUBMITTED, actor_id, occurred_at,
            {"version": self.version},
        )

    def begin_screening(
        self, *, actor_id: UserId, occurred_at: datetime
    ) -> EditorialEvent:
        return self._transition(
            S.UNDER_SCREENING, EventType.SCREENING_STARTED, actor_id, occurred_at, {}
        )

    def record_review(
        self, *, reviewer_id: UserId, occurred_at: datetime
    ) -> EditorialEvent:
        """Count a submitted review, completing the round once the quorum is met.

        The automatic move to REVIEWS_COMPLETE is what makes a decision reachable:
        ACCEPTED and REJECTED are deliberately unreachable from UNDER_REVIEW, so an
        editor cannot decide while reviews are still outstanding.
        """
        if self.status is not S.UNDER_REVIEW:
            raise GuardViolationError(
                f"reviews accepted only while under review, not in {self.status.value}"
            )
        self.submitted_reviews += 1
        event = self._emit(
            EventType.REVIEW_SUBMITTED, reviewer_id, occurred_at,
            {"submitted_reviews": self.submitted_reviews},
        )
        if self.submitted_reviews >= self.minimum_reviews:
            self._transition(
                S.REVIEWS_COMPLETE, EventType.REVIEW_ROUND_CLOSED, reviewer_id,
                occurred_at, {"reviews_complete": True},
            )
        return event

    def record_decision(
        self,
        *,
        decision: DecisionType,
        actor_id: UserId,
        rationale: str,
        occurred_at: datetime,
    ) -> EditorialEvent:
        if (
            decision in _DECISIONS_REQUIRING_REVIEWS
            and self.submitted_reviews < self.minimum_reviews
        ):
            raise GuardViolationError(
                f"{decision.value} requires {self.minimum_reviews} reviews, "
                f"has {self.submitted_reviews}"
            )
        return self._transition(
            _DECISION_TARGETS[decision], EventType.DECISION_RECORDED, actor_id,
            occurred_at, {"decision": decision.value, "rationale": rationale},
        )

    def resubmit(self, *, actor_id: UserId, occurred_at: datetime) -> EditorialEvent:
        if actor_id != self.corresponding_author_id:
            raise GuardViolationError("only the corresponding author may resubmit")
        event = self._transition(
            S.RESUBMITTED, EventType.REVISION_SUBMITTED, actor_id, occurred_at,
            {"version": self.version + 1},
        )
        self.version += 1
        self.submitted_reviews = 0
        return event

    def schedule(
        self, *, issue_id: IssueId, actor_id: UserId, occurred_at: datetime
    ) -> EditorialEvent:
        event = self._transition(
            S.SCHEDULED, EventType.SCHEDULED_FOR_ISSUE, actor_id, occurred_at,
            {"issue_id": str(issue_id)},
        )
        self.issue_id = issue_id
        return event

    def publish(self, *, actor_id: UserId, occurred_at: datetime) -> EditorialEvent:
        return self._transition(
            S.PUBLISHED, EventType.MANUSCRIPT_PUBLISHED, actor_id, occurred_at, {}
        )

    def withdraw(self, *, actor_id: UserId, occurred_at: datetime) -> EditorialEvent:
        return self._transition(
            S.WITHDRAWN, EventType.MANUSCRIPT_WITHDRAWN, actor_id, occurred_at, {}
        )

    def _transition(
        self,
        target: S,
        event_type: EventType,
        actor_id: UserId,
        occurred_at: datetime,
        payload: dict[str, PayloadValue],
    ) -> EditorialEvent:
        assert_legal(self.status, target)
        self.status = target
        return self._emit(event_type, actor_id, occurred_at, payload | {"status": target.value})

    def _emit(
        self,
        event_type: EventType,
        actor_id: UserId,
        occurred_at: datetime,
        payload: dict[str, PayloadValue],
    ) -> EditorialEvent:
        self._sequence += 1
        event = EditorialEvent(
            manuscript_id=self.id,
            sequence=self._sequence,
            event_type=event_type,
            payload=payload,
            actor_id=actor_id,
            occurred_at=occurred_at,
        )
        self._events.append(event)
        return event
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_manuscript.py -v`
Expected: PASS — 14 tests.

Note the `test_publication_requires_an_issue` case passes because `ACCEPTED → PUBLISHED` is absent from the transition table; publication is only reachable via `SCHEDULED`, which is where the issue is attached. The invariant is enforced by the table's shape rather than by a separate check, and Task 10 asserts it independently.

- [ ] **Step 5: Run the full gate**

Run: `cd backend && make check`
Expected: all gates pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/ugjcs/domain/manuscript.py backend/tests/unit/domain/test_manuscript.py
git commit -m "feat: add manuscript aggregate with guarded transitions and event emission"
```

---

### Task 8: Authorisation policy layer

**Files:**
- Create: `backend/src/ugjcs/domain/policies.py`
- Test: `backend/tests/unit/domain/test_policies.py`

**Interfaces:**
- Consumes: `Role` from `enums.py`; `AuthorizationDeniedError` from `errors.py`; `Manuscript` from `manuscript.py`; `UserId` from `ids.py`.
- Produces:
  - `Action` (`StrEnum`): `VIEW`, `SUBMIT`, `SCREEN`, `ASSIGN_REVIEWER`, `REVIEW`, `DECIDE`, `RESUBMIT`, `PUBLISH`, `MANAGE_USERS`, `VIEW_AUDIT`
  - `Actor` frozen dataclass: `id: UserId`, `roles: frozenset[Role]`
  - `can(actor: Actor, action: Action, manuscript: Manuscript | None = None) -> bool`
  - `authorize(actor: Actor, action: Action, manuscript: Manuscript | None = None) -> None` raising `AuthorizationDeniedError`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_policies.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ugjcs.domain.enums import Role
from ugjcs.domain.errors import AuthorizationDeniedError
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Action, Actor, authorize, can

AUTHOR_ID = UserId(uuid4())
OTHER_ID = UserId(uuid4())
NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def actor(*roles: Role, user_id: UserId | None = None) -> Actor:
    return Actor(id=user_id or UserId(uuid4()), roles=frozenset(roles))


def manuscript() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 3),
        title="Federated Learning for Rural Clinics",
        abstract="A federated approach to clinical prediction under bandwidth limits.",
        keywords=("federated learning",),
        author_ids=(AUTHOR_ID,),
        corresponding_author_id=AUTHOR_ID,
    )


def test_editor_may_screen() -> None:
    assert can(actor(Role.EDITOR), Action.SCREEN, manuscript())


def test_author_may_not_screen() -> None:
    assert not can(actor(Role.AUTHOR), Action.SCREEN, manuscript())


def test_reviewer_may_not_decide() -> None:
    assert not can(actor(Role.REVIEWER), Action.DECIDE, manuscript())


def test_editor_in_chief_may_publish() -> None:
    assert can(actor(Role.EDITOR_IN_CHIEF), Action.PUBLISH, manuscript())


def test_editor_may_not_publish() -> None:
    assert not can(actor(Role.EDITOR), Action.PUBLISH, manuscript())


def test_corresponding_author_may_resubmit_own_manuscript() -> None:
    assert can(actor(Role.AUTHOR, user_id=AUTHOR_ID), Action.RESUBMIT, manuscript())


def test_another_author_may_not_resubmit_someone_elses_manuscript() -> None:
    assert not can(actor(Role.AUTHOR, user_id=OTHER_ID), Action.RESUBMIT, manuscript())


def test_administrator_may_manage_users() -> None:
    assert can(actor(Role.ADMINISTRATOR), Action.MANAGE_USERS)


def test_editor_may_not_manage_users() -> None:
    assert not can(actor(Role.EDITOR), Action.MANAGE_USERS)


def test_unknown_role_combination_is_denied_by_default() -> None:
    assert not can(actor(), Action.DECIDE, manuscript())


def test_multiple_roles_grant_the_union_of_permissions() -> None:
    dual = actor(Role.AUTHOR, Role.EDITOR, user_id=AUTHOR_ID)
    assert can(dual, Action.SCREEN, manuscript())
    assert can(dual, Action.RESUBMIT, manuscript())


def test_editor_may_view_any_manuscript() -> None:
    assert can(actor(Role.EDITOR), Action.VIEW, manuscript())


def test_administrator_may_view_any_manuscript() -> None:
    assert can(actor(Role.ADMINISTRATOR), Action.VIEW, manuscript())


def test_author_may_view_their_own_manuscript() -> None:
    assert can(actor(Role.AUTHOR, user_id=AUTHOR_ID), Action.VIEW, manuscript())


def test_author_may_not_view_someone_elses_manuscript() -> None:
    assert not can(actor(Role.AUTHOR, user_id=OTHER_ID), Action.VIEW, manuscript())


def test_reviewer_has_no_unblinded_view() -> None:
    """Reviewers read manuscripts through the blinded projection, never through VIEW.

    If this ever returns True the double-blind guarantee is gone, because VIEW yields the
    full aggregate including author identities.
    """
    assert not can(actor(Role.REVIEWER), Action.VIEW, manuscript())


def test_view_is_denied_when_no_manuscript_is_supplied() -> None:
    assert not can(actor(Role.EDITOR), Action.VIEW)


def test_authorize_is_silent_when_permitted() -> None:
    authorize(actor(Role.EDITOR), Action.SCREEN, manuscript())


def test_authorize_raises_when_denied() -> None:
    with pytest.raises(AuthorizationDeniedError, match="screen"):
        authorize(actor(Role.AUTHOR), Action.SCREEN, manuscript())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_policies.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.domain.policies'`

- [ ] **Step 3: Write the implementation**

Create `backend/src/ugjcs/domain/policies.py`:

```python
"""Authorisation, expressed once and denied by default.

Role grants cover actions that depend only on who the actor is. Actions that also
depend on the actor's relationship to a specific manuscript are handled by explicit
predicates, because encoding ownership in a role table silently over-grants.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from ugjcs.domain.enums import Role
from ugjcs.domain.errors import AuthorizationDeniedError
from ugjcs.domain.ids import UserId
from ugjcs.domain.manuscript import Manuscript


class Action(StrEnum):
    VIEW = "view"
    SUBMIT = "submit"
    SCREEN = "screen"
    ASSIGN_REVIEWER = "assign_reviewer"
    REVIEW = "review"
    DECIDE = "decide"
    RESUBMIT = "resubmit"
    PUBLISH = "publish"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT = "view_audit"


@dataclass(frozen=True, slots=True)
class Actor:
    id: UserId
    roles: frozenset[Role]


_ROLE_GRANTS: Mapping[Action, frozenset[Role]] = {
    Action.SUBMIT: frozenset({Role.AUTHOR}),
    Action.SCREEN: frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF}),
    Action.ASSIGN_REVIEWER: frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF}),
    Action.REVIEW: frozenset({Role.REVIEWER}),
    Action.DECIDE: frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF}),
    Action.PUBLISH: frozenset({Role.EDITOR_IN_CHIEF}),
    Action.MANAGE_USERS: frozenset({Role.ADMINISTRATOR}),
    Action.VIEW_AUDIT: frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF}),
}

_OWNERSHIP_ACTIONS = frozenset({Action.RESUBMIT})


def can(
    actor: Actor, action: Action, manuscript: Manuscript | None = None
) -> bool:
    """Whether `actor` may perform `action`, optionally against `manuscript`."""
    if action in _OWNERSHIP_ACTIONS:
        return (
            manuscript is not None
            and Role.AUTHOR in actor.roles
            and actor.id == manuscript.corresponding_author_id
        )
    if action is Action.VIEW:
        return _can_view(actor, manuscript)
    return bool(actor.roles & _ROLE_GRANTS.get(action, frozenset()))


def _can_view(actor: Actor, manuscript: Manuscript | None) -> bool:
    if manuscript is None:
        return False
    if actor.roles & {Role.EDITOR, Role.EDITOR_IN_CHIEF, Role.ADMINISTRATOR}:
        return True
    return actor.id in manuscript.author_ids


def authorize(
    actor: Actor, action: Action, manuscript: Manuscript | None = None
) -> None:
    """Raise `AuthorizationDeniedError` unless the action is permitted."""
    if not can(actor, action, manuscript):
        raise AuthorizationDeniedError(f"actor {actor.id} may not {action.value}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_policies.py -v`
Expected: PASS — 13 tests.

- [ ] **Step 5: Run the full gate**

Run: `cd backend && make check`
Expected: all gates pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/ugjcs/domain/policies.py backend/tests/unit/domain/test_policies.py
git commit -m "feat: add deny-by-default authorisation policy layer"
```

---

### Task 9: Double-blind projection

**Files:**
- Create: `backend/src/ugjcs/domain/blinding.py`
- Test: `backend/tests/unit/domain/test_blinding.py`

**Interfaces:**
- Consumes: `Manuscript` from `manuscript.py`.
- Produces: `BlindedManuscript` frozen dataclass with fields `tracking_code: str`, `title: str`, `abstract: str`, `keywords: tuple[str, ...]`, `version: int`, `status: str` — and no author fields at all; plus `blind(manuscript: Manuscript) -> BlindedManuscript`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_blinding.py`:

```python
import dataclasses
from uuid import uuid4

from ugjcs.domain.blinding import BlindedManuscript, blind
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript

SENTINEL_AUTHOR = UserId(uuid4())


def manuscript() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 9),
        title="Low-Bandwidth Telemedicine Protocols",
        abstract="A protocol for clinical consultation over intermittent links.",
        keywords=("telemedicine", "protocols"),
        author_ids=(SENTINEL_AUTHOR,),
        corresponding_author_id=SENTINEL_AUTHOR,
    )


def test_blinded_view_preserves_reviewable_content() -> None:
    blinded = blind(manuscript())
    assert blinded.title == "Low-Bandwidth Telemedicine Protocols"
    assert blinded.keywords == ("telemedicine", "protocols")


def test_blinded_view_has_no_author_fields_in_its_type() -> None:
    field_names = {field.name for field in dataclasses.fields(BlindedManuscript)}
    assert not any("author" in name for name in field_names)


def test_blinded_view_never_serialises_an_author_identifier() -> None:
    blinded = blind(manuscript())
    serialised = repr(dataclasses.asdict(blinded))
    assert str(SENTINEL_AUTHOR) not in serialised


def test_blinded_view_is_immutable() -> None:
    blinded = blind(manuscript())
    try:
        blinded.title = "changed"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("BlindedManuscript should be immutable")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_blinding.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.domain.blinding'`

- [ ] **Step 3: Write the implementation**

Create `backend/src/ugjcs/domain/blinding.py`:

```python
"""The reviewer-facing projection of a manuscript.

Blinding is structural: `BlindedManuscript` has no author attributes, so there is no
field a future change could accidentally populate. Filtering a full object would leave
that possibility open; omitting the fields from the type does not.
"""

from dataclasses import dataclass

from ugjcs.domain.manuscript import Manuscript


@dataclass(frozen=True, slots=True)
class BlindedManuscript:
    tracking_code: str
    title: str
    abstract: str
    keywords: tuple[str, ...]
    version: int
    status: str


def blind(manuscript: Manuscript) -> BlindedManuscript:
    """Project a manuscript into the form a reviewer is permitted to see."""
    return BlindedManuscript(
        tracking_code=manuscript.tracking_code.value,
        title=manuscript.title,
        abstract=manuscript.abstract,
        keywords=manuscript.keywords,
        version=manuscript.version,
        status=manuscript.status.value,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_blinding.py -v`
Expected: PASS — 4 tests.

- [ ] **Step 5: Run the full gate**

Run: `cd backend && make check`
Expected: all gates pass, coverage at or above 85.

- [ ] **Step 6: Commit**

```bash
git add backend/src/ugjcs/domain/blinding.py backend/tests/unit/domain/test_blinding.py
git commit -m "feat: add structurally-enforced double-blind manuscript projection"
```

---

### Task 10: Property-based invariant tests

**Files:**
- Create: `backend/tests/unit/domain/test_invariants.py`

**Interfaces:**
- Consumes: everything built in Tasks 3–9.
- Produces: no production code. These tests assert the properties the design document claims universally, over inputs no hand-written example would cover.

- [ ] **Step 1: Write the property tests**

Create `backend/tests/unit/domain/test_invariants.py`:

```python
"""Universal invariants, asserted over generated inputs rather than chosen examples."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

from ugjcs.domain.enums import EventType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.events import EditorialEvent, PayloadValue
from ugjcs.domain.hashchain import ChainBrokenError, append, verify
from ugjcs.domain.ids import ManuscriptId, UserId
from ugjcs.domain.transitions import LEGAL_TRANSITIONS, TERMINAL_STATES, is_legal

BASE_TIME = datetime(2026, 8, 12, tzinfo=UTC)

payloads = st.dictionaries(
    st.text(min_size=1, max_size=12),
    st.one_of(st.integers(), st.text(max_size=20), st.booleans()),
    max_size=5,
)


@given(source=st.sampled_from(list(S)), target=st.sampled_from(list(S)))
def test_no_transition_ever_leaves_a_terminal_state(source: S, target: S) -> None:
    if source in TERMINAL_STATES:
        assert not is_legal(source, target)


@given(source=st.sampled_from(list(S)))
def test_published_is_reachable_only_from_scheduled(source: S) -> None:
    if is_legal(source, S.PUBLISHED):
        assert source is S.SCHEDULED


@given(source=st.sampled_from(list(S)))
def test_accepted_is_reachable_only_from_reviews_complete(source: S) -> None:
    if is_legal(source, S.ACCEPTED):
        assert source is S.REVIEWS_COMPLETE


def test_withdrawal_is_reachable_from_every_non_terminal_state_except_draft() -> None:
    expected = {
        state
        for state in S
        if state not in TERMINAL_STATES and state not in {S.DRAFT, S.RESUBMITTED,
                                                          S.ACCEPTED, S.SCHEDULED}
    }
    actual = {state for state in S if S.WITHDRAWN in LEGAL_TRANSITIONS[state]}
    assert actual == expected


@settings(max_examples=100)
@given(payload_list=st.lists(payloads, min_size=1, max_size=12))
def test_a_chain_built_by_append_always_verifies(
    payload_list: list[dict[str, PayloadValue]],
) -> None:
    manuscript_id = ManuscriptId(uuid4())
    actor_id = UserId(uuid4())
    chain: list = []
    for index, payload in enumerate(payload_list, start=1):
        chain.append(
            append(
                chain,
                EditorialEvent(
                    manuscript_id=manuscript_id,
                    sequence=index,
                    event_type=EventType.DECISION_RECORDED,
                    payload=payload,
                    actor_id=actor_id,
                    occurred_at=BASE_TIME + timedelta(minutes=index),
                ),
            )
        )
    verify(chain)


@settings(max_examples=50)
@given(
    payload_list=st.lists(payloads, min_size=2, max_size=8),
    victim=st.integers(min_value=0),
)
def test_removing_any_event_breaks_the_chain(
    payload_list: list[dict[str, PayloadValue]], victim: int
) -> None:
    manuscript_id = ManuscriptId(uuid4())
    actor_id = UserId(uuid4())
    chain: list = []
    for index, payload in enumerate(payload_list, start=1):
        chain.append(
            append(
                chain,
                EditorialEvent(
                    manuscript_id=manuscript_id,
                    sequence=index,
                    event_type=EventType.DECISION_RECORDED,
                    payload=payload,
                    actor_id=actor_id,
                    occurred_at=BASE_TIME + timedelta(minutes=index),
                ),
            )
        )
    del chain[victim % len(chain)]
    try:
        verify(chain)
    except ChainBrokenError:
        return
    raise AssertionError("removing an event should always break verification")
```

- [ ] **Step 2: Run the property tests**

Run: `cd backend && uv run pytest tests/unit/domain/test_invariants.py -v`
Expected: PASS. If `test_withdrawal_is_reachable_from_every_non_terminal_state_except_draft` fails, the transition table and the spec's withdrawal policy disagree — fix the table in `transitions.py`, not the test, because the spec is authoritative.

- [ ] **Step 3: Run the full gate**

Run: `cd backend && make check`
Expected: all gates pass.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/domain/test_invariants.py
git commit -m "test: add Hypothesis property tests for lifecycle and chain invariants"
```

---

### Task 11: Continuous integration for the backend

**Files:**
- Create: `.github/workflows/backend-ci.yml`

**Interfaces:**
- Consumes: `backend/Makefile`'s `check` target.
- Produces: a required status check that every later plan's pull requests must pass.

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/backend-ci.yml`:

```yaml
name: backend-ci

on:
  push:
    branches: [main]
  pull_request:
    paths: ["backend/**", ".github/workflows/backend-ci.yml"]

jobs:
  check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Lint
        run: uv run ruff check src tests

      - name: Format check
        run: uv run ruff format --check src tests

      - name: Type check
        run: uv run mypy

      - name: Architecture contract
        run: uv run lint-imports

      - name: Tests with coverage gate
        run: uv run pytest --cov --cov-report=term-missing
```

- [ ] **Step 2: Verify the workflow file parses**

Run: `cd "$(git rev-parse --show-toplevel)" && python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/backend-ci.yml')); print('valid')"`
Expected: `valid`

- [ ] **Step 3: Verify the same gate passes locally**

Run: `cd backend && make check`
Expected: every step green, coverage at or above 85.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/backend-ci.yml
git commit -m "ci: run lint, types, architecture contract and coverage gate on the backend"
```

---

## Definition of done for Plan 1

- `docs/03-effort-estimation.md` contains the full UCP derivation, the COCOMO II cross-check, the reconciliation of the two, the MoSCoW cut that governs Plans 2–6, and the method for the closing variance analysis.
- `cd backend && make check` passes from a clean checkout: ruff, ruff format, mypy strict, import-linter, and pytest at or above 85% coverage.
- The domain package imports no framework, verified mechanically rather than by inspection.
- The manuscript lifecycle, hash chain, authorisation policy and blinded projection are each covered by example-based tests and, where the claim is universal, by property-based tests.

## What Plans 2–6 cover

2. **Persistence and API** — SQLAlchemy mapping, Alembic migrations, unit of work, authentication with Argon2id and rotating refresh tokens, the policy dependency applied to every route, and the manuscript, editorial, review and issue endpoints.
3. **Asynchronous pipeline and reviewer matching** — S3 storage adapter, ARQ worker, file validation by magic bytes, PDF metadata stripping, text extraction, MinHash similarity screening, TF-IDF expertise scoring and Hungarian assignment.
4. **Frontend** — the Next.js public archive, the BFF proxy, and the author, reviewer, editor and administrator interfaces.
5. **Infrastructure and deployment** — Terraform for VPC, ECS Fargate, ALB, CloudFront, RDS, S3 and Redis; the deployment workflow; the IAM deploy user replacing root credentials.
6. **Interoperability, hardening and submission** — OAI-PMH, citation export, Playwright end-to-end suite, security and load testing, the seeded demonstration corpus, and the five submission documents.
