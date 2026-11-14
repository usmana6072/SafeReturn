import {test,expect,type Page} from '@playwright/test';import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';import ts from 'typescript';
import {INITIAL_SEED_DATA,type MockUser} from '../lib/admin-mock-data';
import {canReadDemoUsers,demoUserQRCount,filterDemoUsers} from '../lib/admin-user-list';import {uuid} from '../lib/users-contract';
const bundle=require('./qa-browser-bundle.cjs');const options={componentPath:'../components/admin-users.tsx',exportName:'AdminUsers',cssClass:'users-screen'};
async function open(page:Page,role='security_admin',users?:unknown[],preview='authenticated'){
 const css=fs.readdirSync('.next/static/chunks').filter(f=>f.endsWith('.css')).map(f=>fs.readFileSync(path.join('.next/static/chunks',f),'utf8')).join('\n')+fs.readFileSync('components/admin-users.module.css','utf8').replaceAll('.screen','.users-screen');
 await page.route('http://users-demo.test/**',route=>{const pathname=new URL(route.request().url()).pathname;const userId=pathname.startsWith('/admin/users/')?decodeURIComponent(pathname.slice('/admin/users/'.length)):undefined;
 return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body><main class="p-4 max-w-7xl mx-auto"><div id="root"></div></main><script>window.qaRole={authenticatedRoles:['+JSON.stringify(role)+'],selectedRole:'+JSON.stringify(preview)+',effectiveRole:'+JSON.stringify(role)+'};window.qaProps='+JSON.stringify({userId})+';'+bundle(options)+'</script></body></html>'});});
 if(users)await page.addInitScript(({users})=>{if(!sessionStorage.getItem('seeded')){localStorage.setItem('safereturn_demo_db',JSON.stringify({users}));sessionStorage.setItem('seeded','1');}},{users});
 await page.goto('http://users-demo.test/admin/users');
}

test('user filtering and legacy profile semantics preserve shared fixture values',()=>{
 const users=INITIAL_SEED_DATA.users;const before=JSON.stringify(users);
 expect(filterDemoUsers(users,'AMINA','Active','Customer').map(u=>u.id)).toEqual(['USR-8821']);
 expect(filterDemoUsers(users,'TARIQ.M@','Suspended','Customer')).toHaveLength(1);
 expect(filterDemoUsers(users,'USR-9001','Active','Operations Staff')).toHaveLength(1);
 expect(filterDemoUsers(users,'Sarah','Suspended','all')).toHaveLength(0);
 expect(demoUserQRCount(2)).toBe('2 paired profiles');expect(demoUserQRCount(0)).toBe('0 paired profiles');expect(demoUserQRCount(undefined)).toBe('Not available');expect(demoUserQRCount(-1)).toBe('Not available');
 expect(JSON.stringify(users)).toBe(before);
 for(const role of ['support','security_admin','superadmin'])expect(canReadDemoUsers([role])).toBe(true);
 for(const role of ['operations','finance'])expect(canReadDemoUsers([role])).toBe(false);
 expect(filterDemoUsers([{id:'missing'} as MockUser],'missing','all','all')).toHaveLength(1);
});

test('browser name/email/ID search, combined filters, focus, clear, navigation and read-only refresh',async({page})=>{
 await open(page);await expect(page.locator('tbody tr')).toHaveCount(4);const requests:string[]=[];page.on('request',r=>requests.push(r.url()));
 const search=page.getByRole('textbox',{name:'Search users',exact:true});
 await search.fill('aMiNa');await expect(search).toBeFocused();await expect(page.locator('tbody tr')).toHaveCount(1);await expect(page.locator('tbody')).toContainText('MFA Enrolled');await expect(page.locator('tbody')).toContainText('2 paired profiles');
 await search.fill('tariq.m@');await page.getByRole('combobox',{name:'Account Status',exact:true}).selectOption('Suspended');await page.getByRole('combobox',{name:'Account Type',exact:true}).selectOption('Customer');await expect(page.locator('tbody tr')).toHaveCount(1);await expect(page.locator('tbody')).toContainText('None');
 await page.getByRole('combobox',{name:'Account Type',exact:true}).selectOption('Operations Staff');await expect(page.getByText('No matching accounts',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Clear Filters'}).click();await search.fill('usr-9001');await expect(page.locator('tbody tr')).toHaveCount(1);await expect(page.locator('tbody')).toContainText('Operations Staff');expect(requests).toEqual([]);
 await page.getByRole('link',{name:'View Details for USR-9001'}).click();await expect(page.getByRole('heading',{name:'Sarah Jenkins',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Suspend Account',exact:true})).toBeDisabled();
 await page.reload();await expect(page.getByRole('heading',{name:'Sarah Jenkins',exact:true})).toBeVisible();expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
 await page.getByRole('link',{name:'Back to Users'}).first().click();await expect(page.locator('tbody tr')).toHaveCount(4);
 await page.goto('http://users-demo.test/admin/users/unknown');await expect(page.getByText('User not found',{exact:true})).toBeVisible();
});

for(const width of [1366,1440,375])test('users responsive '+width,async({page})=>{
 await page.setViewportSize({width,height:width===1440?900:768});await open(page);await expect(page.locator('tbody tr')).toHaveCount(4);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const search=page.getByRole('textbox',{name:'Search users',exact:true});await search.focus();await page.keyboard.press('Tab');await expect(page.getByRole('combobox',{name:'Account Status',exact:true})).toBeFocused();
 await page.screenshot({path:'test-results/users-'+width+'.png',fullPage:true});
 await expect(page.getByRole('button',{name:/Suspend|Restore|Recovery|Reset|Add User/})).toHaveCount(0);
});

test('missing optional values, invalid records, unknown statuses and unknown enrollment remain safe',async({page})=>{
 await open(page,'support',[{id:'USR-INCOMPLETE',role:'Customer',status:'Unrecognized'},null]);
 await expect(page.getByRole('alert')).toContainText('Some demo account records are invalid');
 await expect(page.locator('tbody')).toContainText('Not available');await expect(page.locator('tbody')).toContainText('Unknown');await expect(page.locator('tbody')).toContainText('Unrecognized');await expect(page.getByRole('link',{name:'View Details for USR-INCOMPLETE'})).toBeVisible();
});

test('preview cannot grant directory access to Operations or Finance',async({page})=>{
 await open(page,'operations',undefined,'Superadmin');await expect(page.getByText('Access denied',{exact:true})).toBeVisible();await expect(page.locator('table')).toHaveCount(0);
});

test('empty data, storage errors and reactive future account changes do not mutate on view',async({page})=>{
 await open(page,'superadmin',[]);await expect(page.getByText('No demo accounts',{exact:true})).toBeVisible();
 await page.evaluate((users)=>{localStorage.setItem('safereturn_demo_db',JSON.stringify({users}));window.dispatchEvent(new Event('storage'));},INITIAL_SEED_DATA.users);
 await expect(page.locator('tbody tr')).toHaveCount(4);const before=await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'));
 await page.getByRole('textbox',{name:'Search users',exact:true}).fill('sarah');expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBe(before);
 await page.reload();await expect(page.locator('tbody tr')).toHaveCount(4);
 await page.addInitScript(()=>{Storage.prototype.getItem=()=>{throw Error('blocked');};});await page.reload();await expect(page.getByRole('alert')).toContainText('Browser demo data could not be read');await expect(page.locator('tbody tr')).toHaveCount(4);
});

test('Users routes keep users.manage/MFA wrapper and security-only real account directory',async()=>{
 const AdminPage=()=>null,AdminNotice=()=>null,AdminUsers=()=>null,UserDirectory=()=>null;
 function load(file:string){const result={exports:{} as any};const source=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
 vm.runInNewContext(source,{exports:result.exports,require:(name:string)=>{if(name==='react/jsx-runtime')return require(name);if(name==='next/link')return ()=>null;if(name.includes('admin-page'))return {AdminPage,AdminNotice};if(name.includes('admin-users'))return {AdminUsers};if(name.includes('user-directory'))return {UserDirectory};if(name.includes('admin-user-list'))return {canReadDemoUsers};if(name.includes('users-contract'))return {uuid};throw Error(name);}});return result.exports.default;}
 const list=load('app/admin/users/page.tsx');for(const role of ['support','security_admin','superadmin','operations','finance']){const page=await list({searchParams:Promise.resolve({})});expect(page.type).toBe(AdminPage);expect(page.props.capability).toBe('users.manage');expect(page.props.children({roles:[role]},false).type).toBe(['support','security_admin','superadmin'].includes(role)?AdminUsers:AdminNotice);}
 const live=await list({searchParams:Promise.resolve({view:'live'})});expect(live.props.children({roles:['superadmin']},false).type).toBe(AdminNotice);expect(live.props.children({roles:['security_admin']},false).props.children[1].type).toBe(UserDirectory);
 const detail=load('app/admin/users/[userId]/page.tsx');const demo=await detail({params:Promise.resolve({userId:'USR-8821'})});expect(demo.props.children({roles:['support']},false).type).toBe(AdminUsers);const real=await detail({params:Promise.resolve({userId:'00000000-0000-0000-0000-000000000001'})});expect(real.props.children({roles:['support'],capabilities:[]},false).type).toBe(AdminNotice);expect(real.props.children({roles:['security_admin'],capabilities:[]},false).type).toBe(UserDirectory);
});
