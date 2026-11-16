"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import type { PaymentInstructions } from "../lib/item-cart";
import { uuid } from "../lib/qr-contract";
import { OfficialPaymentInstructions } from "./item-checkout";

type Attempt = { id: string; state: string; evidence_received: boolean };
type Payment = {
    attempt: Attempt | null;
    paymentOpen: boolean;
    amount: string;
    currency: string;
};
type Upload = { identity: string; token: string; url: string; uploaded: boolean; signature: string };
const uploadStates = ['initiated', 'submitted', 'under_review'];
const evidenceTypes: Record<string, string> = { 'image/png': 'png', 'image/jpeg': 'jpg', 'application/pdf': 'pdf' };

function parsePayment(raw: { items: Attempt[]; payment_open: boolean; payment_due: string; currency_code: string }): Payment {
    if (!Array.isArray(raw.items) || raw.items.some(a => typeof a?.id !== 'string' || !uuid(a.id) || typeof a.state !== 'string' || typeof a.evidence_received !== 'boolean')
        || typeof raw.payment_open !== 'boolean' || !/^\d{1,10}\.\d{2}$/.test(raw.payment_due) || !/^[A-Z]{3}$/.test(raw.currency_code)) {
        throw Error('PROVIDER_UNAVAILABLE');
    }
    return {
        attempt: raw.items.find(a => [...uploadStates, 'verified', 'disputed'].includes(a.state)) ?? null,
        paymentOpen: raw.payment_open,
        amount: raw.payment_due,
        currency: raw.currency_code,
    };
}

async function read(path: string) {
    const response = await fetch('/payments/api?' + new URLSearchParams({ path }), { cache: 'no-store' });
    if (!response.ok) throw Error(String(response.status));
    return response.json();
}

export function PaymentForm({ orderId, language }: { orderId: string; language: string }) {
    const ur = language === 'ur';
    const t = (en: string, translated: string) => ur ? translated : en;
    const [payment, setPayment] = useState<Payment | null>(null);
    const [instructions, setInstructions] = useState<PaymentInstructions | null>(null);
    const [busy, setBusy] = useState(true);
    const [status, setStatus] = useState('');
    const keys = useRef(new Map<string, string>());
    const pending = useRef<Upload | null>(null);
    const running = useRef(false);
    const attemptsPath = `/me/orders/${orderId}/payment-attempts`;
    const attempt = payment?.attempt;
    const canSubmit = payment?.paymentOpen && (!attempt || (!attempt.evidence_received && uploadStates.includes(attempt.state)));

    function failure(error: unknown) {
        const code = error instanceof Error ? error.message : '';
        switch (code) {
            case '401': case '403':
                setStatus(t('Sign in again to continue payment.', 'ادائیگی جاری رکھنے کے لیے دوبارہ سائن ان کریں۔'));
                break;
            case 'FILE_INVALID':
                setStatus(t('Choose a PNG, JPEG or PDF up to 5 MB.', '۵ ایم بی تک PNG، JPEG یا PDF منتخب کریں۔'));
                break;
            case '400': case '422':
                setStatus(t('Check the payment details and receipt, then try again.', 'ادائیگی کی تفصیلات اور رسید چیک کر کے دوبارہ کوشش کریں۔'));
                break;
            case '429':
                setStatus(t('Too many requests. Please try later.', 'درخواستیں زیادہ ہیں۔ کچھ دیر بعد کوشش کریں۔'));
                break;
            case 'UPLOAD_EXPIRED':
                setStatus(t('The upload expired. Submit the receipt again.', 'اپ لوڈ کی مدت ختم ہو گئی۔ رسید دوبارہ جمع کریں۔'));
                break;
            default:
                setStatus(t('Payment submission could not be confirmed. Please try again.', 'ادائیگی جمع ہونے کی تصدیق نہیں ہو سکی۔ دوبارہ کوشش کریں۔'));
        }
    }

    async function load() {
        setBusy(true);
        setPayment(null);
        setInstructions(null);
        setStatus('');
        const [details, bank] = await Promise.allSettled([read(attemptsPath), read(`/me/orders/${orderId}/payment-instructions`)]);
        try {
            if (details.status === 'rejected') throw details.reason;
            setPayment(parsePayment(details.value));
        } catch (error) {
            failure(error);
        }
        if (bank.status === 'fulfilled') {
            const value = bank.value;
            if (value?.currency_code === 'PKR' && ['bank_name', 'account_title', 'account_number', 'raast_id', 'instructions_en', 'instructions_ur'].every(k => typeof value[k] === 'string')) {
                setInstructions(value);
            }
        }
        setBusy(false);
    }
    useEffect(() => { void load(); }, [orderId]);

    async function command(path: string, body: unknown) {
        const signature = JSON.stringify({ path, body });
        if (!keys.current.has(signature)) keys.current.set(signature, crypto.randomUUID());
        const response = await fetch('/payments/api', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path, body, key: keys.current.get(signature) }),
        });
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                setPayment(null);
                setInstructions(null);
                pending.current = null;
            }
            if (response.status === 409) {
                const code = (await response.json().catch(() => null))?.error?.code;
                if (typeof code === 'string') throw Error(code);
            }
            throw Error(String(response.status));
        }
        return response.json();
    }

    async function uploadEvidence(attemptId: string, file: File, extension: string) {
        const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', await file.arrayBuffer())))
            .map(value => value.toString(16).padStart(2, '0')).join('');
        const identity = `${attemptId}:${hash}`;
        let upload = pending.current;
        if (!upload || upload.identity !== identity) {
            const path = `/me/payment-attempts/${attemptId}/evidence-uploads`;
            const body = { filename: `receipt.${extension}`, content_type: file.type, bytes_size: file.size, sha256: hash };
            const grant = await command(path, body);
            if (typeof grant.upload_token !== 'string' || typeof grant.upload_url !== 'string' || new URL(grant.upload_url).protocol !== 'https:') throw Error();
            upload = { identity, token: grant.upload_token, url: grant.upload_url, uploaded: false, signature: JSON.stringify({ path, body }) };
            pending.current = upload;
        }
        if (!upload.uploaded) {
            const response = await fetch(upload.url, { method: 'PUT', headers: { 'Content-Type': file.type, 'x-upsert': 'false' }, body: file });
            if (response.status === 400 || response.status === 401 || response.status === 403) throw Error('UPLOAD_EXPIRED');
            if (!response.ok && response.status !== 409) throw Error();
            upload.uploaded = true;
        }
        const receipt = await command(`/me/payment-attempts/${attemptId}/evidence-finalize`, { upload_token: upload.token, sha256: hash });
        if (receipt.received !== true || typeof receipt.payment_state !== 'string') throw Error();
        pending.current = null;
        setPayment(value => value?.attempt?.id === attemptId
            ? { ...value, attempt: { id: attemptId, state: receipt.payment_state, evidence_received: true } }
            : value);
    }

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (running.current || !canSubmit || !payment) return;
        running.current = true;
        setBusy(true);
        setStatus('');
        try {
            const form = new FormData(event.currentTarget);
            const file = form.get('file');
            const extension = file instanceof File ? evidenceTypes[file.type] : undefined;
            if (!(file instanceof File) || !file.size || file.size > 5000000 || !extension) throw Error('FILE_INVALID');
            let attemptId = attempt?.id;
            if (!attemptId) {
                const reference = String(form.get('reference') ?? '').trim();
                const saved = await command(attemptsPath, {
                    sender_account: String(form.get('account') ?? '').trim(),
                    sender_holder_name: String(form.get('holder') ?? '').trim(),
                    ...(reference ? { transfer_reference: reference } : {}),
                });
                const id = saved.attempt_id;
                if (typeof id !== 'string' || !uuid(id) || !uploadStates.includes(saved.state)) throw Error();
                attemptId = id;
                setPayment({ ...payment, attempt: { id, state: saved.state, evidence_received: false } });
            }
            await uploadEvidence(attemptId, file, extension);
        } catch (error) {
            const code = error instanceof Error ? error.message : '';
            if (['PAYMENT_CLOSED', 'PAYMENT_ALREADY_PENDING', 'EVIDENCE_ALREADY_RECEIVED'].includes(code)) {
                await load();
            } else {
                if (['UPLOAD_EXPIRED', 'EVIDENCE_NOT_UPLOADED'].includes(code) && pending.current) {
                    keys.current.delete(pending.current.signature);
                    pending.current = null;
                }
                failure(error);
            }
        } finally {
            running.current = false;
            setBusy(false);
        }
    }

    let receipt = '';
    if (attempt?.state === 'verified') {
        receipt = t('Payment verified.', 'ادائیگی کی تصدیق ہو گئی۔');
    } else if (attempt?.evidence_received && attempt.state === 'under_review' && payment?.paymentOpen) {
        receipt = t('Payment details and receipt submitted. Your payment is under review.', 'ادائیگی کی تفصیلات اور رسید جمع ہو گئی ہیں۔ ادائیگی زیرِ جائزہ ہے۔');
    } else if (attempt?.evidence_received) {
        receipt = t('Payment receipt received. View your order for its current status.', 'ادائیگی کی رسید موصول ہو گئی ہے۔ موجودہ حالت آرڈر میں دیکھیں۔');
    } else if (payment && !canSubmit) {
        receipt = t('This order is no longer accepting payment details.', 'اس آرڈر کے لیے ادائیگی کی تفصیلات قبول نہیں کی جا رہیں۔');
    }

    return <section aria-busy={busy} dir={ur ? 'rtl' : 'ltr'}>
        <h1>{t('Complete payment', 'ادائیگی مکمل کریں')}</h1>
        {canSubmit && <>
            <p className="lead">{t('Submit your transfer details and receipt to finish checkout.', 'چیک آؤٹ مکمل کرنے کے لیے ٹرانسفر کی تفصیلات اور رسید جمع کریں۔')}</p>
            <p>{t('Amount due', 'واجب الادا رقم')} <strong><bdi>{payment.currency} {payment.amount}</bdi></strong></p>
            {instructions ? <div className="card"><OfficialPaymentInstructions value={instructions} ur={ur}/></div>
                : <p>{t('Official bank instructions are unavailable. Contact support before transferring.', 'بینک کی سرکاری ہدایات دستیاب نہیں ہیں۔ رقم بھیجنے سے پہلے مدد حاصل کریں۔')}</p>}
            <form className="card account-form" onSubmit={submit}>
                {!attempt && <div>
                    <label>{t('Sender holder name', 'بھیجنے والے کا نام')}<input name="holder" required maxLength={160} disabled={busy}/></label>
                    <label>{t('Sender account', 'بھیجنے والے کا اکاؤنٹ')}<input name="account" required minLength={4} maxLength={80} autoComplete="off" disabled={busy}/></label>
                    <label>{t('Transfer reference (optional)', 'ٹرانسفر ریفرنس (اختیاری)')}<input name="reference" maxLength={120} disabled={busy}/></label>
                </div>}
                {attempt?.state === 'initiated' && <p>{t('Your payment details are saved. Submit your receipt to finish checkout.', 'ادائیگی کی تفصیلات محفوظ ہیں۔ چیک آؤٹ مکمل کرنے کے لیے رسید جمع کریں۔')}</p>}
                <label>{t('Payment receipt (required)', 'ادائیگی کی رسید (لازمی)')}<input name="file" type="file" required accept="image/png,image/jpeg,application/pdf" disabled={busy}/></label>
                <p>{t('PNG, JPEG or PDF up to 5 MB.', '۵ ایم بی تک PNG، JPEG یا PDF۔')}</p>
                <button className="button" disabled={busy}>{busy ? t('Submitting…', 'جمع ہو رہا ہے…') : t('Submit payment for review', 'ادائیگی جائزے کے لیے جمع کریں')}</button>
            </form>
        </>}
        <p role="status">{status || receipt || (busy ? t('Loading payment…', 'ادائیگی لوڈ ہو رہی ہے…') : '')}</p>
        {!payment && !busy && <button type="button" onClick={() => void load()}>{t('Try again', 'دوبارہ کوشش کریں')}</button>}
        <Link href={`/orders/${orderId}`}>{t('View order', 'آرڈر دیکھیں')}</Link>
    </section>;
}
