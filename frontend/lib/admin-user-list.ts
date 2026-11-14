import type { MockUser } from "./admin-mock-data";

// Demo visibility supplements the existing server capability/MFA guard.
// It never widens the security_admin-only live directory contract.
export function canReadDemoUsers(roles: readonly string[]) {
  return roles.some(role => ["support", "security_admin", "superadmin"].includes(role));
}

export function canGovernDemoUsers(roles: readonly string[]) {
  return roles.includes("security_admin");
}

export function userDisplayText(value: unknown, fallback = "Not available") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

export function filterDemoUsers(users: MockUser[], query: string, status: string, type: string) {
  const search = query.trim().toLowerCase();
  return users.filter(user =>
    (!search || [user.id, user.name, user.email].some(value => typeof value === "string" && value.toLowerCase().includes(search))) &&
    (status === "all" || userDisplayText(user.status, "Unknown") === status) &&
    (type === "all" || userDisplayText(user.role, "Unknown") === type)
  );
}

export function demoUserQRCount(value: unknown) {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0
    ? `${value} paired ${value === 1 ? "profile" : "profiles"}` : "Not available";
}
