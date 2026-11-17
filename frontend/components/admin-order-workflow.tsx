'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { AdminCard, AdminPageContainer, AdminPageHeader } from './admin-ui';
import { orderStatus } from '../lib/order-status';
import { workflowRequest, type OrderShipment, type OrderSummary } from '../lib/fulfillment-workflow';
import styles from './admin-orders.module.css';

export function OrderDetails({ orderId, ur }: { orderId: string; ur: boolean }) {
  const [order, setOrder] = useState<OrderSummary | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    workflowRequest<OrderSummary>('order', orderId, { signal: controller.signal })
      .then(setOrder).catch(error => { if (!controller.signal.aborted) setError(error.message); });
    return () => controller.abort();
  }, [orderId]);

  return <div className={styles.screen}><AdminPageContainer>
    <AdminPageHeader title={order?.order_number ?? 'Order details'} actions={<Link href="/admin/orders">Back to Orders</Link>} />
    {error ? <p role="alert" className={styles.notice}>{error}</p> : !order ? <p role="status">Loading order…</p> : <>
      <AdminCard><section className={styles.cardBody}>
        <h2>Order status</h2>
        <dl className={styles.facts}>{[
          ['Order', orderStatus(order.order_status, ur)], ['Payment', orderStatus(order.payment_status, ur)],
          ['Fulfillment', orderStatus(order.fulfillment_status, ur)], ['Total', `${order.currency_code} ${order.total_pkr}`],
          ['Created', order.created_at], ['Order ID', order.id],
        ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd><bdi>{value}</bdi></dd></div>)}</dl>
      </section></AdminCard>
      <AdminCard><section className={styles.cardBody}>
        <h2>Ordered items</h2>
        {order.order_items.length ? <ul>{order.order_items.map((item, index) =>
          <li key={index}>{item.product_name_snapshot} × {item.quantity}</li>)}</ul> : <p>No items recorded.</p>}
      </section></AdminCard>
    </>}
  </AdminPageContainer></div>;
}

export function OrderShipmentForm({ orderId, ur }: { orderId: string; ur: boolean }) {
  const [order, setOrder] = useState<OrderShipment | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [nextStatus, setNextStatus] = useState('');
  const command = useRef<{ body: string; key: string } | null>(null);
  const load = useCallback(async (signal?: AbortSignal) => {
    setBusy(true);
    setError('');
    try {
      const latest = await workflowRequest<OrderShipment>('shipment', orderId, { signal });
      setOrder(latest);
      setNextStatus(latest.next_statuses.find(value => value !== 'exception') ?? latest.next_statuses[0] ?? '');
    } catch (error) {
      if (!signal?.aborted) setError((error as Error).message);
    } finally {
      if (!signal?.aborted) setBusy(false);
    }
  }, [orderId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!order || busy) return;
    const form = new FormData(event.currentTarget);
    const field = (name: string) => String(form.get(name) ?? '').trim();
    const shipment = order.shipment;
    const body = JSON.stringify(shipment ? {
      status: nextStatus, expected_status: shipment.status,
      packing_confirmed: form.get('packing_confirmed') === 'on',
      tracking_reference: field('tracking_reference') || null, reason: field('reason'),
    } : { carrier: field('carrier'), tracking_reference: field('tracking_reference') });
    if (command.current?.body !== body) command.current = { body, key: crypto.randomUUID() };
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await workflowRequest('shipment', orderId, {
        method: shipment ? 'PATCH' : 'POST', body,
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': command.current.key },
      });
      command.current = null;
      setMessage(shipment ? 'Shipment status updated.' : 'Shipment created. The buyer can now see it in Shipments.');
      await load();
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const shipment = order?.shipment;
  return <div className={styles.screen}><AdminPageContainer>
    <AdminPageHeader title={shipment ? 'Manage shipment' : 'Create shipment'}
      description={order?.order_number} actions={<Link href={`/admin/orders/${orderId}`}>View order details</Link>} />
    {busy && <p role="status">Loading shipment…</p>}
    {error && <p role="alert" className={styles.notice}>{error}</p>}
    {message && <p role="status" className={styles.notice}>{message}</p>}
    <button type="button" disabled={busy} onClick={() => void load()}>Refresh shipment</button>
    {order && <AdminCard><section className={styles.cardBody}>
      <h2>{shipment ? 'Shipment details' : 'Order readiness'}</h2>
      {shipment ? <dl className={styles.facts}>
        <div><dt>Status</dt><dd>{orderStatus(shipment.status, ur)}</dd></div>
        <div><dt>Courier</dt><dd>{shipment.carrier}</dd></div>
        <div><dt>Tracking Number</dt><dd><bdi>{shipment.tracking_reference ?? 'Pending'}</bdi></dd></div>
      </dl> : <>
        <p>{orderStatus(order.payment_status, ur)} · {orderStatus(order.print_status ?? 'not_requested', ur)}</p>
        {order.print_job_id && <Link href={`/admin/print-jobs/${order.print_job_id}`}>View current print job</Link>}
        {!order.eligible && <p className={styles.notice}>Shipment creation requires verified payment, allocation, and physical QA approval for the current PDF.</p>}
      </>}
      {(!shipment && order.eligible || shipment && order.next_statuses.length > 0) &&
        <form key={shipment?.status ?? 'create'} className={styles.workflowForm} onSubmit={submit}>
          <fieldset disabled={busy}>
            {!shipment && <label>Shipping Service / Courier Name<input name="carrier" required maxLength={80} /></label>}
            {(!shipment || nextStatus === 'dispatched') && <label>Tracking Number<input name="tracking_reference" required maxLength={150} defaultValue={shipment?.tracking_reference ?? ''} dir="ltr" /></label>}
            {shipment && <>
              <label>Next status<select value={nextStatus} onChange={event => setNextStatus(event.target.value)}>
                {order.next_statuses.map(status => <option key={status} value={status}>{orderStatus(status, ur)}</option>)}
              </select></label>
              {nextStatus === 'packed' && <label className="check-field"><input type="checkbox" name="packing_confirmed" required /> I checked the printed items and packed the order.</label>}
              <label>Reason<input name="reason" required minLength={4} maxLength={500} /></label>
            </>}
            <button type="submit">{shipment ? 'Update shipment' : 'Create shipment'}</button>
          </fieldset>
        </form>}
    </section></AdminCard>}
  </AdminPageContainer></div>;
}
