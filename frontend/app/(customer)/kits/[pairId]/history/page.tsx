import {notFound} from 'next/navigation';
import {ownerSession} from '../../../../../lib/qr-server';
import {id} from '../../../../../lib/qr-lifecycle-contract';
import {getLanguage} from '../../../../../lib/i18n';
import {QrLifecycle} from '../../../../../components/qr-lifecycle';
export const dynamic='force-dynamic';
export const metadata={title:'QR public access and history | SafeReturn',robots:{index:false,follow:false},referrer:'no-referrer' as const};
export default async function Page({params}:{params:Promise<{pairId:string}>}){
 let pairId:string;try{pairId=id((await params).pairId);}catch{notFound();}
 await ownerSession();
 return <QrLifecycle key={pairId} pairId={pairId} ur={await getLanguage()==='ur'}/>;
}
