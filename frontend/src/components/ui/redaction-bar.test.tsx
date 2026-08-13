import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RedactedAuthorSlot, RevealedAuthorSlot } from "./redaction-bar";

const AUTHOR_NAME_SENTINEL = "Kwame Osei-Sentinel";

describe("RedactedAuthorSlot", () => {
  it("never renders an author name — the slot has no name prop to leak", () => {
    render(<RedactedAuthorSlot />);
    expect(screen.getByText(/author withheld/i)).toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain(AUTHOR_NAME_SENTINEL);
  });
});

describe("RevealedAuthorSlot", () => {
  it("renders the names it is given, in the same slot shape as the redacted version", () => {
    render(<RevealedAuthorSlot names={[AUTHOR_NAME_SENTINEL]} />);
    expect(screen.getByText(AUTHOR_NAME_SENTINEL)).toBeInTheDocument();
  });

  it("falls back to a plain label when there are no names", () => {
    render(<RevealedAuthorSlot names={[]} />);
    expect(screen.getByText("Unattributed")).toBeInTheDocument();
  });
});
