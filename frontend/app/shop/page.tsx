import { getCatalog } from "../../lib/catalog";
import { getLanguage } from "../../lib/i18n";
import { ShopCatalog } from "../../components/shop-catalog";
export const metadata = { title: "Shop QR Tags | SafeReturn" };
export default async function Shop({ searchParams }: { searchParams: Promise<{ q?: string; category?: string }> }) {
  const [catalog, language, query] = await Promise.all([getCatalog(), getLanguage(), searchParams]);
  return <ShopCatalog catalog={catalog} ur={language === "ur"} initialQuery={typeof query.q === "string" ? query.q : ""} initialCategory={typeof query.category === "string" ? query.category : ""}/>;
}
