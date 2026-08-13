import type { Role } from "@/types/api";

/**
 * Where each role's workspace lives, in precedence order: an account holding several
 * roles lands on the most senior desk it can operate. Administrators land on the
 * accounts console at `/admin`; anyone else falls through to the author view every
 * account can render.
 */
const HOMES: readonly (readonly [Role, string])[] = [
  ["administrator", "/admin"],
  ["editor_in_chief", "/editor"],
  ["editor", "/editor"],
  ["reviewer", "/reviewer"],
  ["author", "/author"],
];

export function roleHome(roles: readonly Role[]): string {
  for (const [role, home] of HOMES) if (roles.includes(role)) return home;
  return "/author";
}
