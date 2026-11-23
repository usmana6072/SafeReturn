import { ownerApi, ownerSession } from "../../../lib/qr-server";
import { getLanguage } from "../../../lib/i18n";
import { orderPage, type CustomerOrder } from "../../../lib/customer-orders";
import { OrdersList } from "../../../components/customer-orders";
export default async function OrdersPage({searchParams}:{searchParams:Promise<{cursor?:string|string[]}>}) {
  const [session,language,params]=await Promise.all([ownerSession(),getLanguage(),searchParams]);
  let items:CustomerOrder[]=[],next:string|null=null,unavailable=false;
  try {
    if(params.cursor!==undefined&&(typeof params.cursor!=="string"||params.cursor.length>2048))throw Error();
    const query=new URLSearchParams({limit:"100"});if(params.cursor)query.set("cursor",params.cursor);
    const response=orderPage(await ownerApi(session.token)<unknown>("/me/orders?"+query));
    items=response.items;next=response.next_cursor;
  }catch{unavailable=true;}
  return <OrdersList key={typeof params.cursor==="string"?params.cursor:"latest"} items={items} next={next} older={!!params.cursor} cursor={typeof params.cursor==="string"?params.cursor:undefined} ur={language==="ur"} unavailable={unavailable}/>;
}
