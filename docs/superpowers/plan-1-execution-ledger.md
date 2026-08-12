# SDD ledger — plan: docs/superpowers/plans/2026-08-12-ugjcs-plan-1-estimation-and-domain-core.md

Branch: feat/plan-1-domain-core (created from master)
Tasks: 11

Pre-flight scan resolutions (controller, before Task 1):
- Task 2 Step 2 says "Append to backend/pyproject.toml", but Step 1 runs `uv init --bare`,
  which already writes a `[project]` table. Appending a second one is a TOML duplicate-key
  error. Ruling: MERGE the given configuration into the existing file, keeping one
  `[project]` table and adding the tool sections. Carried in the Task 2 dispatch.
- Task 2 Step 6 and Task 3 Step 7 state that the coverage gate may fail before Task 4.
  Ruling: this is intended by the plan; only ruff, mypy and lint-imports must pass there.

Constraint added by user mid-flight (2026-08-12): any AI/LLM activity in this project
must run on AWS Bedrock. Current design has NO AI activity (TF-IDF + Hungarian +
MinHash are classical). Decision point deferred to Plan 3: whether to promote
embedding-based reviewer matching from future-evolution into scope using Bedrock.

Task 1: implementer DONE (commit 2629a65), all 9 figures independently reconciled.
Task 1: complete (commits be7adc5..2629a65, review clean — spec compliant, quality approved)
Task 1: minor (deferred): dangling cross-reference "§12" at docs/03-effort-estimation.md:375 should read §11
Task 1: minor (deferred): Must-have UCP calc at :183-189 omits the 207.74 intermediate the full calc shows
Task 1: minor (deferred): FR-28 explanatory note at :96-100 is scope addition beyond the brief (accurate)
Task 1: minor (deferred): shortfall bullets at :297-301 cross-reference the debt register collectively, not per-bullet
Task 1: controller ruling on reviewer's warning item — use-case classifications were supplied by the
  brief as authoritative content to transcribe; transcription was intended, not a gap.
Task 2: implementer DONE_WITH_CONCERNS (commit 5417202). Concern: added
  include_external_packages = True to .importlinter because import-linter 2.13 errors
  without it when forbidden modules are external. Controller ruling: AUTHORISED — the
  contract cannot evaluate at all otherwise, so this is required for the gate to function.
Task 2: complete (commits 2629a65..5417202, review clean — no findings at any severity).
  Reviewer independently reproduced the import-linter failure and confirmed domain-purity
  contract reports KEPT. Venv interpreter verified as Python 3.13.7, not host 3.14.3.
Task 3: implementer DONE_WITH_CONCERNS (commit cdb6925). Two Important findings raised by
  the implementer itself: (a) ruff N818 rejects IllegalTransition/GuardViolation/
  AuthorizationDenied, which the plan mandates verbatim — a plan-vs-rubric conflict;
  (b) repo has no .gitignore, so .pyc files were staged.
Task 3: plan conflict escalated to human partner. RULING: linter governs — rename to
  IllegalTransitionError, GuardViolationError, AuthorizationDeniedError, and
  ChainBrokenError (Task 6). No suppressions. Plan updated accordingly in commit 597e563.
Task 3: fix round 1/5 dispatched to original implementer a8d80a2f387422a4b — rename
  exceptions + add root .gitignore.
Task 3: pre-review remediation complete (commit ff29c26) — exceptions renamed, root
  .gitignore added, all four gates green. Correction to the line above: this was
  pre-review remediation of implementer-reported concerns, not a post-review fix round.
  Full task review now runs over 5417202..ff29c26.
Task 3: complete (commits 5417202..ff29c26, review clean — no Critical/Important findings).
  Controller resolved reviewer's warning item: git ls-files confirms backend/uv.lock is tracked.
  Round-trip risk on TrackingCode.mint/parse for 5-digit sequences traced by reviewer: no bug
  ({sequence:04d} is a minimum width; \d{4,} accepts it).
Task 4: implementer DONE_WITH_CONCERNS, no commit (correctly refused to commit with a gate red).
  Two NEW lint-vs-plan conflicts, both mechanical:
  (a) RUF043 on match="draft.*published" — ruling: use a raw string r"draft.*published".
      Behaviour identical; the .* is intended as regex. Plan updated.
  (b) ruff format wants to collapse TERMINAL_STATES and the S.REVIEWS_COMPLETE entry.
      Ruling: the formatter is authoritative; the plan's line breaks were hand-formatting.
  Controller ruled on both without escalating: neither alters a name, interface or behaviour,
  unlike the N818 rename which changed published class names.
Task 4: complete (commits ff29c26..3ee9037, review clean — no Critical/Important).
  36 tests, coverage 100%. Reviewer ran independent BFS: all 13 states reachable from DRAFT,
  every non-terminal state reaches a terminal state, _WITHDRAWABLE_FROM self-consistent
  with the table's WITHDRAWN edges.
Task 4: minor (deferred): 4 of 19 legal edges are not asserted by name in the permits list
  (UNDER_SCREENING/REVIEWS_COMPLETE/REVISION_REQUESTED -> WITHDRAWN, RESUBMITTED ->
  UNDER_SCREENING). Inherited from the brief. Task 10 property tests are expected to close it
  — verify there, and tell the final reviewer if they do not.
Task 5: first dispatch died on a dropped connection mid-report; files written, nothing
  committed, HEAD still 3ee9037. Agent resumed from transcript.
Task 5: implementer BLOCKED (correctly) — test_canonical_bytes_are_stable_across_key_order
  fails deterministically because the PLAN's make_event() fixture minted fresh uuid4 per call,
  so the two compared events always differed by identity and the determinism assertion was
  vacuous. Implementation was proven correct; the defect was the plan's.
Task 5: controller ruling — plan defect, fixed at source (commit c9707da): MANUSCRIPT and
  ACTOR pinned at module level. Not escalated: a demonstrably broken fixture whose repair
  preserves the test's intent is a bug fix, not a design decision.
Task 5: implementer DONE (commit 8e38d8b), 41/41, coverage 100%. Review: spec compliant,
  quality approved, but ONE Important finding — default=str on payload: Mapping[str, object]
  permits non-deterministic serialisation (set iteration order varies with the per-process
  hash seed; plain objects repr with a memory address). Would cause FALSE tamper alerts from
  the Task 6 chain across processes.
Task 5: controller ruling — real and load-bearing, fixed at source rather than parked.
  Plan commit e5dd8cb introduces `type PayloadValue = str | int | float | bool | None`,
  narrows the payload field, normalises Mapping -> dict, drops default=str so bad values
  raise loudly, and adds a regression test. Task 7 (_transition/_emit) and Task 10
  (property-test annotations) updated to the same alias.
Task 5: fix round 1/5 dispatched to implementer ad82cf6af8e14948a.
Task 5: fix round 1/5 (6 addressed, 0 open; commits 8e38d8b..e908bdf). Re-reviewer confirmed
  the runtime backstop is the loud TypeError from dropping default=str; the type alias is
  static-only protection layered on top. Nested dicts still serialise deterministically
  (sort_keys recurses); a set at any depth raises.
Task 5: complete (commits 3ee9037..e908bdf, review clean). 42/42, coverage 100%.
Task 6: implementer DONE_WITH_CONCERNS (commit 3ba7222). 51 tests, coverage 98.77%.
  Concern: verify()'s previous_hash link check is unreachable by the brief's 9 tests — both
  negative tests trip an earlier check first.
Task 6: controller ruling — the branch is NOT dead code; it is what catches a splice attack
  (real prefix + grafted history, where each link self-reconciles). Untested branch in the
  tamper-evidence path, so closed rather than deferred. Plan commit 9e16259 adds
  test_verify_detects_a_spliced_chain. Fix round 1/5 dispatched.
Task 6: fix round 1/5 (1 addressed, 0 open; commits 3ba7222..e9d0a11). Splice test confirmed
  to reach verify()'s previous_hash link check; hashchain.py coverage 95% -> 100%.
Task 6: review clean on code, ONE Important finding — module docstring overclaimed. Reviewer
  proved three undetectable mutations: tail truncation, forged append, wholesale forgery from
  genesis. Fix round 2 dispatched: docstring corrected (plan commit fb1469b). No code change.
Task 6: FOR THE DOCUMENTATION — technical debt entry required. "Hash chain has no external
  anchor" -> Cause: 48h scope, domain-layer boundary. Impact: tail truncation and wholesale
  forgery undetectable by the application alone. Priority: Scheduled. Resolution: periodically
  published/signed checkpoint of the latest event_hash + expected event count asserted at the
  persistence boundary. Also add to SRS as an explicit limitation so the tamper-evidence claim
  is not overstated.
Task 6: fix round 2/5 (1 addressed, 0 open; commits e9d0a11..44fda7d). Re-reviewer verified the
  new docstring against the implementation and confirmed the under-claim is accurate, not merely
  modest; diff is docstring-only, longest added line 90 chars.
Task 6: complete (commits e908bdf..44fda7d, review clean). 52 tests, coverage 100%.
Task 7: implementer BLOCKED (correctly, no commit) — mypy --strict rejects the PLAN's
  test_review_quorum_closes_the_review_round with [comparison-overlap]: the first inline
  assert narrows manuscript.status to Literal[UNDER_REVIEW] and mypy cannot see that
  record_review mutates it. Implementer built a standalone minimal repro to prove the defect
  was the plan's, not its transcription.
Task 7: controller ruling — plan defect, fixed at source (commit cee58d2): capture both
  statuses into locals annotated `: S` before asserting. Not escalated; behaviour-preserving.
Task 7: implementer also declined a project-wide 100-line file-size hook, correctly — it is
  not one of this task's gates, and splitting the aggregate would break the single
  _transition/_emit write path the design depends on. Controller concurs.
Task 7: .harness/ added to .gitignore (tooling artefact).
Task 7: implementer DONE (commit d049eb9), 66/66, coverage 97.93% (manuscript.py 94%).
Task 7: review = NEEDS FIXES. Two Important findings, both real plan defects:
  (1) _emit derived sequence from len(self._events)+1 while pull_events() clears that list,
      so the first event after any persistence drain restarts at 1 and hashchain.append
      rejects it ("expected sequence 2, received 1"). Invisible to the suite because no test
      emitted after a drain. This would have broken the audit chain in Plan 2.
  (2) schedule() never executed by any test -> the accepted -> scheduled -> published terminal
      path was entirely unverified. test_publication_requires_an_issue proves only the negative.
  Minors also actioned: REQUEST_REVISION wrongly required a quorum so FR-07 pre-review changes
  were impossible at screening; the round-closing event reused REVIEW_SUBMITTED so counting
  over-counted; no test asserted any event payload though payload keys are hashed into the chain.
Task 7: plan corrected (commits cee58d2, 156feb8) — monotonic _sequence field surviving drains,
  new EventType.REVIEW_ROUND_CLOSED, _DECISIONS_REQUIRING_REVIEWS narrowed to {ACCEPT, REJECT},
  and 7 new tests. Fix round 1/5 dispatched.
Task 7: fix round 1 blocked on the SAME mypy narrowing class, this time in the terminal-path
  test the controller had just written. Controller ruling: a recurrence means the local patch
  was the wrong fix. Plan commit a571b98 introduces a status_of(manuscript) -> S helper that
  reads through a call so narrowing cannot persist, reverts last round's annotated-locals
  workaround to it, and applies it to the terminal-path test. Prevents recurrence in Tasks 8-10.
Task 7: controller's test count (21) was wrong; the plan defines 20 tests. Implementer correct.
Task 7: fix round 2/5 dispatched.
Task 7: fix rounds 1-2 (7 addressed, 0 open; commits d049eb9..4bb8437). Re-reviewer confirmed:
  _sequence monotonic across drains (first event after drain is 2); the drain test WOULD have
  failed against the old len(_events)+1 form, so it discriminates; terminal path executes both
  schedule() and publish() bodies fully; narrowing the quorum guard weakened nothing because
  LEGAL_TRANSITIONS[UNDER_REVIEW] excludes REVISION_REQUESTED independently; the EventType
  addition changed no other member's value (explicit string literals, no auto()).
Task 7: complete (commits 44fda7d..4bb8437, review clean). 72 tests, coverage 100%.
Task 8: implementer DONE_WITH_CONCERNS (commit 8fc0db7). 13/13 new, 85/85 suite, total coverage
  96.26% but policies.py only 78% — Action.VIEW and _can_view() entirely unexercised by the
  brief's tests.
Task 8: controller ruling — real gap, not deferrable. VIEW governs who sees an UNBLINDED
  manuscript, so an over-grant there defeats double-blind, and nothing proved a reviewer is
  denied. Plan commit 1c5d7dc adds 6 tests covering every _can_view branch plus an explicit
  reviewer-denial test. Fix round 1/5 dispatched.
Task 8: fix round 1/5 (1 addressed, 0 open; commits 8fc0db7..d9148a4). policies.py 78% -> 100%.
Task 8: complete (commits 4bb8437..d9148a4, review clean — no Critical/Important). Reviewer
  confirmed the suite fails against BOTH an always-True and an always-False can(), so the
  assertions are load-bearing; deny-by-default uses Mapping.get with a default so a future
  11th Action denies rather than raising KeyError.
Task 8: minor (deferred): test_reviewer_has_no_unblinded_view's docstring claims reviewers read
  via the blinded projection, which policies.py cannot itself prove. Accurate once Task 9 lands.
Task 8: FOR PLAN 2 — two architectural notes from the review:
  (a) Actor.roles is caller-supplied and unverified by this layer. The JWT/session layer must
      guarantee roles are authentic and CURRENT (not stale) before constructing an Actor.
      policies.py offers no protection against a forged or stale Actor by design.
  (b) Asymmetry: _can_view grants on identity alone (actor.id in author_ids) without requiring
      Role.AUTHOR, whereas RESUBMIT requires BOTH the role and corresponding authorship.
      Intentional per the brief, but confirm it is what we want when the API layer lands.
Task 9: implementer DONE (commit 38c0444), 95 tests, 100% coverage, clean on first pass.
Task 9: SUBAGENT DISPATCH BLOCKED — account session limit hit, resets 2pm Africa/Accra.
  Independent review could NOT be run. Controller reviewed inline instead and applied three
  fixes directly (commit below). THIS TASK HAS NOT HAD AN INDEPENDENT REVIEW — the final
  whole-branch review MUST cover blinding.py and test_blinding.py explicitly.
Task 9: controller findings, all fixed:
  (a) test_blinded_view_has_no_author_fields_in_its_type only checked for the substring
      "author" in field names — would not catch affiliation/submitter_id/corresponding_email,
      exactly the fields Plan 2 is likely to add. Replaced with an exact field-set assertion
      so any growth of the type fails the test and must be justified.
  (b) Only 2 of 6 fields were asserted; a blind() returning empty strings for abstract,
      status and tracking_code would have passed. Now all six are asserted.
  (c) Docstring omitted the known limitation that title/abstract/keywords are copied
      verbatim, so self-identifying text reaches the reviewer. Now stated in the module.
Task 9: complete pending independent review. 95 tests, 100% coverage on every module.
Task 10: controller-implemented (subagents still blocked). Found TWO defects in the plan's own
  test code before writing it:
  (a) test_removing_any_event_breaks_the_chain used victim % len(chain), which can select the
      LAST element — but tail truncation is undetectable by design, as Task 6's review
      established. The test asserted a property we had already proven false and would have
      failed. Rewritten as test_removing_any_event_except_the_last_breaks_the_chain, and a new
      test_truncating_the_tail_is_not_detected PINS the limitation so it cannot change silently.
  (b) `chain: list = []` is a bare generic that mypy --strict rejects. Extracted a typed
      build_chain() helper returning list[ChainedEvent], removing the duplication too.
  Added two properties the spec claims but the plan omitted: scheduling is reachable only from
  ACCEPTED (which with the PUBLISHED property makes acceptance a structural precondition of
  publication), and the blinded projection never carries author identity for ANY generated
  title/abstract/keywords. 9 property tests, all passing.
Task 11: controller-implemented. CI workflow validated by parsing the YAML and asserting the
  gate order matches the Makefile exactly. Changed the push trigger to [main, master] because
  this repository's default branch is master, not main as the plan assumed.
Task 11: complete. Final state: 104 tests, 100% coverage on every module including branches.

PLAN 1 CODE COMPLETE — commits be7adc5..752b569 on feat/plan-1-domain-core.

OUTSTANDING REVIEW DEBT (subagent dispatch blocked, resets 2pm Africa/Accra):
  - Tasks 9, 10, 11 had NO independent review. Controller wrote or amended all three.
  - The final whole-branch review has NOT been run.
  When subagents return, run the final review over merge-base..HEAD on the most capable model,
  and point it explicitly at blinding.py, test_blinding.py, test_invariants.py and
  .github/workflows/backend-ci.yml as the unreviewed surface. Also give it the deferred-minor
  lines above.

FINAL WHOLE-BRANCH REVIEW (opus, be7adc5..ad49d65): MERGE-READY = NO. Review debt discharged.
  Reviewer ran MUTATION TESTING. Four mutations survived all 104 tests:
  (1) chain_hash no longer mixing in previous_hash  -> 104 passed. The chain stops being a
      chain and nothing notices. This is the branch's headline security property.
  (2) REJECT removed from _DECISIONS_REQUIRING_REVIEWS -> 104 passed (rejection without
      quorum is unguarded by any test).
  (3) RESUBMITTED -> UNDER_SCREENING edge deleted -> 104 passed (FR-07 loop untested).
  (4) import os/socket/sqlite3/urllib/logging into the domain -> contract KEPT. The
      .importlinter contract's NAME overclaims; it is a seven-name denylist.
  Also: CI paths filter would permanently block required checks on docs/frontend/infra PRs;
  append()'s len(chain)+1 forces whole-history loads on every save in Plan 2; payload strategy
  omits float, and json.dumps emits bare NaN which is invalid JSON at the jsonb boundary.
  Estimation document arithmetic independently recomputed: ALL figures reconcile.
  Fix wave dispatched (one agent, complete findings list), then one scoped re-review.
