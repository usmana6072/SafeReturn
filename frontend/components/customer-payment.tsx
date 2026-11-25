"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import type { PaymentInstructions } from "../lib/item-cart";
import { uuid } from "../lib/qr-contract";
import { OfficialPaymentInstructions } from "./item-checkout";
import { CustomerIcon } from "./customer-icon";

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
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
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

    return (
        <section aria-busy={busy} dir={ur ? 'rtl' : 'ltr'}>
            <header className="checkout-header">
                <Link href={`/orders/${orderId}`} className="checkout-back-link">
                    <CustomerIcon name="arrow" />
                    <span>{t("Back to Order Details", "آرڈر کی تفصیلات پر واپس")}</span>
                </Link>
                <div className="checkout-title-row">
                    <div>
                        <h1>{t('Payment Verification', 'ادائیگی کی تصدیق')}</h1>
                        <p className="checkout-subtitle">
                            {t('Order reference', 'آرڈر ریفرنس')}: <bdi style={{ fontWeight: 650, color: 'var(--checkout-ink)' }}>#{orderId.slice(0, 8)}</bdi>
                        </p>
                    </div>
                </div>

                <div className="checkout-stepper" aria-label={t('Progress', 'پیش رفت')}>
                    <span className="checkout-step completed">
                        <span className="checkout-step-number">✓</span>
                        <span>{t('Cart', 'کارٹ')}</span>
                    </span>
                    <span className="checkout-step-divider">→</span>
                    <span className="checkout-step completed">
                        <span className="checkout-step-number">✓</span>
                        <span>{t('Order Placed', 'آرڈر درج ہو گیا')}</span>
                    </span>
                    <span className="checkout-step-divider">→</span>
                    <span className={`checkout-step ${attempt?.state === 'verified' ? 'completed' : 'active'}`}>
                        <span className="checkout-step-number">{attempt?.state === 'verified' ? '✓' : '3'}</span>
                        <span>{t('Payment', 'ادائیگی')}</span>
                    </span>
                    <span className="checkout-step-divider">→</span>
                    <span className="checkout-step">
                        <span className="checkout-step-number">4</span>
                        <span>{t('QR Preparation', 'QR تیاری')}</span>
                    </span>
                </div>
            </header>

            {attempt?.state === 'verified' && (
                <div className="payment-status-card" role="status">
                    <div className="payment-status-icon success">✓</div>
                    <h2>{t('Payment Verified Successfully!', 'ادائیگی کی تصدیق ہو گئی!')}</h2>
                    <p>
                        {t(
                            `Thank you! Your payment of ${payment?.currency ?? 'PKR'} ${payment?.amount ?? ''} has been verified. Your QR identities are being generated and prepared for production.`,
                            `شکریہ! آپ کے آرڈر کی رقم ${payment?.currency ?? 'PKR'} ${payment?.amount ?? ''} تصدیق ہو چکی ہے۔ آپ کے QR کوڈز تیاری اور پرنٹنگ کے لیے منتقل ہو رہے ہیں۔`
                        )}
                    </p>
                    <div className="payment-actions-row">
                        <Link className="button" href={`/orders/${orderId}`}>
                            {t('View Order Progress', 'آرڈر کی پیش رفت دیکھیں')}
                        </Link>
                        <Link className="button secondary" href="/my-qr">
                            {t('View My QR Codes', 'میرے QR کوڈز دیکھیں')}
                        </Link>
                    </div>
                </div>
            )}

            {attempt?.evidence_received && attempt.state === 'under_review' && payment?.paymentOpen && (
                <div className="payment-status-card" role="status">
                    <div className="payment-status-icon waiting">⏱</div>
                    <h2>{t('Payment Receipt Under Review', 'ادائیگی کی رسید زیرِ جائزہ ہے')}</h2>
                    <p>
                        {t(
                            'Your transfer details and receipt have been received. Our finance team will review and verify your transaction shortly. Once verified, QR preparation begins.',
                            'آپ کی منتقلی کی تفصیلات اور رسید موصول ہو گئی ہیں۔ ہماری ٹیم جلد تصدیق مکمل کرے گی جس کے بعد QR کی تیاری شروع ہو جائے گی۔'
                        )}
                    </p>
                    <div className="payment-actions-row">
                        <Link className="button" href={`/orders/${orderId}`}>
                            {t('Track Order Status', 'آرڈر کی حالت دیکھیں')}
                        </Link>
                        <Link className="button secondary" href="/orders">
                            {t('View All Orders', 'تمام آرڈرز دیکھیں')}
                        </Link>
                    </div>
                </div>
            )}

            {payment && !canSubmit && attempt?.state !== 'verified' && !attempt?.evidence_received && (
                <div className="payment-status-card" role="status">
                    <div className="payment-status-icon attention">!</div>
                    <h2>{t('Payment Closed', 'ادائیگی بند ہے')}</h2>
                    <p>
                        {t(
                            'This order is no longer accepting new payment submissions. Please check your order details or contact support if you need assistance.',
                            'اس آرڈر کے لیے نئی ادائیگی قبول نہیں کی جا رہی۔ برائے مہربانی اپنے آرڈر کی تفصیلات دیکھیں یا سپورٹ سے رابطہ کریں۔'
                        )}
                    </p>
                    <div className="payment-actions-row">
                        <Link className="button" href={`/orders/${orderId}`}>
                            {t('View Order Details', 'آرڈر کی تفصیلات دیکھیں')}
                        </Link>
                    </div>
                </div>
            )}

            {canSubmit && (
                <>
                    <div className="payment-hero-banner">
                        <div className="payment-hero-copy">
                            <h1>{t('Complete Your Payment', 'اپنی ادائیگی مکمل کریں')}</h1>
                            <p>
                                {t(
                                    'Transfer the exact amount using Raast or Online Banking, then upload your transaction receipt below to begin QR manufacturing.',
                                    'بینک یا راست کے ذریعے واجب الادا رقم منتقل کریں اور نیچے رسید اپ لوڈ کریں تاکہ آپ کے QR ٹیگز تیار کیے جا سکیں۔'
                                )}
                            </p>
                        </div>
                        <div className="payment-due-card">
                            <small>{t('Total Amount Due', 'کل واجب الادا رقم')}</small>
                            <strong><bdi>{payment.currency} {payment.amount}</bdi></strong>
                        </div>
                    </div>

                    <div className="checkout-layout">
                        <div className="checkout-main">
                            {instructions ? (
                                <OfficialPaymentInstructions value={instructions} ur={ur} />
                            ) : (
                                <div className="checkout-panel">
                                    <p role="alert">
                                        {t('Official bank instructions are unavailable. Contact support before transferring.', 'بینک کی سرکاری ہدایات دستیاب نہیں ہیں۔ رقم بھیجنے سے پہلے مدد حاصل کریں۔')}
                                    </p>
                                </div>
                            )}

                            <form className="checkout-panel" onSubmit={submit}>
                                <h2>{t('Submit Transfer Receipt', 'ٹرانسفر کی رسید جمع کریں')}</h2>
                                <p style={{ fontSize: '0.875rem', color: 'var(--checkout-muted)', margin: '0 0 1.25rem' }}>
                                    {t(
                                        'Please provide the account details you paid from and upload a clear screenshot or PDF receipt.',
                                        'براہ کرم جس اکاؤنٹ سے رقم بھیجی ہے اس کی تفصیلات اور واضح اسکرین شاٹ یا PDF اپ لوڈ کریں۔'
                                    )}
                                </p>

                                {!attempt && (
                                    <div className="checkout-form-grid" style={{ marginBottom: '1.25rem' }}>
                                        <div className="checkout-field">
                                            <label htmlFor="payment-holder">{t('Sender Account Holder Name', 'بھیجنے والے کا نام (اکاؤنٹ ٹائٹل)')}</label>
                                            <input id="payment-holder" name="holder" required maxLength={160} disabled={busy} placeholder={t('e.g. Muhammad Usman', 'مثلاً محمد عثمان')} />
                                        </div>
                                        <div className="checkout-form-grid two-col">
                                            <div className="checkout-field">
                                                <label htmlFor="payment-account">{t('Sender Account / IBAN / Phone', 'اکاؤنٹ نمبر یا موبائل فون')}</label>
                                                <input id="payment-account" name="account" required minLength={4} maxLength={80} autoComplete="off" disabled={busy} placeholder={t('Account or Raast number', 'اکاؤنٹ یا راست نمبر')} />
                                            </div>
                                            <div className="checkout-field">
                                                <label htmlFor="payment-ref">{t('Transfer Reference / TID (optional)', 'ٹرانسفر ریفرنس / TID (اختیاری)')}</label>
                                                <input id="payment-ref" name="reference" maxLength={120} disabled={busy} placeholder={t('Bank Transaction ID', 'بینک ٹرانزیکشن آئی ڈی')} />
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div className="checkout-field">
                                    <label>{t('Payment Receipt (Required)', 'ادائیگی کی رسید (لازمی)')}</label>
                                    <input
                                        ref={fileInputRef}
                                        name="file"
                                        type="file"
                                        required
                                        accept="image/png,image/jpeg,application/pdf"
                                        disabled={busy}
                                        style={{ display: 'none' }}
                                        onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                                    />
                                    <div
                                        className="upload-dropzone"
                                        role="button"
                                        tabIndex={0}
                                        onClick={() => fileInputRef.current?.click()}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' || e.key === ' ') {
                                                e.preventDefault();
                                                fileInputRef.current?.click();
                                            }
                                        }}
                                    >
                                        <div className="upload-icon-circle">
                                            <CustomerIcon name="box" />
                                        </div>
                                        <strong>{selectedFile ? selectedFile.name : t('Click to select receipt screenshot or PDF', 'رسید کا اسکرین شاٹ یا PDF منتخب کرنے کے لیے کلک کریں')}</strong>
                                        <small>{t('Supported: PNG, JPEG or PDF (Maximum 5 MB)', 'فارمیٹ: PNG، JPEG یا PDF (زیادہ سے زیادہ ۵ ایم بی)')}</small>
                                        {selectedFile && (
                                            <div className="upload-selected-file">
                                                <CustomerIcon name="check" />
                                                <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(0)} KB)</span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {status && (
                                    <div className="checkout-notice-box" style={{ background: '#fff4ef', borderColor: '#e6c2b8', color: '#7c372a' }} role="alert">
                                        <p style={{ margin: 0 }}>{status}</p>
                                    </div>
                                )}

                                <button
                                    className="button"
                                    type="submit"
                                    style={{ width: '100%', minHeight: '50px', fontSize: '1rem', marginTop: '1rem' }}
                                    disabled={busy}
                                >
                                    {busy ? t('Submitting receipt…', 'رسید جمع ہو رہی ہے…') : t('Submit Payment for Verification', 'ادائیگی تصدیق کے لیے جمع کریں')}
                                </button>
                            </form>
                        </div>

                        <aside className="checkout-sidebar checkout-summary-sticky">
                            <div className="checkout-panel">
                                <h2>{t('Order Summary', 'آرڈر کا خلاصہ')}</h2>
                                <dl className="checkout-summary-dl">
                                    <div>
                                        <dt>{t('Order Reference', 'آرڈر نمبر')}</dt>
                                        <dd><bdi>#{orderId.slice(0, 8)}</bdi></dd>
                                    </div>
                                    <div className="checkout-summary-total">
                                        <dt>{t('Amount Due', 'واجب الادا رقم')}</dt>
                                        <dd><bdi>{payment.currency} {payment.amount}</bdi></dd>
                                    </div>
                                </dl>

                                <div style={{ borderTop: '1px solid var(--checkout-line)', paddingTop: '1rem', marginTop: '1rem' }}>
                                    <h3 style={{ fontSize: '0.9rem', fontWeight: 650, margin: '0 0 0.5rem', color: 'var(--checkout-ink)' }}>
                                        {t('How It Works', 'طریقہ کار')}
                                    </h3>
                                    <ol style={{ paddingInlineStart: '1.2rem', margin: 0, fontSize: '0.85rem', color: 'var(--checkout-muted)', lineHeight: '1.7' }}>
                                        <li>{t('Transfer total amount to Bank/Raast', 'بینک یا راست پر کل رقم منتقل کریں')}</li>
                                        <li>{t('Save transaction screenshot', 'ٹرانزیکشن کا اسکرین شاٹ محفوظ کریں')}</li>
                                        <li>{t('Upload receipt here for manual review', 'رسید یہاں اپ لوڈ کریں')}</li>
                                    </ol>
                                </div>

                                <div className="checkout-trust-badge">
                                    <CustomerIcon name="shield" />
                                    <span>{t('Official Bank Account · SafeReturn Verified', 'سرکاری بینک اکاؤنٹ · محفوظ تصدیق')}</span>
                                </div>

                                <div style={{ marginTop: '1rem' }}>
                                    <Link className="button secondary" href={`/orders/${orderId}`} style={{ width: '100%', justifyContent: 'center' }}>
                                        {t('View Full Order Details', 'آرڈر کی مکمل تفصیلات')}
                                    </Link>
                                </div>
                            </div>
                        </aside>
                    </div>
                </>
            )}

            {!payment && !busy && (
                <div className="payment-status-card">
                    <p>{t('Payment information could not be loaded.', 'ادائیگی کی معلومات لوڈ نہیں ہو سکیں۔')}</p>
                    <button className="button secondary" type="button" onClick={() => void load()}>
                        {t('Try Again', 'دوبارہ کوشش کریں')}
                    </button>
                </div>
            )}
        </section>
    );
}
