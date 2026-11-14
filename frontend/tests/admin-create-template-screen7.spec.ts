import { expect, test } from "@playwright/test";
import {
  INITIAL_SEED_DATA,
  createPrintTemplateKey,
  getPrintTemplateByKey,
  getPrintTemplatesCount,
  getTemplateRevisionsCount,
  resetAdminMockData,
  loadAdminMockData,
  type MockAdminDatabase,
} from "../lib/admin-mock-data";

test.describe("Screen 7: Create Print Template Key (API-301 Draft Only)", () => {
  test.beforeEach(() => {
    resetAdminMockData();
  });

  test("Screen 7 createPrintTemplateKey validates required fields, character regex, and length limits", () => {
    // 1. Empty key rejection
    const emptyKeyRes = createPrintTemplateKey({
      key: "",
      name: "Valid Template Name",
      purpose: "lost",
    });
    expect(emptyKeyRes.success).toBe(false);
    expect(emptyKeyRes.error).toContain("Template key is required");

    // 2. Invalid character / regex rejection
    const invalidCharRes = createPrintTemplateKey({
      key: "invalid key with spaces",
      name: "Valid Name",
      purpose: "lost",
    });
    expect(invalidCharRes.success).toBe(false);
    expect(invalidCharRes.error).toContain("3–80 ASCII characters");

    // 3. Short key (< 3 chars)
    const shortKeyRes = createPrintTemplateKey({
      key: "ab",
      name: "Valid Name",
      purpose: "lost",
    });
    expect(shortKeyRes.success).toBe(false);
    expect(shortKeyRes.error).toContain("3–80 ASCII characters");

    // 4. Overly long key (> 80 chars)
    const longKey = "a".repeat(81);
    const longKeyRes = createPrintTemplateKey({
      key: longKey,
      name: "Valid Name",
      purpose: "lost",
    });
    expect(longKeyRes.success).toBe(false);
    expect(longKeyRes.error).toContain("3–80 ASCII characters");

    // 5. Empty name rejection
    const emptyNameRes = createPrintTemplateKey({
      key: "valid-key-01",
      name: "   ",
      purpose: "lost",
    });
    expect(emptyNameRes.success).toBe(false);
    expect(emptyNameRes.error).toContain("Template name is required");

    // 6. Overly long name (> 100 chars)
    const longName = "x".repeat(101);
    const longNameRes = createPrintTemplateKey({
      key: "valid-key-02",
      name: longName,
      purpose: "lost",
    });
    expect(longNameRes.success).toBe(false);
    expect(longNameRes.error).toContain("100 characters");

    // 7. Invalid purpose
    const invalidPurposeRes = createPrintTemplateKey({
      key: "valid-key-03",
      name: "Valid Name",
      // @ts-expect-error test invalid purpose
      purpose: "unknown_purpose",
    });
    expect(invalidPurposeRes.success).toBe(false);
    expect(invalidPurposeRes.error).toContain("valid template purpose");
  });

  test("Screen 7 case-sensitive uniqueness prevents duplicate keys while respecting distinct casing", () => {
    // Initial benchmark fixture has "TP-WRIST-V2"
    expect(getPrintTemplateByKey("TP-WRIST-V2")).toBeDefined();

    // Attempting to create duplicate exact key fails
    const dupRes = createPrintTemplateKey({
      key: "TP-WRIST-V2",
      name: "Duplicate Key Attempt",
      purpose: "ice",
    });
    expect(dupRes.success).toBe(false);
    expect(dupRes.error).toBe("Template key already exists.");

    // Distinct casing is allowed under case-sensitive uniqueness
    const distinctCaseRes = createPrintTemplateKey({
      key: "tp-wrist-v2",
      name: "Lowercase Variant Key",
      purpose: "ice",
    });
    expect(distinctCaseRes.success).toBe(true);
    expect(distinctCaseRes.template?.key).toBe("tp-wrist-v2");
    expect(getPrintTemplateByKey("tp-wrist-v2")).toBeDefined();
    // Original remains intact
    expect(getPrintTemplateByKey("TP-WRIST-V2")?.name).toBe("Standard Wristband Layout");
  });

  test("Screen 7 creates draft key only: 0 revisions, draft status, unconfigured size, synthetic audit log", () => {
    const prevCount = getPrintTemplatesCount(loadAdminMockData());
    const prevRevs = getTemplateRevisionsCount(loadAdminMockData());

    const result = createPrintTemplateKey(
      {
        key: "sr-lost-sticker-v1",
        name: "SafeReturn Lost Sticker V1",
        purpose: "lost",
      },
      "operations"
    );

    expect(result.success).toBe(true);
    const tmpl = result.template!;
    expect(tmpl.key).toBe("sr-lost-sticker-v1");
    expect(tmpl.name).toBe("SafeReturn Lost Sticker V1");
    expect(tmpl.purpose).toBe("lost");
    expect(tmpl.revision).toBe(0); // Zero revisions created at key registration
    expect(tmpl.rowVersion).toBe(1);
    expect(tmpl.status).toBe("draft");
    expect(tmpl.size).toBe("Not configured — create revision");
    expect(tmpl.supportedTypes).toEqual(["Sticker"]);
    expect(tmpl.lastAuthor).toBe("operations");

    // Verify mock database updates
    const db = loadAdminMockData();
    expect(getPrintTemplatesCount(db)).toBe(prevCount + 1);
    // Key creation does NOT add revisions; revision metric must not increase
    expect(getTemplateRevisionsCount(db)).toBe(prevRevs);

    // Verify synthetic audit log was added
    expect(db.auditLogs.length).toBeGreaterThan(0);
    const topLog = db.auditLogs[0];
    expect(topLog.action).toBe("API-301 Template Key Created");
    expect(topLog.target).toBe("sr-lost-sticker-v1");
    expect(topLog.details).toContain("Draft key only; no renderer or physical QA");
    expect(topLog.actor).toBe("operations");
  });

  test("Screen 7 enforces role permissions: Operations and Superadmin allowed; Finance, Support, Security rejected", () => {
    // 1. Allowed roles
    const opsRes = createPrintTemplateKey(
      { key: "ops-key-01", name: "Ops Template", purpose: "lost" },
      "Operations"
    );
    expect(opsRes.success).toBe(true);

    const superRes = createPrintTemplateKey(
      { key: "super-key-01", name: "Superadmin Template", purpose: "ice" },
      "Superadmin"
    );
    expect(superRes.success).toBe(true);

    // 2. Restricted roles
    const finRes = createPrintTemplateKey(
      { key: "fin-key-01", name: "Finance Template", purpose: "lost" },
      "Finance"
    );
    expect(finRes.success).toBe(false);
    expect(finRes.error).toContain("restricted from creating print template keys");

    const supRes = createPrintTemplateKey(
      { key: "sup-key-01", name: "Support Template", purpose: "lost" },
      "Support"
    );
    expect(supRes.success).toBe(false);
    expect(supRes.error).toContain("restricted from creating print template keys");

    const secRes = createPrintTemplateKey(
      { key: "sec-key-01", name: "Security Template", purpose: "lost" },
      "Security Admin"
    );
    expect(secRes.success).toBe(false);
    expect(secRes.error).toContain("restricted from creating print template keys");
  });

  test("Screen 7 resetAdminMockData purges user-created template keys and restores fixture benchmark", () => {
    // Create new custom template key
    createPrintTemplateKey({
      key: "custom-temporary-key",
      name: "Temporary Mock Template",
      purpose: "lost",
    });
    expect(getPrintTemplateByKey("custom-temporary-key")).toBeDefined();
    expect(getPrintTemplatesCount(loadAdminMockData())).toBe(4);

    // Reset demo data
    resetAdminMockData();

    // Verify custom key is purged and benchmark state restored
    const db = loadAdminMockData();
    expect(getPrintTemplateByKey("custom-temporary-key")).toBeUndefined();
    expect(getPrintTemplatesCount(db)).toBe(3);
    expect(getTemplateRevisionsCount(db)).toBe(3);
    expect(db.printTemplates.map((t) => t.key)).toEqual([
      "TP-WRIST-V2",
      "TP-TAG-MINI-V1",
      "TP-STICKER-4X",
    ]);
  });
});


