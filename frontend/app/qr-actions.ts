"use server";

import { randomUUID } from "node:crypto";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { authConfig } from "../lib/auth/config";
import { ownerApi, ownerSession } from "../lib/qr-server";
import { ApiError } from "../lib/api/transport";
import { Intent, uuid } from "../lib/qr-contract";
import { ActivationTicket, ScanTicket, readTicket, ticket } from "../lib/scan-ticket";

export type QRState = { status: "idle" | "saved" | "error"; reason?: "stale" | "denied" | "limited" | "invalid" | "unavailable" };
const cookieOptions = { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax" as const, path: "/", maxAge: 900 };
async function origin() {
  if ((await headers()).get("origin") !== authConfig().origin) throw new ApiError("http", 403);
}
function errorState(error: unknown): QRState {
  const status = error instanceof ApiError ? error.status : undefined;
  return { status: "error", reason: status === 412 ? "stale" : status === 429 ? "limited"
    : status === 400 || status === 422 ? "invalid" : status && status < 500 ? "denied" : "unavailable" };
}
export async function beginScan(token: string, _state: QRState, _form: FormData): Promise<QRState> {
  try {
    await origin();
    if (!/^[A-Za-z0-9_-]{1,80}$/.test(token)) return { status: "error", reason: "invalid" };
    await ownerApi()(`/public/qr/${token}/activation-context`);
    const jar = await cookies();
    jar.set("sr-scan", ticket({ token, until: Date.now() + 900000 }, "scan"), cookieOptions);
    jar.delete("sr-activation");
  } catch (error) { return errorState(error); }
  redirect("/activate");
}
export async function prepareActivation(_state: QRState, form: FormData): Promise<QRState> {
  try {
    await origin();
    const session = await ownerSession(), jar = await cookies();
    const scan = readTicket<ScanTicket>(jar.get("sr-scan")?.value, "scan");
    if (!scan) return { status: "error", reason: "denied" };
    const secret = String(form.get("activation_secret") ?? "");
    if (secret && (secret.length < 12 || secret.length > 256)) return { status: "error", reason: "invalid" };
    const result = await ownerApi(session.token)<Intent>("/me/tag-pairs/activation-intents", "POST", {
      scanned_token: scan.token, ...(secret ? { activation_secret: secret } : {}) });
    if (!uuid(result.intent_id) || !uuid(result.pair_id)) throw new Error("contract");
    const until = Math.min(Date.parse(result.expires_at), Date.now() + 900000);
    if (!Number.isFinite(until) || until <= Date.now()) throw new Error("expired");
    jar.set("sr-activation", ticket({ actor: session.user.id, intent: result.intent_id,
      pair: result.pair_id, key: randomUUID(), until }, "activation"), cookieOptions);
  } catch (error) { return errorState(error); }
  redirect("/activate");
}
export async function activatePair(_state: QRState, form: FormData): Promise<QRState> {
  let pair = "";
  try {
    await origin();
    const session = await ownerSession(), jar = await cookies();
    const pending = readTicket<ActivationTicket>(jar.get("sr-activation")?.value, "activation");
    if (!pending || pending.actor !== session.user.id || form.get("confirm") !== "on") return { status: "error", reason: "denied" };
    await ownerApi(session.token)("/me/tag-pairs/activations", "POST", { intent_id: pending.intent, confirm: true }, undefined, pending.key);
    pair = pending.pair;
    jar.delete("sr-activation"); jar.delete("sr-scan");
    revalidatePath("/dashboard");
  } catch (error) { return errorState(error); }
  redirect(`/kits/${pair}?activated=1`);
}
export async function restartActivation() {
  await origin();
  (await cookies()).delete("sr-activation");
  redirect("/activate");
}

export async function saveQR(qrId: string, kind: "lost" | "ice" | "preferences" | "contact" | "privacy", _state: QRState, form: FormData): Promise<QRState> {
  try {
    await origin();
    const session = await ownerSession();
    if (!uuid(qrId)) return { status: "error", reason: "invalid" };
    const version = Number(form.get("version"));
    if (!Number.isSafeInteger(version) || version < 0) return { status: "error", reason: "invalid" };
    const body: Record<string, unknown> = {};
    const checked = (name: string) => form.get(name) === "on";
    const value = (name: string) => String(form.get(name) ?? "").trim();
    let path = `/me/qr/${qrId}/`, method = "PUT";
    if (kind === "privacy") {
      const scope = value("scope");
      if (!["ice", "preferences"].includes(scope)) return { status: "error", reason: "invalid" };
      path += scope === "ice" ? "ice-profile" : "contact-preferences";
      if (scope === "ice") body.published = false;
      else body.whatsapp_enabled = false;
    } else if (kind === "lost" || kind === "ice") {
      path += kind === "lost" ? "lost-profile" : "ice-profile";
      const fields = kind === "lost" ? ["item_label", "description", "reward_text", "return_instructions"]
        : ["display_name", "blood_group", "emergency_instructions"];
      fields.forEach(name => { body[name] = value(name) || null; });
      body.published = checked("published");
      if (kind === "ice") {
        // Empty unchanged field preserves a retained/redacted encrypted value.
        if (checked("clear_medical_notes")) body.medical_notes = null;
        else if (value("medical_notes")) body.medical_notes = value("medical_notes");
        body.show_medical_notes = checked("show_medical_notes");
        body.publication_consent_accepted = checked("consent");
        body.publication_consent_version = "ice-public-v1";
      }
    } else if (kind === "preferences") {
      path += "contact-preferences";
      body.whatsapp_enabled = checked("whatsapp_enabled");
      if (value("whatsapp_phone")) body.whatsapp_phone = value("whatsapp_phone");
      body.public_disclosure_consent = checked("consent"); body.consent_version = "wa-public-v1";
    } else if (kind === "contact") {
      const cid = value("contact_id");
      if (cid && !uuid(cid)) return { status: "error", reason: "invalid" };
      path += `ice-contacts${cid ? `/${cid}` : ""}`;
      if (checked("remove")) {
        if (!cid || !checked("confirm_remove")) return { status: "error", reason: "invalid" };
        method = "DELETE";
      } else {
        method = cid ? "PATCH" : "POST";
        body.relationship_label = value("relationship_label"); body.display_name = value("display_name") || null;
        if (value("phone")) body.phone = value("phone");
        body.published = checked("published"); body.display_order = Number(value("display_order") || "0");
        body.publication_consent_accepted = checked("consent"); body.publication_consent_version = "ice-contact-v1";
      }
    } else return { status: "error", reason: "invalid" };
    await ownerApi(session.token)(path, method, method === "DELETE" ? undefined : body, version);
    revalidatePath(`/my-qr/${qrId}`); revalidatePath("/dashboard"); revalidatePath("/my-qr"); revalidatePath("/kits");
  } catch (error) { return errorState(error); }
  redirect(`/my-qr/${qrId}?saved=1`);
}
