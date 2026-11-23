import { ownerApi, ownerSession } from "../../../lib/qr-server";
import { getLanguage } from "../../../lib/i18n";
import { shipmentPage, type ShipmentSummary } from "../../../lib/customer-shipments";
import { ShipmentsList } from "../../../components/customer-shipments";
export const dynamic="force-dynamic";
export default async function Page({searchParams}:{searchParams:Promise<{cursor?:string|string[]}>}){
  const [session,language,{cursor}]=await Promise.all([ownerSession(),getLanguage(),searchParams]);
  let items:ShipmentSummary[]=[],next:string|null=null,failed=false;
  try{
    if(cursor!==undefined&&(typeof cursor!=="string"||cursor.length>2048))throw Error();
    const query=new URLSearchParams({limit:"100"});if(cursor)query.set("cursor",cursor);
    const response=shipmentPage(await ownerApi(session.token)<unknown>("/me/shipments?"+query));
    items=response.items;next=response.next_cursor;
  }catch{failed=true;}
  return <ShipmentsList key={typeof cursor==="string"?cursor:"latest"} items={items} next={next} cursor={typeof cursor==="string"?cursor:undefined} ur={language==="ur"} failed={failed}/>;
}
