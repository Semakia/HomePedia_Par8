// Roles — SQLite has no native enum, so User.role is a plain string validated
// here. Client-safe (no server imports) so both UI and server code can use it.

export const ROLES = ["USER", "ADMIN"] as const;
export type Role = (typeof ROLES)[number];

export const DEFAULT_ROLE: Role = "USER";

/** Narrow an unknown role string to a valid Role, falling back to USER. */
export function asRole(value: unknown): Role {
  return ROLES.includes(value as Role) ? (value as Role) : DEFAULT_ROLE;
}

export function isAdmin(role: unknown): boolean {
  return asRole(role) === "ADMIN";
}
