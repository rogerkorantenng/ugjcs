import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProblemAlert } from "./alert";

describe("ProblemAlert", () => {
  it("surfaces the problem's title and detail with an alert role", () => {
    render(
      <ProblemAlert
        problem={{
          type: "about:blank",
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
