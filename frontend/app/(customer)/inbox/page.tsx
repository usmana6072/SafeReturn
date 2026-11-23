import { ownerApi, ownerSession } from "../../../lib/qr-server";
import { getLanguage } from "../../../lib/i18n";
import { unreadMessages } from "../../../lib/customer-dashboard";
import { finderPage,inboxContext,inboxQuery,type InboxContext,type FinderSummary } from "../../../lib/finder-inbox";
import { FinderInbox } from "../../../components/finder-inbox";
export const metadata={title:"Finder Messages | SafeReturn"};
export default async function InboxPage({searchParams}:{searchParams:Promise<Record<string,string|string[]|undefined>>}){
 const ur=await getLanguage()==="ur",session=await ownerSession(),params=await searchParams;
 let context:InboxContext={},items:FinderSummary[]=[],next:string|null=null,failed=false;
 try{context=inboxContext(params);const query=inboxQuery(context);query.set("limit","100");
 const page=finderPage(await ownerApi(session.token)<unknown>("/me/finder-messages?"+query));items=page.items;next=page.next_cursor;
 }catch{failed=true;}
 let unread:string|null=null;
 try{const page=await unreadMessages(session.token);unread=String(page.items.length)+(page.more?"+":"");}catch{}
 return <FinderInbox key={inboxQuery(context).toString()} items={items} next={next} context={context} unread={unread} failed={failed} ur={ur} result={typeof params.result==="string"?params.result:undefined}/>;
}
