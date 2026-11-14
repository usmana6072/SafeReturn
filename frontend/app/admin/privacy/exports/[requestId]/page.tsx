import { AdminPage, AdminNotice } from '../../../../../components/admin-page';
import { AdminPrivacyRequests } from '../../../../../components/admin-privacy-requests';
import { canReviewPrivacy } from '../../../../../lib/admin-privacy-metadata';
import { privacyMetadataAdmitted } from '../../../../../lib/privacy-metadata-gate';
export const dynamic='force-dynamic';
export const metadata={title:'Privacy Export Request | SafeReturn',robots:{index:false,follow:false},referrer:'no-referrer' as const};
export default async function Page({params}:{params:Promise<{requestId:string}>}){
  const {requestId}=await params;
  return <AdminPage path="/admin/privacy/exports" capability="privacy.exports">{(security,ur)=>canReviewPrivacy(security.roles)?<AdminPrivacyRequests ur={ur} requestId={requestId} admitted={privacyMetadataAdmitted()}/>:<AdminNotice ur={ur} denied/>}</AdminPage>;
}
