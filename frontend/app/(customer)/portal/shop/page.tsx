import { ShopCatalogPage } from "../../../../components/shop-pages";

export const metadata = { title: "Shop QR Tags | SafeReturn" };

export default function Shop({ searchParams }: { searchParams: Promise<{ q?: string; category?: string }> }) {
  return <ShopCatalogPage searchParams={searchParams} shopPath="/portal/shop" />;
}
