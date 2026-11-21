import type { MockOrder } from "./admin-mock-data";

// Page permissions supplement, and never replace, AdminPage's real MFA/capability guard.
export function canReadDemoOrders(roles: readonly string[]): boolean {
  return roles.some(role => ["operations", "finance", "support", "superadmin"].includes(role));
}

export function filterDemoOrders(orders: MockOrder[], search: string, status: string, payment: string) {
  const query = search.trim().toLowerCase();
  return orders.filter(order =>
    (!query || order.id.toLowerCase().includes(query) || order.customer.toLowerCase().includes(query)) &&
    (status === "all" || order.status === status) &&
    (payment === "all" || (order.payment || "Unknown") === payment)
  );
}

export function orderAmount(amount: number | string | undefined, currency?: string): string {
  if (amount === undefined || amount === null || amount === "") return "Not available";
  const value = typeof amount === "number" ? amount : /^\d+(\.\d+)?$/.test(amount) ? Number(amount) : NaN;
  if (!Number.isFinite(value)) return "Not available";
  const formatted = value.toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // A legacy '$' display alone does not establish an ISO currency or an exchange rate.
  return currency && /^[A-Z]{3}$/.test(currency)
    ? `${currency} ${formatted}`
    : `${formatted} · Currency not specified`;
}
