"use client";
import Link from "next/link";
import { useState } from "react";
import type { StaffSecurityState } from "../lib/auth/staff-contract";
import type { Observation } from "../lib/api/system-observation";
export function SystemHealth({ ur, security }: { ur: boolean; security: StaffSecurityState }) {
  const [observation, setObservation] = useState<Observation | null>(null), [lastResponse, setLastResponse] = useState<string | null>(null);
  const [busy, setBusy] = useState(false), [notice, setNotice] = useState("");
  const t = (en: string, translated: string) => ur ? translated : en;
  async function check() {
    setBusy(true); setNotice(""); setObservation(null);
    try {
      const response = await fetch('/admin/system/api', { cache: 'no-store' });
      if (!response.ok) throw new Error();
      const value: Observation = await response.json(); setObservation(value);
      if (value.state === 'responded') setLastResponse(value.checked_at);
    } catch { setNotice(t('Status unavailable. Access or verification may have changed; retry or sign in again.', 'حالت دستیاب نہیں۔ رسائی یا تصدیق تبدیل ہو سکتی ہے؛ دوبارہ کوشش یا لاگ اِن کریں۔')); }
    finally { setBusy(false); }
  }
  const labels = { responded: t('Process answered', 'عمل نے جواب دیا'), unavailable: t('Liveness check unavailable', 'عمل کی جانچ دستیاب نہیں'), unconfigured: t('API origin unconfigured', 'API کا پتہ مقرر نہیں'), unknown: t('Unknown response', 'نامعلوم جواب') };
  return <>
    <h1>{t('System observations', 'نظام کے مشاہدات')}</h1>
    <p>{t('A process response is not database readiness, worker activity, provider health, email delivery or backup evidence. No checks run automatically.', 'عمل کا جواب ڈیٹابیس، کارکن، فراہم کنندہ، ای میل یا بیک اَپ کی صحت کا ثبوت نہیں۔ جانچ خودکار نہیں چلتی۔')}</p>
    <section aria-label={t('API process observation', 'API عمل کا مشاہدہ')}><h2>{t('API process', 'API عمل')}</h2>
      <button className="button" disabled={busy} onClick={check}>{t('Check process liveness', 'عمل کی جانچ کریں')}</button>
      <p role="status" aria-live="polite">{busy ? t('Checking…', 'جانچ جاری ہے…') : notice || (observation ? labels[observation.state] : t('Not observed', 'مشاہدہ نہیں ہوا'))}</p>
      {observation && <p>{t('Observed at', 'مشاہدے کا وقت')}: <time dir="ltr">{observation.checked_at}</time></p>}
      {lastResponse && (!observation || observation.state !== 'responded') && <p>{t('Stale evidence: previous process response only', 'پرانا ثبوت: صرف پچھلا جواب')}: <time dir="ltr">{lastResponse}</time></p>}
      {observation?.state === 'responded' && <p>{t('This is one historical observation. Refresh before relying on current availability; no approved freshness window is defined.', 'یہ ایک سابقہ مشاہدہ ہے۔ موجودہ دستیابی کے لیے دوبارہ جانچیں؛ تازگی کی منظور شدہ مدت مقرر نہیں۔')}</p>}
    </section>
    <h2>{t('Unobserved dependencies', 'غیر مشاہدہ شدہ خدمات')}</h2>
    <p>{t('Unknown means no approved observation is available. It does not mean configured, healthy, idle or unconfigured.', 'نامعلوم کا مطلب منظور شدہ مشاہدہ موجود نہیں۔ یہ صحت، فعالیت یا ترتیب کی تصدیق نہیں۔')}</p>
    {['Database readiness', 'Durable workers and queue lag', 'Resend delivery', 'Cloudinary', 'Turnstile', 'Google Sheets', 'Private Storage', 'Backup and restore evidence'].map((name, i) => <section key={name} style={{ borderBlockStart: '1px solid #bdd6d4', paddingBlock: '1rem' }}><h3>{ur ? ['ڈیٹابیس کی تیاری', 'کارکن اور قطار میں تاخیر', 'ای میل کی ترسیل', 'کلاؤڈینری', 'ٹرن اسٹائل', 'گوگل شیٹس', 'نجی ذخیرہ', 'بیک اَپ اور بحالی کا ثبوت'][i] : name}</h3><p>{t('Unknown — observation contract unavailable', 'نامعلوم — مشاہدے کا منظور شدہ معاہدہ دستیاب نہیں')}</p></section>)}
    <p>{t('Internal readiness remains separately token-protected. This console cannot access it. Worker heartbeats, provider observations, backup evidence, alert owners and freshness thresholds require approved contracts and evidence under 6.3A/B.', 'اندرونی تیاری الگ حفاظتی ٹوکن سے محفوظ ہے۔ یہ صفحہ اسے نہیں پڑھتا۔ کارکن، فراہم کنندہ، بیک اَپ اور انتباہ کے لیے منظور شدہ معاہدے اور ثبوت درکار ہیں۔')}</p>
    <h2>{t('Existing operational records', 'موجودہ عملی ریکارڈ')}</h2>
    <p>{t('These consoles show scoped records, not provider or worker health.', 'یہ صفحات محدود ریکارڈ دکھاتے ہیں، فراہم کنندہ یا کارکن کی صحت نہیں۔')}</p>
    <ul>
      <li><Link href="/admin/notifications">{t('Notification metadata', 'اطلاعات کی معلومات')}</Link></li>
      {security.capabilities.includes('storage.metadata') && <li><Link href="/admin/storage">{t('Storage and retention metadata', 'ذخیرہ اور پابندی کی معلومات')}</Link></li>}
      {security.capabilities.includes('finance.mirror') && <li><Link href="/admin/finance/sheet-sync">{t('Finance mirror records', 'مالیاتی آئینے کے ریکارڈ')}</Link></li>}
    </ul>
    <p>{t('Runbook reference: Doc 09 §8.2 (liveness versus readiness) and deployment/worker monitoring guidance. No restart, replay, configuration or execution controls are provided.', 'رہنمائی: دستاویز 09، حصہ 8.2 اور کارکن کی نگرانی۔ یہاں دوبارہ چلانے، ترتیب بدلنے یا عمل درآمد کے کنٹرول نہیں۔')}</p>
  </>;
}
