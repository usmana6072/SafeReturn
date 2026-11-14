"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from "./admin-ui";
import { useAdminRole } from "./admin-shell";
import { useAdminToast } from "./admin-toast";
import { OrderStateBadge } from "./admin-orders";
import { useAdminMockData, recordDemoShipmentTracking, type MockOrder, type MockShipment } from "../lib/admin-mock-data";
import { canManageDemoShipments, demoShipmentLabels, demoShipmentTransitions } from "../lib/admin-shipment-policy";
import { demoShipmentReadiness, demoOrderPrintQA } from "../lib/admin-shipment-readiness";
import styles from "./admin-shipments.module.css";

function ShipmentBadge({ status }: { status: string }) {
  return <AdminStatusBadge label={demoShipmentLabels[status] || `Unknown (${status || "not recorded"})`} variant={status === "exception" ? "danger" : status === "delivered" ? "success" : "neutral"} />;
}

export function AdminShipments({ shipmentId, initialTab = "shipments", ur = false, liveConsoleAvailable = false }: { shipmentId?: string; initialTab?: "ready" | "shipments"; ur?: boolean; liveConsoleAvailable?: boolean }) {
  const { data, refresh } = useAdminMockData();
  const role = useAdminRole();
  const [ready, setReady] = useState(false);
  const [storageError, setStorageError] = useState(false);
  const [tab, setTab] = useState(initialTab);
  const [search, setSearch] = useState("");
  const [shipFilter, setShipFilter] = useState("all");
  const [readinessFilter, setReadinessFilter] = useState("all");
  const [selectedOrder, setSelectedOrder] = useState<string>();
  const [tracking, setTracking] = useState(false);
  useEffect(() => {
    try { const raw = localStorage.getItem("safereturn_demo_db"); if (raw) { const value = JSON.parse(raw); if (!value || Array.isArray(value) || (value.shipments !== undefined && !Array.isArray(value.shipments)) || (value.orders !== undefined && !Array.isArray(value.orders))) throw Error(); } }
    catch { setStorageError(true); }
    refresh(); setReady(true);
  }, [refresh]);
  if (!canManageDemoShipments(role.authenticatedRoles)) return <AdminEmptyState title="Access denied" description="Authenticated Operations or Superadmin access is required. Role preview cannot grant access." />;
  if (!ready) return <p role="status">Loading demo logistics…</p>;
  const byOrder = (id: string) => data.orders.find(order => order.id === id);
  const shipments = data.shipments;
  const query = search.trim().toLowerCase();
  const filteredShips = shipments.filter(shipment => [shipment.id, shipment.orderId, shipment.trackingReference, byOrder(shipment.orderId)?.customer].some(value => value?.toLowerCase().includes(query)) && (shipFilter === "all" || shipment.status === shipFilter));
  const candidates = data.orders.filter(order => [order.id, order.customer, ...shipments.filter(shipment => shipment.orderId === order.id).flatMap(shipment => [shipment.id, shipment.trackingReference])].some(value => value?.toLowerCase().includes(query)) && (readinessFilter === "all" || demoShipmentReadiness(order) === readinessFilter));
  const selected = shipments.find(shipment => shipment.id === shipmentId);
  const readinessOrder = byOrder(selectedOrder || "");
  const canUpdate = role.selectedRole === "authenticated" && !storageError;
  const back = <Link href="/admin/shipments" prefetch={false}>Back to Shipments</Link>;
  return <div className={styles.screen} dir={ur ? "rtl" : "ltr"}><AdminPageContainer>
    <AdminPageHeader title={shipmentId ? "Shipment Details" : "Shipments & Logistics"} description={shipmentId || "Review fulfillment readiness and track shipment progress."} badge={<AdminStatusBadge label="Frontend Demo" variant="info" />}
      actions={shipmentId ? back : liveConsoleAvailable ? <Link prefetch={false} href={initialTab === "ready" ? "/admin/ready-to-ship?view=live" : "/admin/shipments?view=live"}>Open existing live logistics console</Link> : undefined} />
    <p className={styles.notice}>Synthetic shipment scenarios only. Tracking references are nonfunctional and are not carrier links. Demo tracking never dispatches an order, verifies delivery, changes payment or print QA, allocates QR identities, deducts stock or sends notifications.</p>
    {storageError && <p role="alert" className={styles.notice}>Browser demo storage could not be read. Fallback fixtures are displayed; tracking writes are unavailable.</p>}
    {role.selectedRole !== "authenticated" && <p role="status" className={styles.notice}>Role preview is read-only. Use your authenticated Operations or Superadmin role for demo tracking updates.</p>}
    {shipmentId === undefined ? <>
      <div className={styles.tabs} role="tablist" aria-label="Logistics views">{([ ["ready", "Ready to Ship"], ["shipments", "All Shipments"] ] as const).map(([value, label], index) => <button key={value} id={`logistics-tab-${value}`} type="button" role="tab" aria-selected={tab === value} aria-controls="logistics-panel" tabIndex={tab === value ? 0 : -1} onClick={() => setTab(value)} onKeyDown={event => {
        if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) { event.preventDefault(); const next = event.key === "Home" ? "ready" : event.key === "End" ? "shipments" : index === 0 ? "shipments" : "ready"; setTab(next); document.getElementById(`logistics-tab-${next}`)?.focus(); }
      }}>{label}</button>)}</div>
      <div className={styles.metrics}>{[["Ready to Ship", "Not available"], ["Mock Dispatched", shipments.filter(shipment => shipment.status === "dispatched").length], ["Delivery Issues", shipments.filter(shipment => shipment.status === "exception").length]].map(([label, count]) => <AdminCard key={label}><div className={styles.metric}><span>{label}</span><strong>{count}</strong></div></AdminCard>)}</div>
      <p className={styles.notice}>Shipment readiness cannot be verified from the available frontend mock data. Candidate orders are shown for inspection, not as an eligible dispatch queue.</p>
      <div role="tabpanel" id="logistics-panel" aria-labelledby={`logistics-tab-${tab}`} tabIndex={0}>
        <AdminCard><div className={styles.toolbar}>
          <label>Search logistics<input placeholder="Search order/tracking..." value={search} onChange={event => setSearch(event.target.value)} /></label>
          {tab === "shipments" ? <label>Shipment Status<select value={shipFilter} onChange={event => setShipFilter(event.target.value)}><option value="all">All shipment statuses</option>{Array.from(new Set(shipments.map(shipment => shipment.status))).map(value => <option key={value} value={value}>{demoShipmentLabels[value] || `Unknown (${value})`}</option>)}</select></label> : <label>Readiness Status<select value={readinessFilter} onChange={event => setReadinessFilter(event.target.value)}><option value="all">All readiness states</option>{Array.from(new Set(data.orders.map(demoShipmentReadiness))).map(value => <option key={value}>{value}</option>)}</select></label>}
          <button type="button" disabled={!search && shipFilter === "all" && readinessFilter === "all"} onClick={() => { setSearch(""); setShipFilter("all"); setReadinessFilter("all"); }}>Clear Filters</button>
        </div>
          {tab === "shipments" ? filteredShips.length ? <div className={styles.scroll} role="region" aria-label="Shipments table" tabIndex={0}><table><thead><tr>{["Shipment ID", "Order ID", "Customer", "Courier", "Tracking Reference", "Shipment Status", "Updated", "Actions"].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{filteredShips.map(shipment => <tr key={shipment.id}><td className={styles.mono}>{shipment.id}</td><td>{shipment.orderId}</td><td>{byOrder(shipment.orderId)?.customer || "Associated order not available"}</td><td>{shipment.courier || "Not available"}</td><td className={styles.mono}>{shipment.trackingReference || "Not available"}</td><td><ShipmentBadge status={shipment.status} /></td><td>{shipment.updatedAt}</td><td><Link prefetch={false} href={`/admin/shipments/${encodeURIComponent(shipment.id)}`} aria-label={`View Details for ${shipment.id}`}>View Details</Link></td></tr>)}</tbody></table></div> : <AdminEmptyState title={shipments.length ? "No matching shipments" : "No demo shipments"} description="No synthetic shipments match this view. Opening the page never creates shipments." /> : candidates.length ? <div className={styles.scroll} role="region" aria-label="Readiness candidates" tabIndex={0}><table><thead><tr>{["Order ID", "Customer", "Products / Copies", "Payment", "Print QA", "Readiness", "Actions"].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{candidates.map(order => <tr key={order.id}><td className={styles.mono}>{order.id}</td><td>{order.customer}</td><td>{order.items || "Not available"}</td><td><OrderStateBadge value={order.payment} payment /></td><td>{demoOrderPrintQA(order.id, data.printJobs)}</td><td><AdminStatusBadge label={demoShipmentReadiness(order)} variant={demoShipmentReadiness(order) === "Blocked" ? "warning" : "neutral"} /></td><td><button type="button" onClick={() => setSelectedOrder(order.id)} aria-label={`View Readiness for ${order.id}`}>View Readiness</button></td></tr>)}</tbody></table></div> : <AdminEmptyState title={data.orders.length ? "No matching readiness candidates" : "No readiness candidates"} description="No demo order records are available in this view. Missing prerequisites never count as passed." />}
          <p className={styles.body} role="status">Showing {tab === "shipments" ? filteredShips.length : candidates.length} records</p>
        </AdminCard>
      </div>
      {tab === "ready" && readinessOrder && <ReadinessPanel order={readinessOrder} printQA={demoOrderPrintQA(readinessOrder.id, data.printJobs)} />}
    </> : selected ? <>
      <div className={styles.details}><div className={styles.column}>
        <AdminCard><section className={styles.body}><h2>Shipment Information</h2><dl className={styles.facts}>{[["Shipment ID", selected.id], ["Order ID", selected.orderId], ["Customer", byOrder(selected.orderId)?.customer || "Associated order not available"], ["Courier", selected.courier || "Not available"], ["Tracking Reference", selected.trackingReference || "Not available"], ["Created", selected.createdAt], ["Last updated", selected.updatedAt]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}<div><dt>Shipment Status</dt><dd><ShipmentBadge status={selected.status} /></dd></div></dl>
          {byOrder(selected.orderId) && <Link href={`/admin/orders/${encodeURIComponent(selected.orderId)}`} prefetch={false}>View Order</Link>}
        </section></AdminCard>
        <AdminCard><section className={styles.body}><h2>Delivery Information</h2>{selected.delivery ? <><p>Synthetic delivery record only</p><p>{selected.delivery.recipient}</p><p>{selected.delivery.address}</p>{selected.delivery.city && <p>{selected.delivery.city}</p>}</> : <p>Delivery address not available in this demo record.</p>}</section></AdminCard>
        <AdminCard><section className={styles.body}><h2>Products in Shipment</h2>{byOrder(selected.orderId) ? <ShipmentProducts order={byOrder(selected.orderId)!} /> : <p>Associated order not available. No products or prices are inferred.</p>}<p className={styles.muted}>For supported single-QR orders, each distinct logical order item requires its own identity; sizes and repeated copies share that item's identity. No credentials are allocated or activated here.</p></section></AdminCard>
      </div><div className={styles.column}>
        {byOrder(selected.orderId) && <ReadinessPanel order={byOrder(selected.orderId)!} printQA={demoOrderPrintQA(selected.orderId, data.printJobs)} />}
        <AdminCard><section className={styles.body}><h2>Demo Tracking</h2><p>Updates apply only to the synthetic shipment record. They are not carrier scans or actual delivery confirmations.</p>
          <button className={styles.primary} type="button" disabled={!canUpdate || !byOrder(selected.orderId) || !demoShipmentTransitions[selected.status]?.length} onClick={() => setTracking(true)}>Record Demo Tracking Update</button>
          {!demoShipmentTransitions[selected.status]?.length && <p>No supported demo transition is available for this status.</p>}
          {!byOrder(selected.orderId) && <p>Tracking updates are unavailable because the associated order is missing.</p>}
        </section></AdminCard>
      </div></div>
      <AdminCard><section className={styles.body}><h2>Tracking History</h2>{selected.events.length ? <ol className={styles.history}>{[...selected.events].reverse().map(event => <li key={event.id}><ShipmentBadge status={event.status} /><p>{event.actor} · <time dateTime={event.timestamp}>{event.timestamp}</time></p>{event.note && <p>{event.note}</p>}</li>)}</ol> : <p>No synthetic tracking events recorded. History is not inferred from the current status.</p>}</section></AdminCard>
      {tracking && <DemoTrackingUpdateDialog shipment={selected} onClose={() => setTracking(false)} onSaved={() => { setTracking(false); refresh(); }} />}
    </> : <AdminEmptyState title="Shipment not found" description="This identifier does not match an existing synthetic shipment." action={back} />}
  </AdminPageContainer></div>;
}

function ReadinessPanel({ order, printQA }: { order: MockOrder; printQA: string }) {
  return <AdminCard><section className={styles.body} aria-label={`Readiness for ${order.id}`}><h2>Shipment Readiness · {order.id}</h2><p className={styles.notice}>Shipment readiness cannot be verified from the available frontend mock data.</p><dl className={styles.facts}>{[["Payment verification", `${order.payment || "Unknown"} — mock label, no independent bank proof`], ["Order snapshot", order.lineItems?.length ? "Stored item metadata; release validity not verified" : "Legacy summary only; structured copy data unavailable"], ["QR identity allocation", "Not verified"], ["Print completion / validated artifact", "Not verified"], ["Physical Print QA", printQA], ["Delivery information", "Not available"], ["Shipment release authority", "Not verified"]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><p className={styles.muted}>Payment labels and tabletop print QA cannot establish readiness. Ready to Ship is separate from actual courier acceptance and dispatch.</p></section></AdminCard>;
}

function ShipmentProducts({ order }: { order: MockOrder }) {
  return order.lineItems?.length ? <ul>{order.lineItems.map(item => <li key={item.id}>{item.title} · Stored quantity: {item.quantity}</li>)}</ul> : <><p>{order.items || "Not available"}</p><p className={styles.muted}>Legacy item summary only. Structured size/copy breakdown and purchase prices are not available; no quantities are inferred from the current catalog.</p></>;
}

function DemoTrackingUpdateDialog({ shipment, onClose, onSaved }: { shipment: MockShipment; onClose: () => void; onSaved: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const busy = useRef(false);
  const [status, setStatus] = useState("");
  const [note, setNote] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState("");
  const role = useAdminRole();
  const { showToast } = useAdminToast();
  // Freeze the version displayed when opened; stale submissions must be rejected.
  const expectedStatus = useRef(shipment.status);
  useEffect(() => { const previous = document.activeElement as HTMLElement | null; dialog.current?.showModal(); return () => { previous?.focus(); }; }, []);
  return <dialog ref={dialog} aria-labelledby="demo-tracking-title" onCancel={onClose}><form className={styles.body} onSubmit={event => {
    event.preventDefault(); if (busy.current) return; busy.current = true;
    const result = recordDemoShipmentTracking({ shipmentId: shipment.id, expectedStatus: expectedStatus.current, status, note, confirmed, authenticatedRoles: role.authenticatedRoles, previewRole: role.selectedRole });
    if (!result.success) { setError(result.error); busy.current = false; return; }
    showToast("Demo tracking update recorded. No real delivery or fulfillment action performed.", "success"); onSaved();
  }}><h2 id="demo-tracking-title">Record Demo Tracking Update</h2><p className={styles.mono}>{shipment.id} · {shipment.orderId}</p><p className={styles.notice}>This changes only the synthetic shipment status. No courier request, customer notification, order update or QR activation occurs.</p>
    <label>Demonstration status<select value={status} required onChange={event => setStatus(event.target.value)}><option value="">Select a supported demo transition</option>{(demoShipmentTransitions[expectedStatus.current] || []).map(value => <option key={value} value={value}>{demoShipmentLabels[value]}</option>)}</select></label>
    <label>Tracking note (optional)<textarea rows={3} maxLength={500} value={note} onChange={event => setNote(event.target.value)} /></label><p className={styles.muted}>Synthetic operational notes only. Do not enter addresses, phone numbers or other personal data. {note.length}/500</p>
    <label className={styles.check}><input type="checkbox" required checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />I confirm this is a demo tracking update, not actual dispatch or delivery confirmation.</label>
    {error && <p role="alert">{error}</p>}<div className={styles.actions}><button type="button" onClick={onClose}>Cancel</button><button type="submit" className={styles.primary}>Confirm Demo Tracking Update</button></div>
  </form></dialog>;
}
