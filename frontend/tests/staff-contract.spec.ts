import { test, expect } from "@playwright/test";
import { parseStaffSecurity, permittedModules, staffLanding, type Capability } from "../lib/auth/staff-contract";
import { mfaReturn } from "../lib/auth/mfa-return";
for (const cap of ["catalog.manage", "payments.review", "fulfillment.manage", "printing.manage", "notifications.manage", "support.manage"] as Capability[]) {
  test(`navigation uses backend capability ${cap}`, () => {
    const state = parseStaffSecurity({ roles: ["support"], mfa_verified: true, capabilities: [cap] });
    expect(permittedModules(state).every(module => module.capability === cap)).toBe(true);
  });
}
for (const value of [null, {}, { roles: ["finance"], mfa_verified: false, capabilities: ["payments.review"] },
  { roles: ["unknown"], mfa_verified: true, capabilities: [] }, { roles: ["finance"], mfa_verified: true, capabilities: ["everything"] }]) {
  test(`malformed capability state fails closed ${JSON.stringify(value)}`, () => expect(() => parseStaffSecurity(value)).toThrow());
}
test("customers, staff AAL1, staff AAL2 land on fixed routes", () => {
  expect(staffLanding(null)).toBe("/account");
  expect(staffLanding({ roles: ["finance"], mfa_verified: false, capabilities: [] })).toBe("/admin/security/mfa?returnTo=%2Fadmin");
  expect(staffLanding({ roles: ["finance"], mfa_verified: true, capabilities: ["payments.review"] })).toBe("/admin");
  expect(mfaReturn("/admin")).toBe("/admin");
  expect(mfaReturn("/admin?returnTo=https://evil.test")).toBe("/account");
});
