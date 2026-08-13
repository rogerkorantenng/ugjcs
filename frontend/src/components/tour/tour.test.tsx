import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { Tour, type TourStep } from "./tour";

// The test runner's Node-provided `localStorage` is inert (no `--localstorage-file`), so
// give the tour a deterministic in-memory Storage instead of relying on the environment.
const store = new Map<string, string>();
beforeAll(() => {
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => void store.set(key, String(value)),
      removeItem: (key: string) => void store.delete(key),
      clear: () => store.clear(),
    },
  });
});

const STEPS: TourStep[] = [
  { target: "alpha", title: "Alpha step", body: "The first stop." },
  { target: "beta", title: "Beta step", body: "The second stop." },
  { target: "gamma", title: "Gamma step", body: "The final stop." },
];

/** Renders anchor elements for the given targets alongside the tour itself, the way a
 * dashboard page carries `data-tour` attributes next to its mounted `<Tour>`. */
function Fixture({ anchors, storageKey }: { anchors: string[]; storageKey: string }) {
  return (
    <>
      {anchors.map((anchor) => (
        <div key={anchor} data-tour={anchor}>
          {anchor} anchor
        </div>
      ))}
      <Tour steps={STEPS} storageKey={storageKey} />
    </>
  );
}

describe("Tour", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("offers the welcome card on first visit only — never again after a choice", async () => {
    const { unmount } = render(<Fixture anchors={["alpha", "beta", "gamma"]} storageKey="ugjcs-tour-test-v1" />);
    expect(screen.getByText("Let us show you around.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Skip" }));
    expect(screen.queryByText("Let us show you around.")).not.toBeInTheDocument();
    expect(window.localStorage.getItem("ugjcs-tour-test-v1")).toBe("seen");

    unmount();
    render(<Fixture anchors={["alpha", "beta", "gamma"]} storageKey="ugjcs-tour-test-v1" />);
    expect(screen.queryByText("Let us show you around.")).not.toBeInTheDocument();
  });

  it("advances and steps back through the script, ending on Done", async () => {
    render(<Fixture anchors={["alpha", "beta", "gamma"]} storageKey="ugjcs-tour-test-v2" />);
    await userEvent.click(screen.getByRole("button", { name: "Start tour" }));

    expect(screen.getByRole("dialog")).toHaveTextContent("1 of 3");
    expect(screen.getByText("Alpha step")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("2 of 3");
    expect(screen.getByText("Beta step")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Alpha step")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Gamma step")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("skips steps whose target is missing and keeps the count honest", async () => {
    render(<Fixture anchors={["alpha", "gamma"]} storageKey="ugjcs-tour-test-v3" />);
    await userEvent.click(screen.getByRole("button", { name: "Start tour" }));

    expect(screen.getByRole("dialog")).toHaveTextContent("1 of 2");
    expect(screen.getByText("Alpha step")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Gamma step")).toBeInTheDocument();
    expect(screen.queryByText("Beta step")).not.toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    render(<Fixture anchors={["alpha", "beta", "gamma"]} storageKey="ugjcs-tour-test-v4" />);
    await userEvent.click(screen.getByRole("button", { name: "Start tour" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
