import {test,expect as baseExpect} from '@playwright/test';
const expect=baseExpect.configure({timeout:20000});
test('bounded synthetic notification recovery, stale refusal, role denial and RTL',async({page,context,request})=>{
 test.setTimeout(240000);
 await page.goto('/admin/notifications');await expect(page).toHaveURL(/login/);
 expect((await page.request.get('/admin/notifications/api')).status()).toBe(401);
 async function login(role:string){await context.clearCookies();await request.post('http://127.0.0.1:8115/fixture/notification-role/'+role);await page.goto('/login');await page.getByLabel('Email address').fill(role+'@synthetic.invalid');await page.locator('input[name=password]').fill('synthetic-password');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/admin/);}
 await login('operations');await page.goto('/admin/notifications?view=live&status=dead');await expect(page.getByRole('status')).toBeEmpty();
 const target=process.env.NOTIFICATION_EVENT!;
 const card=page.locator('section').filter({has:page.getByRole('heading',{name:target,exact:true})});await card.getByRole('link',{name:'Open notification'}).click();
 await expect(page.getByRole('heading',{name:target,exact:true})).toBeVisible();await expect(page.getByRole('status')).toBeEmpty();
 await expect(page.locator('body')).not.toContainText('PRIVATE-FINDER');await expect(page.locator('body')).not.toContainText('original-owner');
 const checkbox=page.getByRole('checkbox');await expect(checkbox).not.toBeChecked();await checkbox.check();await page.getByRole('button',{name:'Queue reviewed retry'}).click();
 await expect(page.getByText('Retry queued. This receipt does not confirm email delivery.',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Queue reviewed retry'})).toHaveCount(0);
 // The worker stub is an isolated in-memory provider, never Resend.
 await request.post('http://127.0.0.1:8115/fixture/notification-deliver/'+target);await page.getByRole('button',{name:'Refresh notifications'}).click();await expect(page.getByRole('status')).toBeEmpty();await expect(page.locator('section')).toContainText('sent');
 await page.getByText('Template metadata',{exact:true}).click();await expect(page.locator('body')).toContainText('Historical template versions were not recorded');
 await request.post('http://127.0.0.1:8115/fixture/notification-stale');await page.goto('/admin/notifications/'+process.env.NOTIFICATION_STALE);await expect(page.getByRole('checkbox')).not.toBeChecked();
 await request.post('http://127.0.0.1:8115/fixture/notification-stale');await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Queue reviewed retry'}).click();await expect(page.getByRole('status')).toContainText('Retry refused');
 expect((await page.request.post('/admin/notifications/api',{headers:{Origin:'https://untrusted.invalid'},data:{}})).status()).toBe(403);
 expect((await page.request.get('/admin/notifications/api?path=/admin/payments')).status()).toBe(400);
 await login('finance');await page.goto('/admin/notifications/'+target);await expect(page.getByRole('heading',{name:'Access denied',exact:true})).toBeVisible();expect((await page.request.get('/admin/notifications/api?id='+target)).status()).toBe(403);
 const rsc=await page.request.get('/admin/notifications/'+target,{headers:{RSC:'1'}});expect(await rsc.text()).not.toContain('PRIVATE-FINDER');expect(await rsc.text()).toContain('Access denied');
 await login('security_admin');await context.addCookies([{name:'safereturn-language',value:'ur',url:'http://127.0.0.1:3100'}]);await page.setViewportSize({width:375,height:900});await page.goto('/admin/notifications/'+target);await expect(page.getByRole('heading',{name:target,exact:true})).toBeVisible();await expect(page.getByRole('status')).toBeEmpty();await expect(page.locator('html')).toHaveAttribute('dir','rtl');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(await page.evaluate(()=>[localStorage.length,sessionStorage.length])).toEqual([0,0]);await page.screenshot({path:'../output/task57h/loaded-rtl.png',fullPage:true});
});
