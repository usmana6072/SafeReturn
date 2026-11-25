import { getCatalog } from "../lib/catalog";
import { FeaturedCatalog } from "./catalog";

export async function FeaturedProductsSection({
  language,
  emptyText,
}: {
  language: "en" | "ur";
  emptyText?: string;
}) {
  const featured = await getCatalog(true);
  const catalog = !featured.unavailable && featured.products.length === 0 ? await getCatalog() : featured;
  return <FeaturedCatalog catalog={catalog} language={language} home emptyText={emptyText} />;
}
