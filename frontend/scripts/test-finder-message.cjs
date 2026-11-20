const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict'), ts = require('typescript');
class ApiError extends Error { constructor(kind, status) { super(kind); this.status = status; } }
let failure, receipt = { status: 'accepted' }, calls = [];
const box = { exports: {}, require: name => name.endsWith('/qr-server') ? {
  ownerApi: () => async (...args) => { calls.push(args); if (failure) throw failure; return receipt; }
} : { ApiError } };
vm.runInNewContext(ts.transpileModule(fs.readFileSync('app/q/[token]/finder-message.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
}).outputText, box);
async function main() {
  const data = new FormData();
  data.set('message', 'I found your bag near the station.');
  data.set('contact_consent_accepted', 'on'); data.set('idempotency_key', 'stable-retry-key-001');
  const send = async () => JSON.parse(await box.exports.submitFinderMessage('public-token', '', data)).status;
  assert.equal(await send(), 'invalid_contact'); assert.equal(calls.length, 0);
  data.set('finder_email', ' finder@example.test ');
  assert.equal(await send(), 'accepted'); assert.equal(calls[0][2].finder_email, 'finder@example.test');
  assert.equal(calls[0][4], 'stable-retry-key-001');
  failure = new ApiError('http', 422); assert.equal(await send(), 'invalid_contact');
  for (const error of [new ApiError('http', 503), new ApiError('http', 429), new Error('timeout')]) {
    failure = error; assert.equal(await send(), 'unavailable');
  }
  failure = null; receipt = { status: 'unexpected' }; assert.equal(await send(), 'unavailable');
  console.log('PASS finder action: confirmed saves only, validation, failures and stable retries');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
