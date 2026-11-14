import {AdminPage,AdminNotice} from '../../../../../components/admin-page';
import {AdminFinanceSync} from '../../../../../components/admin-finance-sync';
import {canReadSync} from '../../../../../lib/finance-storage-contract';
import {financeSyncReadAdmitted,financeSyncRetryAdmitted} from '../../../../../lib/finance-storage-gate';
export const dynamic='force-dynamic';
export const metadata={title:'Finance Sheet Sync | SafeReturn',robots:{index:false,follow:false},referrer:'no-referrer' as const};
export default async function Page({params}:{params:Promise<{syncId:string}>}){
const {syncId}=await params;
return <AdminPage path="/admin/finance/sheet-sync" capability="finance.mirror">{(security,ur)=>canReadSync(security.roles)?<AdminFinanceSync ur={ur} admitted={financeSyncReadAdmitted()} retryAdmitted={financeSyncRetryAdmitted()} syncId={syncId}/>:<AdminNotice ur={ur} denied/>}</AdminPage>;
}

