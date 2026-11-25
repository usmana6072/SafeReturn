import Link from "next/link";
import { notFound } from "next/navigation";
import { CheckoutCart } from "../../components/checkout";
import { PaymentForm } from "../../components/customer-payment";
import { CustomerIcon } from "../../components/customer-icon";
import { getCatalog } from "../../lib/catalog";
import { getLanguage } from "../../lib/i18n";
import { uuid } from "../../lib/qr-contract";
import { verifiedSession } from "../../lib/auth/server";

export default async function Checkout({ searchParams }: { searchParams: Promise<{ orderId?: string | string[] }> }) {
    const session = await verifiedSession();
    const { orderId } = await searchParams;
    const language = await getLanguage();
    const ur = language === 'ur';

    if (orderId !== undefined) {
        if (typeof orderId !== 'string' || !uuid(orderId)) notFound();
        return (
            <div id="main" className="checkout-screen" dir={ur ? 'rtl' : 'ltr'} lang={ur ? 'ur' : 'en'} tabIndex={-1}>
                <PaymentForm key={orderId} orderId={orderId} language={language}/>
            </div>
        );
    }

    const catalog = await getCatalog();

    if (!session) {
        return (
            <div id="main" className="checkout-screen" dir={ur ? 'rtl' : 'ltr'} lang={ur ? 'ur' : 'en'} tabIndex={-1}>
                <header className="checkout-header">
                    <Link href="/cart" className="checkout-back-link">
                        <CustomerIcon name="arrow" />
                        <span>{ur ? 'واپس کارٹ پر جائیں' : 'Back to Cart'}</span>
                    </Link>
                    <div className="checkout-title-row">
                        <div>
                            <h1>{ur ? 'چیک آؤٹ' : 'Checkout'}</h1>
                            <p className="checkout-subtitle">
                                {ur ? 'آرڈر مکمل کرنے کے لیے اکاؤنٹ لاگ اِن درکار ہے' : 'Sign in required to complete your order'}
                            </p>
                        </div>
                    </div>
                </header>
                <div className="checkout-auth-card">
                    <span className="eyebrow">{ur ? "اکاؤنٹ درکار ہے" : "ACCOUNT REQUIRED"}</span>
                    <h1>{ur ? "آرڈر مکمل کرنے کے لیے لاگ اِن کریں" : "Sign in to complete your checkout"}</h1>
                    <p>
                        {ur
                            ? "اپنا آرڈر محفوظ کرنے اور ترسیل کا پتہ منتخب کرنے کے لیے لاگ اِن کریں یا نیا اکاؤنٹ بنائیں۔ آپ کا کارٹ محفوظ رہے گا۔"
                            : "Please log in or create an account to enter your delivery address and confirm your order. Your cart is preserved."}
                    </p>
                    <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBlock: "24px" }}>
                        <Link className="button" href="/login?returnTo=/checkout">
                            {ur ? "لاگ اِن کریں" : "Log In to Checkout"}
                        </Link>
                        <Link className="button secondary" href="/signup?returnTo=/checkout">
                            {ur ? "نیا اکاؤنٹ بنائیں" : "Create an Account"}
                        </Link>
                        <Link className="button secondary" href="/cart">
                            {ur ? "واپس کارٹ" : "Back to Cart"}
                        </Link>
                    </div>
                </div>
                <div style={{ marginBlockStart: "32px" }}>
                    <h2 style={{ fontSize: "1.25rem", fontWeight: 650, color: "var(--checkout-ink)", marginBottom: "1rem" }}>
                        {ur ? "آپ کے منتخب کردہ آئٹمز" : "Items in Your Cart"}
                    </h2>
                    <CheckoutCart products={catalog.products} language={language} checkout={false}/>
                </div>
            </div>
        );
    }

    return (
        <div id="main" className="checkout-screen" dir={ur ? 'rtl' : 'ltr'} lang={ur ? 'ur' : 'en'} tabIndex={-1}>
            <header className="checkout-header">
                <Link href="/cart" className="checkout-back-link">
                    <CustomerIcon name="arrow" />
                    <span>{ur ? 'واپس کارٹ پر جائیں' : 'Back to Cart'}</span>
                </Link>
                <div className="checkout-title-row">
                    <div>
                        <h1>{ur ? 'چیک آؤٹ' : 'Checkout'}</h1>
                        <p className="checkout-subtitle">
                            {ur ? 'ترسیل کا پتہ منتخب کریں اور اپنے آرڈر کا جائزہ لیں' : 'Confirm your delivery address and review order total'}
                        </p>
                    </div>
                </div>
                <div className="checkout-stepper" aria-label={ur ? 'مراحل' : 'Checkout steps'}>
                    <span className="checkout-step completed">
                        <span className="checkout-step-number">✓</span>
                        <span>{ur ? 'کارٹ' : 'Cart'}</span>
                    </span>
                    <span className="checkout-step-divider">→</span>
                    <span className="checkout-step active">
                        <span className="checkout-step-number">2</span>
                        <span>{ur ? 'ترسیل اور جائزہ' : 'Shipping & Review'}</span>
                    </span>
                    <span className="checkout-step-divider">→</span>
                    <span className="checkout-step">
                        <span className="checkout-step-number">3</span>
                        <span>{ur ? 'ادائیگی' : 'Payment'}</span>
                    </span>
                </div>
            </header>
            <CheckoutCart products={catalog.products} language={language} checkout/>
        </div>
    );
}
