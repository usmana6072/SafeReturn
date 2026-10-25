export const staffRoles = ["support", "operations", "finance", "security_admin", "superadmin"] as const;
export const capabilities = ["orders.read", "inventory.manage", "users.manage", "catalog.manage", "payments.review", "fulfillment.manage", "printing.manage", "notifications.manage", "support.manage", "privacy.exports", "finance.mirror", "storage.metadata", "storage.holds", "audit.search"] as const;
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
  { path: "/admin/print-jobs", capability: "printing.manage", en: "Print job metadata", ur: "پرنٹ کام کی معلومات", description: "Inspect job versions and artifact metadata.", descriptionUr: "کام کے ورژن اور فائل کی معلومات دیکھیں۔" },
  { path: "/admin/orders", capability: "orders.read", en: "Orders", ur: "آرڈر", description: "Search authorized order metadata.", descriptionUr: "مجاز آرڈر معلومات تلاش کریں۔" },
  { path: "/admin/finance/reconciliation", capability: "payments.review", en: "Reconciliation signals", ur: "مالی مطابقت کے اشارے", description: "Inspect stored-state signals and unavailable checks.", descriptionUr: "محفوظ حالت کے اشارے اور غیر دستیاب جانچ دیکھیں۔" },
  { path: "/admin/inventory", capability: "inventory.manage", en: "Inventory", ur: "ذخیرہ", description: "Inspect pairs, batches and explicit QA observations.", descriptionUr: "جوڑوں، بیچ اور جانچ کے مشاہدات کا جائزہ لیں۔" },
  { path: "/admin/batches", capability: "inventory.manage", en: "Batches", ur: "بیچ", description: "Inspect or generate paired inventory.", descriptionUr: "جوڑوں کے ذخیرے کا جائزہ لیں یا تیار کریں۔" },
  { path: "/admin/users", capability: "users.manage", en: "User directory", ur: "صارفین کی فہرست", description: "Inspect limited account state and case-approved actions.", descriptionUr: "محدود اکاؤنٹ معلومات اور مجاز کارروائیوں کا جائزہ لیں۔" },
  { path: "/admin/system", capability: "notifications.manage", en: "System observations", ur: "نظام کے مشاہدات", description: "Inspect process liveness and explicit telemetry gaps.", descriptionUr: "عمل کے جواب اور مشاہدات کی کمی دیکھیں۔" },
  { path: "/admin/audit", capability: "audit.search", en: "Audit search", ur: "آڈٹ تلاش", description: "Search restricted event metadata.", descriptionUr: "محدود واقعات کی معلومات تلاش کریں۔" },
  { path: "/admin/finance/sheet-sync", capability: "finance.mirror", en: "Finance mirror", ur: "مالیاتی آئینہ", description: "Inspect masked reporting state and reviewed retries.", descriptionUr: "محدود رپورٹ اور دوبارہ کوشش کا جائزہ لیں۔" },
  { path: "/admin/storage", capability: "storage.metadata", en: "Storage and retention", ur: "ذخیرہ اور برقرار رکھنا", description: "Inspect artifact metadata and authorized retention controls.", descriptionUr: "فائل کی معلومات اور مجاز پابندیوں کا جائزہ لیں۔" },
  { path: "/admin/privacy/exports", capability: "privacy.exports", en: "Reviewed exports", ur: "منظور شدہ برآمدات", description: "Review limited exports for specifically authorized privacy cases.", descriptionUr: "مخصوص مجاز رازداری معاملات کی محدود برآمدات کا جائزہ لیں۔" },
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
