import type { Metadata } from "next";
import { getLanguage } from "../lib/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: "SafeReturn | Stay connected to what matters",
  description: "Paired Lost and Emergency QR stickers with independently editable profiles.",
  applicationName: "SafeReturn",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "32x32", type: "image/x-icon" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
  manifest: "/manifest.webmanifest",
  openGraph: {
    title: "SafeReturn | Stay connected to what matters",
    description: "Paired Lost and Emergency QR stickers with independently editable profiles.",
    siteName: "SafeReturn",
    type: "website",
  },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const language = await getLanguage();
  return <html lang={language} dir={language === "ur" ? "rtl" : "ltr"}><body>{children}</body></html>;
}
