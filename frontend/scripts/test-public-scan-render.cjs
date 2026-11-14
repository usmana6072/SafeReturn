// Render the real public scan Server Component with allowlisted synthetic API
// results. No app server, credentials, customer profiles or network requests.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript'),assert=require('node:assert/strict');
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
let current=null,language='en',calls=0;
const source=ts.transpileModule(fs.readFileSync(path.resolve(__dirname,'../app/q/[token]/page.tsx'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
const moduleValue={exports:{}};
const stub=()=>null;
vm.runInNewContext(source,{module:moduleValue,exports:moduleValue.exports,require(name){
 if(name==='react/jsx-runtime')return require(name);
 if(name==='node:crypto')return require(name);
 if(name==='next/link')return {__esModule:true,default:({href,children,...rest})=>React.createElement('a',{href,...rest},children)};
 if(name.endsWith('/qr-server'))return {ownerApi:()=>async()=>{calls++;if(current instanceof Error)throw current;return current;}};
 if(name.endsWith('/i18n'))return {getLanguage:async()=>language};
 if(name.endsWith('/scan-language'))return {changeScanLanguage:async()=>{}};
 if(name.endsWith('/qr-forms'))return {ScanForm:stub};
 if(name.endsWith('/public-actions'))return {ContactReveal:stub,WhatsAppAction:stub};
 if(name.endsWith('/finder-message'))return {FinderMessageForm:stub};
 throw Error('Unexpected import '+name);
},process:{env:{}},console},{filename:'public-scan-page.tsx'});
(async()=>{
 const Page=moduleValue.exports.default,token='A'.repeat(43);
 async function render(value,lang='en',scanned=token){current=value;language=lang;return renderToStaticMarkup(await Page({params:Promise.resolve({token:scanned})}));}
 const profile={tag_type:'lost',status:'active',locale_options:['en','ur'],lost_item:{label:'Shared bag',description:'Owner-selected description',reward_text:'Public reward'},features:{finder_form_enabled:false,whatsapp_contact_enabled:false,location_sharing_available:false},private_email:'HIDDEN-EMAIL',phone:'HIDDEN-PHONE',medical_notes:'HIDDEN-MEDICAL'};
 let html=await render(profile);assert(html.includes('Shared bag')&&html.includes('Owner-selected description'));assert(html.includes('href="/"'));for(const value of ['HIDDEN-EMAIL','HIDDEN-PHONE','HIDDEN-MEDICAL'])assert(!html.includes(value));
 let checks=1;
 for(const status of ['unactivated','owner_disabled','admin_suspended','revoked']){html=await render({...profile,status});assert(!html.includes('Shared bag'));assert(!html.includes('Owner-selected description'));assert(html.includes('href="/"'));checks++;}
 html=await render(new Error('PRIVATE_PROVIDER_ERROR'));assert(!html.includes('PRIVATE_PROVIDER_ERROR'));checks++;
 const before=calls;html=await render(profile,'en','invalid!');assert.equal(calls,before);assert(!html.includes('Shared bag'));checks++;
 html=await render({...profile,tag_type:'ice',lost_item:undefined,ice:{display_name:'Shared person',blood_group:'A+',medical_notes:null,contacts:[],owner_information_disclaimer:'Owner-provided information'}});assert(html.includes('Shared person'));assert(!html.includes('HIDDEN-PHONE'));checks++;
 html=await render(profile,'ur');assert(html.includes('href="/"')&&html.includes('Shared bag'));checks++;
 console.log('PASS '+checks+' actual public scan page render checks: owner-selected fields, inactive-state privacy, Home link, malformed token, provider errors and Urdu; no network.');
})().catch(error=>{console.error(error);process.exitCode=1;});
