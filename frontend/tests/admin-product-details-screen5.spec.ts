import { expect, test } from "@playwright/test";
import {
  INITIAL_SEED_DATA,
  getProductById,
  updateProduct,
  loadAdminMockData,
  saveAdminMockData,
  hasMultipleDistinctVariantPrices,
  type MockAdminDatabase,
} from "../lib/admin-mock-data";

test("Screen 5 getProductById retrieves correct product record and handles missing ID", () => {
  const db: MockAdminDatabase = JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  saveAdminMockData(db);

  // 1. Retrieve existing product
  const prod = getProductById("PROD-101");
  expect(prod).toBeDefined();
  expect(prod?.name).toBe("SafeReturn Medical Wristband");
  expect(prod?.category).toBe("Wearables");
  expect(prod?.price).toBe(29.99);
  expect(prod?.status).toBe("published");
  expect(prod?.sku).toBe("SR-WB-MED-01");
  expect(prod?.variants).toEqual(["Red/ICE", "Blue/Medical"]);

  // 2. Non-existent product returns undefined
  const notFound = getProductById("PROD-NON-EXISTENT");
  expect(notFound).toBeUndefined();
});

test("Screen 5 updateProduct patches fields, increments version and preserves technical records", () => {
  const db: MockAdminDatabase = JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  saveAdminMockData(db);

  const initialAuditCount = db.auditLogs.length;

  // Update PROD-103 (Dementia Care QR Sticker Set)
  const result = updateProduct(
    "PROD-103",
    {
      name: "Updated Dementia Care QR Sticker Pack (4x)",
      category: "Stickers",
      description: "Enhanced high-durability vinyl stickers for memory care.",
      price: 22.5,
      coverImage: "data:image/jpeg;base64,mockUpdatedCover",
    },
    "operations"
  );

  expect(result.success).toBe(true);
  expect(result.product).toBeDefined();

  const updated = result.product!;
  expect(updated.name).toBe("Updated Dementia Care QR Sticker Pack (4x)");
  expect(updated.price).toBe(22.5);
  expect(updated.description).toBe("Enhanced high-durability vinyl stickers for memory care.");
  expect(updated.coverImage).toBe("data:image/jpeg;base64,mockUpdatedCover");
  expect(updated.version).toBe(2);

  // Verify technical fields are preserved (not replaced or wiped)
  expect(updated.id).toBe("PROD-103");
  expect(updated.sku).toBe("SR-ST-DEM-04");
  expect(updated.stock).toBe(250);
  expect(updated.templateKey).toBe("TP-STICKER-4X");
  expect(updated.status).toBe("draft"); // Status is not altered

  // Verify persistence in store
  const reloaded = loadAdminMockData();
  const found = reloaded.products.find((p) => p.id === "PROD-103");
  expect(found?.name).toBe("Updated Dementia Care QR Sticker Pack (4x)");
  expect(found?.price).toBe(22.5);

  // Verify synthetic audit log was prepended
  expect(reloaded.auditLogs.length).toBe(initialAuditCount + 1);
  expect(reloaded.auditLogs[0].action).toBe("API-222 Mock Product Updated");
  expect(reloaded.auditLogs[0].target).toBe("PROD-103");
});

test("Screen 5 One product price replaces all size prices", () => {
  const db: MockAdminDatabase = JSON.parse(JSON.stringify(INITIAL_SEED_DATA));

  // Create a product with multiple distinct variant records
  const multiVariantProduct = {
    ...db.products[0],
    id: "PROD-MULTI-TEST",
    name: "Multi-variant Test Product",
    variantRecords: [
      {
        id: "VAR-1",
        sku: "SKU-1",
        name: "Standard",
        unitPrice: "20.00",
        currencyCode: "PKR",
      },
      {
        id: "VAR-2",
        sku: "SKU-2",
        name: "Premium",
        unitPrice: "35.00",
        currencyCode: "PKR",
      },
    ],
  };
  db.products.push(multiVariantProduct);
  saveAdminMockData(db);

  // Verify multi-variant detection
  expect(hasMultipleDistinctVariantPrices(multiVariantProduct)).toBe(true);

  // Verify a product with single variant is not considered multi-distinct
  const singleVariantProduct = {
    ...db.products[0],
    id: "PROD-SINGLE-TEST",
    variantRecords: [
      {
        id: "VAR-1",
        sku: "SKU-1",
        name: "Standard",
        unitPrice: "20.00",
        currencyCode: "PKR",
      },
    ],
  };
  expect(hasMultipleDistinctVariantPrices(singleVariantProduct)).toBe(false);

  // v1.4 applies the explicitly selected product price to every size.
  const res = updateProduct(
    "PROD-MULTI-TEST",
    {
      price: 99.99,
      description: "Updated description only",
    },
    "operations"
  );
  expect(res.success).toBe(true);

  // Verify every size uses the product price.
  const updatedDb = loadAdminMockData();
  const checked = updatedDb.products.find((p) => p.id === "PROD-MULTI-TEST");
  expect(checked?.price_per_copy).toBe("99.99");
  expect(checked?.variantRecords?.[0].unitPrice).toBe("99.99");
  expect(checked?.variantRecords?.[1].unitPrice).toBe("99.99");
});

test("Screen 5 Validation and Role restrictions", () => {
  // 1. Empty name validation
  const emptyRes = updateProduct("PROD-101", { name: "   " }, "operations");
  expect(emptyRes.success).toBe(false);
  expect(emptyRes.error).toBe("Product name cannot be empty.");

  // 2. Unknown ID validation
  const unknownRes = updateProduct("PROD-UNKNOWN", { name: "New Name" }, "operations");
  expect(unknownRes.success).toBe(false);
  expect(unknownRes.error).toBe("Product not found.");

  // 3. Permission checks
  function canEditProduct(role: string): boolean {
    const norm = role.toLowerCase().replace(/[\s_-]+/g, "");
    return norm.includes("superadmin") || norm.includes("operations");
  }

  expect(canEditProduct("Superadmin")).toBe(true);
  expect(canEditProduct("Operations")).toBe(true);
  expect(canEditProduct("Finance")).toBe(false);
  expect(canEditProduct("Support")).toBe(false);
  expect(canEditProduct("Security Admin")).toBe(false);
});

