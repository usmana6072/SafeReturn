import type { MetadataRoute } from "next";
import { getCatalog } from "../lib/catalog";

function getBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_SITE_URL || process.env.SAFERETURN_WEB_ORIGIN;
  if (envUrl && !envUrl.includes("localhost")) {
    return envUrl.replace(/\/$/, "");
  }
  return "https://safe-return-frontend.vercel.app";
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = getBaseUrl();
  const currentDate = new Date();

  // Core static public storefront pages
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: `${baseUrl}/`,
      lastModified: currentDate,
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${baseUrl}/shop`,
      lastModified: currentDate,
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: `${baseUrl}/help`,
      lastModified: currentDate,
      changeFrequency: "weekly",
      priority: 0.7,
    },
    {
      url: `${baseUrl}/login`,
      lastModified: currentDate,
      changeFrequency: "monthly",
      priority: 0.5,
    },
    {
      url: `${baseUrl}/signup`,
      lastModified: currentDate,
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];

  // Dynamic product detail pages
  let productPages: MetadataRoute.Sitemap = [];
  try {
    const catalog = await getCatalog();
    if (catalog && !catalog.unavailable && Array.isArray(catalog.products)) {
      const seenSkus = new Set<string>();
      for (const product of catalog.products) {
        for (const variant of product.variants ?? []) {
          if (variant.sku && !seenSkus.has(variant.sku)) {
            seenSkus.add(variant.sku);
            productPages.push({
              url: `${baseUrl}/shop/${encodeURIComponent(variant.sku)}`,
              lastModified: currentDate,
              changeFrequency: "weekly",
              priority: 0.8,
            });
          }
        }
      }
    }
  } catch {
    // If catalog fetch is unavailable at build or offline, static pages are returned
  }

  return [...staticPages, ...productPages];
}
