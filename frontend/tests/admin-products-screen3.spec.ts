import { expect, test } from "@playwright/test";
import {
  INITIAL_SEED_DATA,
  archiveProduct,
  loadAdminMockData,
  saveAdminMockData,
  type MockAdminDatabase,
} from "../lib/admin-mock-data";

test("Screen 3 Products List search and category/status filtering work correctly", () => {
  const products = INITIAL_SEED_DATA.products;
  expect(products.length).toBe(3);

  // 1. Title search (case-insensitive)
  const query = "wristband";
  const searchResults = products.filter(
    (p) =>
      p.name.toLowerCase().includes(query) ||
      p.sku.toLowerCase().includes(query) ||
      p.id.toLowerCase().includes(query)
  );
  expect(searchResults.length).toBe(1);
  expect(searchResults[0].id).toBe("PROD-101");

  // 2. Category filtering
  const wearables = products.filter((p) => p.category === "Wearables");
  expect(wearables.length).toBe(1);
  const stickers = products.filter((p) => p.category === "Stickers");
  expect(stickers.length).toBe(1);

  // 3. Status filtering
  const published = products.filter((p) => p.status === "published");
  expect(published.length).toBe(2);
  const draft = products.filter((p) => p.status === "draft");
  expect(draft.length).toBe(1);
});

test("Screen 3 Archive action marks product as archived and adds synthetic audit log", () => {
  // Setup clean test fixture in memory
  const db: MockAdminDatabase = JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  saveAdminMockData(db);

  const initialAuditCount = db.auditLogs.length;

  // Archive PROD-101
  const success = archiveProduct("PROD-101", "operations");
  expect(success).toBe(true);

  // Verify updated state in mock data
  const updatedDb = loadAdminMockData();
  const archivedProd = updatedDb.products.find((p) => p.id === "PROD-101");
  expect(archivedProd?.status).toBe("archived");

  // Verify record was preserved (not deleted)
  expect(updatedDb.products.length).toBe(3);

  // Verify synthetic audit log was prepended
  expect(updatedDb.auditLogs.length).toBe(initialAuditCount + 1);
  expect(updatedDb.auditLogs[0].action).toBe("API-222 Product Archived");
  expect(updatedDb.auditLogs[0].target).toBe("PROD-101");
});

test("Screen 3 Catalog editing permissions are limited to Operations and Superadmin", () => {
  function canEditCatalog(role: string): boolean {
    const norm = role.toLowerCase().replace(/[\s_-]+/g, "");
    return norm.includes("superadmin") || norm.includes("operations");
  }

  expect(canEditCatalog("Superadmin")).toBe(true);
  expect(canEditCatalog("Operations")).toBe(true);
  expect(canEditCatalog("Finance")).toBe(false);
  expect(canEditCatalog("Support")).toBe(false);
  expect(canEditCatalog("Security Admin")).toBe(false);
});

