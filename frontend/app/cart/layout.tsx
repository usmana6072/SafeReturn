import { CustomerShell } from "../../components/customer";
import { getLanguage } from "../../lib/i18n";
export default async function Layout({children}:{children:React.ReactNode}) { return <CustomerShell ur={await getLanguage() === "ur"}>{children}</CustomerShell>; }
