export function canReviewDemoPayments(roles: readonly string[]): boolean {
  return roles.some(role => role === "finance" || role === "superadmin");
}
