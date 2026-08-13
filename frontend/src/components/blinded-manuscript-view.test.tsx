import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BlindedManuscriptView } from "./blinded-manuscript-view";
import type { BlindedManuscript } from "@/types/api";

// Distinctive sentinels: strings that would only appear in the DOM if author identity leaked.
const AUTHOR_NAME_SENTINEL = "Kwame Osei-Sentinel";
const AFFILIATION_SENTINEL = "University of Nowhere-Sentinel";

const BASE_MANUSCRIPT: BlindedManuscript = {
  tracking_code: "SDJ-2026-0042",
  title: "Fair Scheduling for Shared GPU Clusters",
  abstract: "A scheduler balancing fairness against utilisation.",
  keywords: ["scheduling"],
  version: 1,
  status: "under_review",
};

describe("BlindedManuscriptView", () => {
  it("never renders author identity, even if an upstream bug smuggles it into the payload", () => {
    // Cast through `unknown`: a conforming backend can never produce this shape, which is
    // exactly the point — the test proves the *component* is the second line of defence,
    // not merely that a well-behaved fixture looks fine.
    const contaminated = {
      ...BASE_MANUSCRIPT,
      author_ids: ["u-999"],
      corresponding_author_id: "u-999",
      author_names: [AUTHOR_NAME_SENTINEL],
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
    expect(screen.getByText(BASE_MANUSCRIPT.tracking_code)).toBeInTheDocument();
  });

  // Compile-time half of the guarantee: the type itself has nothing to leak. If someone
  // widens `BlindedManuscript` to include an author field, this line stops compiling and
  // `make check`'s typecheck gate fails — do not delete it to make the type change land.
  it("has no author field on the type (enforced by tsc, not by this assertion)", () => {
    // @ts-expect-error BlindedManuscript intentionally has no author_ids field
    const _leak: string[] = BASE_MANUSCRIPT.author_ids;
    void _leak;
  });
});
