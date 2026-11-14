import type { MockSupportCase } from "./admin-mock-data";

export const supportLabels: Record<string, string> = {
  open: "Open", investigating: "Investigating", resolved: "Resolved", closed: "Closed",
  activation: "Activation", lost_tag: "Lost tag", payment: "Payment", privacy: "Privacy",
  ownership_dispute: "Ownership dispute", other: "Other", low: "Low", normal: "Normal", high: "High", urgent: "Urgent",
};
export const supportText = (value?: string) => value ? supportLabels[value] ?? value : "Not available";
export const canManageDemoSupport = (roles: readonly string[]) => roles.includes("support");
export function sensitiveSupportCase(entry: MockSupportCase) {
  return ["payment", "privacy", "ownership_dispute"].includes(entry.category) || entry.requiresEscalation;
}
export function demoSupportNextStates(entry: MockSupportCase): string[] {
  if (!Object.hasOwn(supportLabels, entry.category) || !["activation", "lost_tag", "payment", "privacy", "ownership_dispute", "other"].includes(entry.category)) return [];
  if (entry.status === "open") return ["investigating"];
  if (sensitiveSupportCase(entry) || entry.hasActiveHold) return [];
  return entry.status === "investigating" ? ["resolved"] : entry.status === "resolved" ? ["closed"] : [];
}
export function isDemoSupportCase(value: unknown): value is MockSupportCase {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const entry = value as MockSupportCase;
  return [entry.customerId, entry.subject, entry.description, entry.createdAt, entry.updatedAt].every(field => field === undefined || typeof field === "string") &&
    typeof entry.id === "string" && !!entry.id && typeof entry.status === "string" &&
    typeof entry.category === "string" && typeof entry.priority === "string" &&
    ["assigned", "unassigned", "other"].includes(entry.demoScope) && Number.isSafeInteger(entry.revision) && entry.revision > 0 &&
    typeof entry.requiresEscalation === "boolean" && typeof entry.hasActiveHold === "boolean" &&
    Array.isArray(entry.notes) && entry.notes.every(note => note && typeof note.id === "string" && typeof note.text === "string" && typeof note.author === "string" && typeof note.timestamp === "string") &&
    Array.isArray(entry.activity) && entry.activity.every(event => event && typeof event.id === "string" && typeof event.event === "string" && typeof event.actor === "string" && typeof event.timestamp === "string");
}
