import type { MockUser } from "./admin-mock-data";
import { DEMO_ROLES, type DemoRoleName } from "./admin-navigation";
import { staffRoles } from "./auth/staff-contract";

export const canInspectDemoStaff = (roles: readonly string[]) => roles.includes("security_admin");
export function canonicalRoleId(role: DemoRoleName) {
  const candidate = role.toLowerCase().replaceAll(" ", "_");
  return staffRoles.find(id => id === candidate);
}
export function demoStaffRole(user: MockUser): DemoRoleName | undefined {
  // Existing explicitly marked staff fixture; this is a legacy display
  // relationship, not a role grant or a verified provisioning registry.
  return user.role === "Operations Staff" ? DEMO_ROLES.find(role => canonicalRoleId(role) === "operations") : undefined;
}
export function getDemoStaff(users: MockUser[]) {
  return users.filter(user => user && typeof user === "object" && !Array.isArray(user) && demoStaffRole(user));
}
