"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export async function changeLanguage(formData: FormData) {
  const language = formData.get("language");
  if (language !== "en" && language !== "ur") return;
  (await cookies()).set("safereturn-language", language, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  });
  redirect("/");
}
