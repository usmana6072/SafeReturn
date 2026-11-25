import Link from "next/link";
import { notFound } from "next/navigation";
import { getProduct } from "../../../lib/catalog";
import { getLanguage } from "../../../lib/i18n";
import { KitConfigurator } from "../../../components/checkout";
import { ShopImage, ShopCartLink, ShopRetry } from "../../../components/shop-catalog";
export default async function Product({ params }: { params: Promise<{ sku: string }> }) {
  const { sku } = await params;
  const [product, language] = await Promise.all([getProduct(sku), getLanguage()]);
  const ur = language === "ur";
  if (product === null) notFound();
  if (product === undefined) return <section className="shop-screen"><div className="shop-empty"><h1>{ur ? "مصنوعہ لوڈ نہیں ہو سکی۔" : "Product could not be loaded. Please try again."}</h1><ShopRetry ur={ur}/><Link href="/shop">{ur ? "تمام مصنوعات" : "All Products"}</Link></div></section>;
  return (
    <section className="shop-screen shop-detail">
      <div className="shop-detail-nav">
        <Link className="shop-back-link" href="/shop">
          <span aria-hidden="true">{ur ? "→" : "←"}</span>
          <span>{ur ? "واپس دکان" : "Back to Shop"}</span>
        </Link>
        <div className="shop-detail-nav-cart">
          <ShopCartLink ur={ur} />
        </div>
      </div>
      <div className="shop-detail-grid">
        <div className="shop-product-story">
          <div className="shop-detail-image-wrap">
            <ShopImage product={product} />
          </div>
          <span className="shop-category">{product.category.name}</span>
          <h1 className="shop-product-title">{product.name}</h1>
          {product.description && <p className="shop-description">{product.description}</p>}
          <p className="shop-model-note">
            {product.commerce_model === "single_qr"
              ? (ur ? "اس آئٹم کی تمام کاپیاں ایک QR پروفائل استعمال کرتی ہیں۔" : "Every copy of this item uses the same QR profile.")
              : (ur ? "ایک جوڑا، الگ Lost اور Emergency پروفائل۔ اضافی کاپیاں وہی پروفائل استعمال کرتی ہیں۔" : "One pair provides separate Lost and Emergency profiles. Extra copies share those profiles.")}
          </p>
        </div>
        <div id="order" tabIndex={-1} className="shop-purchase">
          <KitConfigurator product={product} language={language} premium />
        </div>
      </div>
    </section>
  );
}
