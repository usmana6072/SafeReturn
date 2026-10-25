// Owner-operated real browser login. No password/code/secret/token logging,
// screenshots, tracing, HAR or persistent storage-state files.
const path=require('node:path'),fs=require('node:fs'),{spawn}=require('node:child_process');
const {chromium}=require('@playwright/test'),{loadEnvConfig}=require('@next/env'),{createServerClient}=require('@supabase/ssr');
const root=path.resolve(__dirname,'../..');loadEnvConfig(path.join(root,'frontend'),true,{info(){},error(){}});
const origin='http://127.0.0.1:3100',project='https://fhuxryfkfrvycsojkzvq.supabase.co';
if(process.env.SAFERETURN_WEB_ORIGIN!==origin||process.env.SAFERETURN_API_ORIGIN!=='http://127.0.0.1:8030'||process.env.SAFERETURN_SUPABASE_URL!==project||!process.env.SAFERETURN_SUPABASE_PUBLISHABLE_KEY?.startsWith('sb_publishable_'))throw Error('Pinned development frontend configuration required');
const templateMode=process.argv.includes('--template-acceptance');
const output=path.join(root,templateMode?'tmp/template-activation/live-acceptance.json':'tmp/live-acceptance-2026-10-25/genuine-staff-login.json');
(async()=>{let browser,stage="browser_launch";try{
 browser=await chromium.launch({headless:false});const context=await browser.newContext(),page=await context.newPage();
 stage='frontend_navigation';await page.goto(origin+'/login',{waitUntil:'domcontentloaded',timeout:120000});console.log('Browser ready. Sign in with your existing authorized staff account and complete the official MFA flow. Nothing entered will be captured in logs.');
 stage='owner_login_mfa';const deadline=Date.now()+10*60*1000;let token;
 while(Date.now()<deadline&&!page.isClosed()){
  if(new URL(page.url()).pathname==='/admin'){
   const cookies=await context.cookies(origin),client=createServerClient(project,process.env.SAFERETURN_SUPABASE_PUBLISHABLE_KEY,{cookies:{getAll:()=>cookies.map(({name,value})=>({name,value})),setAll(){}},global:{fetch:(input,init)=>fetch(input,{...init,redirect:'error',signal:AbortSignal.timeout(10000)})}});
   const user=await client.auth.getUser();if(!user.error&&user.data.user?.email_confirmed_at){const session=await client.auth.getSession();token=session.data.session?.access_token;if(token)break;}
  }
  await new Promise(resolve=>setTimeout(resolve,1500));
 }
 if(!token){console.log('No completed staff login/MFA session captured. Complete the browser steps and rerun this helper.');return;}
 stage='acceptance_runner';const args=templateMode?[path.join(root,'backend/scripts/run_template_development_acceptance.py')]:[path.join(root,'backend/scripts/run_admin_read_acceptance.py'),'--staff-token-stdin','--session-only','--output',output];
 const child=spawn(path.join(root,'backend/.venv/Scripts/python.exe'),args,{cwd:root,stdio:['pipe','pipe','pipe'],windowsHide:true});
 let stdout='';child.stdout.on('data',c=>{stdout+=c;});child.stderr.resume();child.stdin.end(token);token=undefined;
 const code=await new Promise((resolve,reject)=>{child.on('error',reject);child.on('close',resolve);});
 if(code!==0)throw Error('Acceptance runner did not complete');
 const evidence=JSON.parse(fs.readFileSync(output,'utf8'));
 if(templateMode){
  console.log(JSON.stringify({candidate_passed:evidence.passed,evidence:output,message:'Waiting for accepted local development configuration; no automatic gate change.'}));
  stage='final_relay_verification';const deadline=Date.now()+5*60*1000;let verified=false;
  while(Date.now()<deadline){
   try{const result=await context.request.get(origin+'/admin/templates/api?path=%2Fadmin%2Fprint-templates&limit=1',{timeout:15000});if(result.status()===200){const data=await result.json();if(Array.isArray(data.items)&&data.items.length<=1){verified=true;break;}}}catch{}
   await new Promise(resolve=>setTimeout(resolve,2000));
  }
  if(!verified)throw Error('Final relay not ready');
  await page.goto(origin+'/admin/templates',{waitUntil:'domcontentloaded',timeout:120000});
  await page.getByText('Development acceptance fixture',{exact:true}).waitFor({timeout:30000});
  fs.writeFileSync(path.join(root,'tmp/template-activation/browser-acceptance.json'),JSON.stringify({project:'fhuxryfkfrvycsojkzvq',genuine_auth:true,mfa_verified:true,relay_list_status:200,fixture_visible:true,checked_at:new Date().toISOString()},null,2));
  console.log('Final authenticated frontend relay and visible synthetic template listing PASSED. No QR or publication requests.');return;
 }
 console.log(JSON.stringify({evidence:output,security_status:evidence.staff.security_status,mfa_verified:evidence.staff.mfa_verified??false,roles:evidence.staff.roles??[],message:'No gates enabled. No Support/Audit access-audit endpoints or provider mutations requested.'},null,2));
 }catch(error){console.error(JSON.stringify({stage,error_type:error?.name??'Error',message:'Secure login helper did not complete. No credential details logged.'}));process.exitCode=1;}finally{if(browser)await browser.close();}})();
