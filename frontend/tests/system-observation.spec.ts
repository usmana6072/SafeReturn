import { test, expect } from '@playwright/test';
import { observeLiveness } from '../lib/api/system-observation';
test('liveness observation is minimal and never sends credentials', async () => {
  let path = '';
  const result = await observeLiveness('https://synthetic.invalid', async (input, init) => {
    path = String(input); expect(init?.headers).toEqual({ Accept: 'application/json' }); expect(init?.redirect).toBe('error');
    return new Response('{"status":"ok"}', { headers: { 'Content-Type': 'application/json' } });
  });
  expect(path).toBe('https://synthetic.invalid/api/v1/health/live'); expect(result.state).toBe('responded');
  expect(Object.keys(result).sort()).toEqual(['checked_at', 'state']);
});
test('unconfigured origin is distinct without exposing its value', async () => {
  const value = await observeLiveness('PRIVATE_CANARY', async () => { throw new Error('must not fetch'); });
  expect(value.state).toBe('unconfigured'); expect(JSON.stringify(value)).not.toContain('CANARY');
});
test('unexpected or private payload remains unknown', async () => {
  const value = await observeLiveness('https://synthetic.invalid', async () => new Response('{"status":"ok","key":"PRIVATE_CANARY"}', { headers: { 'Content-Type': 'application/json' } }));
  expect(value.state).toBe('unknown'); expect(JSON.stringify(value)).not.toContain('CANARY');
});
test('provider-shaped error and network failure expose no private text', async () => {
  for (const status of [401, 503]) expect((await observeLiveness('https://synthetic.invalid', async () => new Response('PRIVATE_CANARY', { status }))).state).toBe('unavailable');
  const value = await observeLiveness('https://synthetic.invalid', async () => { throw new Error('PRIVATE_CANARY'); });
  expect(value.state).toBe('unavailable'); expect(JSON.stringify(value)).not.toContain('CANARY');
});
