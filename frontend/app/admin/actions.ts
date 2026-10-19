"use server";
import { headers, cookies } from "next/headers";
import { redirect } from "next/navigation";
import { authConfig } from "../../lib/auth/config";
import { mfaReturn } from "../../lib/auth/mfa-return";
import { staffSecurity } from "../../lib/auth/staff";
export async function adminLanguage(form: FormData) {
  if ((await headers()).get("origin") !== authConfig().origin) return;
  const language = form.get("language");
  if (language !== "en" && language !== "ur") return;
  await staffSecurity();
  (await cookies()).set("safereturn-language", language, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 31536000 });
  redirect(mfaReturn(form.get("returnTo")));
}
