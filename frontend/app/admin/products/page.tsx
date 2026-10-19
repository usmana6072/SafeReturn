import { AdminPage } from "../../../components/admin-page";
import { getLanguage } from "../../../lib/i18n";
import { CatalogAdmin } from "../../../components/catalog-admin";
export default async function Page() { return <AdminPage path="/admin/products" capability="catalog.manage"><CatalogAdmin language={await getLanguage()}/></AdminPage>; }
