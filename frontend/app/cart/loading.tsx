import { getLanguage } from "../../lib/i18n";
import "../../components/shopping-cart.css";

export default async function CartLoading() {
  const ur = (await getLanguage()) === "ur";
  return (
    <section className="cart-screen cart-loading" aria-busy="true" aria-live="polite">
      <header className="cart-intro">
        <div>
          <h1 style={{ opacity: 0.8 }}>{ur ? "خریداری کی ٹوکری" : "Shopping Cart"}</h1>
          <p>{ur ? "آپ کا کارٹ لوڈ ہو رہا ہے…" : "Loading your cart…"}</p>
        </div>
      </header>
      <div className="cart-layout">
        <div className="cart-items">
          {[1, 2].map((i) => (
            <div className="cart-card" key={i} aria-hidden="true" style={{ minHeight: "10rem" }}>
              <div style={{ display: "flex", gap: "1rem" }}>
                <div style={{ width: "76px", height: "86px", borderRadius: "14px", background: "#f1e8dd", flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <i style={{ width: "60%", height: "1.2rem", borderRadius: "6px" }} />
                  <i style={{ width: "40%", height: "0.9rem", borderRadius: "4px" }} />
                </div>
              </div>
            </div>
          ))}
        </div>
        <aside className="cart-summary" style={{ minHeight: "14rem" }}>
          <i style={{ width: "50%", height: "1.4rem", borderRadius: "6px", marginBottom: "1.5rem" }} />
          <i style={{ width: "100%", height: "1rem", borderRadius: "4px" }} />
          <i style={{ width: "100%", height: "1rem", borderRadius: "4px" }} />
          <i style={{ width: "100%", height: "2.8rem", borderRadius: "99px", marginTop: "1.5rem" }} />
        </aside>
      </div>
    </section>
  );
}
