// Closed, metadata-only browser contract. URLs and labels come from this registry.
export const dashboardRoles: Record<string, readonly string[]> = {
  catalog: ['operations', 'security_admin', 'superadmin'], inventory: ['operations'],
  fulfillment: ['operations'], printing: ['operations'], finance: ['finance'],
  notifications: ['operations', 'security_admin'], support: ['support'],
  finance_mirror: ['finance', 'security_admin', 'superadmin'],
};
export const dashboardGroups: Record<string, [string, string]> = {
  catalog: ['Catalogue', 'مصنوعات'], inventory: ['Inventory', 'ذخیرہ'], fulfillment: ['Fulfillment', 'ترسیل'],
  printing: ['Print QA', 'پرنٹ کی جانچ'], finance: ['Finance review', 'مالی جائزہ'],
  notifications: ['Notifications', 'اطلاعات'], support: ['Support cases', 'معاونت کے معاملات'], finance_mirror: ['Finance mirror', 'مالیاتی آئینہ'],
};
type Definition = { group: string; unit: string; path: string; label: [string, string]; warning?: [string, string] };
export const dashboardMetrics: Record<string, Definition> = {
  'catalog.products': { group: 'catalog', unit: 'product', path: '/admin/products', label: ['Products — all states', 'مصنوعات — تمام حالتیں'] },
  'catalog.variants': { group: 'catalog', unit: 'variant', path: '/admin/products', label: ['Variants — all states', 'ویریئنٹ — تمام حالتیں'] },
  'fulfillment.ready_orders': { group: 'fulfillment', unit: 'order', path: '/admin/ready-to-ship', label: ['Orders ready for packing / dispatch', 'پیکنگ اور روانگی کے لیے تیار آرڈرز'] },
  'fulfillment.requires_review': { group: 'fulfillment', unit: 'shipment', path: '/admin/shipments?requires_review=true', label: ['Packages requiring eligibility review', 'اہلیت کے جائزے والے پیکیج'], warning: ['Operations · Doc 09 fulfillment controls', 'آپریشنز · دستاویز 09 ترسیل کی رہنمائی'] },
  'finance_mirror.records': { group: 'finance_mirror', unit: 'sync_record', path: '/admin/finance/sheet-sync', label: ['Mirror records — all states', 'آئینے کے ریکارڈ — تمام حالتیں'] },
};
for (const [state, en, ur] of [
  ['preparing', 'Preparing packages', 'تیار ہوتے پیکیج'], ['packed', 'Packed packages', 'پیک شدہ پیکیج'],
  ['dispatched', 'Dispatched packages', 'روانہ پیکیج'], ['delivered', 'Delivered packages', 'پہنچائے گئے پیکیج'],
  ['exception', 'Delivery exceptions', 'ترسیل میں مسئلے'], ['returned', 'Returned packages', 'واپس آئے پیکیج'],
]) dashboardMetrics['shipments.' + state] = { group: 'fulfillment', unit: 'shipment', path: '/admin/shipments?status=' + state, label: [en, ur], ...(state === 'exception' ? { warning: ['Operations · Doc 09 fulfillment controls', 'آپریشنز · دستاویز 09 ترسیل کی رہنمائی'] as [string, string] } : {}) };
for (const [state, en, ur] of [
  ['pending', 'Pending notification events', 'منتظر اطلاعات'], ['leased', 'Leased notification events', 'کارکن کے سپرد اطلاعات'],
  ['retry', 'Retrying notification events', 'دوبارہ کوشش والی اطلاعات'], ['sent', 'Sent notification events', 'بھیجی گئی اطلاعات'], ['dead', 'Dead-letter notification events', 'روکی گئی اطلاعات'],
]) dashboardMetrics['notifications.' + state] = { group: 'notifications', unit: 'outbox_event', path: '/admin/notifications?status=' + state, label: [en, ur], ...(state === 'dead' ? { warning: ['Operations / security · Doc 09 notification reconciliation', 'آپریشنز / سکیورٹی · دستاویز 09 اطلاعات کا جائزہ'] as [string, string] } : {}) };
for (const [state, en, ur] of [['open', 'Open cases in your queue', 'آپ کی فہرست کے کھلے معاملات'], ['investigating', 'Cases being investigated in your queue', 'آپ کی فہرست میں زیر تفتیش معاملات']]) dashboardMetrics['support.' + state] = { group: 'support', unit: 'case', path: '/admin/support?status=' + state, label: [en, ur] };
export const dashboardSeries: Record<string, { roles: readonly string[]; unit: string; label: [string, string]; path: string | null }> = {
  orders_placed: { roles: ['operations', 'finance'], unit: 'order', label: ['Placed orders', 'درج شدہ آرڈرز'], path: null },
  shipments_dispatched: { roles: ['operations'], unit: 'shipment', label: ['Dispatch observations', 'روانگی کے مشاہدات'], path: '/admin/shipments' },
  notifications_created: { roles: ['operations', 'security_admin'], unit: 'outbox_event', label: ['Created notification events', 'درج شدہ اطلاعات'], path: '/admin/notifications' },
};
export type Count = { value: number; is_exact: boolean };
export type Metric = { metric_id: string; unit: string; count: Count; drilldown: string };
export type Group = { group: string; status: 'ready' | 'unavailable'; as_of: string | null; metrics: Metric[]; reason_code: string | null };
export type Summary = { as_of: string; groups: Group[] };
export type Bucket = { start: string; end: string; count: Count };
export type Series = { series_id: string; unit: string; status: 'ready' | 'unavailable'; reason_code: string | null; buckets: Bucket[] };
export type Trends = { as_of: string; range_start: string; range_end: string; bucket_timezone: 'UTC'; display_timezone: 'UTC' | 'Asia/Karachi'; series: Series[] };
const reasons = ['QUERY_UNAVAILABLE', 'DRILLDOWN_UNAVAILABLE', 'FEATURE_DISABLED', 'LOW_STOCK_UNCONFIGURED', 'REQUEST_BUDGET_EXHAUSTED'];
function bad(): never { throw new Error('unavailable'); }
function object(value: unknown, keys: string[]): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length !== keys.length || keys.some(k => !(k in value))) bad();
  return value as Record<string, unknown>;
}
export function dashboardTime(value: unknown): string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(value) || !Number.isFinite(Date.parse(value))) bad();
  if (new Date(value).toISOString().slice(0, 19) !== value.slice(0, 19)) bad();
  return value;
}
function count(value: unknown): Count {
  const c = object(value, ['value', 'is_exact']);
  if (!Number.isInteger(c.value) || (c.value as number) < 0 || (c.value as number) > 1000 || c.is_exact !== ((c.value as number) < 1000)) bad();
  return c as Count;
}
function unique(values: string[]) { if (new Set(values).size !== values.length) bad(); }
function permitted(allowed: readonly string[], roles: readonly string[]) { return roles.some(role => allowed.includes(role)); }
function state(v: Record<string, unknown>, items: unknown[], stamp?: unknown) {
  if (!['ready', 'unavailable'].includes(String(v.status))) bad();
  if (v.status === 'ready') { if (v.reason_code !== null || (stamp !== undefined && stamp === null)) bad(); }
  else if (typeof v.reason_code !== 'string' || !reasons.includes(v.reason_code) || items.length || (stamp !== undefined && stamp !== null)) bad();
}
export function parseDashboardSummary(value: unknown, roles: readonly string[]): Summary {
  const v = object(value, ['as_of', 'groups']); dashboardTime(v.as_of);
  if (!Array.isArray(v.groups) || v.groups.length > 8) bad();
  const groups = v.groups.map(raw => {
    const g = object(raw, ['group', 'status', 'as_of', 'metrics', 'reason_code']);
    if (typeof g.group !== 'string' || !Object.hasOwn(dashboardRoles, g.group) || !permitted(dashboardRoles[g.group], roles) || !Array.isArray(g.metrics) || g.metrics.length > 8) bad();
    state(g, g.metrics, g.as_of); if (g.as_of !== null) dashboardTime(g.as_of);
    const metrics = g.metrics.map(rawMetric => {
      const m = object(rawMetric, ['metric_id', 'unit', 'count', 'drilldown']);
      const def = typeof m.metric_id === 'string' && Object.hasOwn(dashboardMetrics, m.metric_id) ? dashboardMetrics[m.metric_id] : null;
      if (!def || def.group !== g.group || def.unit !== m.unit || def.path !== m.drilldown) bad();
      return { ...m, count: count(m.count) } as Metric;
    });
    unique(metrics.map(m => m.metric_id));
    if (g.status === 'ready' && (!metrics.length || metrics.length !== Object.values(dashboardMetrics).filter(m => m.group === g.group).length)) bad();
    return { ...g, metrics } as Group;
  }); unique(groups.map(g => g.group)); return { as_of: v.as_of as string, groups };
}
export function parseDashboardTrends(value: unknown, roles: readonly string[], timezone: string): Trends {
  const v = object(value, ['as_of', 'range_start', 'range_end', 'bucket_timezone', 'display_timezone', 'series']);
  dashboardTime(v.as_of); const start = Date.parse(dashboardTime(v.range_start)), end = Date.parse(dashboardTime(v.range_end));
  if (v.bucket_timezone !== 'UTC' || !['UTC', 'Asia/Karachi'].includes(timezone) || v.display_timezone !== timezone || end - start !== 30 * 86400000 || end % 86400000 || end > Date.parse(v.as_of as string) || Date.parse(v.as_of as string) - end >= 86400000 || !Array.isArray(v.series) || v.series.length > 3) bad();
  const series = v.series.map(raw => {
    const s = object(raw, ['series_id', 'unit', 'status', 'reason_code', 'buckets']);
    const def = typeof s.series_id === 'string' && Object.hasOwn(dashboardSeries, s.series_id) ? dashboardSeries[s.series_id] : null;
    if (!def || !permitted(def.roles, roles) || s.unit !== def.unit || !Array.isArray(s.buckets)) bad();
    state(s, s.buckets); if (s.status === 'ready' && (s.buckets.length !== 30 || def.path === null)) bad();
    const buckets = s.buckets.map((rawBucket, i) => {
      const b = object(rawBucket, ['start', 'end', 'count']);
      if (Date.parse(dashboardTime(b.start)) !== start + i * 86400000 || Date.parse(dashboardTime(b.end)) !== start + (i + 1) * 86400000) bad();
      return { ...b, count: count(b.count) } as Bucket;
    }); return { ...s, buckets } as Series;
  }); unique(series.map(s => s.series_id)); return { ...v, series } as Trends;
}
