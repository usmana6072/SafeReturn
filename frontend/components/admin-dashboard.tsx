'use client';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { dashboardGroups, dashboardMetrics, dashboardRoles, dashboardSeries, parseDashboardSummary, parseDashboardTrends, type Summary, type Trends, type Count } from '../lib/dashboard-contract';
import styles from './admin-dashboard.module.css';

export function AdminDashboard({ ur, roles }: { ur: boolean; roles: string[] }) {
  const [summary, setSummary] = useState<Summary | null>(null), [trends, setTrends] = useState<Trends | null>(null);
  const [errors, setErrors] = useState({ summary: '', trends: '' }), [busy, setBusy] = useState({ summary: true, trends: true });
  const [timezone, setTimezone] = useState('UTC'), [hidden, setHidden] = useState(false);
  const requests = useRef<Record<string, AbortController>>({}), sequence = useRef({ summary: 0, trends: 0 }), denied = useRef(false);
  const t = (en: string, translation: string) => ur ? translation : en;
  const number = (c: Count) => String(c.value) + (c.is_exact ? '' : '+');
  const date = (stamp: string) => new Intl.DateTimeFormat(ur ? 'ur-PK' : 'en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone }).format(new Date(stamp));
  const reason = (code: string | null) => code === 'LOW_STOCK_UNCONFIGURED' ? t('Low-stock threshold is unconfigured; the inventory drill-down is pending.', 'ذخیرے کی حد مقرر نہیں؛ تفصیلی صفحہ ابھی تیار نہیں۔') : code === 'FEATURE_DISABLED' ? t('This dependency is disabled. No count is available.', 'یہ سہولت بند ہے۔ گنتی دستیاب نہیں۔') : code === 'DRILLDOWN_UNAVAILABLE' ? t('The matching operational drill-down is not implemented. No count is available.', 'متعلقہ عملی صفحہ ابھی تیار نہیں۔ گنتی دستیاب نہیں۔') : code === 'REQUEST_BUDGET_EXHAUSTED' ? t('The query budget was reached. Refresh to retry.', 'جانچ کا وقت ختم ہو گیا۔ دوبارہ کوشش کریں۔') : t('Observation unavailable. Refresh to retry.', 'مشاہدہ دستیاب نہیں۔ دوبارہ کوشش کریں۔');

  async function load(kind: 'summary' | 'trends', tz = timezone) {
    const current = ++sequence.current[kind]; requests.current[kind]?.abort();
    const controller = new AbortController(); requests.current[kind] = controller;
    setBusy(v => ({ ...v, [kind]: true })); setErrors(v => ({ ...v, [kind]: '' }));
    if (kind === 'summary') setSummary(null); else setTrends(null);
    try {
      const r = await fetch('/admin/dashboard/api?kind=' + kind + (kind === 'trends' ? '&display_timezone=' + encodeURIComponent(tz) : ''), { cache: 'no-store', signal: controller.signal });
      if (r.status === 401 || r.status === 403) {
        denied.current = true; setSummary(null); setTrends(null);
        setErrors({ summary: 'access', trends: 'access' }); return;
      }
      if (!r.ok) throw new Error();
      const value: unknown = await r.json();
      if (current !== sequence.current[kind] || controller.signal.aborted || denied.current) return;
      if (kind === 'summary') setSummary(parseDashboardSummary(value, roles));
      else setTrends(parseDashboardTrends(value, roles, tz));
    } catch {
      if (!controller.signal.aborted && current === sequence.current[kind] && !denied.current) setErrors(v => ({ ...v, [kind]: 'unavailable' }));
    } finally { if (current === sequence.current[kind]) setBusy(v => ({ ...v, [kind]: false })); }
  }
  function refresh() { denied.current = false; setHidden(false); void load('summary'); void load('trends'); }
  const roleKey = roles.join(',');
  useEffect(() => {
    denied.current = false; void load('summary'); void load('trends');
    const visibility = () => { if (document.visibilityState === 'hidden') setHidden(true); };
    document.addEventListener('visibilitychange', visibility);
    return () => { Object.values(requests.current).forEach(c => c.abort()); sequence.current.summary++; sequence.current.trends++; document.removeEventListener('visibilitychange', visibility); };
    // The live backend checks roles/session/MFA on every independent read.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleKey]);
  const access = errors.summary === 'access' || errors.trends === 'access';
  return <section className={styles.dashboard} aria-labelledby="dashboard-heading" dir={ur ? 'rtl' : 'ltr'}>
    <h2 id="dashboard-heading">{t('Operational overview', 'عملی جائزہ')}</h2>
    <p>{t('Counts are independent historical observations of retained records. They do not certify settlement, delivery, physical QA or provider health.', 'گنتیاں محفوظ ریکارڈ کے الگ مشاہدات ہیں۔ یہ ادائیگی، ترسیل، عملی جانچ یا فراہم کنندہ کی صحت کی تصدیق نہیں۔')}</p>
    <div className={styles.controls}><button className="button secondary" onClick={refresh} disabled={busy.summary || busy.trends}>{t('Refresh dashboard', 'جائزہ تازہ کریں')}</button>
      <label>{t('Display timezone', 'وقت کا علاقہ')} <select value={timezone} disabled={busy.trends} onChange={e => { setTimezone(e.target.value); if (!denied.current) void load('trends', e.target.value); }}><option value="UTC">UTC</option><option value="Asia/Karachi">Asia/Karachi</option></select></label></div>
    {hidden && <p role="status">{t('These observations may be stale after leaving the page. Refresh before acting.', 'صفحہ چھوڑنے کے بعد یہ مشاہدات پرانے ہو سکتے ہیں۔ کارروائی سے پہلے تازہ کریں۔')}</p>}
    {access && <p role="alert">{t('Access changed or the session expired. Sign in again; prior observations have been cleared.', 'رسائی تبدیل ہو گئی یا نشست ختم ہو گئی۔ دوبارہ لاگ اِن کریں؛ پچھلے مشاہدات ہٹا دیے گئے ہیں۔')} <Link href="/login">{t('Sign in', 'لاگ اِن')}</Link></p>}
    <div aria-live="polite" role="status">{busy.summary ? t('Loading current counts…', 'گنتیاں لوڈ ہو رہی ہیں…') : errors.summary && !access ? t('Counts unavailable. No zero or healthy state is implied.', 'گنتیاں دستیاب نہیں۔ اس کا مطلب صفر یا صحت مند حالت نہیں۔') : ''}</div>
    <div className={styles.groups}>{summary?.groups.filter(g => dashboardRoles[g.group].some(r => roles.includes(r))).map(g => <section className={styles.group} key={g.group} aria-label={dashboardGroups[g.group][ur ? 1 : 0]}>
      <h3>{dashboardGroups[g.group][ur ? 1 : 0]}</h3>
      {g.status === 'unavailable' ? <p>{reason(g.reason_code)}</p> : <>
        <p className={styles.time}>{t('Observed at', 'مشاہدے کا وقت')}: <time dateTime={g.as_of!}><bdi>{date(g.as_of!)}</bdi></time></p>
        <dl>{g.metrics.map(m => { const def = dashboardMetrics[m.metric_id]; return <div key={m.metric_id} className={styles.metric}>
          <dt><Link href={m.drilldown} prefetch={false}>{def.label[ur ? 1 : 0]}</Link></dt><dd><bdi>{number(m.count)}</bdi></dd>
          {def.warning && m.count.value > 0 && <dd className={styles.warning}>{t('Needs review', 'جائزہ درکار ہے')} · {def.warning[ur ? 1 : 0]}</dd>}
        </div>; })}</dl>
      </>}
    </section>)}</div>
    {summary && summary.groups.length === 0 && <p>{t('No dashboard observations are permitted for the current roles.', 'موجودہ کرداروں کے لیے مشاہدات کی اجازت نہیں۔')}</p>}
    <h3>{t('Daily operational trends', 'روزانہ کے عملی رجحانات')}</h3>
    <p>{t('30 completed UTC days. Display timezone changes labels only. Current returns or later state changes do not erase recorded dispatch timestamps; this is not a historical state snapshot.', 'مکمل شدہ 30 UTC دن۔ وقت کا علاقہ صرف لیبل بدلتا ہے۔ بعد کی واپسی یا حالت کی تبدیلی روانگی کا وقت نہیں مٹاتی؛ یہ سابقہ حالت کی مکمل تصویر نہیں۔')}</p>
    <p role="status" aria-live="polite">{busy.trends ? t('Loading trends…', 'رجحانات لوڈ ہو رہے ہیں…') : errors.trends && !access ? t('Trends unavailable. Other observations may still be available.', 'رجحانات دستیاب نہیں۔ دوسرے مشاہدات دستیاب ہو سکتے ہیں۔') : ''}</p>
    {trends?.series.filter(s => dashboardSeries[s.series_id].roles.some(r => roles.includes(r))).map(s => <section key={s.series_id} className={styles.group}>
      <h4>{dashboardSeries[s.series_id].label[ur ? 1 : 0]}</h4>
      {s.status === 'unavailable' ? <p>{reason(s.reason_code)}</p> : <>
        <p>{t('Observed at', 'مشاہدے کا وقت')}: <time dateTime={trends.as_of}><bdi>{date(trends.as_of)}</bdi></time></p>
        <div className={styles.bars} role="img" aria-label={t('Daily counts. The following table contains every value. Bars marked 1000+ are capped.', 'روزانہ گنتیاں۔ نیچے جدول میں تمام قدریں ہیں۔ 1000+ محدود گنتی ہے۔')}>
          {s.buckets.map(b => <span key={b.start} aria-hidden="true" style={{ height: `${Math.max(1, b.count.value / Math.max(1, ...s.buckets.map(v => v.count.value)) * 100)}%` }} title={`${date(b.start)}: ${number(b.count)}`}/>)}
        </div>
        <details><summary>{t('View all daily counts as a table', 'تمام روزانہ گنتیاں جدول میں دیکھیں')}</summary><table><caption>{t('UTC intervals, labels in', 'UTC وقفے، وقت کا علاقہ')} <bdi>{timezone}</bdi></caption>
          <thead><tr><th scope="col">{t('Start (included)', 'ابتدا (شامل)')}</th><th scope="col">{t('End (excluded)', 'اختتام (غیر شامل)')}</th><th scope="col">{t('Count', 'گنتی')}</th></tr></thead>
          <tbody>{s.buckets.map(b => <tr key={b.start}><td><bdi>{date(b.start)}</bdi></td><td><bdi>{date(b.end)}</bdi></td><td><bdi>{number(b.count)}</bdi></td></tr>)}</tbody></table></details>
        <Link href={dashboardSeries[s.series_id].path!} prefetch={false}>{t('Open records (all dates / states)', 'ریکارڈ کھولیں (تمام تاریخیں / حالتیں)')}</Link>
      </>}
    </section>)}
    <p className={styles.note}>{t('Some breakdowns await matching drill-downs. Registered-user counts, revenue, profit, refunds, activation history and scan analytics are not available here. No action or background provider check runs from this dashboard.', 'کچھ تفصیلات کے متعلقہ صفحات ابھی تیار نہیں۔ صارفین، آمدنی، منافع، رقم کی واپسی، فعالیت کی تاریخ اور اسکین کے اعداد یہاں دستیاب نہیں۔ یہاں سے کوئی کارروائی یا بیرونی جانچ نہیں چلتی۔')}</p>
    <p>{t('1000+ means a capped count, never an exact total. Refresh for a new observation; no freshness SLA is certified.', '1000+ محدود گنتی ہے، مکمل تعداد نہیں۔ نئے مشاہدے کے لیے تازہ کریں؛ تازگی کی ضمانت نہیں۔')}</p>
    {!Object.keys(dashboardRoles).some(g => dashboardRoles[g].some(r => roles.includes(r))) && <p>{t('No authorized dashboard groups.', 'جائزے کے کسی حصے کی اجازت نہیں۔')}</p>}
  </section>;
}
