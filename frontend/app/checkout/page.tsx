import { ownerSession } from "../../lib/qr-server";
import { getCatalog } from "../../lib/catalog";
import { getLanguage } from "../../lib/i18n";
import { CheckoutCart } from "../../components/checkout";
export default async function Checkout(){await ownerSession();const language=await getLanguage(),catalog=await getCatalog();return <main id="main" className="container section" tabIndex={-1}><a href="/cart">{language==="ur"?"کارٹ":"Cart"}</a><h1>{language==="ur"?"چیک آؤٹ":"Checkout"}</h1><CheckoutCart products={catalog.products} language={language} checkout/></main>;}
