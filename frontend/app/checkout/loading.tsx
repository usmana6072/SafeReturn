import { getLanguage } from "../../lib/i18n";
import "../../components/shopping-cart.css";

export default async function CheckoutLoading() {
  const ur = (await getLanguage()) === "ur";
  return (
    <section id="main" className="container section" tabIndex={-1} aria-busy="true" aria-live="polite">
      <div style={{ marginBottom: "16px", color: "var(--teal)" }}>
        <span>{ur ? "← واپس کارٹ" : "← Back to Cart"}</span>
      </div>
      <h1>{ur ? "چیک آؤٹ" : "Checkout"}</h1>
      <p style={{ color: "var(--muted)" }}>{ur ? "معلومات لوڈ ہو رہی ہیں…" : "Loading checkout details…"}</p>
      <div style={{ display: "grid", gap: "1rem", marginTop: "24px" }}>
        {[1, 2].map((i) => (
          <div key={i} style={{ height: "80px", borderRadius: "16px", background: "#f6eee6", border: "1px solid var(--line)" }} />
        ))}
      </div>
    </section>
  );
}
