// Actual Products BFF + protected template parsers. Synthetic read responses only.
const assert=require('node:assert/strict');
const {createHarness}=require('../tests/products-fixture.cjs');
const {content,tid,rid}=require('../tests/templates-fixture.cjs');
const stamp='2026-10-25T12:00:00Z';
const template={template_id:tid,key:'approved-template',name:'Published design',purpose:'lost',lifecycle_status:'active',row_version:3,created_at:stamp};
const revision=(version,status='published')=>({revision_id:rid,template_id:tid,version,status,row_version:3,content:content(),fingerprint_sha256:status==='draft'?null:'a'.repeat(64),created_at:stamp,published_at:['published','retired'].includes(status)?stamp:null});
const get=h=>h.dispatch('https://products.test/admin/catalog-api?path=/admin/catalog/approved-templates');
(async()=>{
 let checks=0;
 const h=createHarness();h.state.publishedTemplates=[template];h.state.publishedDetails[tid]={template,revisions:[revision(1),revision(2),revision(3,'draft'),revision(4,'pending_qa'),revision(5,'retired')],next_cursor:null};
 let r=await get(h);assert.equal(r.status,200);let body=await r.json();assert.deepEqual(body.items,[{template_key:'approved-template',template_version:1},{template_key:'approved-template',template_version:2}]);checks++;
 assert(h.state.calls.every(c=>c.method==='GET'&&c.options.cache==='no-store'&&c.options.redirect==='error'));checks++;
 h.state.publishedDetails[tid].template={...template,lifecycle_status:'retired'};r=await get(h);assert.deepEqual((await r.json()).items,[{template_key:'approved-template',template_version:1}]);checks++;
 for(const status of [401,403,503]){const fail=createHarness();fail.state.templateStatus=status;r=await get(fail);assert.equal(r.status,status);assert(!(await r.text()).includes('synthetic-only-token'));checks++;}
 const disabled=createHarness();disabled.state.templateStatus=503;disabled.state.templateCode='TEMPLATE_MANAGEMENT_DISABLED';assert.equal((await get(disabled)).status,200);checks++;
 const paged=createHarness();paged.state.templatePages={start:{as_of:stamp,items:[template],next_cursor:'next_template'},next_template:{as_of:stamp,items:[],next_cursor:null}};paged.state.revisionPages={[tid+'@start']:{template,revisions:[revision(1)],next_cursor:'next_revision'},[tid+'@next_revision']:{template,revisions:[revision(2)],next_cursor:null}};
 r=await get(paged);assert.equal(r.status,200);body=await r.json();assert.equal(body.items.length,2);assert(paged.state.calls.some(c=>c.path.includes('print-templates')&&c.options.method==='GET'));assert.equal(paged.state.calls.length,5);checks++;
 paged.state.templatePages.next_template.next_cursor='next_template';assert.equal((await get(paged)).status,503);checks++;
 const empty=createHarness();empty.state.publishedTemplates=[template];empty.state.publishedDetails[tid]={template,revisions:[revision(1,'draft')],next_cursor:null};r=await get(empty);assert.equal(r.status,200);assert.equal((await r.json()).items.length,1);checks++;
 console.log('PASS '+checks+' published-choice BFF checks: publication filtering, exact versions, dedupe, pagination, cycle rejection, auth/provider failures and management-disabled compatibility; zero writes.');
})().catch(e=>{console.error(e);process.exitCode=1;});
