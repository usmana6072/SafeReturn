import Link from "next/link";
import { AdminPage } from "../../components/admin-page";
import { permittedModules, type StaffSecurityState } from "../../lib/auth/staff-contract";
import styles from "../../components/admin-shell.module.css";
export const dynamic = "force-dynamic";
export const metadata = { title: "Staff console | SafeReturn", robots: { index: false, follow: false }, referrer: "no-referrer" as const };
function Modules({ security, ur }: { security: StaffSecurityState; ur: boolean }) {
  const modules = permittedModules(security);
  return <main><h1>{ur ? "عملے کی کام کی جگہ" : "Your staff workspace"}</h1>
    <p>{ur ? "اپنے موجودہ کردار کے مطابق کام کا حصہ منتخب کریں۔" : "Choose a workspace available to your current roles."}</p>
    <div className={styles.cards}>{modules.map(module => <Link className={styles.card} href={module.path} prefetch={false} key={module.path}><h2>{ur ? module.ur : module.en}<span aria-hidden="true"> ↗</span></h2><p>{ur ? module.descriptionUr : module.description}</p></Link>)}</div>
    {!modules.length && <section className={styles.notice}><h2>{ur ? "کوئی کام کا حصہ دستیاب نہیں" : "No modules available"}</h2><p>{ur ? "آپ کے کردار کے لیے کوئی کام کا صفحہ ابھی دستیاب نہیں ہے۔ رسائی سے متعلق سوال کے لیے اپنے سکیورٹی ذمہ دار سے رابطہ کریں۔" : "No implemented modules are available to your role yet. Contact your security owner about access."}</p></section>}
  </main>;
}
export default function Admin() { return <AdminPage path="/admin">{(security, ur) => <Modules security={security} ur={ur}/>}</AdminPage>; }
