/**
 * The seeded desks a reader is most likely to want to try, one per role, mirroring
 * `backend/src/ugjcs/scripts/seed_demo.py`. Emails only: the picker fills the address so
 * nobody has to retype it, but the password is always typed by hand — a one-click "log me
 * in as an editor" button would make the sign-in step meaningless.
 *
 * The seed also carries author2 and reviewer2..7, which exist so the reviewer picker has
 * enough candidates to show affiliation exclusions. They are deliberately not listed here:
 * this is a way in, not a directory.
 */
export interface DemoAccount {
  readonly label: string;
  readonly email: string;
}

export const DEMO_ACCOUNTS: readonly DemoAccount[] = [
  { label: "Author", email: "author@sdj.test" },
  { label: "Reviewer", email: "reviewer@sdj.test" },
  { label: "Editor", email: "editor@sdj.test" },
  { label: "Editor-in-chief", email: "eic@sdj.test" },
  { label: "Administrator", email: "admin@sdj.test" },
];
