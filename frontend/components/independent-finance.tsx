'use client';
import { useEffect, useRef, useState } from 'react';
import { parseAllocation, type Allocation } from '../lib/allocation';

export function IndependentFinance({ orderId, ur = false }: { orderId?: string; ur?: boolean }) {
    const [value, setValue] = useState<Allocation | null>(null);
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState('');
    const key = useRef<string | null>(null);

    async function load() {
        if (!orderId || busy)
            return;
        setBusy(true);
        setMessage('');
        try {
            const response = await fetch('/payments/api?path=' + encodeURIComponent(`/admin/orders/${orderId}/qr-allocation`), { cache: 'no-store' });
            if (!response.ok)
                throw Error(response.status === 403 ? 'Finance permission and recent MFA are required.' : 'Allocation records are unavailable.');
            setValue(parseAllocation(await response.json()));
        } catch (error) {
            setValue(null);
            setMessage(error instanceof Error ? error.message : 'Allocation records are unavailable.');
        } finally {
            setBusy(false);
        }
    }

    async function retry() {
        if (!orderId || !value || value.state !== 'reconciliation_pending' || busy)
            return;
        setBusy(true);
        setMessage('');
        key.current ??= crypto.randomUUID();
        try {
            const response = await fetch('/payments/api', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: `/admin/orders/${orderId}/qr-allocation/retry`,
                    key: key.current,
                    body: { confirmed: true },
                }),
            });
            if (!response.ok)
                throw Error(response.status === 403 ? 'Finance permission and recent MFA are required.' : 'Allocation retry was not completed.');
            const result = await response.json();
            const allocation = parseAllocation(result.allocation);
            setValue(allocation);
            key.current = null;
            setMessage(allocation.state === 'allocated'
                ? (ur ? 'تخصیص مکمل ہو گئی۔' : 'Allocation completed. The print job will appear after processing.')
                : (ur ? 'تخصیص ابھی مکمل نہیں ہوئی۔' : 'Allocation is still pending reconciliation.'));
        } catch (error) {
            setMessage(error instanceof Error ? error.message : 'Allocation retry was not completed.');
        } finally {
            setBusy(false);
        }
    }

    useEffect(() => {
        setValue(null);
        key.current = null;
        if (orderId)
            void load();
    }, [orderId]);

    return <section aria-label="QR allocation reconciliation" dir={ur ? 'rtl' : 'ltr'}>
        <h2>{ur ? 'QR کی تخصیص' : 'QR allocation'}</h2>
        <button type="button" disabled={!orderId || busy} onClick={() => void load()}>{ur ? 'تخصیص کی حالت تازہ کریں' : 'Load reconciliation'}</button>
        {value && <><p>Allocation: <strong>{value.state}</strong>{value.reason_code ? ` (${value.reason_code})` : ''}</p><p>{value.allocated_count} / {value.requested_count} QR identities allocated.</p></>}
        {value?.state === 'reconciliation_pending' && <button type="button" disabled={busy} onClick={() => void retry()}>{ur ? 'دوبارہ تخصیص کی کوشش' : 'Retry whole-order allocation'}</button>}
        <p role="status">{message}</p>
    </section>;
}
