import Link from 'next/link';
import { ownerApi, ownerSession } from '../../../lib/qr-server';
import { orderStatus } from '../../../lib/order-status';
import { getLanguage } from '../../../lib/i18n';
import { Unavailable } from '../../../components/customer';
import { ShipmentRefresh } from '../../../components/shipment-refresh';
import type { BuyerShipment } from '../../../lib/fulfillment-workflow';

export const dynamic = 'force-dynamic';
export const metadata = { title: 'My Shipments | SafeReturn', robots: { index: false, follow: false } };

type ShipmentPage = { items: BuyerShipment[]; next_cursor: string | null };

export default async function Page({ searchParams }: { searchParams: Promise<{ cursor?: string | string[] }> }) {
  const { cursor } = await searchParams;
  const ur = await getLanguage() === 'ur';
  const session = await ownerSession();
  const t = (en: string, translated: string) => ur ? translated : en;
  let shipments: ShipmentPage | undefined;
  try {
    if (cursor === undefined || typeof cursor === 'string' && cursor.length <= 2048) {
      const query = cursor ? `?${new URLSearchParams({ cursor })}` : '';
      shipments = await ownerApi(session.token)<ShipmentPage>(`/me/shipments${query}`);
    }
  } catch { /* The authenticated route supplies the existing unavailable state. */ }

  return <>
    <div className="customer-heading"><h1>{t('My shipments', 'میری ترسیلات')}</h1><ShipmentRefresh ur={ur} /></div>
    {!shipments ? <Unavailable ur={ur} /> : shipments.items.length === 0 ?
      <p className="empty-state">{t('No shipments yet.', 'ابھی کوئی ترسیل نہیں۔')}</p> :
      <div className="order-list">{shipments.items.map(shipment => <article className="qr-card" key={shipment.id}>
        <h2><bdi>{shipment.order_number}</bdi></h2>
        <p>{orderStatus(shipment.status, ur)}</p>
        <p>{t('Courier', 'کوریئر')}: <bdi>{shipment.carrier}</bdi></p>
        <p>{t('Tracking number', 'ٹریکنگ نمبر')}: <bdi>{shipment.tracking_reference ?? '—'}</bdi></p>
        <p>{t('Order total', 'آرڈر کی کل رقم')}: <bdi>{shipment.currency_code} {shipment.total_pkr}</bdi></p>
        {shipment.order_items.map((item, index) => <p key={index}>{item.product_name_snapshot} × {item.quantity}</p>)}
        <Link href={`/orders/${shipment.order_id}`} prefetch={false}>{t('View order', 'آرڈر دیکھیں')}</Link>
      </article>)}</div>}
    {cursor && <Link className="button secondary" href="/shipments">{t('Latest shipments', 'تازہ ترین ترسیلات')}</Link>}
    {shipments?.next_cursor && <Link className="button secondary" href={`/shipments?${new URLSearchParams({ cursor: shipments.next_cursor })}`}>
      {t('Older shipments', 'پرانی ترسیلات')}
    </Link>}
  </>;
}
