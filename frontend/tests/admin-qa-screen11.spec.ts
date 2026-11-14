import { test, expect } from "@playwright/test";
import {
  loadAdminMockData,
  resetAdminMockData,
  getQAPairs,
  getQAPairById,
  getQAInspections,
  recordQAPass,
  recordQAQuarantine,
  getQASummary,
  type MockQAPair,
  createDemoQRBatch,
} from "../lib/admin-mock-data";
import { DEMO_PERMISSIONS } from "../lib/admin-navigation";

test.describe("Screen 11: QR Quality Assurance", () => {
  test.beforeEach(() => {
    resetAdminMockData();
  });

  test.afterEach(() => {
    resetAdminMockData();
  });

  test("Screen 11 loads benchmark synthetic QA pairs and inspection summary", () => {
    const pairs = getQAPairs();
    expect(pairs.length).toBeGreaterThanOrEqual(6);

    const p1 = getQAPairById("PAIR-2026-001");
    expect(p1).toBeDefined();
    expect(p1?.status).toBe("Passed");
    expect(p1?.batchId).toBe("BATCH-2026-09");

    const p3 = getQAPairById("PAIR-2026-003");
    expect(p3).toBeDefined();
    expect(p3?.status).toBe("Quarantined");
    expect(p3?.batchId).toBe("BATCH-2026-10");
    expect(p3?.rejectionReason).toBe("QR readability issue");

    const p4 = getQAPairById("PAIR-2026-004");
    expect(p4).toBeDefined();
    expect(p4?.status).toBe("Awaiting QA");
    expect(p4?.batchId).toBe("BATCH-2026-10");

    // Summary counts
    const summary = getQASummary();
    expect(summary.totalInspected).toBe(3);
    expect(summary.passed).toBe(2);
    expect(summary.quarantined).toBe(1);
    expect(summary.awaiting).toBe(3);
  });

  test("Screen 11 lookup by pair ID works case-insensitively and rejects unknown pairs", () => {
    // Valid lookup (exact and case-insensitive)
    const exact = getQAPairById("PAIR-2026-004");
    expect(exact).toBeDefined();
    expect(exact?.id).toBe("PAIR-2026-004");

    const lower = getQAPairById("pair-2026-004");
    expect(lower).toBeDefined();
    expect(lower?.id).toBe("PAIR-2026-004");

    // Unknown pair
    const unknown = getQAPairById("PAIR-NONEXISTENT");
    expect(unknown).toBeUndefined();
  });

  test("Screen 11 filters available pairs by batch correctly", () => {
    const b9Pairs = getQAPairs("BATCH-2026-09");
    expect(b9Pairs.length).toBe(2);
    b9Pairs.forEach((p) => expect(p.batchId).toBe("BATCH-2026-09"));

    const b10Pairs = getQAPairs("BATCH-2026-10");
    expect(b10Pairs.length).toBe(4);
    b10Pairs.forEach((p) => expect(p.batchId).toBe("BATCH-2026-10"));
  });

  test("Screen 11 records Pass QA outcome with audit log and updates summary", () => {
    const result = recordQAPass({
      pairId: "PAIR-2026-004",
      inspector: "Sarah Jenkins (Operations)",
    });

    expect(result.success).toBe(true);
    if (!result.success) return;

    expect(result.pair.status).toBe("Passed");
    expect(result.pair.inspector).toBe("Sarah Jenkins (Operations)");
    expect(result.pair.lastInspectedAt).toBeDefined();

    // Verify inspection record was created
    const inspections = getQAInspections();
    const latest = inspections.find((i) => i.pairId === "PAIR-2026-004");
    expect(latest).toBeDefined();
    expect(latest?.outcome).toBe("Passed");
    expect(latest?.inspector).toBe("Sarah Jenkins (Operations)");

    // Verify synthetic audit log
    const db = loadAdminMockData();
    const log = db.auditLogs.find(
      (l) => l.action === "Demo QA Passed" && l.target === "PAIR-2026-004"
    );
    expect(log).toBeDefined();

    // Summary counts reflect pass
    const summary = getQASummary();
    expect(summary.passed).toBe(3);
    expect(summary.awaiting).toBe(2);
  });

  test("Screen 11 records Reject & Quarantine outcome with required reason and updates summary", () => {
    // Attempting quarantine without reason is rejected
    const rNoReason = recordQAQuarantine({
      pairId: "PAIR-2026-005",
      rejectionReason: "",
    });
    expect(rNoReason.success).toBe(false);
    if (!rNoReason.success) {
      expect(rNoReason.error).toContain("reason is required");
    }

    // Valid quarantine with reason and note
    const result = recordQAQuarantine({
      pairId: "PAIR-2026-005",
      rejectionReason: "Print quality issue",
      notes: "Severe ink bleeding across quiet zone",
      inspector: "Operations Lead",
    });

    expect(result.success).toBe(true);
    if (!result.success) return;

    expect(result.pair.status).toBe("Quarantined");
    expect(result.pair.rejectionReason).toBe("Print quality issue");
    expect(result.pair.notes).toBe("Severe ink bleeding across quiet zone");

    // Verify inspection record
    const inspections = getQAInspections();
    const latest = inspections.find((i) => i.pairId === "PAIR-2026-005");
    expect(latest).toBeDefined();
    expect(latest?.outcome).toBe("Quarantined");
    expect(latest?.rejectionReason).toBe("Print quality issue");

    // Summary counts reflect quarantine
    const summary = getQASummary();
    expect(summary.quarantined).toBe(2);
    expect(summary.awaiting).toBe(2);
  });

  test("Screen 11 prevents reinspection of already inspected pairs", () => {
    // Attempting to pass an already passed pair
    const rPassed = recordQAPass({ pairId: "PAIR-2026-001" });
    expect(rPassed.success).toBe(false);
    if (!rPassed.success) {
      expect(rPassed.error).toContain("Reinspection is not available");
    }

    // Attempting to quarantine an already quarantined pair
    const rQuarantined = recordQAQuarantine({
      pairId: "PAIR-2026-003",
      rejectionReason: "Physical damage",
    });
    expect(rQuarantined.success).toBe(false);
    if (!rQuarantined.success) {
      expect(rQuarantined.error).toContain("Reinspection is not available");
    }
  });

  test("Screen 11 QA actions STRICTLY isolate batch status and Screen 9 inventory", () => {
    const dbBefore = loadAdminMockData();
    const b10StatusBefore = dbBefore.qrBatches.find(
      (b) => b.id === "BATCH-2026-10"
    )?.status;
    const backpackStockBefore = dbBefore.products.find(
      (p) => p.sku === "SR-TG-KID-02"
    )?.stock;

    // Pass a pair from BATCH-2026-10
    recordQAPass({ pairId: "PAIR-2026-004" });

    // Verify batch status is NOT automatically changed to QA Passed
    const dbAfter = loadAdminMockData();
    const b10StatusAfter = dbAfter.qrBatches.find(
      (b) => b.id === "BATCH-2026-10"
    )?.status;
    expect(b10StatusAfter).toBe(b10StatusBefore);

    // Verify Screen 9 product inventory is NOT modified
    const backpackStockAfter = dbAfter.products.find(
      (p) => p.sku === "SR-TG-KID-02"
    )?.stock;
    expect(backpackStockAfter).toBe(backpackStockBefore);
  });

  test("Screen 11 role permissions grant access to Operations and Superadmin while restricting others", () => {
    expect(DEMO_PERMISSIONS.Operations.pages).toContain("qa");
    expect(DEMO_PERMISSIONS.Superadmin.pages).toContain("qa");

    expect(DEMO_PERMISSIONS.Finance.pages).not.toContain("qa");
    expect(DEMO_PERMISSIONS.Support.pages).not.toContain("qa");
    expect(DEMO_PERMISSIONS["Security Admin"].pages).not.toContain("qa");
  });

  test("Screen 11 resetAdminMockData cleanly restores baseline QA pairs and inspections", () => {
    // Perform inspection on PAIR-2026-006
    recordQAPass({ pairId: "PAIR-2026-006" });
    expect(getQAPairById("PAIR-2026-006")?.status).toBe("Passed");

    // Reset data
    resetAdminMockData();

    // Verify PAIR-2026-006 is restored to Awaiting QA
    expect(getQAPairById("PAIR-2026-006")?.status).toBe("Awaiting QA");
    const summary = getQASummary();
    expect(summary.totalInspected).toBe(3);
    expect(summary.passed).toBe(2);
    expect(summary.quarantined).toBe(1);
    expect(summary.awaiting).toBe(3);
  });
});


test('QA lookup does not materialize pairs or change a newly generated batch', () => {
  resetAdminMockData();
  const before = loadAdminMockData().qaPairs.length;
  createDemoQRBatch({ pairsCount: 10, batchLabel: 'BATCH-DEMO-EMPTY' });
  expect(getQAPairs('BATCH-DEMO-EMPTY')).toEqual([]);
  expect(loadAdminMockData().qaPairs).toHaveLength(before);
  resetAdminMockData();
});
