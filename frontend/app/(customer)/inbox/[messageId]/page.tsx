import Link from "next/link";
import { ApiError } from "../../../../lib/api/transport";
import { changeMessage } from "../../../inbox-actions";
import { ownerApi,ownerSession } from "../../../../lib/qr-server";
import { getLanguage } from "../../../../lib/i18n";
import { uuid } from "../../../../lib/qr-contract";
import { finderDetail,finderPage,inboxContext,inboxQuery,inboxHref,type InboxContext,type FinderSummary } from "../../../../lib/finder-inbox";
import { FinderMessageDetails } from "../../../../components/finder-message-details";
import { FinderRetry } from "../../../../components/finder-inbox";
export const metadata={title:"Message Details | SafeReturn"};
export default async function FinderMessagePage({params,searchParams}:{params:Promise<{messageId:string}>;searchParams:Promise<Record<string,string|string[]|undefined>>}){
 const ur=await getLanguage()==="ur",session=await ownerSession(),{messageId}=await params,p=await searchParams;
 let context:InboxContext={};try{context=inboxContext(p);}catch{}
 let message;
 try{if(!uuid(messageId))throw new ApiError("http",404);message=finderDetail(await ownerApi(session.token)<unknown>("/me/finder-messages/"+messageId));if(message.id!==messageId)throw Error("Unavailable");}
 catch(error){const missing=!uuid(messageId)||(error instanceof ApiError&&error.status===404);
 return <section className="finder-screen"><Link className="finder-back" href={inboxHref(context)}>{ur?"پیغامات پر واپس":"Back to Messages"}</Link><div className="finder-empty" role="alert"><h1>{ur?"پیغام دستیاب نہیں":missing?"Message Unavailable":"Couldn’t Load Message"}</h1><p>{ur?"دوبارہ کوشش کریں یا اِن باکس پر واپس جائیں۔":missing?"This message is no longer available.":"Please try again."}</p>{!missing&&<FinderRetry ur={ur}/>}</div></section>;}
 let summary:FinderSummary|null=null;
 // The detail API does not expose QR ownership metadata. Only link an association
 // verified by matching the message ID in the authenticated owner list.
 try{const q=inboxQuery({...context,status:undefined});q.set("limit","100");const page=finderPage(await ownerApi(session.token)<unknown>("/me/finder-messages?"+q));summary=page.items.find(m=>m.id===messageId)??null;}catch{}
 return <FinderMessageDetails message={message} summary={summary} context={context} action={changeMessage.bind(null,messageId)} ur={ur} result={typeof p.result==="string"?p.result:undefined}/>;
}
