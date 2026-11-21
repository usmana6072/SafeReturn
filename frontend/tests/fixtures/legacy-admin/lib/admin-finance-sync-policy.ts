import type { MockFinanceSync } from "./admin-mock-data";
export const canReadDemoFinanceSync = (roles: readonly string[]) => roles.some(role => ["finance", "security_admin", "superadmin"].includes(role));
export const financeSyncLabels: Record<string, string> = { pending: "Pending", synced: "Mock Synced", retry: "Mock Retry Pending", failed: "Failed" };
export const financeSyncLabel = (value?: string) => value && Object.hasOwn(financeSyncLabels, value) ? financeSyncLabels[value] : "Unknown";
export const financeSyncErrors: Record<string, string> = { destination_unavailable: "Demo destination unavailable", missing_configuration: "Demo configuration missing", validation_issue: "Demo validation issue" };
export const financeSyncError = (value?: string) => !value ? "Not recorded" : Object.hasOwn(financeSyncErrors, value) ? financeSyncErrors[value] : "Unrecognized error — private details unavailable";
export function isMockFinanceSync(value: unknown): value is MockFinanceSync {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const entry = value as MockFinanceSync;
  return typeof entry.id === "string" && entry.id.startsWith("DEMO-SYNC-") &&
    [entry.orderId, entry.paymentId, entry.currency, entry.status, entry.createdAt, entry.errorCode].every(field => field === undefined || typeof field === "string") &&
    (entry.amount === undefined || typeof entry.amount === "string" || typeof entry.amount === "number") &&
    (entry.attempts === undefined || (Array.isArray(entry.attempts) && entry.attempts.every(attempt => attempt && typeof attempt.id === "string" && typeof attempt.timestamp === "string" && typeof attempt.result === "string" && (attempt.errorCode === undefined || typeof attempt.errorCode === "string"))));
}
