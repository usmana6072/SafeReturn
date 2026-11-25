import { ShopProductPage } from "../../../../../components/shop-pages";

export default function Product({ params }: { params: Promise<{ sku: string }> }) {
  return <ShopProductPage params={params} shopPath="/portal/shop" />;
}
