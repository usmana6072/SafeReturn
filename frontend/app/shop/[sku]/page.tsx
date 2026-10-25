import { notFound } from "next/navigation";
import { getProduct } from "../../../lib/catalog";
import { getLanguage } from "../../../lib/i18n";
import { KitConfigurator } from "../../../components/checkout";
import { ProductCard } from "../../../components/catalog";
export default async function Product({ params }: { params: Promise<{ sku: string }> }) {
 const { sku } = await params, product = await getProduct(sku), language = await getLanguage();
 if (product === undefined) return <main id="main" className="container section"><h1>{language === "ur" ? "مصنوعات لوڈ نہیں ہو سکیں۔ دوبارہ کوشش کریں۔" : "Product could not be loaded. Please try again."}</h1><a href="/shop">{language === "ur" ? "تمام مصنوعات" : "All products"}</a></main>;
 if (product === null) notFound();
 return <main id="main" className="container section" tabIndex={-1}><a href="/shop">{language === "ur" ? "تمام مصنوعات" : "All products"}</a><h1>{product.name}</h1><ProductCard product={product} language={language}/><KitConfigurator product={product} language={language}/><p>{product.commerce_model==="single_qr"?(language==="ur"?"ہر آئٹم کے لیے ایک منتخب قسم کا QR۔":"One selected QR type per item."):language === "ur" ? "Lost اور ICE کے لیے ایک جوڑا، دو الگ پروفائل۔ ایک QR کی اضافی کاپیاں اسی پروفائل سے منسلک رہتی ہیں۔" : "One pair provides separate Lost and ICE profiles. Extra copies of the same QR share its profile."}</p></main>;
}
