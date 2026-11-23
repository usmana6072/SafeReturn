import {redirect} from "next/navigation";
import {getLanguage} from "../../lib/i18n";
import {verifiedSession,accountRequest} from "../../lib/auth/server";
import {CustomerShell} from "../../components/customer";
import {AccountSettings,AccountRetry} from "../../components/account-settings";
import {accountCopy} from "../../lib/account-copy";
import {logout,saveAccount,saveAccountLanguage} from "../auth/actions";
export const dynamic="force-dynamic";
export const metadata={title:"Account Settings | SafeReturn",robots:{index:false,follow:false},referrer:"no-referrer" as const};
export default async function AccountPage({searchParams}:{searchParams:Promise<Record<string,string|string[]|undefined>>}){
 const ur=await getLanguage()==="ur",c=accountCopy(ur);
 let session;
 try{session=await verifiedSession();}catch{return <CustomerShell ur={ur}><section className="settings-screen settings-empty" role="alert"><h1>{c.unavailable}</h1><p>{c.unavailableText}</p><AccountRetry ur={ur}/></section></CustomerShell>;}
 if(!session)redirect("/login");
 let account;
 try{account=await accountRequest(session.token);if(account.user_id!==session.user.id)throw Error("Unavailable");}
 catch{return <CustomerShell ur={ur}><section className="settings-screen settings-empty" role="alert"><h1>{c.unavailable}</h1><p>{c.unavailableText}</p><AccountRetry ur={ur}/><form action={logout}><button className="settings-logout">{c.logout}</button></form></section></CustomerShell>;}
 const params=await searchParams,initialName=typeof session.user.user_metadata?.display_name==="string"?session.user.user_metadata.display_name.slice(0,120):"";
 return <CustomerShell ur={ur}><AccountSettings account={account} email={session.user.email??""} initialName={initialName} ur={ur} saved={params.saved==="1"} logoutFailed={params.logout==="failed"} saveAction={saveAccount} languageAction={saveAccountLanguage} logoutAction={logout}/></CustomerShell>;
}
