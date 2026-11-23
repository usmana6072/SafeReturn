// Production Next page against isolated public catalog fixtures; no live writes.
const {chromium,expect}=require('@playwright/test'),{spawn}=require('node:child_process'),http=require('node:http'),assert=require('node:assert/strict');
const {setTimeout:delay}=require('node:timers/promises');
const base='http://127.0.0.1:3487',id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const products=[1,2,3,4].map((n)=>({product_id:id(n),slug:'fixture-tag-'+n,name:['Everyday Lost QR Sticker','Emergency Information Tag','Travel QR Sticker','Everyday QR Copies'][n-1],description:'An editable QR profile for the things that matter. Choose your copies and manage the details you share.',commerce_model:n===4?'legacy_pair':'single_qr',qr_type:n===2?'ice':'lost',checkout_available:n!==3,checkout_unavailable_reasons:n===3?['SINGLE_QR_CHECKOUT_NOT_RELEASED']:[],featured:true,catalog_version:1,price_per_copy:n===1?'150.25':n===2?'275.00':'199.99',max_order_copies:100,category:{id:id(20),slug:'qr-stickers',name:'QR Stickers'},images:[],variants:[{variant_id:id(n+30),sku:'HOME-'+n,name:'35 mm',currency_code:'PKR',unit_price_pkr:n===1?'150.25':n===2?'275.00':'199.99'},{variant_id:id(n+40),sku:'HOME-LARGE-'+n,name:'45 mm',currency_code:'PKR',unit_price_pkr:n===4?'129.05':n===1?'150.25':n===2?'275.00':'199.99'}]}));
let mode='empty',calls=[];
const server=http.createServer((req,res)=>{
 const p=new URL(req.url,'http://localhost').pathname;calls.push(p);
 const send=(v,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(v));};
 if(p==='/api/v1/public/catalog/featured'){
  if(mode==='error')return send({},503);
  return send({items:mode==='empty'||mode==='fallback'?[]:mode==='malformed'?[{...products[0],price_per_copy:'bad'}]:mode==='single'?[products[0]]:products});
 }
 if(p==='/api/v1/public/products')return send(mode==='empty'?[]:products);
 if(p.startsWith('/api/v1/public/products/')){const product=products.find(item=>item.variants.some(v=>p.endsWith(v.sku)));return product?send(product):send({},404);}
 return send({},404);
});
async function suite(){
 const child=spawn(process.execPath,['node_modules/@playwright/test/cli.js','test','tests/home.spec.ts','--config','playwright.config.ts','--workers=1'],{windowsHide:true,stdio:'inherit',env:{...process.env,PLAYWRIGHT_EXTERNAL_SERVER:'1',PLAYWRIGHT_BASE_URL:base}});
 await new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',code=>code===0?resolve():reject(Error('Homepage regression checks failed')));});
}
(async()=>{let child,browser;
 try{
 await new Promise((resolve,reject)=>server.once('error',reject).listen(8115,'127.0.0.1',resolve));
 child=spawn(process.execPath,['node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3487'],{windowsHide:true,stdio:['ignore','inherit','inherit'],env:{...process.env,SAFERETURN_API_ORIGIN:'http://127.0.0.1:8115',SAFERETURN_WEB_ORIGIN:base,NEXT_TELEMETRY_DISABLED:'1'}});
 for(let i=0;i<60;i++){try{if((await fetch(base)).ok)break;}catch{}await delay(250);}
 await suite();mode='populated';browser=await chromium.launch();
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'}),page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(String(e)));page.setDefaultTimeout(10000);
 const snap=name=>page.screenshot({path:'test-results/premium-home-'+name+'.png',fullPage:true});
 for(const lang of ['en','ur']){
  await context.addCookies([{name:'safereturn-language',value:lang,url:base}]);calls=[];await page.goto(base);await expect(page.locator('.home-product')).toHaveCount(4);await page.waitForLoadState('networkidle');
  assert.equal(calls.filter(p=>p==='/api/v1/public/catalog/featured').length,1);assert.equal(calls.filter(p=>p==='/api/v1/public/products').length,0);
  for(const width of [320,360,375,390,412,430,768,1024,1440]){
   await page.setViewportSize({width,height:900});await page.evaluate(()=>scrollTo(0,0));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'overflow '+lang+width);
   if([320,390,768,1440].includes(width))await snap(lang+'-'+width);
   const regions=await page.locator('.home-page a[href]').evaluateAll(links=>links.filter(link=>link.getAttribute('href').startsWith('#')).map(link=>link.getAttribute('href')));
   for(const target of regions)assert(await page.locator(target).count(),'missing anchor '+target);
  }
  await page.setViewportSize({width:390,height:844});await page.locator('.mobile-menu summary').click();await expect(page.locator('.mobile-menu nav')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('.mobile-menu nav')).not.toBeVisible();await expect(page.locator('.mobile-menu summary')).toBeFocused();
  await page.locator('.mobile-menu summary').click();await page.locator('.mobile-menu a[href="#stickers"]').click();await expect(page.locator('.mobile-menu nav')).not.toBeVisible();
  const next=page.getByRole('button',{name:lang==='en'?'Next products':'اگلی مصنوعات',exact:true});await expect(next).toBeEnabled();const before=await page.locator('.featured-scroll').evaluate(el=>Math.abs(el.scrollLeft));await next.click();await expect.poll(()=>page.locator('.featured-scroll').evaluate(el=>Math.abs(el.scrollLeft))).toBeGreaterThan(before);
 }
 await context.addCookies([{name:'safereturn-language',value:'en',url:base}]);await page.goto(base);await expect(page.locator('.home-product').first()).toContainText('PKR 150.25');
 const legacy=page.locator('.home-product').nth(3);await expect(legacy.locator('.home-product-price')).toContainText('PKR 129.05');await expect(legacy.locator('.home-product-price')).toContainText('45 mm');
 await legacy.locator('summary').click();await expect(legacy.locator('ul')).toContainText('PKR 199.99');await expect(legacy.locator('ul')).toContainText('PKR 129.05');
 await expect(page.locator('.home-product').nth(2).getByRole('button',{name:'Order now'})).toBeDisabled();await expect(page.locator('.home-product').nth(2)).toContainText('Online purchasing has not been enabled yet.');
 await page.locator('.home-product').first().getByRole('link',{name:'View details',exact:true}).click();await expect(page).toHaveURL(base+'/shop/HOME-1');await expect(page.locator('h1')).toHaveText(products[0].name);
 await page.goto(base);await page.locator('.home-product').first().getByRole('link',{name:'Order now',exact:true}).click();await expect(page).toHaveURL(base+'/shop/HOME-1#order');
 mode='fallback';calls=[];await page.goto(base);await expect(page.locator('.home-product')).toHaveCount(4);assert.equal(calls.filter(p=>p==='/api/v1/public/products').length,1);
 mode='single';await page.reload();await expect(page.locator('.home-product')).toHaveCount(1);await expect(page.getByRole('button',{name:'Next products'})).toHaveCount(0);await snap('single');
 mode='empty';await page.reload();await expect(page.locator('.empty-state')).toContainText('No QR stickers are available');await snap('empty');
 mode='error';calls=[];await page.reload();await expect(page.locator('.empty-state')).toContainText('Products could not be loaded');assert.equal(calls.filter(p=>p==='/api/v1/public/products').length,0);await snap('error');
 mode='malformed';await page.reload();await expect(page.locator('.home-product')).toHaveCount(0);await expect(page.locator('.empty-state')).toContainText('Products could not be loaded');
 mode='populated';await page.reload();await page.setViewportSize({width:320,height:900});await page.evaluate(()=>document.documentElement.style.fontSize='200%');const overflow=await page.evaluate(()=>[...document.querySelectorAll('.home-page *')].filter(el=>{const box=el.getBoundingClientRect();return box.right>innerWidth+1&&getComputedStyle(el).position!=='absolute'&&!el.closest('.featured-scroll')&&!el.closest('.home-visual-stage');}).slice(0,12).map(el=>({tag:el.tagName,className:el.className,width:el.getBoundingClientRect().width,right:el.getBoundingClientRect().right})));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'200% text overflow '+JSON.stringify(overflow));
 assert.deepEqual(errors,[]);console.log('PASS premium homepage: existing homepage regression suite, 18 EN/Urdu populated layouts, exact prices and legacy variant amounts, disabled checkout state, details/order routes, featured fallback, empty/error/malformed/one-product states, menu Escape/anchor behavior, RTL carousel, no duplicate catalog reads and 200% text.');
 }finally{await browser?.close();child?.kill();server.close();server.closeAllConnections();}
})().catch(error=>{console.error(error);process.exitCode=1;});

