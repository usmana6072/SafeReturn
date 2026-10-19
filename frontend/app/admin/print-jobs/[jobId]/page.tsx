import { AdminPage } from "../../../../components/admin-page";
import { getLanguage } from "../../../../lib/i18n";
import { PrintingAdmin } from "../../../../components/printing-admin";
import { notFound } from "next/navigation";
export default async function Printing({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  if (!/^[a-f0-9-]{36}$/.test(jobId)) notFound();
  return <AdminPage path="/admin" capability="printing.manage"><PrintingAdmin initialJobId={jobId} language={await getLanguage()}/></AdminPage>;
}
