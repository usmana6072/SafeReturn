// Isolated provider adapter tests: no browser, socket, environment file or Auth write.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');

function harness() {
  const state = {
    origin: 'http://localhost:3000', project: 'https://fhuxryfkfrvycsojkzvq.supabase.co',
    env: { NODE_ENV: 'development', SAFERETURN_SUPPORT_DEV_ONBOARDING: 'true', SAFERETURN_SUPPORT_DEV_SUBJECT_ID: 'synthetic-id' },
    user: { id: 'synthetic-id', email: 'usmana6072@gmail.com', email_confirmed_at: '2026-10-24T00:00:00Z', is_anonymous: false },
    factors: [], level: 'aal2', calls: [], fail: false,
  };
  const session = { get user() { return state.user; }, client: { auth: { mfa: {
    listFactors: async () => ({ error: state.fail, data: { all: state.factors } }),
    enroll: async () => { state.calls.push('enroll'); return { error: state.fail, data: { id: 'synthetic-factor', totp: { qr_code: 'data:image/svg+xml;utf-8,<svg/>', secret: 'NEVER_RETURN_RAW_SEED', uri: 'NEVER_RETURN_URI' } } }; },
    challengeAndVerify: async () => { state.calls.push('challengeAndVerify'); return { error: state.fail }; },
    getAuthenticatorAssuranceLevel: async () => ({ error: state.fail, data: { currentLevel: state.level } }),
  } } } };
  const cache = new Map();
  function load(file) {
    file = path.resolve(file);
    if (cache.has(file)) return cache.get(file).exports;
    const module = { exports: {} }; cache.set(file, module);
    const source = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
    const req = name => {
      if (name === 'server-only') return {};
      if (name === 'next/headers') return { headers: async () => ({ get: () => state.origin }) };
      if (name.endsWith('/config') || name === './config') return { authConfig: () => ({ origin: 'http://localhost:3000', url: state.project }) };
      if (name === './server') return { verifiedSession: async () => state.user ? session : null };
      if (name.startsWith('.')) return load(path.resolve(path.dirname(file), name + '.ts'));
      throw new Error('Unexpected dependency: ' + name);
    };
    vm.runInNewContext(`(function(require,module,exports,process,URL){${source}\n})`, {})(req, module, module.exports, { env: state.env }, URL);
    return module.exports;
  }
  return { state, auth: load(path.join(__dirname, '../lib/auth/support-onboarding.ts')), actions: load(path.join(__dirname, '../app/dev/support-onboarding/actions.ts')) };
}

(async () => {
  let checks = 0;
  const form = values => ({ get: key => values[key] ?? null });
  for (const change of [s => s.env.NODE_ENV = 'production', s => s.env.SAFERETURN_SUPPORT_DEV_ONBOARDING = 'false', s => s.project = 'https://other.supabase.co', s => s.user.email = 'other@synthetic.test', s => s.user.email_confirmed_at = null, s => s.env.SAFERETURN_SUPPORT_DEV_SUBJECT_ID = 'wrong']) {
    const h = harness(); change(h.state);
    await assert.rejects(h.auth.supportOnboardingSession()); checks++;
    assert.equal(h.state.calls.length, 0);
  }
  const h = harness();
  let result = await h.actions.onboardingAction({}, form({ mode: 'enroll' }));
  assert.equal(result.factor, 'synthetic-factor');
  assert.doesNotMatch(JSON.stringify(result), /NEVER_RETURN|secret|uri|token/i); checks++;
  h.state.factors = [{ id: 'synthetic-factor', factor_type: 'totp', status: 'verified' }];
  result = await h.actions.onboardingAction({}, form({ mode: 'enroll' }));
  assert.ok(result.error); assert.deepEqual(h.state.calls, ['enroll']); checks++;
  result = await h.actions.onboardingAction({}, form({ mode: 'verify', factor: 'wrong', code: '123456' }));
  assert.ok(result.error); assert.deepEqual(h.state.calls, ['enroll']); checks++;
  result = await h.actions.onboardingAction({}, form({ mode: 'verify', factor: 'synthetic-factor', code: '123456' }));
  assert.equal(result.verified, true); assert.equal(h.state.calls.at(-1), 'challengeAndVerify'); checks++;
  h.state.level = 'aal1';
  result = await h.actions.onboardingAction({}, form({ mode: 'verify', factor: 'synthetic-factor', code: '123456' }));
  assert.ok(result.error); assert.equal(result.verified, undefined); checks++;
  h.state.origin = 'https://attacker.test';
  const before = h.state.calls.length;
  result = await h.actions.onboardingAction({}, form({ mode: 'enroll' }));
  assert.ok(result.error); assert.equal(h.state.calls.length, before); checks++;
  console.log(`${checks} isolated development Support onboarding checks passed; no network, account or MFA mutation occurred.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
