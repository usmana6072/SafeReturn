import "server-only";
import { cache } from "react";
import { redirect } from "next/navigation";
import { verifiedSession, accountRequest } from "./auth/server";
import { collection } from "./independent-qr";
import { ownerApi } from "./qr-server";

export const customerSession = cache(verifiedSession);

type Order = { id: string; order_number: string; payment_status: string; fulfillment_status: string; total_pkr: string; currency_code: string; created_at: string };
type Message = { id: string; qr_id: string; qr_label: string | null; status: string; submitted_at: string };

function pageOf<T>(value: unknown, fields: (keyof T)[], limit: number) {
  if (!value || typeof value !== "object") throw Error("Invalid collection");
  const { items, next_cursor } = value as { items: unknown; next_cursor: unknown };
  if (!Array.isArray(items) || items.length > limit || !(next_cursor === null || typeof next_cursor === "string")
    || items.some(item => !item || typeof item !== "object" || fields.some(key => typeof item[key] !== "string"))) throw Error("Invalid collection");
  return { items: items as T[], more: next_cursor !== null };
}

// Request-scoped so the shell badge and the dashboard share a single authenticated read.
export const unreadMessages = cache(async (token: string) => {
  const value = await ownerApi(token)<unknown>("/me/finder-messages?status=new&limit=5");
  const page = pageOf<Message>(value, ["id", "qr_id", "status", "submitted_at"], 5);
  if (page.items.some(m => m.status !== "new" || !Number.isFinite(Date.parse(m.submitted_at))
    || !(typeof m.qr_label === "string" || m.qr_label === null))) throw Error("Invalid message");
  return page;
});

async function recentOrders(token: string) {
  // The owner endpoint orders by created_at DESC, id DESC before applying the limit.
  const value = await ownerApi(token)<unknown>("/me/orders?limit=20");
  const page = pageOf<Order>(value, ["id", "order_number", "payment_status", "fulfillment_status", "total_pkr", "currency_code", "created_at"], 20);
  if (page.items.some(o => !Number.isFinite(Date.parse(o.created_at)))) throw Error("Invalid order date");
  return page;
}

async function allocatedIdentities(token: string) {
  return collection(await ownerApi(token)<unknown>("/me/independent-qr?limit=100"));
}

export async function readCustomerDashboard() {
  const session = await customerSession();
  if (!session) redirect("/login");
  const { token } = session;
  const [identities, orders, inbox, account] = await Promise.allSettled([
    allocatedIdentities(token),
    recentOrders(token),
    unreadMessages(token),
    accountRequest(token),
  ]);
  const name = account.status === "fulfilled" ? account.value.display_name : session.user.user_metadata.display_name;
  return {
    firstName: typeof name === "string" ? name.trim().split(/\s+/)[0] : "",
    identities: identities.status === "fulfilled" ? identities.value : null,
    orders: orders.status === "fulfilled" ? orders.value : null,
    inbox: inbox.status === "fulfilled" ? inbox.value : null,
  };
}
export type DashboardData = Awaited<ReturnType<typeof readCustomerDashboard>>;
