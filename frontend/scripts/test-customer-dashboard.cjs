const fs=require('node:fs'),vm=require('node:vm'),ts=require('typescript'),React=require('react'),assert=require('node:assert/strict');
const {renderToStaticMarkup}=require('react-dom/server');
let failQR=false;const requests=[];
const id='00000000-0000-4000-8000-000000000001';
function compile(file,dependency){const m={exports:{}};vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{fileName:file,compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText,{exports:m.exports,require:dependency});return m.exports;}
const inventory=compile('lib/inventory-contract.ts',()=>{throw Error();});
const independent=compile('lib/independent-qr.ts',()=>inventory);
const {CustomerDashboard}=compile('components/customer-dashboard.tsx',name=>{
 if(name==='react/jsx-runtime')return require(name);
 if(name==='next/link')return{__esModule:true,default:({href,children,...rest})=>React.createElement('a',{href,...rest},children)};
 if(name.endsWith('/qr-server'))return{ownerSession:async()=>({token:'synthetic'}),ownerApi:token=>{assert.equal(token,'synthetic');return async url=>{requests.push(url);if(url.includes('independent-qr')){if(failQR)throw Error('PRIVATE_CANARY');return{items:[{logical_item_id:id,qr_id:id,order_id:id,product_name_snapshot:'Purchased QR',tag_type:'lost',ownership_status:'unclaimed',public_status:'unactivated',revision:1,activated_at:null,can_activate:false}],next_cursor:null,activation_released:false};}if(url.includes('orders'))return{items:[{id,order_number:'SR-test',payment_status:'under_review',fulfillment_status:'unallocated',total_pkr:'120.00',currency_code:'PKR'}],next_cursor:null};return{items:[],next_cursor:null};}}};
 if(name.endsWith('/independent-qr'))return independent;
 if(name.endsWith('/i18n'))return{getLanguage:async()=> 'en'};
 if(name.endsWith('/order-status'))return{orderStatus:value=>value};
 if(name==='./customer')return{Unavailable:()=>React.createElement('p',null,'Information unavailable')};
 throw Error(name);
});
(async()=>{let html=renderToStaticMarkup(await CustomerDashboard());assert(html.includes('Purchased QR')&&html.includes('SR-test')&&html.includes('under_review'));assert(!html.includes('tag-pairs'));assert.equal(requests.length,3);failQR=true;html=renderToStaticMarkup(await CustomerDashboard());assert(html.includes('Information unavailable')&&html.includes('SR-test'));assert(!html.includes('PRIVATE_CANARY'));console.log('PASS customer dashboard authenticated endpoints, independent counts, server payment state and partial failure isolation.');})().catch(error=>{console.error(error);process.exitCode=1;});


