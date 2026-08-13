// The role-to-links map behind `AppNav`, kept as data so the nav component stays purely
// presentational. `tour` marks a link as an onboarding-tour anchor (`data-tour`): the
// author tour points at "Submit" from the dashboard, where the page itself has no submit
// button to spotlight.
export const LINKS: Record<string, { href: string; label: string; tour?: string }[]> = {
  author: [{ href: "/author", label: "My submissions" }, { href: "/author/submit", label: "Submit", tour: "author-submit" }],
  reviewer: [{ href: "/reviewer", label: "My assignments" }],
  editor: [{ href: "/editor", label: "Screening queue" }],
  editor_in_chief: [{ href: "/editor", label: "Screening queue" }],
  administrator: [{ href: "/admin", label: "Accounts" }],
};

// Exactly the routes that mount a `<Tour>`; the "Show me around" trigger only renders
// where dispatching the start event will actually reach a listener.
export const TOUR_ROOTS = new Set(["/author", "/reviewer", "/editor"]);

export const ROLE_LABELS: Record<string, string> = {
  author: "Author",
  reviewer: "Reviewer",
  editor: "Editor",
  editor_in_chief: "Editor-in-Chief",
  administrator: "Administrator",
};
