import { getCatalog } from "../../lib/catalog";
import { getLanguage } from "../../lib/i18n";
import { CheckoutCart } from "../../components/checkout";
export default async function Cart(){const language=await getLanguage(),catalog=await getCatalog();return <main id="main" className="container section" tabIndex={-1}><a href="/shop">{language==="ur"?"مصنوعات":"Products"}</a><h1>{language==="ur"?"کارٹ":"Your cart"}</h1><CheckoutCart products={catalog.products} language={language}/></main>;}
