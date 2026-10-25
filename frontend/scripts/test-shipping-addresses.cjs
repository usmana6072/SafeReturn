/* Synthetic component browser checks. Requests are intercepted; no server or provider. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const webpack = require('next/dist/compiled/webpack/webpack').webpack;
const { chromium } = require('@playwright/test');
const out = path.resolve(__dirname, '../../output/task52a/browser');
fs.mkdirSync(out, { recursive: true });
const components = path.resolve(__dirname, '../components').replaceAll('\\', '/');
const modules = path.resolve(__dirname, '../node_modules');
fs.writeFileSync(path.join(out, 'loader.cjs'), `const ts=require(${JSON.stringify(path.join(modules,'typescript'))});module.exports=function(source){return ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2017,module:ts.ModuleKind.ESNext}}).outputText;};`);
fs.writeFileSync(path.join(out, 'entry.tsx'), `import React from 'react';import {createRoot} from 'react-dom/client';import {ShippingAddresses} from '${components}/shipping-addresses';import {CheckoutCart} from '${components}/checkout';const root=createRoot(document.getElementById('root'));window.show=(mode,ur=false)=>root.render(mode==='checkout'?<CheckoutCart language={ur?'ur':'en'} checkout products={[{product_id:'p',slug:'synthetic',name:'Synthetic product',description:null,featured:false,catalog_version:1,category:{id:'c',slug:'synthetic',name:'Synthetic'},images:[],variants:[{variant_id:'00000000-0000-4000-8000-000000000001',sku:'SYNTHETIC',name:'Synthetic variant',currency_code:'PKR',unit_price_pkr:'10.00'}]}]}/>:<ShippingAddresses ur={ur}/>);`);

async function main() {
  await new Promise((resolve, reject) => webpack({ mode: 'development', devtool: false, entry: path.join(out, 'entry.tsx'), output: { path: out, filename: 'bundle.js' }, resolve: { extensions: ['.tsx','.ts','.js'], modules: [modules] }, module: { rules: [{ test: /\.tsx?$/, use: path.join(out,'loader.cjs') }] } }, (error, stats) => error || stats.hasErrors() ? reject(error || Error(stats.toString({ all:false,errors:true }))) : resolve()));
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    let version = 0, items = [], fail = false;
    const writes = [], quotes = [];
    await page.route('https://synthetic.test/**', async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.pathname === '/account/shipping-addresses/api') {
        if (request.method() === 'GET') return route.fulfill({ json: { book_version: version, items } });
        const data = request.postDataJSON(); writes.push({ method: request.method(), data });
        if (fail) return route.fulfill({ status:409, json:{error:{code:'CONFLICT',message:'PRIVATE_ERROR_CANARY'}} });
        version++;
        if (request.method() === 'POST') items.push({ ...data, id: '00000000-0000-4000-8000-000000000002', version: 1 });
        if (request.method() === 'PATCH') items = items.map(a => a.id === data.id ? { ...a, ...data.body.address, is_default: data.body.is_default, version:a.version+1 } : a);
        if (request.method() === 'DELETE') { items = items.filter(a => a.id !== data.id); return route.fulfill({ status:204 }); }
        return route.fulfill({ status:request.method()==='POST'?201:200,json:{book_version:version,item:items[0]} });
      }
      if (url.pathname === '/checkout/api') { quotes.push(request.postDataJSON()); return route.fulfill({status:201,json:{quote_id:'00000000-0000-4000-8000-000000000003',expires_at:new Date(Date.now()+60000).toISOString(),subtotal_pkr:'10.00',shipping_pkr:'1.00',tax_pkr:'0.00',total_pkr:'11.00',currency_code:'PKR',new_pair_count:1}}); }
      return route.fulfill({ contentType:'text/html', body:'<!doctype html><html><body><main id="root" class="container section"></main></body></html>' });
    });
    await page.goto('https://synthetic.test/'); for (const file of fs.readdirSync(path.resolve(__dirname,'../../tmp/task52a-web/.next/static/css'))) { if(file.endsWith('.css')) await page.addStyleTag({content:fs.readFileSync(path.resolve(__dirname,'../../tmp/task52a-web/.next/static/css',file),'utf8')}); } await page.addScriptTag({ path:path.join(out,'bundle.js') });
    await page.evaluate(() => window.show('manager'));
    await page.getByLabel('Recipient name',{exact:true}).fill('Synthetic browser recipient');
    await page.getByLabel('Phone (+923…)',{exact:true}).fill('+923000000001');
    await page.getByLabel('Street address',{exact:true}).fill('Synthetic private browser street');
    await page.getByLabel('City',{exact:true}).fill('Synthetic city');
    await page.getByLabel('Default address',{exact:true}).check();
    await page.getByRole('button',{name:'Save address',exact:true}).click();
    await page.getByRole('button',{name:'Edit',exact:true}).waitFor();
    assert.equal(writes[0].data.expected_book_version,0);
    await page.getByRole('button',{name:'Edit',exact:true}).click();
    assert.equal(await page.getByLabel('Street address',{exact:true}).inputValue(),'Synthetic private browser street');
    await page.getByLabel('City',{exact:true}).fill('Edited synthetic city');
    await page.getByRole('button',{name:'Save address',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('[role=status]')?.textContent==='Changes saved.');
    assert.equal(writes[1].data.body.expected_version,1);
    // Stale or referenced writes are explicit, private errors and require a fresh list.
    await page.getByRole('button',{name:'Edit',exact:true}).click(); fail=true;
    await page.getByRole('button',{name:'Save address',exact:true}).click();
    await page.getByText('Change not confirmed.',{exact:false}).waitFor();
    assert.equal((await page.locator('body').innerText()).includes('PRIVATE_ERROR_CANARY'),false);
    fail=false; await page.getByRole('button',{name:'Reload list',exact:true}).click();
    await page.getByRole('button',{name:'Edit',exact:true}).waitFor();
    await page.evaluate(() => { localStorage.setItem('safereturn-cart-v1',JSON.stringify([{variant_id:'00000000-0000-4000-8000-000000000001',lost:1,ice:1}])); window.show('checkout'); });
    await page.getByRole('combobox', { name: /Choose shipping address/ }).waitFor();
    await page.waitForFunction(() => document.querySelector('select')?.value.endsWith('0002'));
    assert.equal(await page.getByLabel('Street address',{exact:true}).count(),0);
    await page.getByLabel('I confirm the shipping phone and address.',{exact:true}).check();
    await page.getByRole('button',{name:'Get final quote',exact:true}).click();
    await page.getByRole('region',{name:'Final quote',exact:true}).waitFor();
    assert.equal(quotes[0].body.shipping_address_version,2);
    assert.equal(quotes[0].body.shipping_address_id,items[0].id);
    assert.equal('address' in quotes[0].body,false);
    await page.getByRole('combobox', { name: /Choose shipping address/ }).selectOption('');
    assert.equal(await page.getByRole('region',{name:'Final quote',exact:true}).count(),0);
    assert.equal(await page.getByLabel('I confirm the shipping phone and address.',{exact:true}).isChecked(),false);
    assert.equal(await page.evaluate(() => JSON.stringify({local:{...localStorage},session:{...sessionStorage}}).includes('Synthetic')),false);
    await page.evaluate(() => { document.documentElement.dir='rtl'; document.documentElement.lang='ur'; window.show('manager',true); });
    await page.getByRole('heading',{name:'ترسیل کے محفوظ پتے',exact:true}).waitFor();
    await page.screenshot({path:path.join(out,'addresses-ur-mobile.png'),fullPage:true});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
    await page.evaluate(() => { document.documentElement.dir='ltr'; document.documentElement.lang='en'; window.show('manager',false); });
    await page.getByRole('button',{name:'Delete',exact:true}).waitFor();
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button',{name:'Delete',exact:true}).click();
    await page.getByText('No saved addresses.',{exact:true}).waitFor();
    assert.equal(writes.at(-1).data.expected_version,2);
    assert.deepEqual(errors,[]);
    console.log('PASS: synthetic manager CRUD/conflict; saved checkout DTO/default/reset; private storage; Urdu mobile. No server/provider/DB.');
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode=1; });
