/* Synthetic contract/relay/component checks. All browser requests intercepted; no listener. */
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const ts = require('typescript'), { NextRequest } = require('next/server'), { chromium, expect } = require('@playwright/test');
const root = path.resolve(__dirname, '..'), out = path.resolve(root, '../output/task57b/browser'); fs.mkdirSync(out, { recursive: true });
const origin = 'https://dashboard.synthetic.invalid', upstream = 'https://dashboard-api.synthetic.invalid';
const privateCanary = 'PRIVATE_DASHBOARD_BROWSER_CANARY';
function compile(file, requireImpl, globals = {}) {
  const sandbox = { exports: {}, require: requireImpl, ...globals };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText, sandbox);
  return sandbox.exports;
}
const contract = compile(path.join(root, 'lib/dashboard-contract.ts'), () => { throw Error('unexpected import'); });
const roles = ['operations', 'finance'];
function summary(forRoles = roles) {
  const unsupported = new Set(['inventory', 'printing', 'finance']);
  return { as_of: new Date().toISOString(), groups: Object.entries(contract.dashboardRoles).filter(([, permitted]) => permitted.some(r => forRoles.includes(r))).map(([group]) => ({
    group, status: unsupported.has(group) ? 'unavailable' : 'ready', as_of: unsupported.has(group) ? null : new Date().toISOString(),
    reason_code: group === 'finance' ? 'FEATURE_DISABLED' : group === 'inventory' ? 'LOW_STOCK_UNCONFIGURED' : group === 'printing' ? 'DRILLDOWN_UNAVAILABLE' : null,
    metrics: unsupported.has(group) ? [] : Object.entries(contract.dashboardMetrics).filter(([, m]) => m.group === group).map(([id, m]) => ({
      metric_id: id, unit: m.unit, drilldown: m.path, count: id === 'catalog.products' ? { value: 1000, is_exact: false } : { value: id === 'shipments.exception' ? 0 : 2, is_exact: true },
    })),
  })) };
}
function trends(forRoles = roles, timezone = 'UTC') {
  const now = new Date(), end = new Date(now); end.setUTCHours(0, 0, 0, 0);
  const start = new Date(+end - 30 * 86400000);
  return { as_of: now.toISOString(), range_start: start.toISOString(), range_end: end.toISOString(), bucket_timezone: 'UTC', display_timezone: timezone,
    series: Object.entries(contract.dashboardSeries).filter(([, def]) => def.roles.some(r => forRoles.includes(r))).map(([series_id, def]) => ({
      series_id, unit: def.unit, status: def.path ? 'ready' : 'unavailable', reason_code: def.path ? null : 'DRILLDOWN_UNAVAILABLE',
      buckets: def.path ? Array.from({ length: 30 }, (_, i) => ({ start: new Date(+start + i * 86400000).toISOString(), end: new Date(+start + (i+1) * 86400000).toISOString(), count: { value: i === 29 ? 1000 : i, is_exact: i !== 29 } })) : [],
    })),
  };
}

function parserChecks() {
  const valid = summary(); assert.equal(contract.parseDashboardSummary(valid, roles).groups.length, 7);
  const clone = value => JSON.parse(JSON.stringify(value));
  const malformed = [];
  let b = clone(valid); b.private = privateCanary; malformed.push(b);
  b = clone(valid); b.groups[0].metrics[0].count.value = '1'; malformed.push(b);
  b = clone(valid); b.groups[0].metrics[0].count.is_exact = true; malformed.push(b);
  b = clone(valid); b.groups[0].metrics[0].drilldown = '//foreign.test/'; malformed.push(b);
  b = clone(valid); b.groups[0].metrics[0].private = privateCanary; malformed.push(b);
  b = clone(valid); b.groups.push(b.groups[0]); malformed.push(b);
  b = clone(valid); b.groups[0].group = '__proto__'; malformed.push(b);
  b = clone(valid); b.groups[0].metrics[0].metric_id = 'toString'; malformed.push(b);
  b = clone(valid); b.as_of = '2026-02-30T10:00:00Z'; malformed.push(b);
  b = clone(valid); b.groups[1].status = 'ready'; b.groups[1].as_of = valid.as_of; b.groups[1].reason_code = null; malformed.push(b);
  for (const data of malformed) assert.throws(() => contract.parseDashboardSummary(data, roles), /unavailable/);
  assert.throws(() => contract.parseDashboardSummary(valid, ['finance']), /unavailable/);
  assert.equal(contract.parseDashboardTrends(trends(), roles, 'UTC').series.length, 3);
  const temporal = [];
  b = trends(); b.series[1].buckets[1].start = b.series[1].buckets[0].start; temporal.push(b);
  b = trends(); b.series[1].buckets.pop(); temporal.push(b);
  b = trends(); b.series[1].buckets[0].count.value = -1; temporal.push(b);
  b = trends(); b.range_end = b.as_of; temporal.push(b);
  b = trends(); b.display_timezone = 'Europe/London'; temporal.push(b);
  b = trends(); b.series[0].status = 'ready'; b.series[0].reason_code = null; b.series[0].buckets = b.series[1].buckets; temporal.push(b);
  for (const data of temporal) assert.throws(() => contract.parseDashboardTrends(data, roles, 'UTC'), /unavailable/);
  console.log('PASS parser: closed fields, exact role/path/unit/cap/state contracts, duplicate/prototype/privacy/date/bucket rejection.');
}

async function relayChecks() {
  let session = null, mfa = true, mode = 'valid', calls = [], staffFailure = 0;
  class StaffAccessError extends Error { constructor(status) { super('safe'); this.status = status; } }
  const globals = { AbortSignal, TextDecoder, process: { env: { SAFERETURN_API_ORIGIN: upstream } }, fetch: async (url, options) => {
    calls.push({ url, options });
    if (mode === 'network') throw Error(privateCanary);
    const data = new URL(url).pathname.endsWith('/summary') ? summary() : trends(roles, new URL(url).searchParams.get('display_timezone'));
    if (mode === 'private') data.private = privateCanary;
    return new Response(mode === 'oversize' ? 'x'.repeat(64001) : mode === 'down' ? privateCanary : JSON.stringify(data), { status: mode === 'down' ? 503 : 200, headers: { 'Content-Type': mode === 'mime' ? 'text/html' : 'application/json' } });
  } };
  const relay = compile(path.join(root, 'lib/api/dashboard-relay.ts'), name => {
    if (name === 'next/server') return require(name);
    if (name === '../auth/server') return { verifiedSession: async () => session };
    if (name === '../auth/staff') return { StaffAccessError, staffState: async () => { if (staffFailure) throw new StaffAccessError(staffFailure); return { roles, mfa_verified: mfa }; } };
    if (name === '../auth/config') return { authConfig: () => ({ origin }) };
    if (name === './transport') return { validateOrigin: value => { assert.equal(value, upstream); return value; } };
    if (name === '../dashboard-contract') return contract;
    throw Error('unexpected import');
  }, globals).dashboardRelay;
  const request = (query = 'kind=summary', headers = {}) => new NextRequest(origin + '/admin/dashboard/api?' + query, { headers });
  assert.equal((await relay(request())).status, 401); assert.equal(calls.length, 0);
  session = { token: 'synthetic-only-token' };
  assert.equal((await relay(request('kind=summary', { Origin: 'https://foreign.invalid' }))).status, 403);
  mfa = false; assert.equal((await relay(request())).status, 403); mfa = true;
  for (const status of [401, 403]) { staffFailure = status; assert.equal((await relay(request())).status, status); } staffFailure = 0;
  for (const query of ['kind=summary&path=/admin/users', 'kind=summary&kind=trends', 'kind=summary&display_timezone=UTC', 'kind=trends&display_timezone=bad', 'kind=../payments']) assert.equal((await relay(request(query))).status, 422);
  assert.equal(calls.length, 0);
  let response = await relay(request()); assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'private, no-store');
  assert.equal(calls[0].url, upstream + '/api/v1/admin/dashboard/summary'); assert.equal(calls[0].options.redirect, 'error'); assert.equal(calls[0].options.cache, 'no-store');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer synthetic-only-token'); assert.equal((await response.text()).includes('synthetic-only-token'), false);
  response = await relay(request('kind=trends&display_timezone=Asia%2FKarachi')); assert.equal(response.status, 200);
  for (const failure of ['private', 'down', 'network', 'mime', 'oversize']) {
    mode = failure; response = await relay(request()); assert.equal(response.status, 503); assert.equal((await response.text()).includes(privateCanary), false);
  }
  console.log('PASS relay: session/MFA/origin, closed queries, fixed GET targets, private headers, caps/MIME/canaries/failures.');
}

async function browserChecks() {
  const modules = path.join(root, 'node_modules'), component = path.join(root, 'components/admin-dashboard').replaceAll('\\', '/');
  fs.writeFileSync(path.join(out, 'loader.cjs'), `const ts=require(${JSON.stringify(path.join(modules, 'typescript'))});module.exports=source=>ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2017,module:ts.ModuleKind.ESNext}}).outputText;`);
  fs.writeFileSync(path.join(out, 'css-loader.cjs'), `module.exports=source=>'module.exports='+JSON.stringify(Object.fromEntries([...source.matchAll(/\\.([a-zA-Z][\\w-]*)/g)].map(m=>[m[1],m[1]])));`);
  fs.writeFileSync(path.join(out, 'link.tsx'), `import React from 'react';export default function Link({href,children,...props}){delete props.prefetch;return <a href={href} {...props}>{children}</a>}`);
  fs.writeFileSync(path.join(out, 'entry.tsx'), `import React from 'react';import{createRoot}from'react-dom/client';import{AdminDashboard}from'${component}';const root=createRoot(document.getElementById('root'));let k=0;window.show=(ur=false,roles=['operations','finance'])=>root.render(<AdminDashboard key={++k} ur={ur} roles={roles}/>);`);
  const webpack = require('next/dist/compiled/webpack/webpack').webpack;
  await new Promise((resolve, reject) => webpack({ mode: 'development', devtool: false, entry: path.join(out, 'entry.tsx'), output: { path: out, filename: 'bundle.js' }, resolve: { extensions: ['.tsx', '.ts', '.js'], modules: [modules], alias: { 'next/link': path.join(out, 'link.tsx') } }, module: { rules: [{ test: /\.tsx?$/, use: path.join(out, 'loader.cjs') }, { test: /\.css$/, use: path.join(out, 'css-loader.cjs') }] } }, (e, stats) => e || stats.hasErrors() ? reject(e || Error(stats.toString({ all: false, errors: true }))) : resolve()));
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } }), errors = [];
    page.setDefaultTimeout(15000); page.on('pageerror', e => errors.push(e.message));
    let mode = 'valid', selectedRoles = roles;
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      assert.equal(url.origin, origin); // no un-intercepted provider / listener
      if (url.pathname === '/admin/dashboard/api') {
        if (mode === 'denied') return route.fulfill({ status: 403, json: { private: privateCanary } });
        if (mode === 'down' || (mode === 'partial' && url.searchParams.get('kind') === 'summary')) return route.fulfill({ status: 503, json: { private: privateCanary } });
        const data = url.searchParams.get('kind') === 'summary' ? summary(selectedRoles) : trends(selectedRoles, url.searchParams.get('display_timezone'));
        return route.fulfill({ json: data });
      }
      if (url.pathname === '/bundle.js') return route.fulfill({ contentType: 'text/javascript', body: fs.readFileSync(path.join(out, 'bundle.js')) });
      if (url.pathname === '/style.css') return route.fulfill({ contentType: 'text/css', body: fs.readFileSync(path.join(root, 'components/admin-dashboard.module.css')) });
      return route.fulfill({ contentType: 'text/html', body: '<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/style.css"></head><body><div id="root"></div><script src="/bundle.js"></script></body></html>' });
    });
    await page.goto(origin); await page.evaluate(() => window.show());
    await expect(page.getByRole('heading', { name: 'Operational overview' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Catalogue', exact: true }).getByText('1000+', { exact: true })).toBeVisible();
    await expect(page.getByText('Low-stock threshold is unconfigured; the inventory drill-down is pending.', { exact: true })).toBeVisible();
    assert.equal(await page.getByRole('link', { name: 'Delivery exceptions', exact: true }).getAttribute('href'), '/admin/shipments?status=exception');
    await page.getByRole('combobox', { name: 'Display timezone' }).selectOption('Asia/Karachi');
    await expect(page.getByRole('img')).toHaveCount(2);
    await page.getByText('View all daily counts as a table', { exact: true }).first().click();
    await expect(page.locator('table').first().locator('tbody tr')).toHaveCount(30);
    mode = 'partial'; await page.getByRole('button', { name: 'Refresh dashboard' }).click();
    await expect(page.getByText('Counts unavailable. No zero or healthy state is implied.', { exact: true })).toBeVisible();
    await expect(page.getByRole('img')).toHaveCount(2);
    mode = 'denied'; await page.getByRole('button', { name: 'Refresh dashboard' }).click();
    await expect(page.getByRole('alert')).toContainText('Access changed');
    await expect(page.getByRole('img')).toHaveCount(0); await expect(page.getByText('1000+', { exact: true })).toHaveCount(0);
    assert.equal((await page.content()).includes(privateCanary), false);
    mode = 'valid'; selectedRoles = ['finance']; await page.evaluate(() => window.show(false, ['finance']));
    await expect(page.getByRole('heading', { name: 'Finance mirror', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Products — all states', exact: true })).toHaveCount(0);
    selectedRoles = roles; await page.setViewportSize({ width: 320, height: 844 }); await page.evaluate(() => window.show(true));
    await expect(page.getByRole('heading', { name: 'عملی جائزہ', exact: true })).toBeVisible();
    await expect(page.locator('section[aria-labelledby="dashboard-heading"]')).toHaveAttribute('dir', 'rtl');
    await expect(page.getByRole('img')).toHaveCount(2);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.deepEqual(await page.evaluate(() => [localStorage.length, sessionStorage.length]), [0, 0]);
    await page.getByRole('button', { name: 'جائزہ تازہ کریں' }).focus(); assert.equal(await page.evaluate(() => document.activeElement.tagName), 'BUTTON');
    await page.screenshot({ path: path.join(out, 'dashboard-ur-mobile.png'), fullPage: true });
    assert.deepEqual(errors, []);
    console.log('PASS browser: real component, cap/zero/gaps, tables, timezone, partial outage, denial clears, role omission, Urdu/RTL/320px/focus/no storage; all requests intercepted, no server.');
  } finally { await browser.close(); }
}
(async () => { if (!process.argv.includes('--browser-only')) { parserChecks(); await relayChecks(); } if (!process.argv.includes('--contract-only')) await browserChecks(); })().catch(error => { console.error(error); process.exitCode = 1; });
