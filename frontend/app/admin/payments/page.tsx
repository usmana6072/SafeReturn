import { AdminPage } from "../../../components/admin-page";
import { getLanguage } from "../../../lib/i18n";
import { FinanceForm } from "../../../components/payments";
export default async function Page() { return <AdminPage path="/admin/payments" capability="payments.review"><FinanceForm language={await getLanguage()}/></AdminPage>; }
