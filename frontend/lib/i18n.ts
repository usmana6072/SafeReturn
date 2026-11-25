import { cache } from "react";
import { cookies } from "next/headers";
import en from "../messages/en.json";
import ur from "../messages/ur.json";

export const getLanguage = cache(async () => {
  return (await cookies()).get("safereturn-language")?.value === "ur" ? "ur" : "en";
});

export const messages = { en, ur };
