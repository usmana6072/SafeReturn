import {AdminPage,AdminNotice} from '../../../../components/admin-page';
import {AdminStorageRetention} from '../../../../components/admin-storage-retention';
import {canReadArtifacts} from '../../../../lib/finance-storage-contract';
import {storageReadAdmitted} from '../../../../lib/finance-storage-gate';
export const dynamic='force-dynamic';
export const metadata={title:'Storage Artifacts | SafeReturn',robots:{index:false,follow:false},referrer:'no-referrer' as const};
export default async function Page({params}:{params:Promise<{recordId:string}>}){
const {recordId}=await params;
return <AdminPage path="/admin/storage" capability="storage.metadata">{(security,ur)=>canReadArtifacts(security.roles)?<AdminStorageRetention ur={ur} admitted={storageReadAdmitted()}  recordId={recordId}/>:<AdminNotice ur={ur} denied/>}</AdminPage>;
}

