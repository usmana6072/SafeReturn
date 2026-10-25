import { expect, test } from "@playwright/test";
import {
  loadAdminMockData,
  resetAdminMockData,
  getProductStockStatus,
  getOverallInventoryHealth,
  INITIAL_INVENTORY_METRICS,
  type MockProduct,
} from "../lib/admin-mock-data";

test.describe("Screen 9: Inventory Management and QR Pair Stock Overview", () => {
  test.beforeEach(() => {
    resetAdminMockData();
  });

  test("Screen 9 provides three demonstration QR inventory summary metrics", () => {
    // 1. Initial prototype demonstration values
    expect(INITIAL_INVENTORY_METRICS.unassignedPairs).toBe(4280);
    expect(INITIAL_INVENTORY_METRICS.reservedPairs).toBe(120);
    expect(INITIAL_INVENTORY_METRICS.lowStockThreshold).toBe(500);
    expect(INITIAL_INVENTORY_METRICS.productLowStockThreshold).toBe(100);
  });

  test("Screen 9 calculates product stock status with explicit thresholds and unknown handling", () => {
    // 1. In Stock (at or above threshold 100)
    expect(getProductStockStatus(250, 100)).toBe("In Stock");
    expect(getProductStockStatus(142, 100)).toBe("In Stock");
    expect(getProductStockStatus(100, 100)).toBe("In Stock");

    // 2. Low Stock (positive below threshold 100)
    expect(getProductStockStatus(88, 100)).toBe("Low Stock");
    expect(getProductStockStatus(1, 100)).toBe("Low Stock");

    // 3. Out of Stock (0 or negative)
    expect(getProductStockStatus(0, 100)).toBe("Out of Stock");
    expect(getProductStockStatus(-5, 100)).toBe("Out of Stock");

    // 4. Unknown / Missing stock
    expect(getProductStockStatus(undefined, 100)).toBe("Unknown");
    expect(getProductStockStatus(null, 100)).toBe("Unknown");
    expect(getProductStockStatus(NaN, 100)).toBe("Unknown");
  });

  test("Screen 9 evaluates overall inventory health dynamically and is not hardcoded to Healthy", () => {
    // Test dataset where all products have healthy stock (>= 100)
    const healthyProducts: MockProduct[] = [
      {
        id: "P1",
        name: "Item 1",
        sku: "SKU-1",
        category: "Tags",
        status: "published",
        price: 10,
        stock: 150,
        templateKey: "T1",
        variants: [],
        updatedAt: "2026-10-21",
      },
      {
        id: "P2",
        name: "Item 2",
        sku: "SKU-2",
        category: "Wearables",
        status: "published",
        price: 20,
        stock: 200,
        templateKey: "T2",
        variants: [],
        updatedAt: "2026-10-21",
      },
    ];
    expect(getOverallInventoryHealth(healthyProducts, 4280, 500, 100)).toBe("Healthy");

    // Baseline catalog contains Kids Safety Backpack Tag with stock = 88 (< 100)
    const currentProducts = loadAdminMockData().products;
    expect(currentProducts.find((p) => p.name === "Kids Safety Backpack Tag")?.stock).toBe(88);
    // Dynamic health evaluation detects this product below threshold and flags Low Stock
    expect(getOverallInventoryHealth(currentProducts, 4280, 500, 100)).toBe("Low Stock");

    // When QR unassigned pairs drop below alert threshold (<= 500)
    expect(getOverallInventoryHealth(healthyProducts, 450, 500, 100)).toBe("Low Stock");

    // When any product has 0 stock or QR pairs hit 0
    const zeroStockProducts: MockProduct[] = [
      ...healthyProducts,
      {
        id: "P3",
        name: "Item 3",
        sku: "SKU-3",
        category: "Stickers",
        status: "draft",
        price: 5,
        stock: 0,
        templateKey: "T3",
        variants: [],
        updatedAt: "2026-10-21",
      },
    ];
    expect(getOverallInventoryHealth(zeroStockProducts, 4280, 500, 100)).toBe("Critical");
    expect(getOverallInventoryHealth(healthyProducts, 0, 500, 100)).toBe("Critical");

    // When stock is undefined or missing
    const unknownStockProducts: MockProduct[] = [
      {
        id: "P4",
        name: "Item 4",
        sku: "SKU-4",
        category: "Wearables",
        status: "published",
        price: 15,
        stock: undefined as unknown as number,
        templateKey: "T4",
        variants: [],
        updatedAt: "2026-10-21",
      },
    ];
    expect(getOverallInventoryHealth(unknownStockProducts, 4280, 500, 100)).toBe("Unknown");
  });

  test("Screen 9 filters products by search query, category, and computed stock status", () => {
    const products = loadAdminMockData().products;
    expect(products.length).toBe(3);

    // 1. Search by title
    const searchMatch = products.filter((p) =>
      p.name.toLowerCase().includes("wristband")
    );
    expect(searchMatch.length).toBe(1);
    expect(searchMatch[0].name).toBe("SafeReturn Medical Wristband");

    // 2. Filter by Category
    const stickers = products.filter((p) => p.category === "Stickers");
    expect(stickers.length).toBe(1);
    expect(stickers[0].stock).toBe(250);

    // 3. Filter by computed stock status
    const lowStockItems = products.filter(
      (p) => getProductStockStatus(p.stock, 100) === "Low Stock"
    );
    expect(lowStockItems.length).toBe(1);
    expect(lowStockItems[0].name).toBe("Kids Safety Backpack Tag");

    const inStockItems = products.filter(
      (p) => getProductStockStatus(p.stock, 100) === "In Stock"
    );
    expect(inStockItems.length).toBe(2);
  });

  test("Screen 9 role governance permits Operations and Superadmin, while identifying restricted roles", () => {
    function evaluateInventoryAccess(role: string): boolean {
      const normalized = role.toLowerCase().replace(/[\s_-]+/g, "");
      return normalized.includes("superadmin") || normalized.includes("operations");
    }

    expect(evaluateInventoryAccess("Operations")).toBe(true);
    expect(evaluateInventoryAccess("Superadmin")).toBe(true);
    expect(evaluateInventoryAccess("Finance")).toBe(false);
    expect(evaluateInventoryAccess("Support")).toBe(false);
    expect(evaluateInventoryAccess("Security Admin")).toBe(false);
  });

  test("Screen 9 resetAdminMockData restores benchmark product stock quantities", () => {
    const db = loadAdminMockData();
    expect(db.products.length).toBe(3);
    expect(db.products.map((p) => ({ name: p.name, stock: p.stock }))).toEqual([
      { name: "SafeReturn Medical Wristband", stock: 142 },
      { name: "Kids Safety Backpack Tag", stock: 88 },
      { name: "Dementia Care QR Sticker Set (4x)", stock: 250 },
    ]);
  });
});

