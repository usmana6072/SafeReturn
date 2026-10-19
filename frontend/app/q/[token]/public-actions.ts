"use server";
import { randomUUID } from "node:crypto";
import { headers } from "next/headers";
import { ownerApi } from "../../../lib/qr-server";
import { ApiError } from "../../../lib/api/transport";
import { uuid } from "../../../lib/qr-contract";

async function input(token: string, form: FormData) {
  if ((await headers()).get("origin") !== process.env.SAFERETURN_WEB_ORIGIN || !/^[A-Za-z0-9_-]{20,80}$/.test(token)) throw new Error("Invalid request");
  const proof = form.get("cf-turnstile-response");
  if (typeof proof !== "string" || !proof || proof.length > 2048) throw new Error("Verification required");
  return proof;
}
function unavailable(error: unknown) {
  return JSON.stringify({status: error instanceof ApiError && error.status === 429 ? "limited" : "unavailable",attempt:randomUUID()});
}
export async function revealContact(token: string, _state: string, form: FormData) {
  try {
    const proof = await input(token,form), contact = String(form.get("contact_id") ?? "");
    if (!uuid(contact)) throw new Error("Invalid contact");
    const result = await ownerApi()<{phone:string;tel_uri:string}>(`/public/qr/${token}/contact-reveals`,"POST",{contact_id:contact,turnstile_token:proof});
    if (!/^\+[1-9][0-9]{7,14}$/.test(result.phone) || result.tel_uri !== `tel:${result.phone}`) throw new Error("Invalid response");
    return JSON.stringify({status:"revealed",phone:result.phone,tel_uri:result.tel_uri});
  } catch(error) { return unavailable(error); }
}
export async function openWhatsApp(token: string, _state: string, form: FormData) {
  try {
    const proof = await input(token,form);
    const result = await ownerApi()<{url:string;disclosure:string}>(`/public/qr/${token}/whatsapp-link`,"POST",{intent:"open_chat",turnstile_token:proof});
    const url = new URL(result.url);
    if (url.protocol !== "https:" || url.hostname !== "wa.me" || url.port || url.username || url.password || !/^\/[1-9][0-9]{7,14}$/.test(url.pathname)) throw new Error("Invalid destination");
    return JSON.stringify({status:"ready",url:result.url});
  } catch(error) { return unavailable(error); }
}
