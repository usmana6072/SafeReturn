import type { MockAdminDatabase, MockNotification } from "./admin-mock-data";
import { canReadDemoOrders } from "./admin-orders";
import { canManageDemoShipments } from "./admin-shipment-policy";

export const canReadDemoNotifications = (roles: readonly string[]) => roles.some(role => role === "operations" || role === "security_admin");
export const notificationStates: Record<string, string> = { pending: "Pending", leased: "Leased", retry: "Retry scheduled", sent: "Sent", dead: "Failed (Dead)" };
export const notificationStateLabel = (status?: string) => status && Object.hasOwn(notificationStates, status) ? notificationStates[status] : "Unknown state";
export const notificationChannelLabel = (channel?: string) => channel === "email" ? "Email" : "Unknown channel";
export const notificationFailures: Record<string, string> = { provider_failure: "Provider failure (synthetic)", rate_limited: "Rate limited (synthetic)", recipient_ineligible: "Recipient ineligible (synthetic)" };
export function maskedDemoDestination(value?: string) {
  // Only already-masked, explicitly nonfunctional fixture addresses are displayable.
  return value && /^[a-z0-9][•*]{2,}@example\.invalid$/i.test(value) ? value : "Not available";
}
export const sensitiveDemoNotification = (entry: MockNotification) => entry.sensitive || /finder|authentication|recovery|emergency/i.test(entry.category ?? "");
export function notificationRelatedTarget(entry: MockNotification, db: MockAdminDatabase, roles: readonly string[], capabilities: readonly string[]) {
  const related = entry.related;
  if (!related) return { message: "No related record stored." };
  const known = related.kind === "order" ? /^ORD-\d+$/.test(related.id) && db.orders.some(order => order?.id === related.id) : related.kind === "shipment" ? /^DEMO-SHIP-\d+$/.test(related.id) && db.shipments.some(shipment => shipment?.id === related.id) : /^DEMO-CASE-\d+$/.test(related.id) && db.supportCases.some(item => item?.id === related.id && item.demoScope === "assigned");
  if (!known) return { message: "Related record is missing or unavailable in the demo." };
  const allowed = related.kind === "order" ? canReadDemoOrders(roles) && capabilities.includes("orders.read") : related.kind === "shipment" ? canManageDemoShipments(roles) && capabilities.includes("fulfillment.manage") : roles.includes("support") && capabilities.includes("support.manage");
  if (!allowed) return { message: "Related record access requires its separate role and capability." };
  return { message: "Open related demo record", href: `/admin/${related.kind === "order" ? "orders" : related.kind === "case" ? "support" : "shipments"}/${encodeURIComponent(related.id)}` };
}
export function isMockNotification(value: unknown): value is MockNotification {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const entry = value as MockNotification;
  return typeof entry.id === "string" && entry.id.startsWith("DEMO-NTF-") &&
    [entry.event, entry.category, entry.channel, entry.status, entry.recipientId, entry.maskedDestination, entry.createdAt, entry.updatedAt, entry.templateRef, entry.title, entry.summary].every(field => field === undefined || typeof field === "string") &&
    (entry.sensitive === undefined || typeof entry.sensitive === "boolean") &&
    (entry.related === undefined || (!!entry.related && ["order", "case", "shipment"].includes(entry.related.kind) && typeof entry.related.id === "string")) &&
    (entry.attempts === undefined || (Array.isArray(entry.attempts) && entry.attempts.every(attempt => attempt && Number.isSafeInteger(attempt.number) && attempt.number > 0 && typeof attempt.timestamp === "string" && typeof attempt.outcome === "string" && (attempt.errorCode === undefined || typeof attempt.errorCode === "string"))));
}
