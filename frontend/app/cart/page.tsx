import { getCatalog } from "../../lib/catalog";
import { getLanguage } from "../../lib/i18n";
import { ShoppingCart } from "../../components/shopping-cart";
export const metadata = { title: "Shopping Cart | SafeReturn" };
export default async function Cart() {
  const [catalog, language] = await Promise.all([getCatalog(), getLanguage()]);
  return <ShoppingCart catalog={catalog} ur={language === "ur"}/>;
}
