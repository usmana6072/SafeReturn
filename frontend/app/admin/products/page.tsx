import { AdminPage } from "../../../components/admin-page";
import { AdminPageContainer } from "../../../components/admin-ui";
import { ProductsList } from "../../../components/admin-products-list";
export const dynamic = "force-dynamic";
export const metadata = { title: "Products | SafeReturn Staff", robots: { index: false, follow: false } };
export default async function Page() {
    return <AdminPage path="/admin/products" capability="catalog.manage">{(_security, ur) => <AdminPageContainer><ProductsList ur={ur}/></AdminPageContainer>}</AdminPage>;
}
