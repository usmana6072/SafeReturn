import { AdminStatusBadge } from "./admin-ui";
function userDisplayText(value: unknown, fallback = "Not available") { return typeof value === "string" && value.trim() ? value.trim() : fallback; }

export function UserStatusBadge({ value }: { value: unknown }) {
  const status = userDisplayText(value, "Unknown");
  return <AdminStatusBadge label={status} variant={status === "Active" ? "success" : status === "Suspended" ? "danger" : "neutral"} />;
}

export function UserMFAIndicator({ enrolled }: { enrolled: unknown }) {
  return <AdminStatusBadge label={enrolled === true ? "MFA Enrolled" : enrolled === false ? "None" : "Unknown"} variant={enrolled === true ? "success" : "neutral"} />;
}
