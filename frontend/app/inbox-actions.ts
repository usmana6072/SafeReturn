"use server";
import { headers } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { authConfig } from "../lib/auth/config";
import { ownerApi, ownerSession } from "../lib/qr-server";
import { uuid } from "../lib/qr-contract";

export async function changeMessage(messageId: string, form: FormData) {
  const session = await ownerSession();
  if ((await headers()).get("origin") !== authConfig().origin || !uuid(messageId)) throw new Error("Invalid inbox request");
  const status = String(form.get("status") ?? "");
  if (!["viewed", "archived", "flagged", "deleted"].includes(status)) throw new Error("Invalid inbox request");
  if (status === "deleted" && form.get("confirm") !== "on") redirect(`/inbox/${messageId}?result=confirm`);
  try {
    await ownerApi(session.token)(`/me/finder-messages/${messageId}`, status === "deleted" ? "DELETE" : "PATCH", status === "deleted" ? undefined : { status });
  } catch { redirect(`/inbox/${messageId}?result=error`); }
  revalidatePath("/inbox");
  revalidatePath(`/inbox/${messageId}`);
  redirect(status === "deleted" ? "/inbox?result=deleted" : `/inbox/${messageId}?result=saved`);
}


export async function requestAccountDeletion(form: FormData) {
  const session=await ownerSession();
  if ((await headers()).get("origin") !== authConfig().origin) throw new Error("Invalid account request");
  if(form.get("confirm")!=="on") redirect('/settings?deletion=confirm');
  const reason=String(form.get("reason")??"").trim();
  if(reason.length>1000) redirect('/settings?deletion=error');
  try {
    await ownerApi(session.token)('/me/account-deletion-requests','POST',{confirm:true,...(reason?{reason}:{})});
  } catch { redirect('/settings?deletion=error'); }
  redirect('/settings?deletion=requested');
}
