import {test,expect,Page} from "@playwright/test";
const path=(kind:string)=>`/q/${process.env[`PUBLIC_QR_${kind.toUpperCase()}`]}`;
const phone="+923001234567",wa="923005555555";
async function widget(page:Page,mode="success") {
  await page.route("https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit",route=>route.fulfill({contentType:"application/javascript",body:`window.turnstile={render:(el,o)=>{el.textContent='Verification widget (test)';el.style.width=o.size==='compact'?'150px':'300px';el.style.height=o.size==='compact'?'140px':'65px';window.fixtureWidgetCount=(window.fixtureWidgetCount||0)+1;window.fixtureComplete=(mode)=>o.callback(mode==='success'?o.action+':'+o.cData+':'+crypto.randomUUID():mode);setTimeout(()=>o.callback(${JSON.stringify(mode)}==='success'?o.action+':'+o.cData+':'+crypto.randomUUID():${JSON.stringify(mode)}),20);return 'fixture-widget';},remove:()=>{}};`}));
}
async function verify(page:Page,kind="ice") {
  await page.getByRole('button',{name:kind==='ice'?'Reveal contact number':'Open WhatsApp',exact:true}).click();
  const submit=page.getByRole('button',{name:'Verify and continue',exact:true});
  await expect(submit).toBeEnabled();await submit.click();
}

test('phone is absent until deliberate verified action and disappears after reload',async({page,request})=>{
  await widget(page);
  let posts=0;
  page.on('request',r=>{if(r.method()==='POST')posts++;});
  await page.goto(path('ice'));
  for(const response of [await request.get(path('ice')),await request.get(path('ice'),{headers:{RSC:'1'}})])expect(await response.text()).not.toContain(phone);
  expect(await page.content()).not.toContain(phone);
  expect(posts).toBe(0);
  await verify(page);
  await expect(page.getByRole('link',{name:'Call now',exact:true})).toHaveAttribute('href','tel:'+phone);
  expect(await page.content()).not.toContain(wa);
  expect(posts).toBe(1);
  await page.screenshot({path:'test-results/protected-contact-en.png',fullPage:true});
  await page.reload();expect(await page.content()).not.toContain(phone);
});

test('WhatsApp requires warning, verification and separate external-link confirmation',async({page})=>{
  await widget(page);await page.goto(path('lost'));
  await expect(page.getByText(/Chats happen outside SafeReturn/)).toBeVisible();
  expect(await page.content()).not.toContain(wa);
  await verify(page,'lost');
  const link=page.getByRole('link',{name:'Continue in WhatsApp',exact:true});
  await expect(link).toHaveAttribute('href',`https://wa.me/${wa}?text=Hello%2C%20I%20found%20your%20item`);
  await expect(link).toHaveAttribute('rel','noopener noreferrer');
  await expect(page).toHaveURL(path('lost'));
});

test('invalid challenge does not reveal or hide emergency content',async({page})=>{
  await widget(page,'invalid');await page.goto(path('ice'));await verify(page);
  await expect(page.locator('.public-action').getByRole('alert')).toContainText('Verification failed or too many requests');
  await expect(page.getByRole('heading',{name:'Emergency information',exact:true})).toBeVisible();
  expect(await page.content()).not.toContain(phone);
});

test('challenge provider outage shows explicit unavailable with safe emergency content',async({page})=>{
  await widget(page,'outage');await page.goto(path('ice'));await verify(page);
  await expect(page.locator('.public-action').getByRole('alert')).toContainText('This contact is currently unavailable.');
  await expect(page.getByRole('heading',{name:'Emergency information',exact:true})).toBeVisible();
  expect(await page.content()).not.toContain(phone);
});

test('Urdu keyboard reveal keeps dial number LTR and fits narrow screen',async({page,context})=>{
  await context.addCookies([{name:'safereturn-language',value:'ur',domain:'127.0.0.1',path:'/'}]);
  await widget(page);await page.setViewportSize({width:320,height:740});await page.goto(path('ice'));
  const start=page.getByRole('button',{name:'نمبر دکھائیں',exact:true});
  await start.focus();await page.keyboard.press('Enter');
  const submit=page.getByRole('button',{name:'تصدیق کر کے جاری رکھیں',exact:true});
  await expect(submit).toBeEnabled();await submit.focus();await page.keyboard.press('Enter');
  await expect(page.getByRole('link',{name:'ابھی کال کریں',exact:true})).toHaveAttribute('href','tel:'+phone);
  await expect(page.locator('bdi').filter({hasText:phone})).toHaveAttribute('dir','ltr');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/protected-contact-ur-mobile.png',fullPage:true});
});

test('contact revoked after page load cannot be revealed',async({page,request})=>{
  await widget(page);await page.goto(path('ice'));
  await request.post('http://127.0.0.1:8115/fixture/contact-state/off');
  try {
    await verify(page);
    await expect(page.locator('.public-action').getByRole('alert')).toContainText('This contact is currently unavailable.');
    expect(await page.content()).not.toContain(phone);
  } finally {await request.post('http://127.0.0.1:8115/fixture/contact-state/on');}
});

test('WhatsApp disabled after page load cannot issue a saved link',async({page,request})=>{
  await widget(page);await page.goto(path('lost'));
  await request.post('http://127.0.0.1:8115/fixture/whatsapp-state/off');
  try {
    await verify(page,'lost');
    await expect(page.locator('.public-action').getByRole('alert')).toContainText('This contact is currently unavailable.');
    await expect(page.getByRole('link',{name:'Continue in WhatsApp'})).toHaveCount(0);
    expect(await page.content()).not.toContain(wa);
  } finally {await request.post('http://127.0.0.1:8115/fixture/whatsapp-state/on');}
});


test('repeated verification failure refreshes the widget and permits a fresh retry',async({page})=>{
  await widget(page,'invalid');await page.goto(path('lost'));await verify(page,'lost');
  await expect(page.locator('.public-action').getByRole('alert')).toContainText('Verification failed or too many requests');
  await expect.poll(()=>page.evaluate(()=>(window as unknown as {fixtureWidgetCount:number}).fixtureWidgetCount)).toBe(2);
  const submit=page.getByRole('button',{name:'Verify and continue',exact:true});
  await expect(submit).toBeEnabled();await submit.click();
  await expect.poll(()=>page.evaluate(()=>(window as unknown as {fixtureWidgetCount:number}).fixtureWidgetCount)).toBe(3);
  await page.evaluate(()=>(window as unknown as {fixtureComplete:(mode:string)=>void}).fixtureComplete('success'));
  await expect(submit).toBeEnabled();await submit.click();
  await expect(page.getByRole('link',{name:'Continue in WhatsApp',exact:true})).toBeVisible();
});
