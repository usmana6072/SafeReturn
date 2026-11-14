import {test,expect,type Page} from '@playwright/test';import fs from 'node:fs';import path from 'node:path';
import {INITIAL_SEED_DATA,loadAdminMockData,resetAdminMockData,recordDemoAccountGovernance} from '../lib/admin-mock-data';
const bundle=require('./qa-browser-bundle.cjs');const options={componentPath:'../components/admin-users.tsx',exportName:'AdminUsers',cssClass:'governance-screen'};
async function open(page:Page,role='security_admin',preview='authenticated'){
 const css=fs.readdirSync('.next/static/chunks').filter(f=>f.endsWith('.css')).map(f=>fs.readFileSync(path.join('.next/static/chunks',f),'utf8')).join('\n')+['admin-users','admin-user-details'].map(name=>fs.readFileSync('components/'+name+'.module.css','utf8').replaceAll('.screen','.governance-screen')).join('\n');
 await page.route('http://governance-demo.test/**',route=>{const pathname=new URL(route.request().url()).pathname;const userId=pathname.startsWith('/admin/users/')?decodeURIComponent(pathname.slice('/admin/users/'.length)):undefined;
 return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body><main class="p-4 max-w-7xl mx-auto"><div id="root"></div></main><script>window.qaRole={authenticatedRoles:['+JSON.stringify(role)+'],selectedRole:'+JSON.stringify(preview)+',effectiveRole:'+JSON.stringify(role)+'};window.qaProps='+JSON.stringify({userId})+';'+bundle(options)+'</script></body></html>'});});
 await page.goto('http://governance-demo.test/admin/users/USR-8821');
}
const input={userId:'USR-8821',action:'suspend' as const,reason:'Synthetic security scenario',caseReference:'DEMO-GOV-USR-8821',expectedRevision:1,expectedStatus:'Active',confirmed:true,authenticatedRoles:['security_admin'],previewRole:'authenticated'};

test('mock governance enforces role, fixture, reason, revision, confirmation and preserves unrelated state',()=>{
 resetAdminMockData();const before=loadAdminMockData();
 for(const role of ['support','superadmin','finance','operations'])expect(recordDemoAccountGovernance({...input,authenticatedRoles:[role]}).success).toBe(false);
 expect(recordDemoAccountGovernance({...input,previewRole:'Security Admin'}).success).toBe(false);
 for(const reason of ['', 'short','123456789', 'x'.repeat(501)])expect(recordDemoAccountGovernance({...input,reason}).success).toBe(false);
 expect(recordDemoAccountGovernance({...input,confirmed:false}).success).toBe(false);
 expect(recordDemoAccountGovernance({...input,expectedRevision:0}).success).toBe(false);
 expect(recordDemoAccountGovernance({...input,caseReference:'wrong'}).success).toBe(false);
 expect(recordDemoAccountGovernance({...input,userId:'USR-9001',caseReference:'DEMO-GOV-USR-9001'}).success).toBe(false);
 expect(recordDemoAccountGovernance({...input,action:'recover' as any}).success).toBe(false);
 expect(recordDemoAccountGovernance(input).success).toBe(true);expect(recordDemoAccountGovernance(input).success).toBe(false);
 let db=loadAdminMockData();const {governanceRevision,governanceHistory,status,...other}=db.users[0];const {status:old,...oldOther}=before.users[0];expect(other).toEqual(oldOther);expect(status).toBe('Suspended');expect(governanceHistory).toHaveLength(1);
 for(const key of ['orders','printJobs','shipments','products','qrBatches','qaPairs'] as const)expect(db[key]).toEqual(before[key]);
 expect(db.auditLogs[0].details).not.toContain(input.reason);
 expect(recordDemoAccountGovernance({...input,action:'restore',expectedRevision:2,expectedStatus:'Suspended'}).success).toBe(true);
 db=loadAdminMockData();expect(db.users[0].status).toBe('Active');expect(db.users[0].governanceHistory).toHaveLength(2);expect(db.users[0].governanceRevision).toBe(3);
 resetAdminMockData();expect(loadAdminMockData().users).toEqual(INITIAL_SEED_DATA.users);
});

test('details, cancellation, suspension/restoration, shared list, refresh and no network',async({page})=>{
 await open(page);await expect(page.getByRole('heading',{name:'Amina Khan',exact:true})).toBeVisible();await expect(page.getByText('No governance activity recorded in this demo.',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Escalate Recovery — unavailable'})).toBeDisabled();
 const requests:string[]=[];page.on('request',r=>requests.push(r.url()));
 await page.getByRole('button',{name:'Suspend Account',exact:true}).click();await page.getByRole('button',{name:'Cancel',exact:true}).click();expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();await expect(page.getByRole('button',{name:'Suspend Account',exact:true})).toBeFocused();
 await page.getByRole('button',{name:'Suspend Account',exact:true}).click();await page.getByRole('button',{name:'Confirm Demo Suspension'}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('textbox',{name:'Demo suspension reason'}).fill('Synthetic security scenario');await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Confirm Demo Suspension'}).click();
 await expect(page.getByText('Demo account marked as Suspended.',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Suspend Account',exact:true})).toBeDisabled();expect(requests).toEqual([]);
 await page.reload();await expect(page.getByText('Synthetic security scenario',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Restore Account',exact:true}).click();await page.getByRole('textbox',{name:'Demo restoration reason'}).fill('Synthetic restoration review');await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Confirm Demo Restoration'}).click();await expect(page.getByText('Demo account marked as Active.',{exact:true})).toBeVisible();
 const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('safereturn_demo_db')!));expect(stored.users[0].governanceHistory).toHaveLength(2);expect(stored.users[0].mfaEnrolled).toBe(true);expect(stored.users[0].qrCount).toBe(2);
 await page.getByRole('link',{name:'Back to Users'}).click();await expect(page.locator('tbody tr').filter({hasText:'USR-8821'})).toContainText('Active');await page.getByRole('link',{name:'View Details for USR-8821'}).click();await expect(page.getByText('Mock account restored',{exact:true})).toBeVisible();
});

for(const width of [1366,1440,375])test('user details responsive '+width,async({page})=>{
 await page.setViewportSize({width,height:width===1440?900:768});await open(page);await expect(page.getByRole('heading',{name:'Amina Khan',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'test-results/user-details-'+width+'.png',fullPage:true});
 await page.getByRole('button',{name:'Suspend Account',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();expect(await page.getByRole('dialog').evaluate(el=>el.getBoundingClientRect().width)).toBeLessThan(width);await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
});

for(const role of ['support','superadmin'])test(role+' details are read-only without governance inheritance',async({page})=>{
 await open(page,role);await expect(page.getByRole('heading',{name:'Amina Khan',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Suspend Account',exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'Escalate Recovery — unavailable'})).toBeDisabled();
});

test('preview, staff targets, missing IDs and failed storage stay safe',async({page})=>{
 await open(page,'security_admin','Superadmin');await expect(page.getByRole('button',{name:'Suspend Account',exact:true})).toBeDisabled();await page.goto('http://governance-demo.test/admin/users/USR-9001');await expect(page.getByRole('button',{name:'Suspend Account',exact:true})).toBeDisabled();await page.goto('http://governance-demo.test/admin/users/unknown');await expect(page.getByText('User not found',{exact:true})).toBeVisible();
 await page.unrouteAll();await open(page);await page.getByRole('button',{name:'Suspend Account',exact:true}).click();await page.getByRole('textbox',{name:'Demo suspension reason'}).fill('Synthetic failure scenario');await page.getByRole('checkbox').check();await page.evaluate(()=>{Storage.prototype.setItem=()=>{throw Error('quota');};});await page.getByRole('button',{name:'Confirm Demo Suspension'}).click();await expect(page.getByRole('alert')).toContainText('Unable to save demo account action');expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
});

test('stale governance submission cannot overwrite a newer revision',async({page})=>{
 await open(page);await page.getByRole('button',{name:'Suspend Account',exact:true}).click();await page.getByRole('textbox',{name:'Demo suspension reason'}).fill('Synthetic stale scenario');await page.getByRole('checkbox').check();
 await page.evaluate(seed=>{const users=seed.users.map(u=>u.id==='USR-8821'?{...u,governanceRevision:2}:u);localStorage.setItem('safereturn_demo_db',JSON.stringify({...seed,users}));window.dispatchEvent(new Event('storage'));},INITIAL_SEED_DATA);
 await page.getByRole('button',{name:'Confirm Demo Suspension'}).click();await expect(page.getByRole('alert')).toContainText('Account state changed');
});
