import Link from "next/link";
import { notFound } from "next/navigation";
import { CheckoutCart } from "../../components/checkout";
import { PaymentForm } from "../../components/customer-payment";
import { getCatalog } from "../../lib/catalog";
import { getLanguage } from "../../lib/i18n";
import { uuid } from "../../lib/qr-contract";
import { ownerSession } from "../../lib/qr-server";

export default async function Checkout({ searchParams }: { searchParams: Promise<{ orderId?: string | string[] }> }) {
    await ownerSession();
    const { orderId } = await searchParams;
    const language = await getLanguage();
    const ur = language === 'ur';
    if (orderId !== undefined) {
        if (typeof orderId !== 'string' || !uuid(orderId)) notFound();
        return <section id="main" className="container section" tabIndex={-1}>
            <PaymentForm key={orderId} orderId={orderId} language={language}/>
        </section>;
    }
    const catalog = await getCatalog();
    return <section id="main" className="container section" tabIndex={-1}>
        <Link href="/cart">{ur ? 'کارٹ' : 'Cart'}</Link>
        <h1>{ur ? 'چیک آؤٹ' : 'Checkout'}</h1>
        <CheckoutCart products={catalog.products} language={language} checkout/>
    </section>;
}
