import Link from "next/link";
import { AdminPage } from "../../components/admin-page";
import { permittedModules, type StaffSecurityState } from "../../lib/auth/staff-contract";
import { AdminPageContainer } from "../../components/admin-ui";
import { OverviewDashboard } from "../../components/admin-overview";
import {dashboardTrendsAdmitted} from "../../lib/phase13-gate";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "Staff console | SafeReturn",
  robots: { index: false, follow: false },
  referrer: "no-referrer" as const,
};

function Modules({ security, ur }: { security: StaffSecurityState; ur: boolean }) {
  const modules = permittedModules(security).filter(module=>!['/admin/inventory','/admin/batches','/admin/ready-to-ship','/admin/finance/reconciliation'].includes(module.path));

  return (
    <AdminPageContainer>
      {/* Primary heading tested by staff-console.spec.ts */}
      <div className="space-y-1">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">
          {ur ? "عملے کی کام کی جگہ" : "Your staff workspace"}
        </h1>
        <p className="text-xs text-slate-500">
          {ur
            ? "اپنے موجودہ کردار کے مطابق کام کا حصہ منتخب کریں۔"
            : "Choose a workspace available to your current roles."}
        </p>
      </div>

      {/* Source-safe Trends; quarantined Summary remains unavailable. */}
      <OverviewDashboard ur={ur} trendsAdmitted={dashboardTrendsAdmitted()} />

      {/* Quick Navigation Cards */}
      {modules.length > 0 ? (
        <div className="space-y-3 pt-2">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-600">
            {ur ? "دستیاب ماڈیولز" : "Available Administrative Modules"}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {modules.map((module) => (
              <Link
                key={module.path}
                href={module.path}
                prefetch={false}
                className="group block p-4 bg-white rounded-xl border border-slate-200 hover:border-slate-300 shadow-xs hover:shadow-sm transition-all"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-800 group-hover:text-sky-600 transition-colors">
                    {ur ? module.ur : module.en}
                  </h3>
                  <span
                    className="text-slate-400 group-hover:text-sky-600 transition-colors"
                    aria-hidden="true"
                  >
                    ↗
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                  {ur ? module.descriptionUr : module.description}
                </p>
              </Link>
            ))}
          </div>
        </div>
      ) : (
        <section className="bg-white border border-slate-200 rounded-xl p-6 text-center space-y-2 mt-4 shadow-xs">
          <h2 className="text-sm font-bold text-slate-800">
            {ur ? "کوئی کام کا حصہ دستیاب نہیں" : "No modules available"}
          </h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            {ur
              ? "آپ کے کردار کے لیے کوئی کام کا صفحہ ابھی دستیاب نہیں ہے۔ رسائی سے متعلق سوال کے لیے اپنے سکیورٹی ذمہ دار سے رابطہ کریں۔"
              : "No implemented modules are available to your role yet. Contact your security owner about access."}
          </p>
        </section>
      )}
    </AdminPageContainer>
  );
}

export default function Admin() {
  return (
    <AdminPage path="/admin">
      {(security, ur) => <Modules security={security} ur={ur} />}
    </AdminPage>
  );
}
