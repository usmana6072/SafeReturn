import type { Metadata } from "next";
import { getLanguage } from "../lib/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: "SafeReturn | Stay connected to what matters",
  description: "Paired Lost and Emergency QR stickers with independently editable profiles.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const language = await getLanguage();
  return <html lang={language} dir={language === "ur" ? "rtl" : "ltr"}><body>{children}</body></html>;
}
