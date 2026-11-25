import { getLanguage } from "../../lib/i18n";
import "../../components/shopping-cart.css";
import "../../components/checkout.css";

export default async function CheckoutLoading() {
  const ur = (await getLanguage()) === "ur";
  return (
    <div id="main" className="checkout-screen" dir={ur ? "rtl" : "ltr"} tabIndex={-1} aria-busy="true" aria-live="polite">
      <header className="checkout-header">
        <span className="checkout-back-link" style={{ opacity: 0.6 }}>
          <span>{ur ? "← واپس کارٹ" : "← Back to Cart"}</span>
        </span>
        <div className="checkout-title-row">
          <div>
            <h1>{ur ? "چیک آؤٹ" : "Checkout"}</h1>
            <p className="checkout-subtitle">{ur ? "معلومات لوڈ ہو رہی ہیں…" : "Loading checkout details…"}</p>
          </div>
        </div>
        <div className="checkout-stepper" style={{ opacity: 0.6 }}>
          <span className="checkout-step completed">
            <span className="checkout-step-number">✓</span>
            <span>{ur ? "کارٹ" : "Cart"}</span>
          </span>
          <span className="checkout-step-divider">→</span>
          <span className="checkout-step active">
            <span className="checkout-step-number">2</span>
            <span>{ur ? "ترسیل اور جائزہ" : "Shipping & Review"}</span>
          </span>
          <span className="checkout-step-divider">→</span>
          <span className="checkout-step">
            <span className="checkout-step-number">3</span>
            <span>{ur ? "ادائیگی" : "Payment"}</span>
          </span>
        </div>
      </header>

      <div className="checkout-layout">
        <div className="checkout-main">
          <div className="checkout-panel">
            <div style={{ width: "160px", height: "24px", borderRadius: "6px", background: "#f2e7db", marginBottom: "1rem" }} />
            {[1, 2].map((i) => (
              <div key={i} className="checkout-item-card">
                <div className="checkout-item-thumb" style={{ background: "#f3e8dd" }} />
                <div className="checkout-item-info">
                  <div style={{ width: "60%", height: "18px", borderRadius: "6px", background: "#ecdcd0", marginBottom: "0.5rem" }} />
                  <div style={{ width: "40%", height: "14px", borderRadius: "4px", background: "#f3e8dd" }} />
                </div>
              </div>
            ))}
          </div>

          <div className="checkout-panel">
            <div style={{ width: "180px", height: "24px", borderRadius: "6px", background: "#f2e7db", marginBottom: "1rem" }} />
            <div className="checkout-form-grid">
              <div style={{ height: "48px", borderRadius: "12px", background: "#f7f1eb", border: "1px solid var(--checkout-line)" }} />
              <div style={{ height: "48px", borderRadius: "12px", background: "#f7f1eb", border: "1px solid var(--checkout-line)" }} />
              <div style={{ height: "48px", borderRadius: "12px", background: "#f7f1eb", border: "1px solid var(--checkout-line)" }} />
            </div>
          </div>
        </div>

        <aside className="checkout-sidebar">
          <div className="checkout-panel" style={{ minHeight: "280px" }}>
            <div style={{ width: "140px", height: "24px", borderRadius: "6px", background: "#f2e7db", marginBottom: "1.25rem" }} />
            <div style={{ display: "grid", gap: "0.75rem", marginBottom: "1.5rem" }}>
              <div style={{ width: "100%", height: "16px", borderRadius: "4px", background: "#f5eee6" }} />
              <div style={{ width: "100%", height: "16px", borderRadius: "4px", background: "#f5eee6" }} />
              <div style={{ width: "100%", height: "24px", borderRadius: "4px", background: "#f2e7db", marginTop: "0.5rem" }} />
            </div>
            <div style={{ height: "48px", borderRadius: "99px", background: "#d4a99b" }} />
          </div>
        </aside>
      </div>
    </div>
  );
}
