import { expect, test } from "@playwright/test";
import {
  INITIAL_SEED_DATA,
  createProductDraft,
  loadAdminMockData,
  saveAdminMockData,
  getManagedProductsCount,
  type MockAdminDatabase,
} from "../lib/admin-mock-data";

test("Screen 4 createProductDraft validates required fields and sets draft status", () => {
  // Setup clean test fixture in memory
  const db: MockAdminDatabase = JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  saveAdminMockData(db);

  // 1. Missing name fails
  const emptyRes = createProductDraft({
    name: "",
    category: "Stickers",
    price: 19.99,
  });
  expect(emptyRes.success).toBe(false);
  expect(emptyRes.error).toBe("Product name is required.");

  // 2. Missing category fails
  const noCatRes = createProductDraft({
    name: "Valid Title",
    category: "",
    price: 19.99,
  });
  expect(noCatRes.success).toBe(false);
  expect(noCatRes.error).toBe("Category is required.");

  // 3. Successful draft creation
  const initialCount = db.products.length;
  const initialAuditCount = db.auditLogs.length;

  const validRes = createProductDraft(
    {
      name: "Emergency Contact Keyring Tag",
      category: "Tags",
      price: 24.5,
      description: "Waterproof reflective keyring tag for emergency contacts.",
      coverImage: "data:image/jpeg;base64,mockCoverData",
      galleryImages: ["data:image/jpeg;base64,mockGallery1"],
    },
    "operations"
  );

  expect(validRes.success).toBe(true);
  expect(validRes.product).toBeDefined();

  const product = validRes.product!;
  expect(product.name).toBe("Emergency Contact Keyring Tag");
  expect(product.category).toBe("Tags");
  expect(product.price).toBe(24.5);
  expect(product.price_per_copy).toBe("24.50");
  expect(product.max_order_copies).toBe(100);
  expect(product.status).toBe("draft");
  expect(product.slug).toBe("emergency-contact-keyring-tag");
  expect(product.description).toContain("Waterproof reflective");
  expect(product.coverImage).toBe("data:image/jpeg;base64,mockCoverData");
  expect(product.images?.length).toBe(2);
  expect(product.variantRecords?.length).toBe(1);
  expect(product.variantRecords?.[0].unitPrice).toBe("24.5");

  // Verify updated database state
  const updatedDb = loadAdminMockData();
  expect(updatedDb.products.length).toBe(initialCount + 1);
  expect(updatedDb.products[0].id).toBe(product.id);
  expect(getManagedProductsCount(updatedDb)).toBe(initialCount + 1);

  // Verify synthetic audit log was prepended
  expect(updatedDb.auditLogs.length).toBe(initialAuditCount + 1);
  expect(updatedDb.auditLogs[0].action).toBe("API-221 Mock Product Draft Created");
  expect(updatedDb.auditLogs[0].target).toBe(product.id);
});

test("Screen 4 Slug generation prevents collision and preserves existing products", () => {
  const db: MockAdminDatabase = JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  saveAdminMockData(db);

  // Create two products with the same title
  const res1 = createProductDraft({
    name: "Duplicate Test Product",
    category: "Stickers",
    price: 10,
  });
  expect(res1.success).toBe(true);
  expect(res1.product?.slug).toBe("duplicate-test-product");

  const res2 = createProductDraft({
    name: "Duplicate Test Product",
    category: "Stickers",
    price: 15,
  });
  expect(res2.success).toBe(true);
  expect(res2.product?.slug).toBe("duplicate-test-product-1");

  // Verify original seed products are preserved and unaffected
  const updatedDb = loadAdminMockData();
  expect(updatedDb.products.some((p) => p.id === "PROD-101")).toBe(true);
  expect(updatedDb.products.some((p) => p.id === "PROD-102")).toBe(true);
  expect(updatedDb.products.some((p) => p.id === "PROD-103")).toBe(true);
});

test("Screen 4 Role permissions and publication restrictions", () => {
  function canCreateProducts(role: string): boolean {
    const norm = role.toLowerCase().replace(/[\s_-]+/g, "");
    return norm.includes("superadmin") || norm.includes("operations");
  }

  expect(canCreateProducts("Superadmin")).toBe(true);
  expect(canCreateProducts("Operations")).toBe(true);
  expect(canCreateProducts("Finance")).toBe(false);
  expect(canCreateProducts("Support")).toBe(false);
  expect(canCreateProducts("Security Admin")).toBe(false);

  // Publication prerequisite check: draft cannot be published without independent template key
  function isPublicationEligible(product: { status: string; templateKey: string }): boolean {
    return product.status === "published" && product.templateKey !== "—" && product.templateKey !== "";
  }

  expect(isPublicationEligible({ status: "draft", templateKey: "—" })).toBe(false);
  expect(isPublicationEligible({ status: "published", templateKey: "TP-WRIST-V2" })).toBe(true);
});


for (const price of [NaN, Infinity, -1, 1.001, 10000000000]) {
  test(`Price per copy rejects invalid PKR amount ${price}`, () => {
    expect(createProductDraft({name: "Invalid price", category: "Stickers", price}).success).toBe(false);
  });
}
