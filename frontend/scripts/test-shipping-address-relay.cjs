/* Real route module with synthetic session/fetch; no network or providers. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');
const { NextRequest } = require('next/server');
const origin = 'https://synthetic.test';
let session = { token: 'synthetic-token' }, calls = [], status = 200;
const code = ts.transpileModule(fs.readFileSync(path.join(__dirname,'../app/account/shipping-addresses/api/route.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const sandbox = { exports:{}, AbortSignal, process:{env:{SAFERETURN_API_ORIGIN:'https://synthetic-api.test'}}, fetch: async (url, options) => { calls.push({url,options}); return new Response(status===204?null:JSON.stringify(status>=400?{error:{message:'PRIVATE_BACKEND_CANARY'}}:{book_version:0,items:[]}),{status,headers:{'Content-Type':'application/json'}}); }, require: name => {
  if(name==='next/server') return require(name);
  if(name.endsWith('/auth/server')) return {verifiedSession:async()=>session};
  if(name.endsWith('/auth/config')) return {authConfig:()=>({origin})};
  if(name.endsWith('/api/transport')) return {validateOrigin:value=>{assert.equal(value,'https://synthetic-api.test');return value;}};
  throw Error('Unexpected dependency');
} };
vm.runInNewContext(code,sandbox);
function request(method,data,requestOrigin=origin) { return new NextRequest(origin+'/account/shipping-addresses/api',{method,headers:{Origin:requestOrigin,'Content-Type':'application/json'},...(data===undefined?{}:{body:JSON.stringify(data)})}); }
async function main() {
  session=null;
  let r=await sandbox.exports.GET(request('GET'));
  assert.equal(r.status,401); assert.equal(r.headers.get('Cache-Control'),'private, no-store'); assert.equal(calls.length,0);
  session={token:'synthetic-token'};
  r=await sandbox.exports.POST(request('POST',{},'https://foreign.test'));
  assert.equal(r.status,403);assert.equal(calls.length,0);
  r=await sandbox.exports.PATCH(request('PATCH',{id:'../admin',body:{}}));assert.equal(r.status,400);assert.equal(calls.length,0);
  r=await sandbox.exports.DELETE(request('DELETE',{id:'00000000-0000-4000-8000-000000000001',expected_version:true,expected_book_version:0}));assert.equal(r.status,400);
  r=await sandbox.exports.GET(request('GET')); assert.equal(r.status,200);assert.equal(calls[0].options.cache,'no-store');assert.equal(calls[0].options.redirect,'error');assert.equal(calls[0].options.headers.Origin,origin);
  status=409;
  r=await sandbox.exports.POST(request('POST',{expected_book_version:0})); assert.equal(r.status,409);assert.equal((await r.text()).includes('PRIVATE_BACKEND_CANARY'),false);assert.equal(r.headers.get('Cache-Control'),'private, no-store');
  status=204;
  r=await sandbox.exports.DELETE(request('DELETE',{id:'00000000-0000-4000-8000-000000000001',expected_version:2,expected_book_version:3}));assert.equal(r.status,204);assert.equal(await r.text(),'');assert.equal(calls.at(-1).url,'https://synthetic-api.test/api/v1/me/shipping-addresses/00000000-0000-4000-8000-000000000001?expected_version=2&expected_book_version=3');
  sandbox.fetch=async()=>{throw Error('PRIVATE_NETWORK_CANARY');};
  r=await sandbox.exports.GET(request('GET')); assert.equal(r.status,503);assert.equal((await r.text()).includes('PRIVATE_NETWORK_CANARY'),false);
  console.log('PASS: relay anonymous/Origin/path/version denial, private headers, fixed target, safe backend/network errors, 204 handling; no network.');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
