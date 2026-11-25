import Link from "next/link";
import { notFound } from "next/navigation";
import { CheckoutCart } from "../../components/checkout";
import { PaymentForm } from "../../components/customer-payment";
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
            <section id="main" className="container section" tabIndex={-1}>
                <PaymentForm key={orderId} orderId={orderId} language={language}/>
            </section>
        );
    }

    const catalog = await getCatalog();

    if (!session) {
        return (
            <section id="main" className="container section" tabIndex={-1}>
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
                    <h2>{ur ? "آپ کے منتخب کردہ آئٹمز" : "Items in Your Cart"}</h2>
                    <CheckoutCart products={catalog.products} language={language} checkout={false}/>
                </div>
            </section>
        );
    }

    return (
        <section id="main" className="container section" tabIndex={-1}>
            <div style={{ marginBottom: "16px" }}>
                <Link href="/cart" style={{ color: "var(--teal)", textDecoration: "underline" }}>
                    {ur ? '← واپس کارٹ' : '← Back to Cart'}
                </Link>
            </div>
            <h1>{ur ? 'چیک آؤٹ' : 'Checkout'}</h1>
            <CheckoutCart products={catalog.products} language={language} checkout/>
        </section>
    );
}
