// Display-only demo metadata, not queue, provider or monitoring contracts.
export interface MockMonitoringJob {
  id: string;
  type: string;
  status: string;
  relatedId?: string;
  createdAt?: string;
  updatedAt?: string;
  attempts?: number;
  errorCode?: string;
}
export interface MockMonitoringAlert {
  id: string;
  component: string;
  state: string;
  severity?: string;
  createdAt?: string;
  jobId?: string;
}
export const canReadDemoMonitoring = (roles: readonly string[]) => roles.some(role => role === "operations" || role === "security_admin");
// Documented components only; this catalog contains no health observations.
export const MONITORING_COMPONENTS = [
  { id: "backend", name: "Backend API", description: "API process availability is separate from business readiness." },
  { id: "database", name: "Database", description: "Database transaction readiness requires protected, approved observations." },
  { id: "notifications", name: "Notification processing", description: "Outbox delivery records do not establish worker or provider health." },
  { id: "finance", name: "Finance synchronization", description: "Reporting mirror records do not establish worker availability." },
  { id: "printing", name: "Print workflow", description: "Print and QA records are separate from processing-health evidence." },
] as const;
export function monitoringTime(value?: string) {
  if (typeof value !== "string" || !/(?:Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) return "Timestamp unavailable";
  return new Date(value).toISOString().replace("T", " ").replace(".000Z", " UTC");
}
export const safeMonitoringId = (value: unknown): value is string => typeof value === "string" && /^[A-Za-z0-9_-]{1,80}$/.test(value);
export function isMonitoringJob(value: unknown): value is MockMonitoringJob {
  if (!value || typeof value !== "object") return false;
  const job = value as MockMonitoringJob;
  return safeMonitoringId(job.id) && safeMonitoringId(job.type) && safeMonitoringId(job.status);
}
export function isMonitoringAlert(value: unknown): value is MockMonitoringAlert {
  if (!value || typeof value !== "object") return false;
  const alert = value as MockMonitoringAlert;
  return safeMonitoringId(alert.id) && safeMonitoringId(alert.component) && safeMonitoringId(alert.state);
}
export const monitoringType = (type: string) => ({ notification: "Notification", finance_sync: "Finance sync", print: "Print processing" } as Record<string, string>)[type] ?? "Unknown type";
export const monitoringStatus = (status: string) => ({ pending: "Mock Pending", failed: "Mock Failed", completed: "Mock Completed" } as Record<string, string>)[status] ?? "Unknown state";
