import {guardedBackendFetch} from '../../../lib/api/quarantine';
import {NextRequest,NextResponse} from 'next/server';
import {verifiedSession} from '../../../lib/auth/server';
import {authConfig} from '../../../lib/auth/config';
import {validateOrigin} from '../../../lib/api/transport';
import {collection,commandResult} from '../../../lib/independent-qr';
const headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'};
const uuid=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(v);
async function boundedText(stream:ReadableStream<Uint8Array>|null,limit:number){const reader=stream?.getReader();if(!reader)throw Error();let raw='',size=0;const decoder=new TextDecoder('utf-8',{fatal:true});try{for(;;){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>limit)throw Error();raw+=decoder.decode(part.value,{stream:true});}raw+=decoder.decode();}finally{await reader.cancel();}return raw;}
async function relay(request:NextRequest){
 const error=(status:number)=>NextResponse.json({error:{code:status===401?'AUTH_REQUIRED':status===403?'FORBIDDEN':'UNAVAILABLE'}},{status,headers});
 try{
  if(request.headers.get('sec-fetch-site')==='cross-site'||request.method!=='GET'&&request.headers.get('origin')!==authConfig().origin)return error(403);
  const session=await verifiedSession();if(!session)return error(401);
  let path='/me/independent-qr',method='GET',body:unknown,key:string|undefined,action='',cards=false;
  if(request.method==='GET'){
   const q=request.nextUrl.searchParams;if([...q.keys()].some(k=>!['after','limit','view'].includes(k)||q.getAll(k).length!==1))return error(422);
   if(q.has('view')){
     if(q.get('view')!=='cards'||q.has('limit'))return error(422);
     cards=true;
   }
   if(q.has('after')&&!uuid(q.get('after'))||q.has('limit')&&!/^(?:[1-9]|[1-9][0-9]|100)$/.test(q.get('limit')!))return error(422);
   if(cards)path+='?limit=8'+(q.has('after')?'&after='+q.get('after'):'');
   else if(q.size)path+='?'+q;
  }else{
   let raw:string;try{raw=await boundedText(request.body,8192);}catch{return error(413);}const input=JSON.parse(raw);
   if(!input||Object.keys(input).some(k=>!['action','body','key','qr_id'].includes(k)))return error(422);
   body=input.body;key=input.key;method='POST';action=input.action;
   if(input.action==='begin')path+='/activation-intents';
   else if(input.action==='confirm')path+='/activations';
   else if(input.action==='availability'&&uuid(input.qr_id)){path+='/'+input.qr_id+'/availability';method='PATCH';}
   else if(input.action==='history'&&uuid(input.qr_id)){path+='/'+input.qr_id+'/history';if(input.body?.after_revision!==undefined){if(!Number.isSafeInteger(input.body.after_revision)||input.body.after_revision<1)return error(422);path+='?after_revision='+input.body.after_revision;}method='GET';body=undefined;}
   else return error(422);
   if(['confirm','availability'].includes(input.action)&&(typeof key!=='string'||!/^[A-Za-z0-9._:-]{8,160}$/.test(key)))return error(422);
  }
  const r=await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')+'/api/v1'+path,{method,cache:'no-store',redirect:'error',signal:AbortSignal.timeout(10000),headers:{Authorization:`Bearer ${session.token}`,Accept:'application/json',...(body!==undefined?{'Content-Type':'application/json'}:{}),...(key?{'Idempotency-Key':key}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
  if(!r.ok)return error([401,403,404,409,412,422,429].includes(r.status)?r.status:503);
  const raw=await boundedText(r.body,524288);
  const value=JSON.parse(raw);
  if(cards){
    const page=collection(value);
    // The owner list has no display names. Project only labels of active records on this page.
    const labels:Record<string,string>={};
    await Promise.all(page.items.slice(0,8).filter(item=>item.ownership_status==='active').map(async item=>{
      try {
        const result=await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')+'/api/v1/me/qr/'+item.qr_id,{
          method:'GET',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(3500),headers:{Authorization:`Bearer ${session.token}`,Accept:'application/json'}
        });
        if(!result.ok)return;
        const tag=JSON.parse(await boundedText(result.body,65536));
        if(tag.qr_id===item.qr_id&&typeof tag.profile_label==='string'&&tag.profile_label.trim()) labels[item.qr_id]=tag.profile_label.slice(0,120);
      } catch { /* The verified collection can still render its product names. */ }
    }));
    return NextResponse.json({...page,labels},{headers});
  }
  return NextResponse.json(request.method==='GET'?collection(value):commandResult(action,value),{status:r.status,headers});
 }catch{return error(503);}
}
export const GET=relay;export const POST=relay;
