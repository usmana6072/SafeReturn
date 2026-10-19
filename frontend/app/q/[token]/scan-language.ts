"use server";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
export async function changeScanLanguage(form: FormData) {
  const language = form.get("language"), token = form.get("token");
  if ((language !== "en" && language !== "ur") || typeof token !== "string" || !/^[A-Za-z0-9_-]{20,80}$/.test(token)) return;
  (await cookies()).set("safereturn-language", language, {
    httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 31536000,
  });
  redirect(`/q/${token}`);
}
