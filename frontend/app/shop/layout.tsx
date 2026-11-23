import { CustomerShell } from "../../components/customer";
import { getLanguage } from "../../lib/i18n";
import "../../components/shop.css";
export const viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };
export default async function Layout({children}:{children:React.ReactNode}) { return <CustomerShell ur={await getLanguage() === "ur"}>{children}</CustomerShell>; }
