import type { MockAdminDatabase, MockAuditLog } from "./admin-mock-data";
import { canReadDemoOrders } from "./admin-orders";
export const canReadDemoAudit = (roles: readonly string[]) => roles.includes("security_admin");
const actions = new Set([
  "API-320 Account Suspended", "API-221 Product Draft Created", "API-241 Payment Review Approved",
  "Internal demo privacy review note added", "Internal demo note added", "Mock account suspended", "Mock account restored",
  "Demo tracking update", "Mock print QA Passed", "Mock print QA Rejected", "Demo payment follow-up recorded",
  "API-222 Product Archived", "API-221 Mock Product Draft Created", "API-301 Template Key Created",
  "API-303 Draft Revision Created", "API-304 Draft Revision Updated", "API-222 Mock Product Updated",
  "API-090 Demo Batch Created", "Demo QA Passed", "Demo QA Quarantined",
  "Mock status updated: open → investigating", "Mock status updated: investigating → resolved", "Mock status updated: resolved → closed",
]);
export const auditAction = (value?: string) => value && actions.has(value) ? value : "Restricted event label";
const actors = new Set(["security_admin", "operations", "finance", "superadmin", "support", "Demo Security Admin", "Demo Support scenario", "Demo Security Admin review scenario", "Demo Finance", "Demo Superadmin", "Demo Operations", "Operations Staff", "Sarah Jenkins (Operations)", "Security Admin", "Operations", "Superadmin", "Finance"]);
export const auditActor = (value?: string) => !value ? "Not available" : actors.has(value) ? value : "Unreviewed mock actor";
export const auditIdentifier = (value?: string) => value && /^(?:LOG-\d+|DEMO-[A-Z0-9_-]+|USR-\d+|ORD-\d+|PROD-\d+|TMP-[A-Z0-9_-]+|TP-[A-Z0-9_-]+|BATCH-[A-Z0-9_-]+|PAIR-[A-Z0-9_-]+)$/i.test(value) && value.length <= 160 ? value : "Reference unavailable";

export function auditTimestamp(value?: string): { label: string; day?: string; rank: number; time: number } {
  const unavailable = { label: "Timestamp unavailable", rank: 0, time: 0 };
  if (!value) return unavailable;
  const match = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(\.\d{1,3})?(Z|[+-]\d{2}:\d{2})?$/.exec(value);
  if (!match) return unavailable;
  const [, year, month, day, hour, minute, second, fraction = "", zone] = match;
  const wall = Date.UTC(+year, +month - 1, +day, +hour, +minute, +second);
  const date = new Date(wall);
  if (+year < 1000 || date.getUTCFullYear() !== +year || date.getUTCMonth() !== +month - 1 || date.getUTCDate() !== +day || +hour > 23 || +minute > 59 || +second > 59) return unavailable;
  if (!zone) return { label: `${year}-${month}-${day} ${hour}:${minute}:${second}${fraction} · Timezone not recorded`, day: `${year}-${month}-${day}`, rank: 1, time: wall };
  if (zone !== "Z" && (+zone.slice(1, 3) > 23 || +zone.slice(4) > 59)) return unavailable;
  const absolute = Date.parse(`${year}-${month}-${day}T${hour}:${minute}:${second}${fraction}${zone}`);
  if (!Number.isFinite(absolute)) return unavailable;
  const iso = new Date(absolute).toISOString();
  return { label: `${iso.slice(0, 10)} ${iso.slice(11, 23)} UTC`, day: iso.slice(0, 10), rank: 2, time: absolute };
}
export function isMockAuditLog(value: unknown): value is MockAuditLog {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const entry = value as MockAuditLog;
  return typeof entry.id === "string" && !!entry.id && [entry.timestamp, entry.actor, entry.action, entry.target, entry.details].every(field => field === undefined || typeof field === "string");
}
export function sortedDemoAudit(events: MockAuditLog[]) {
  return events.map((entry, index) => ({ entry, index, stamp: auditTimestamp(entry.timestamp) })).sort((a, b) => b.stamp.rank - a.stamp.rank || b.stamp.time - a.stamp.time || a.index - b.index).map(item => item.entry);
}
export function auditRelatedTarget(entry: MockAuditLog, db: MockAdminDatabase, roles: readonly string[], capabilities: readonly string[]) {
  const target = entry.target;
  if (!target || auditIdentifier(target) === "Reference unavailable") return undefined;
  const template = db.printTemplates.find(item => item?.id === target || item?.key === target);
  if (template && /^[A-Z0-9_-]+$/i.test(template.key) && capabilities.includes("printing.manage") && roles.some(role => ["operations", "security_admin", "superadmin"].includes(role))) return `/admin/templates/${encodeURIComponent(template.key)}`;
  if (/^USR-\d+$/.test(target) && db.users.some(user => user?.id === target) && roles.includes("security_admin") && capabilities.includes("users.manage")) return `/admin/users/${encodeURIComponent(target)}`;
  if (/^ORD-\d+$/.test(target) && db.orders.some(order => order?.id === target) && canReadDemoOrders(roles) && capabilities.includes("orders.read")) return `/admin/orders/${encodeURIComponent(target)}`;
  if (/^DEMO-CASE-\d+$/.test(target) && db.supportCases.some(item => item?.id === target && item.demoScope === "assigned") && roles.includes("support") && capabilities.includes("support.manage")) return `/admin/support/${encodeURIComponent(target)}`;
  if (/^DEMO-PRIV-\d+$/.test(target) && db.privacyRequests.some(item => item?.id === target) && roles.includes("security_admin") && capabilities.includes("privacy.exports")) return `/admin/privacy/exports/${encodeURIComponent(target)}`;
  return undefined;
}
