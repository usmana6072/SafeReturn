export const mfaReturns = ["/admin/templates", "/admin/print-jobs", "/admin/orders", "/admin/finance/reconciliation", "/admin/inventory", "/admin/batches", "/admin/users", "/account", "/admin", "/admin/payments", "/admin/payments/review", "/admin/products", "/admin/ready-to-ship", "/admin/shipments", "/admin/notifications", "/admin/support", "/admin/privacy/exports", "/admin/finance/sheet-sync", "/admin/storage", "/admin/audit", "/admin/system"] as const;
export function mfaReturn(value: unknown): string {
  return typeof value === "string" && mfaReturns.some(path => path === value) ? value : "/account";
}
