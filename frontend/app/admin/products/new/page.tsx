import { AdminPage } from "../../../../components/admin-page";
import { AdminPageContainer } from "../../../../components/admin-ui";
import { AddProductForm } from "../../../../components/admin-add-product";
export const dynamic = "force-dynamic";
export const metadata = { title: "Add Product | SafeReturn Staff", robots: { index: false, follow: false } };
export default async function Page() {
    return <AdminPage path="/admin/products/new" capability="catalog.manage">{(_security, ur) => <AdminPageContainer><AddProductForm ur={ur}/></AdminPageContainer>}</AdminPage>;
}
