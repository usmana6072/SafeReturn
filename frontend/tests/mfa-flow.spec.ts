import { test, expect } from "@playwright/test";
import { runMfa } from "../lib/auth/mfa-flow";
import type { staffSecurity } from "../lib/auth/staff";
function fixture({ after = true, revoked = false, providerError = false as boolean | { status?: number; code?: string } } = {}) {
  let reads = 0; let mutations = 0;
  const authenticate = (async () => {
    reads++;
    if (revoked) throw new Error("revoked session or role");
    return { security: { roles: ["finance"], mfa_verified: reads > 1 && after }, client: { auth: { mfa: {
      listFactors: async () => ({ data: { all: [{ id: "factor", factor_type: "totp" }] }, error: null }),
      challengeAndVerify: async () => { mutations++; return { error: providerError ? (typeof providerError === "object" ? providerError : {}) : null }; },
    } } } };
  }) as unknown as typeof staffSecurity;
  const form = new FormData(); form.set("mode", "verify"); form.set("factor", "factor"); form.set("code", "123456"); form.set("returnTo", "/admin/payments");
  return { authenticate, form, reads: () => reads, mutations: () => mutations };
}
test("MFA action requires exact Origin before all authentication/mutation", async () => {
  const f = fixture();
  expect((await runMfa({}, f.form, "https://evil.test", "https://app.test", f.authenticate)).error).toBeTruthy();
  expect(f.reads()).toBe(0); expect(f.mutations()).toBe(0);
});
test("MFA action rechecks live assurance before fixed return", async () => {
  const f = fixture();
  expect((await runMfa({}, f.form, "https://app.test", "https://app.test", f.authenticate)).destination).toBe("/admin/payments");
  expect(f.reads()).toBe(2);
});
for (const options of [{ after: false }, { revoked: true }, { providerError: true }]) {
  test(`MFA action fails closed ${JSON.stringify(options)}`, async () => {
    const f = fixture(options);
    const result = await runMfa({}, f.form, "https://app.test", "https://app.test", f.authenticate);
    expect(result.error).toBeTruthy(); expect(result.destination).toBeUndefined();
    if (options.revoked) expect(f.mutations()).toBe(0);
  });
}
test("MFA action sanitizes return after genuine assurance", async () => {
  const f = fixture(); f.form.set("returnTo", "//evil.test");
  expect((await runMfa({}, f.form, "https://app.test", "https://app.test", f.authenticate)).destination).toBe("/account");
});

test("untrusted previous action state cannot supply a redirect on failure", async () => {
  const f = fixture({ providerError: true });
  const result = await runMfa({ destination: "https://evil.test" } as never, f.form, "https://app.test", "https://app.test", f.authenticate);
  expect(result.destination).toBeUndefined();
  expect(result.error).toBeTruthy();
});

for (const [error, message] of [
  [{ status: 429 }, "Too many verification attempts"],
  [{ status: 401 }, "sign-in session expired"],
  [{ code: "mfa_challenge_expired" }, "Verification expired"],
  [{ code: "mfa_verification_failed" }, "Code invalid or expired"],
  [{ code: "mfa_verification_rejected" }, "authentication policy"],
  [{ code: "mfa_ip_address_mismatch" }, "connection changed"],
  [{ code: "mfa_factor_not_found" }, "no longer available"],
  [{ status: 503 }, "verification is unavailable"],
] as const) {
  test(`MFA distinguishes provider failures ${JSON.stringify(error)}`, async () => {
    const f = fixture({ providerError: error });
    const result = await runMfa({}, f.form, "https://app.test", "https://app.test", f.authenticate);
    expect(result.error).toContain(message);
    expect(result.destination).toBeUndefined();
    expect(f.reads()).toBe(1);
  });
}
