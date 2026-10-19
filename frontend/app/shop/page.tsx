import { getCatalog } from "../../lib/catalog";
import { getLanguage } from "../../lib/i18n";
import { ProductCard } from "../../components/catalog";
export default async function Shop({ searchParams }: { searchParams: Promise<{ q?: string; category?: string }> }) {
 const language = await getLanguage(), ur = language === "ur", catalog = await getCatalog(), query = await searchParams;
 const products = catalog.products.filter(p => (!query.category || p.category.slug === query.category) && (!query.q || `${p.name} ${p.description ?? ""}`.toLowerCase().includes(query.q.toLowerCase())));
 return <main id="main" className="container section" tabIndex={-1}><a href="/">SafeReturn</a><h1>{ur ? "مصنوعات" : "Products"}</h1><form method="get"><label>{ur ? "تلاش" : "Search"}<input name="q" defaultValue={query.q} maxLength={120}/></label><button>{ur ? "تلاش کریں" : "Search"}</button><a href="/shop">{ur ? "فلٹر ہٹائیں" : "Reset filters"}</a></form><nav aria-label={ur ? "اقسام" : "Categories"}><a href="/shop">{ur ? "تمام" : "All"}</a>{Array.from(new Map(catalog.products.map(p=>[p.category.slug,p.category])).values()).map(c=><a key={c.slug} href={`/shop?category=${encodeURIComponent(c.slug)}`}>{c.name}</a>)}</nav><p role="status">{catalog.unavailable ? ur ? "مصنوعات لوڈ نہیں ہو سکیں۔ دوبارہ کوشش کریں۔" : "Products could not be loaded. Please try again." : `${products.length} ${ur ? "مصنوعات" : "products"}`}</p><div className="catalog-grid">{products.map(p=><ProductCard product={p} language={language} key={p.product_id}/>)}</div></main>;
}
