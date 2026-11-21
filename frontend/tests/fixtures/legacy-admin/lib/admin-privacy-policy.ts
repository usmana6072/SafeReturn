import type { MockPrivacyRequest } from "./admin-mock-data";

export const canReviewDemoPrivacy = (roles: readonly string[]) => roles.includes("security_admin");
export const privacyTypes: Record<string, string> = { access: "Data access", deletion: "Data deletion" };
export const privacyStates: Record<string, string> = { requested: "Pending Review", reviewing: "In Review", held: "Held (demo)" };
export const privacyTypeLabel = (value?: string) => value && Object.hasOwn(privacyTypes, value) ? privacyTypes[value] : "Unknown request type";
export const privacyStateLabel = (value?: string) => value && Object.hasOwn(privacyStates, value) ? privacyStates[value] : "Unknown status";
export function isMockPrivacyRequest(value: unknown): value is MockPrivacyRequest {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const entry = value as MockPrivacyRequest;
  return typeof entry.id === "string" && entry.id.startsWith("DEMO-PRIV-") &&
    [entry.customerId, entry.type, entry.status, entry.verification, entry.submittedAt, entry.updatedAt, entry.summary].every(field => field === undefined || typeof field === "string") &&
    typeof entry.demoReviewEnabled === "boolean" && Number.isSafeInteger(entry.revision) && entry.revision > 0 &&
    Array.isArray(entry.notes) && entry.notes.every(note => note && typeof note.id === "string" && typeof note.text === "string" && typeof note.author === "string" && typeof note.timestamp === "string") &&
    Array.isArray(entry.activity) && entry.activity.every(event => event && typeof event.id === "string" && typeof event.description === "string" && typeof event.actor === "string" && typeof event.timestamp === "string");
}
