import { orderStatus } from "../../../lib/order-status";
import Link from "next/link";
import { ownerApi, ownerSession } from "../../../lib/qr-server";
import { getLanguage } from "../../../lib/i18n";
import { Unavailable } from "../../../components/customer";

type Order = {
  id: string;
  order_number: string;
  order_status: string;
  payment_status: string;
  fulfillment_status: string;
  currency_code: string;
  total_pkr: string;
  created_at: string;
};

export default async function OrdersPage({ searchParams }: { searchParams: Promise<{ cursor?: string }> }) {
  const cursor = (await searchParams).cursor;
  let next: string | null = null;
  const ur = await getLanguage() === "ur";
  const session = await ownerSession();
  let orders: Order[] = [];
  try {
    const response = await ownerApi(session.token)<{ items: Order[]; next_cursor: string | null }>("/me/orders" + (cursor ? "?cursor=" + encodeURIComponent(cursor) : ""));
    next = response.next_cursor;
    orders = response.items;
  } catch {
    return <><h1>{ur ? "میرے آرڈرز" : "My orders"}</h1><Unavailable ur={ur} /></>;
  }
  return <>
    <div className="customer-heading"><h1>{ur ? "میرے آرڈرز" : "My orders"}</h1><Link className="button secondary" href="/shop">{ur ? "خریداری" : "Shop"}</Link></div>
    {orders.length === 0 ? <div className="empty-state"><p>{ur ? "ابھی کوئی آرڈر نہیں۔" : "No orders yet."}</p></div> :
      <div className="order-list">{orders.map(order => <article className="qr-card" key={order.id}>
        <p className="eyebrow"><bdi>{order.order_number}</bdi></p>
        <h2><bdi>{order.currency_code} {order.total_pkr}</bdi></h2>
        <p>{ur ? "ادائیگی" : "Payment"}: <bdi>{orderStatus(order.payment_status, ur)}</bdi></p>
        <p>{ur ? "فراہمی" : "Fulfillment"}: <bdi>{orderStatus(order.fulfillment_status, ur)}</bdi></p>
        <Link className="button secondary" href={`/orders/${order.id}`}>{ur ? "آرڈر دیکھیں" : "View order"}</Link>
      </article>)}</div>}
    {next && <Link className="button secondary" href={"/orders?cursor="+encodeURIComponent(next)}>{ur ? "اگلے آرڈرز" : "Next orders"}</Link>}
  </>;
}
