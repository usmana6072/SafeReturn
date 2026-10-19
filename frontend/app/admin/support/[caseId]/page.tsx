import { notFound } from "next/navigation";
import { AdminPage } from "../../../../components/admin-page";
import { SupportAdmin } from "../../../../components/support-admin";
import { getLanguage } from "../../../../lib/i18n";
export default async function Page({params}:{params:Promise<{caseId:string}>}){const {caseId}=await params;if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(caseId))notFound();return <AdminPage path="/admin/support" capability="support.manage"><SupportAdmin ur={await getLanguage()==="ur"} mode="detail" id={caseId}/></AdminPage>;}
