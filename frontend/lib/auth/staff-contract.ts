export const staffRoles = ["support", "operations", "finance", "security_admin", "superadmin"] as const;
export const capabilities = ["catalog.manage", "payments.review", "fulfillment.manage", "printing.manage", "notifications.manage", "support.manage"] as const;
export type Capability = typeof capabilities[number];
export type StaffSecurityState = { roles: string[]; mfa_verified: boolean; capabilities: Capability[] };
export function parseStaffSecurity(value: unknown): StaffSecurityState {
  if (!value || typeof value !== "object") throw new Error("unavailable");
  const state = value as StaffSecurityState;
  if (!Array.isArray(state.roles) || !state.roles.length || !state.roles.every(role => staffRoles.some(known => known === role))
    || new Set(state.roles).size !== state.roles.length || typeof state.mfa_verified !== "boolean"
    || !Array.isArray(state.capabilities) || !state.capabilities.every(cap => capabilities.includes(cap))
    || new Set(state.capabilities).size !== state.capabilities.length
    || (!state.mfa_verified && state.capabilities.length)) throw new Error("unavailable");
  return { roles: state.roles, mfa_verified: state.mfa_verified, capabilities: state.capabilities };
}
export const adminModules: { path: string; capability: Capability; en: string; ur: string; description: string; descriptionUr: string }[] = [
  { path: "/admin/products", capability: "catalog.manage", en: "Products", ur: "مصنوعات", description: "Manage the product catalog and publication.", descriptionUr: "مصنوعات اور ان کی اشاعت کا انتظام کریں۔" },
  { path: "/admin/payments", capability: "payments.review", en: "Payments", ur: "ادائیگیاں", description: "Review payment evidence and independently verified settlement.", descriptionUr: "ادائیگی کے ثبوت اور تصدیق شدہ وصولی کا جائزہ لیں۔" },
  { path: "/admin/ready-to-ship", capability: "fulfillment.manage", en: "Ready to ship", ur: "ترسیل کے لیے تیار", description: "Open the packing and dispatch queue.", descriptionUr: "پیکنگ اور روانگی کی فہرست کھولیں۔" },
  { path: "/admin/support", capability: "support.manage", en: "Support cases", ur: "معاونت کے معاملات", description: "Claim and review assigned support cases.", descriptionUr: "اپنے سپرد معاونت کے معاملات کا جائزہ لیں۔" },
  { path: "/admin/notifications", capability: "notifications.manage", en: "Notifications", ur: "اطلاعات", description: "Inspect delivery metadata and reviewed single-event retries.", descriptionUr: "ترسیل کی معلومات اور واحد اطلاع کی دوبارہ کوشش کا جائزہ لیں۔" },
  { path: "/admin/shipments", capability: "fulfillment.manage", en: "Shipments", ur: "ترسیلات", description: "Manage dispatch, tracking and shipment history.", descriptionUr: "روانگی، ٹریکنگ اور ترسیل کی تاریخ کا انتظام کریں۔" },
];
export function permittedModules(state: StaffSecurityState) {
  return state.mfa_verified ? adminModules.filter(module => state.capabilities.includes(module.capability)) : [];
}
export function staffLanding(state: StaffSecurityState | null) {
  return !state ? "/account" : state.mfa_verified ? "/admin" : "/admin/security/mfa?returnTo=%2Fadmin";
}
