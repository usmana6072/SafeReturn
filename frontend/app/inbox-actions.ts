"use server";
import { headers } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { authConfig } from "../lib/auth/config";
import { ownerApi, ownerSession } from "../lib/qr-server";
import { uuid } from "../lib/qr-contract";
import { inboxContext, inboxQuery, inboxHref } from "../lib/finder-inbox";

export async function changeMessage(messageId: string, form: FormData) {
  const session = await ownerSession();
  if ((await headers()).get("origin") !== authConfig().origin || !uuid(messageId)) throw new Error("Invalid inbox request");
  const context = inboxContext({status:form.get("return_status")??undefined,cursor:form.get("return_cursor")??undefined,qr_id:form.get("return_qr_id")??undefined});
  const detail = (result:string) => {const q=inboxQuery(context);q.set("result",result);return `/inbox/${messageId}?${q}`;};
  const status = String(form.get("status") ?? "");
  if (!["viewed", "archived", "flagged", "deleted"].includes(status)) throw new Error("Invalid inbox request");
  if (status === "deleted" && form.get("confirm") !== "on") redirect(detail("confirm"));
  try {
    await ownerApi(session.token)(`/me/finder-messages/${messageId}`, status === "deleted" ? "DELETE" : "PATCH", status === "deleted" ? undefined : { status });
  } catch { redirect(detail("error")); }
  revalidatePath("/inbox");
  revalidatePath(`/inbox/${messageId}`);
  revalidatePath("/", "layout");
  redirect(status === "deleted" ? inboxHref(context,"deleted") : detail("saved"));
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
