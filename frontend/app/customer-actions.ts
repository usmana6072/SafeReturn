"use server";
import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";

export async function customerLanguage(form: FormData) {
  const language = form.get("language");
  if (language !== "en" && language !== "ur") return;
  (await cookies()).set("safereturn-language", language, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 31536000 });
  revalidatePath("/", "layout");
}
