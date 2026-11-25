import { getLanguage } from "../../../lib/i18n";
import "../../../components/shop.css";

export default async function ProductLoading() {
  const ur = (await getLanguage()) === "ur";
  return (
    <section className="shop-screen shop-detail" aria-busy="true" aria-live="polite">
      <div className="shop-detail-nav">
        <span className="shop-back-link" style={{ opacity: 0.6 }}>
          <span>{ur ? "← واپس دکان" : "← Back to Shop"}</span>
        </span>
      </div>
      <div className="shop-detail-grid">
        <div className="shop-product-story">
          <div className="shop-detail-image-wrap">
            <div className="shop-image" style={{ background: "#f6ede3" }}>
              <div
                style={{
                  width: "100%",
                  height: "100%",
                  background: "linear-gradient(90deg, #f3e8dd 0%, #faefe5 50%, #f3e8dd 100%)",
                  backgroundSize: "200% 100%",
                }}
              />
            </div>
          </div>
          <div style={{ width: "80px", height: "18px", borderRadius: "99px", background: "#f3e7db", marginBottom: "8px" }} />
          <div style={{ width: "65%", height: "32px", borderRadius: "8px", background: "#eddcd0", marginBottom: "12px" }} />
          <div style={{ width: "100%", height: "16px", borderRadius: "6px", background: "#eddcd0", marginBottom: "8px" }} />
          <div style={{ width: "85%", height: "16px", borderRadius: "6px", background: "#eddcd0", marginBottom: "16px" }} />
          <div style={{ width: "100%", height: "48px", borderRadius: "12px", background: "#faf4ef", border: "1px dashed #e7dcd2" }} />
        </div>
        <div className="shop-purchase">
          <div style={{ width: "50%", height: "26px", borderRadius: "8px", background: "#eddcd0", marginBottom: "16px" }} />
          <div style={{ width: "100%", height: "54px", borderRadius: "13px", background: "#f6eee6", marginBottom: "12px" }} />
          <div style={{ width: "100%", height: "80px", borderRadius: "15px", background: "#fdf8f4", border: "1px solid #e7dcd2", marginBottom: "16px" }} />
          <div style={{ width: "100%", height: "48px", borderRadius: "99px", background: "#d4a99b" }} />
        </div>
      </div>
    </section>
  );
}
