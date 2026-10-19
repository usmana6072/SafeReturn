import "server-only";
import { redirect } from "next/navigation";
import { verifiedSession } from "./auth/server";
import { qrClient } from "./qr-contract";

export async function ownerSession() {
  const session = await verifiedSession();
  if (!session) redirect("/login");
  return session;
}
export function ownerApi(token?: string) {
  return qrClient(process.env.SAFERETURN_API_ORIGIN ?? "", token);
}
