'use client';

import Link from 'next/link';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { AdminCard } from './admin-ui';
import { workflowRequest, type PhysicalQA } from '../lib/fulfillment-workflow';
import styles from './admin-orders.module.css';

const inspections = [
  ['scan_passed', 'I scanned every assigned QR and matched it to the print job.'],
  ['logo_quiet_zone_passed', 'I checked the logo and clear space around each QR.'],
  ['bilingual_passed', 'I checked the English and Urdu print.'],
  ['cutting_packaging_passed', 'I checked cutting and packaging.'],
  ['actual_scale_passed', 'I measured the printed labels at actual scale.'],
] as const;

export function PhysicalPrintQA({ jobId, onRecorded }: { jobId: string; onRecorded: () => void }) {
  const [qa, setQA] = useState<PhysicalQA | null>(null);
  const [approved, setApproved] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const command = useRef<{ body: string; key: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    workflowRequest<PhysicalQA>('qa', jobId, { signal: controller.signal })
      .then(setQA).catch(error => { if (!controller.signal.aborted) setError(error.message); });
    return () => controller.abort();
  }, [jobId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!qa || busy) return;
    const form = new FormData(event.currentTarget);
    const body = JSON.stringify({
      approved,
      artifact_sha256: qa.artifact_sha256,
      inspected_item_ids: form.getAll('inspected_item_id'),
      observed: qa.expected.map((entry, index) => ({
        tag_type: entry.tag_type, symbol_mm: String(form.get(`size_${index}`)), copies: Number(form.get(`copies_${index}`)),
      })),
      ...Object.fromEntries(inspections.map(([name]) => [name, form.get(name) === 'on'])),
      reason: String(form.get('reason')).trim(),
    });
    if (command.current?.body !== body) command.current = { body, key: crypto.randomUUID() };
    setBusy(true);
    setError('');
    try {
      const result = await workflowRequest<{ status: string }>('qa', jobId, {
        method: 'POST', body,
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': command.current.key },
      });
      setQA({ ...qa, status: result.status });
      onRecorded();
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return <AdminCard><section className={styles.cardBody} aria-label="Physical print QA">
    <h2>Physical print QA</h2>
    {error && <p role="alert" className={styles.notice}>{error}</p>}
    {!qa && !error && <p role="status">Loading inspection details…</p>}
    {qa?.status === 'qa_passed' && <><p>Physical print QA passed.</p><Link href={`/admin/orders/${qa.order_id}/shipment`}>Create shipment</Link></>}
    {qa?.status === 'failed' && <p role="status">Physical print QA failed. This revision is held from shipping.</p>}
    {qa && ['ready', 'downloaded'].includes(qa.status) && <form className={styles.workflowForm} onSubmit={submit}>
      <fieldset disabled={busy}>
        <label>Inspection result<select value={approved ? 'pass' : 'fail'} onChange={event => setApproved(event.target.value === 'pass')}>
          <option value="pass">Approve physical print</option><option value="fail">Record failed inspection</option>
        </select></label>
        {qa.inspection_items.map(item => <label key={item.id}>
          <input type="checkbox" name="inspected_item_id" value={item.id} required={approved} />
          Inspected the printed copies for {item.product_name_snapshot} ({item.qr_type_snapshot === 'ice' ? 'Emergency' : 'Lost'})
        </label>)}
        {qa.expected.map((entry, index) => <div key={`${entry.tag_type}-${entry.symbol_mm}`} className={styles.qaGroup}>
          <p>{entry.tag_type === 'ice' ? 'Emergency' : 'Lost'} · Expected {entry.symbol_mm} mm · {entry.copies} copies</p>
          <label>Measured QR size (mm)<input name={`size_${index}`} inputMode="decimal" pattern="[0-9]{2,3}(\.[0-9]{1,2})?" required /></label>
          <label>Printed copies counted<input name={`copies_${index}`} type="number" min={1} max={5000} step={1} required /></label>
        </div>)}
        {inspections.map(([field, label]) => <label key={field}><input type="checkbox" name={field} required={approved} />{label}</label>)}
        <label>Inspection notes<textarea name="reason" required minLength={4} maxLength={1000} /></label>
        <button type="submit">{approved ? 'Approve physical print' : 'Record failed inspection'}</button>
      </fieldset>
    </form>}
  </section></AdminCard>;
}
