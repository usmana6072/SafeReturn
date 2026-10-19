export const mfaReturns = ["/account", "/admin", "/admin/payments", "/admin/products", "/admin/ready-to-ship", "/admin/shipments", "/admin/notifications", "/admin/support"] as const;
export function mfaReturn(value: unknown): string {
  return typeof value === "string" && mfaReturns.some(path => path === value) ? value : "/account";
}
