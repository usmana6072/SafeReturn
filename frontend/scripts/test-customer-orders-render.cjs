const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm"),ts=require("typescript"),React=require("react"),assert=require("node:assert/strict");
const {renderToStaticMarkup}=require("react-dom/server");
const oid="00000000-0000-4000-8000-000000000001";
let denied=false,requests=[];
const summary={id:oid,order_number:"SR-SYNTHETIC",order_status:"placed",payment_status:"under_review",fulfillment_status:"unallocated",currency_code:"PKR",total_pkr:"180.00",created_at:"2026-11-01T12:00:00Z",public_token:"PRIVATE_CANARY"};
const quarantine=require("../tests/load-quarantine.cjs")(()=>{throw Error("Network prohibited")});
function load(file){
 const module={exports:{}};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText,{
  module,exports:module.exports,URLSearchParams,require(name){
   if(name==="react"||name==="react/jsx-runtime")return require(name);
   if(name==="next/navigation")return{notFound:()=>{throw Error("not found")},useRouter:()=>({refresh(){}})};
   if(name==="next/link")return{__esModule:true,default:({href,children,prefetch,...rest})=>React.createElement("a",{href,...rest},children)};
   if(name.endsWith("/customer-capabilities"))return{customerOperationAvailable:(method,url)=>{try{quarantine.assertBackendOperation(method,"/api/v1"+url);return true;}catch{return false;}}};
   if(name.endsWith("/qr-contract"))return{uuid:value=>/^[a-f0-9-]{36}$/.test(value)};
   if(name.endsWith("/api/transport"))return{ApiError:class ApiError extends Error{}};
   if(name.endsWith("/qr-server"))return{ownerSession:async()=>({token:"SYNTHETIC"}),ownerApi:token=>{assert.equal(token,"SYNTHETIC");return async url=>{requests.push(url);if(denied)throw Error("PRIVATE_PROVIDER_ERROR");return url.endsWith("/shipments")?{items:[]}:{items:[summary],next_cursor:null};}}};
   if(name.endsWith("/i18n"))return{getLanguage:async()=>"en"};
   if(name.endsWith("/cancellation-request"))return{CancellationRequest:()=>null};
   if(name.endsWith(".css"))return{};
   if(name.startsWith(".")){
    const target=path.resolve(path.dirname(file),name);
    return load(fs.existsSync(target+".tsx")?target+".tsx":target+".ts");
   }
   throw Error(name);
  },
 });return module.exports;
}
(async()=>{
 const list=load(path.resolve("app/(customer)/orders/page.tsx")).default;
 const detail=load(path.resolve("app/(customer)/orders/[orderId]/page.tsx")).default;
 let html=renderToStaticMarkup(await list({searchParams:Promise.resolve({cursor:"opaque_next"})}));
 assert.equal(requests[0],"/me/orders?limit=100&cursor=opaque_next");assert(html.includes("SR-SYNTHETIC")&&html.includes("Payment Under Review")&&!html.includes("PRIVATE_CANARY"));
 html=renderToStaticMarkup(await detail({params:Promise.resolve({orderId:oid})}));
 assert(html.includes("currently unavailable")&&html.includes("View Payment Details")&&!html.includes("PRIVATE_CANARY"));
 assert(!requests.includes("/me/orders/"+oid));
 await detail({params:Promise.resolve({orderId:oid}),searchParams:Promise.resolve({cursor:"older_page"})});
 assert(requests.includes("/me/orders?limit=100&cursor=older_page"));
 denied=true;html=renderToStaticMarkup(await detail({params:Promise.resolve({orderId:oid})}));
 assert(html.includes("couldn’t be loaded")&&!html.includes("PRIVATE_PROVIDER_ERROR")&&!html.includes("SR-SYNTHETIC"));
 console.log("PASS owner-scoped order paging, accurate statuses, restricted detail with independent payment/shipment access, partial failures and private field projection.");
})().catch(e=>{console.error(e);process.exitCode=1});
