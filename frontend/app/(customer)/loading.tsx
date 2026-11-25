import { getLanguage } from "../../lib/i18n";

export default async function CustomerLoading() {
  const ur = (await getLanguage()) === "ur";
  return (
    <div className="customer-main" aria-busy="true" aria-live="polite">
      <div className="customer-heading">
        <div style={{ width: "220px", height: "36px", borderRadius: "8px", background: "var(--soft)" }} />
      </div>
      <div className="pair-card" style={{ marginTop: "24px", minHeight: "180px", background: "white" }}>
        <div style={{ width: "180px", height: "24px", borderRadius: "6px", background: "var(--soft)", marginBottom: "16px" }} />
        <div style={{ width: "100%", height: "16px", borderRadius: "4px", background: "var(--soft)", marginBottom: "8px" }} />
        <div style={{ width: "70%", height: "16px", borderRadius: "4px", background: "var(--soft)" }} />
      </div>
      <p role="status" className="sr-only">
        {ur ? "آپ کی معلومات لوڈ ہو رہی ہیں…" : "Loading your information…"}
      </p>
    </div>
  );
}
