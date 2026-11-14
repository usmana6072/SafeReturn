import { test, expect } from "@playwright/test";
import {
  loadAdminMockData,
  saveAdminMockData,
  resetAdminMockData,
  getQRBatches,
  getQRBatchById,
  createDemoQRBatch,
  INITIAL_SEED_DATA,
  type MockQRBatch,
} from "../lib/admin-mock-data";
import { DEMO_ROLES, DEMO_PERMISSIONS } from "../lib/admin-navigation";

test.describe("Screen 10: QR Batch Generation and Batch Details", () => {
  test.beforeEach(() => {
    resetAdminMockData();
  });

  test.afterEach(() => {
    resetAdminMockData();
  });

  test("Screen 10 loads benchmark QR batch fixtures matching prototype specifications", () => {
    const batches = getQRBatches();
    expect(batches.length).toBeGreaterThanOrEqual(2);

    const b9 = batches.find((b) => b.id === "BATCH-2026-09");
    expect(b9).toBeDefined();
    expect(b9?.size).toBe(1000);
    expect(b9?.pairsCount).toBe(500);
    expect(b9?.generatedAt).toBe("2026-10-01");
    expect(b9?.status).toBe("QA Passed");
    expect(b9?.exported).toBe(true);

    const b10 = batches.find((b) => b.id === "BATCH-2026-10");
    expect(b10).toBeDefined();
    expect(b10?.size).toBe(500);
    expect(b10?.pairsCount).toBe(250);
    expect(b10?.generatedAt).toBe("2026-10-15");
    expect(b10?.status).toBe("In QA");
    expect(b10?.exported).toBe(false);
  });

  test("Screen 10 enforces exact 1 pair = 2 tags mathematical relationship", () => {
    const batches = getQRBatches();
    batches.forEach((b) => {
      expect(b.size).toBe(b.pairsCount * 2);
    });
  });

  test("Screen 10 search by Batch ID and QA status filtering work case-insensitively", () => {
    const batches = getQRBatches();

    // 1. Search by batch ID substring
    const query = "2026-09";
    const searchResults = batches.filter((b) =>
      b.id.toLowerCase().includes(query.toLowerCase())
    );
    expect(searchResults.length).toBe(1);
    expect(searchResults[0].id).toBe("BATCH-2026-09");

    // 2. Filter by QA Status
    const passedBatches = batches.filter((b) => b.status === "QA Passed");
    expect(passedBatches.length).toBe(1);
    expect(passedBatches[0].id).toBe("BATCH-2026-09");

    const inQABatches = batches.filter((b) => b.status === "In QA");
    expect(inQABatches.length).toBe(1);
    expect(inQABatches[0].id).toBe("BATCH-2026-10");
  });

  test("Screen 10 createDemoQRBatch validates pair bounds and rejects invalid inputs", () => {
    // 0 pairs rejected
    const rZero = createDemoQRBatch({ pairsCount: 0 });
    expect(rZero.success).toBe(false);
    if (!rZero.success) {
      expect(rZero.error).toContain("1 and 1,000");
    }

    // Negative pairs rejected
    const rNeg = createDemoQRBatch({ pairsCount: -5 });
    expect(rNeg.success).toBe(false);

    // Over 1000 pairs rejected
    const rOver = createDemoQRBatch({ pairsCount: 1001 });
    expect(rOver.success).toBe(false);

    // Non-integer pairs rejected
    const rFloat = createDemoQRBatch({ pairsCount: 12.5 });
    expect(rFloat.success).toBe(false);

    // Duplicate custom ID rejected
    const rDup = createDemoQRBatch({
      pairsCount: 100,
      batchLabel: "BATCH-2026-09",
    });
    expect(rDup.success).toBe(false);
    if (!rDup.success) {
      expect(rDup.error).toContain("already exists");
    }

    // Invalid batch ID characters rejected
    const rBadChars = createDemoQRBatch({
      pairsCount: 100,
      batchLabel: "BAD BATCH!@#",
    });
    expect(rBadChars.success).toBe(false);
  });

  test("Screen 10 creates synthetic demo batch with initial Awaiting QA status and audit logging", () => {
    const result = createDemoQRBatch({
      pairsCount: 300,
      batchLabel: "BATCH-2026-11",
      printMaterial: "synthetic-waterproof",
      actor: "operations_staff",
    });

    expect(result.success).toBe(true);
    if (!result.success) return;

    const created = result.batch;
    expect(created.id).toBe("BATCH-2026-11");
    expect(created.pairsCount).toBe(300);
    expect(created.size).toBe(600); // 300 * 2
    expect(created.status).toBe("Awaiting QA");
    expect(created.exported).toBe(false);
    expect(created.isDemo).toBe(true);

    // Verify persistence
    const loaded = getQRBatchById("BATCH-2026-11");
    expect(loaded).toBeDefined();
    expect(loaded?.pairsCount).toBe(300);
    expect(loaded?.size).toBe(600);

    // Verify audit log was recorded
    const db = loadAdminMockData();
    const log = db.auditLogs.find(
      (l) => l.action === "API-090 Demo Batch Created" && l.target === "BATCH-2026-11"
    );
    expect(log).toBeDefined();
    expect(log?.actor).toBe("operations_staff");
    expect(log?.details).toContain("300 pairs");
  });

  test("Screen 10 batch creation STRICTLY preserves Screen 9 product inventory without modification", () => {
    const dbBefore = loadAdminMockData();
    const backpackStockBefore = dbBefore.products.find(
      (p) => p.sku === "SR-TG-KID-02"
    )?.stock;
    const wristbandStockBefore = dbBefore.products.find(
      (p) => p.sku === "SR-WB-MED-01"
    )?.stock;

    // Create a demo batch of 500 pairs
    const result = createDemoQRBatch({ pairsCount: 500 });
    expect(result.success).toBe(true);

    // Verify product inventory in Screen 9 was not modified
    const dbAfter = loadAdminMockData();
    const backpackStockAfter = dbAfter.products.find(
      (p) => p.sku === "SR-TG-KID-02"
    )?.stock;
    const wristbandStockAfter = dbAfter.products.find(
      (p) => p.sku === "SR-WB-MED-01"
    )?.stock;

    expect(backpackStockAfter).toBe(backpackStockBefore);
    expect(wristbandStockAfter).toBe(wristbandStockBefore);
  });

  test("Screen 10 batch details resolves existing batches and handles missing batches safely", () => {
    // Existing batch lookup
    const b9 = getQRBatchById("BATCH-2026-09");
    expect(b9).toBeDefined();
    expect(b9?.id).toBe("BATCH-2026-09");
    expect(b9?.status).toBe("QA Passed");

    // Case-insensitive lookup
    const b9Lower = getQRBatchById("batch-2026-09");
    expect(b9Lower).toBeDefined();
    expect(b9Lower?.id).toBe("BATCH-2026-09");

    // Missing batch lookup returns undefined
    const missing = getQRBatchById("BATCH-DOES-NOT-EXIST");
    expect(missing).toBeUndefined();
  });

  test("Screen 10 role permissions restrict unauthorized roles from accessing QR Batches", () => {
    expect(DEMO_PERMISSIONS.Operations.pages).toContain("qr_batches");
    expect(DEMO_PERMISSIONS.Superadmin.pages).toContain("qr_batches");

    expect(DEMO_PERMISSIONS.Finance.pages).not.toContain("qr_batches");
    expect(DEMO_PERMISSIONS.Support.pages).not.toContain("qr_batches");
    expect(DEMO_PERMISSIONS["Security Admin"].pages).not.toContain("qr_batches");
  });

  test("Screen 10 resetAdminMockData cleanly restores original benchmark batches", () => {
    // Add custom demo batch
    createDemoQRBatch({ pairsCount: 400, batchLabel: "BATCH-TEST-CUSTOM" });
    expect(getQRBatchById("BATCH-TEST-CUSTOM")).toBeDefined();

    // Reset demo data
    resetAdminMockData();

    // Verify custom batch is removed and original 2 batches remain
    expect(getQRBatchById("BATCH-TEST-CUSTOM")).toBeUndefined();
    const batches = getQRBatches();
    expect(batches.length).toBe(2);
    expect(batches.map((b) => b.id)).toEqual(["BATCH-2026-09", "BATCH-2026-10"]);
  });
});
