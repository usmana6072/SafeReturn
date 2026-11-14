/* Synthetic actual component+relay checks. No server, network, account or provider. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const ts=require('typescript'),{NextRequest}=require('next/server'),{chromium}=require('@playwright/test');
const origin='https://synthetic.test',oid='00000000-0000-4000-8000-000000000001';
const out=path.resolve(__dirname,'../../output/task53a/browser');fs.mkdirSync(out,{recursive:true});

async function relayChecks(){
 let session=null,calls=[],status=202;
 const source=fs.readFileSync(path.join(__dirname,'../app/orders/cancellation-api/route.ts'),'utf8');
 const sandbox={exports:{},AbortSignal,process:{env:{SAFERETURN_API_ORIGIN:'https://synthetic-api.test'}},fetch:async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify(status>=400?{error:{message:'PRIVATE_BACKEND_CANARY'}}:{request_status:'requested'}),{status,headers:{'Content-Type':'application/json'}});},require:name=>{
  if(name==='next/server')return require(name);
  if(name.endsWith('/auth/server'))return{verifiedSession:async()=>session};
  if(name.endsWith('/auth/config'))return{authConfig:()=>({origin})};
  if(name.endsWith('/api/transport'))return{validateOrigin:value=>{assert.equal(value,'https://synthetic-api.test');return value;}};
  throw Error('Unexpected dependency');
 }};
 vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,sandbox);
 const request=(data,where=origin)=>new NextRequest(origin+'/orders/cancellation-api',{method:'POST',headers:{Origin:where,'Content-Type':'application/json'},body:JSON.stringify(data)});
 const data={order_id:oid,key:'synthetic-cancellation-key',body:{expected_revision:1,reason_code:'other',confirmed:true}};
 let r=await sandbox.exports.POST(request(data));assert.equal(r.status,401);assert.equal(r.headers.get('Cache-Control'),'private, no-store');
 session={token:'synthetic-token'};
 r=await sandbox.exports.POST(request(data,'https://foreign.test'));assert.equal(r.status,403);
 r=await sandbox.exports.POST(request({...data,order_id:'../admin'}));assert.equal(r.status,400);assert.equal(calls.length,0);
 r=await sandbox.exports.POST(request(data));assert.equal(r.status,202);assert.equal(calls[0].url,`https://synthetic-api.test/api/v1/me/orders/${oid}/cancel`);assert.equal(calls[0].options.headers.Origin,origin);assert.equal(calls[0].options.cache,'no-store');assert.equal(calls[0].options.redirect,'error');
 status=409;r=await sandbox.exports.POST(request(data));assert.equal(r.status,409);assert.equal((await r.text()).includes('PRIVATE_BACKEND_CANARY'),false);
 sandbox.fetch=async()=>{throw Error('PRIVATE_NETWORK_CANARY');};r=await sandbox.exports.POST(request(data));assert.equal(r.status,503);assert.equal((await r.text()).includes('PRIVATE_NETWORK_CANARY'),false);
 console.log('PASS relay: anonymous, CSRF, fixed target, private headers, safe errors, idempotency forwarding.');
}

async function browserChecks(){
 const modules=path.resolve(__dirname,'../node_modules'),component=path.resolve(__dirname,'../components/cancellation-request').replaceAll('\\','/');
 fs.writeFileSync(path.join(out,'loader.cjs'),`const ts=require(${JSON.stringify(path.join(modules,'typescript'))});module.exports=source=>ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2017,module:ts.ModuleKind.ESNext}}).outputText;`);
 fs.writeFileSync(path.join(out,'entry.tsx'),`import React from 'react';import {createRoot} from 'react-dom/client';import {CancellationRequest} from '${component}';const root=createRoot(document.getElementById('root'));window.show=(ur=false,revision=3,summary=null)=>root.render(<CancellationRequest key={String(ur)+revision+JSON.stringify(summary)} orderId='${oid}' ur={ur} revision={revision} summary={summary}/>);`);
 const webpack=require('next/dist/compiled/webpack/webpack').webpack;
 await new Promise((resolve,reject)=>webpack({mode:'development',devtool:false,entry:path.join(out,'entry.tsx'),output:{path:out,filename:'bundle.js'},resolve:{extensions:['.tsx','.ts','.js'],modules:[modules]},module:{rules:[{test:/\.tsx?$/,use:path.join(out,'loader.cjs')}]}},(error,stats)=>error||stats.hasErrors()?reject(error||Error(stats.toString({all:false,errors:true}))):resolve()));
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[],sent=[];let mode='down';
  page.on('pageerror',error=>errors.push(error.message));
  await page.route(origin+'/**',async route=>{
   if(new URL(route.request().url()).pathname==='/orders/cancellation-api'){
    sent.push(route.request().postDataJSON());
    return route.fulfill({status:mode==='down'?503:202,json:mode==='down'?{error:{message:'PRIVATE_ERROR_CANARY'}}:{request_id:'synthetic-request',request_status:'requested',next_action:'await_review',revision:3}});
   }
   return route.fulfill({contentType:'text/html',body:'<!doctype html><html><body><main id="root" class="container section"></main></body></html>'});
  });
  await page.goto(origin);const css=path.resolve(__dirname,'../../tmp/task52a-web/.next/static/css');
  for(const file of fs.readdirSync(css)){if(file.endsWith('.css'))await page.addStyleTag({content:fs.readFileSync(path.join(css,file),'utf8')});}
  await page.addScriptTag({path:path.join(out,'bundle.js')});await page.evaluate(()=>window.show());
  const confirmation=page.getByLabel('I confirm this cancellation request for review.',{exact:true});
  await confirmation.waitFor();assert.equal(await page.getByRole('button',{name:'Request review',exact:true}).isDisabled(),true);
  await confirmation.check();await page.getByRole('button',{name:'Request review',exact:true}).click();await page.getByText('Request not confirmed.',{exact:false}).waitFor();
  assert.equal((await page.locator('body').innerText()).includes('PRIVATE_ERROR_CANARY'),false);
  mode='ok';await page.getByRole('button',{name:'Request review',exact:true}).click();await page.getByText('Request saved for review.',{exact:true}).waitFor();
  assert.equal(sent[0].key,sent[1].key);assert.equal(sent[1].body.expected_revision,3);assert.equal(sent[1].body.confirmed,true);assert.equal(await page.getByRole('button',{name:'Request review',exact:true}).count(),0);
  assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  await page.evaluate(()=>{document.documentElement.dir='rtl';document.documentElement.lang='ur';window.show(true);});
  await page.getByRole('heading',{name:'منسوخی کی درخواست',exact:true}).waitFor();
  await page.getByRole('combobox').focus();assert.equal(await page.getByRole('combobox').evaluate(el=>el===document.activeElement),true);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:path.join(out,'cancellation-ur-mobile.png'),fullPage:true});
  await page.evaluate(()=>window.show(false,0));await page.getByText('Cancellation review is currently unavailable.',{exact:true}).waitFor();
  assert.deepEqual(errors,[]);console.log('PASS browser: review-only form, confirmation, same-key retry, safe failures/status, no storage, disabled gate, RTL/mobile/keyboard.');
 }finally{await browser.close();}
}
(async()=>{await relayChecks();await browserChecks();})().catch(error=>{console.error(error);process.exitCode=1;});
