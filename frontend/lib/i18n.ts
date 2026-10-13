import { cookies } from "next/headers";
import en from "../messages/en.json";
import ur from "../messages/ur.json";

export async function getLanguage() {
  return (await cookies()).get("safereturn-language")?.value === "ur" ? "ur" : "en";
}

export const messages = { en, ur };
