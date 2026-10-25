import { AdminPage } from "../../../../components/admin-page";
import { AdminPageContainer } from "../../../../components/admin-ui";
import { AdminProductDetails } from "../../../../components/admin-product-details";
export const dynamic = "force-dynamic";
export const metadata = { title: "Product Details | SafeReturn Staff", robots: { index: false, follow: false } };
export default async function Page({ params, searchParams }: {
    params: Promise<{
        productId: string;
    }>;
    searchParams: Promise<{
        edit?: string;
    }>;
}) {
    const { productId } = await params;
    const query = await searchParams;
    return <AdminPage path={`/admin/products/${productId}`} capability="catalog.manage">{(_security, ur) => <AdminPageContainer><AdminProductDetails productId={productId} initialEdit={query.edit === "true"} ur={ur}/></AdminPageContainer>}</AdminPage>;
}
