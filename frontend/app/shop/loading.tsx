import { getLanguage } from "../../lib/i18n";
import "../../components/shop.css";

export default async function ShopLoading() {
  const ur = (await getLanguage()) === "ur";
  return (
    <section className="shop-screen shop-loading" aria-busy="true" aria-live="polite">
      <header className="shop-intro">
        <div>
          <i className="shop-loading-title" />
          <i style={{ width: "80%", height: "1.2rem", margin: ".5rem 0 0" }} />
        </div>
        <div className="shop-cart" style={{ opacity: 0.6 }}>
          <span>{ur ? "کارٹ" : "Cart"}</span>
        </div>
      </header>
      <div className="shop-search" style={{ opacity: 0.6 }}>
        <i style={{ width: "100%", height: "24px" }} />
      </div>
      <div className="shop-toolbar" style={{ opacity: 0.6 }}>
        <i style={{ width: "80px", height: "36px", borderRadius: "99px" }} />
        <i style={{ width: "120px", height: "36px", borderRadius: "99px" }} />
        <i style={{ width: "70px", height: "20px", marginInlineStart: "auto" }} />
      </div>
      <div className="shop-grid">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <article className="shop-card" key={i} aria-hidden="true">
            <i />
            <i />
            <i style={{ width: "90%", height: "1rem" }} />
            <i style={{ width: "45%", height: "1.2rem" }} />
            <i />
          </article>
        ))}
      </div>
    </section>
  );
}
