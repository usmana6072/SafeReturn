export function canInspectDemoPrintJobs(roles: readonly string[]) {
  return roles.some(role => role === "operations" || role === "superadmin");
}

// Sample UI categories, not production API reason codes.
export const demoPrintReasons = ["Print quality issue", "Copy or size mismatch", "Physical damage", "Other sample concern"] as const;
