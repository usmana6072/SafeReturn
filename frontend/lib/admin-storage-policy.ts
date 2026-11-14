import type { MockStorageRecord } from "./admin-mock-data";

export const canReadDemoStorage = (roles: readonly string[]) => roles.some(role => ["operations", "finance", "security_admin", "superadmin"].includes(role));
export const storagePolicies = [
  { id: "print_artifact", label: "Print artifacts", storageClass: "Private Supabase Storage", source: "Doc 07 A12 / BTR-10", rule: "Confirmed delivery and latest authorized reprint, verified settlement, completed work and absence of active grants, holds, disputes or reprint requests must be reviewed. Future PDF grace design is approved; activation and policy evidence remain gated." },
  { id: "payment_evidence", label: "Payment evidence", storageClass: "Private Supabase Storage", source: "Doc 07 A12 / BTR-10", rule: "Finance/legal record-class requirements and dispute exceptions must be verified. Review alone does not authorize deletion; retention duration remains unset." },
  { id: "product_assets", label: "Public product assets", storageClass: "Cloudinary — public marketing/product assets only", source: "Doc 07 A9 / API-242 boundary", rule: "Public asset unlink and cleanup policy is separate from private file retention. Not Defined / Requires Verification." },
  { id: "notification_records", label: "Notification records", storageClass: "Database outbox / attempt metadata", source: "Doc 03 retention register / Doc 07", rule: "Limited non-PII troubleshooting history; actual retention schedule requires verification. No duration or purge authority established here." },
  { id: "audit_records", label: "Audit records", storageClass: "Database audit history", source: "Doc 07 A11–A12", rule: "Preserve required security and lifecycle evidence; record-class policy and exceptions require verification. No audit deletion through this screen." },
  { id: "backups", label: "Backups", storageClass: "Backup system — provider configuration unverified", source: "Doc 07 A12 / BTR-12", rule: "Backup expiry, restoration tombstones and retained-data exceptions require an approved policy. Application deletion is not immediate erasure from backups." },
] as const;
export const storageCategory = (value?: string) => storagePolicies.find(policy => policy.id === value)?.label ?? "Unknown category";
export const storageLifecycle = (value?: string) => value === "retained" ? "Retained (demo)" : value === "quarantined" ? "Quarantined (demo)" : "Unknown";
export const storageHold = (value?: boolean) => value === true ? "Active (demo)" : value === false ? "Not Active (demo)" : "Unknown";
export const storageSize = (value?: number) => typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? `${value.toLocaleString("en-US")} bytes` : "Not available";
export function canReadStorageRecord(entry: MockStorageRecord, roles: readonly string[]) {
  if (roles.some(role => ["security_admin", "superadmin"].includes(role))) return true;
  return entry.category === "print_artifact" ? roles.includes("operations") : entry.category === "payment_evidence" && roles.includes("finance");
}
export function isMockStorageRecord(value: unknown): value is MockStorageRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const entry = value as MockStorageRecord;
  return typeof entry.id === "string" && entry.id.startsWith("DEMO-STORAGE-") &&
    [entry.category, entry.createdAt, entry.lifecycle].every(field => field === undefined || typeof field === "string") &&
    (entry.sizeBytes === undefined || typeof entry.sizeBytes === "number") && (entry.onHold === undefined || typeof entry.onHold === "boolean") &&
    (entry.activity === undefined || Array.isArray(entry.activity) && entry.activity.every(event => event && typeof event.id === "string" && typeof event.timestamp === "string" && event.kind === "review_noted"));
}
