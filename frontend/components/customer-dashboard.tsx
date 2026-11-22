import { getLanguage } from "../lib/i18n";
import { Suspense, type ReactNode } from "react";
import { customerSession, readCustomerDashboard } from "../lib/customer-dashboard";
import { ownerApi } from "../lib/qr-server";
import { DashboardOverview, qrName } from "./dashboard-overview";

async function ProfileName({ qrId, fallback }: { qrId: string; fallback: string }) {
  try {
    const session = await customerSession();
    if (session) {
      const tag = await ownerApi(session.token)<{ profile_label: string | null }>(`/me/qr/${qrId}`);
      if (typeof tag.profile_label === "string" && tag.profile_label.trim()) return <bdi>{tag.profile_label}</bdi>;
    }
  } catch { /* The allocated identity remains usable when its optional label is unavailable. */ }
  return fallback;
}

export async function CustomerDashboard() {
  const [language, data] = await Promise.all([getLanguage(), readCustomerDashboard()]);
  const ur = language === "ur";
  const names: Record<string, ReactNode> = {};
  for (const qr of data.identities?.items.slice(0, 4) ?? []) {
    if (qr.ownership_status !== "active") continue;
    const known = data.inbox?.items.find(m => m.qr_id === qr.qr_id && m.qr_label)?.qr_label;
    const fallback = qrName(qr, ur);
    names[qr.qr_id] = known ? <bdi>{known}</bdi> : <Suspense fallback={fallback}><ProfileName qrId={qr.qr_id} fallback={fallback}/></Suspense>;
  }
  return <DashboardOverview ur={ur} data={data} names={names}/>;
}
