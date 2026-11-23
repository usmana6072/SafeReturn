import {CustomerShell} from "../../components/customer";
import {AccountSkeleton} from "../../components/account-settings";
import {getLanguage} from "../../lib/i18n";
export default async function AccountLoading(){return <CustomerShell ur={await getLanguage()==="ur"}><AccountSkeleton/></CustomerShell>;}

