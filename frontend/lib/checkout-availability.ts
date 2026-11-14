import type { CatalogProduct } from "./catalog";

export function canOrder(product: CatalogProduct): boolean {
  return product.commerce_model === "single_qr"
    ? product.checkout_available === true && !product.checkout_unavailable_reasons?.length
    : product.checkout_available !== false;
}

export function checkoutUnavailableMessage(product: CatalogProduct, language: "en" | "ur"): string {
  const ur = language === "ur", reasons = product.checkout_unavailable_reasons ?? [];
  if (reasons.includes("CHECKOUT_CHARGES_UNCONFIGURED")) return ur
    ? "ترسیل اور ٹیکس کی رقم مقرر ہونے تک چیک آؤٹ دستیاب نہیں۔"
    : "Checkout is unavailable until delivery and tax amounts are configured.";
  if (reasons.includes("CHECKOUT_RUNTIME_DISABLED")) return ur
    ? "سرور پر چیک آؤٹ ابھی فعال نہیں ہے۔"
    : "Checkout is not enabled on the server yet.";
  const release = reasons.includes("SINGLE_QR_CHECKOUT_NOT_RELEASED");
  const payment = reasons.includes("PAYMENT_INSTRUCTIONS_UNAVAILABLE");
  if (release && payment) return ur
    ? "آن لائن خریداری ابھی فعال نہیں اور منظور شدہ بینک / راست ادائیگی کی ہدایات دستیاب نہیں ہیں۔"
    : "Online purchasing has not been enabled, and approved Bank / Raast payment instructions are not available.";
  if (release) return ur ? "آن لائن خریداری ابھی فعال نہیں کی گئی۔" : "Online purchasing has not been enabled yet.";
  if (payment) return ur ? "منظور شدہ بینک / راست ادائیگی کی ہدایات دستیاب ہونے تک خریداری بند ہے۔" : "Purchasing is paused until approved Bank / Raast payment instructions are available.";
  return ur ? "اس مصنوعہ کی آن لائن خریداری ابھی دستیاب نہیں۔" : "Online ordering is not available yet.";
}
