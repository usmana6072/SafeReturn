import type { MetadataRoute } from "next";

function getBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_SITE_URL || process.env.SAFERETURN_WEB_ORIGIN;
  if (envUrl && !envUrl.includes("localhost")) {
    return envUrl.replace(/\/$/, "");
  }
  return "https://safe-return-frontend.vercel.app";
}

export default function robots(): MetadataRoute.Robots {
  const baseUrl = getBaseUrl();

  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/shop", "/shop/*", "/help", "/login", "/signup"],
        disallow: [
          "/admin",
          "/admin/*",
          "/dashboard",
          "/dashboard/*",
          "/account",
          "/account/*",
          "/my-qr",
          "/my-qr/*",
          "/orders",
          "/orders/*",
          "/shipments",
          "/shipments/*",
          "/inbox",
          "/inbox/*",
          "/settings",
          "/settings/*",
          "/checkout",
          "/checkout/*",
          "/cart",
          "/auth/*",
          "/api/*",
          "/q/*",
        ],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
