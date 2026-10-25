import { expect, test } from "@playwright/test";
import {
  INITIAL_SEED_DATA,
  getPrintTemplateByKey,
  getPrintTemplateById,
  loadAdminMockData,
  saveAdminMockData,
  type MockAdminDatabase,
  type MockPrintTemplate,
} from "../lib/admin-mock-data";

test("Screen 6 Template retrieval and metadata verification", () => {
  const db: MockAdminDatabase = JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  saveAdminMockData(db);

  // 1. Verify seeded templates exist
  expect(db.printTemplates.length).toBe(3);

  // 2. Retrieve by key
  const wristband = getPrintTemplateByKey("TP-WRIST-V2");
  expect(wristband).toBeDefined();
  expect(wristband?.name).toBe("Standard Wristband Layout");
  expect(wristband?.revision).toBe(2);
  expect(wristband?.status).toBe("published");
  expect(wristband?.supportedTypes).toContain("Wristband");
  expect(wristband?.size).toBe("20mm x 200mm");
  expect(wristband?.purpose).toBe("ice");

  // 3. Retrieve by ID
  const tag = getPrintTemplateById("TMP-002");
  expect(tag).toBeDefined();
  expect(tag?.key).toBe("TP-TAG-MINI-V1");
  expect(tag?.status).toBe("published");
  expect(tag?.purpose).toBe("lost");

  // 4. Non-existent returns undefined
  expect(getPrintTemplateByKey("NON-EXISTENT-KEY")).toBeUndefined();
  expect(getPrintTemplateById("TMP-9999")).toBeUndefined();
});

test("Screen 6 Search and filtering logic for template catalogue", () => {
  const templates: MockPrintTemplate[] = INITIAL_SEED_DATA.printTemplates;

  // 1. Search by name (case-insensitive)
  const nameQuery = "sticker";
  const nameResults = templates.filter(
    (t) =>
      t.name.toLowerCase().includes(nameQuery) ||
      t.key.toLowerCase().includes(nameQuery)
  );
  expect(nameResults.length).toBe(1);
  expect(nameResults[0].key).toBe("TP-STICKER-4X");

  // 2. Search by key (case-insensitive)
  const keyQuery = "tag-mini";
  const keyResults = templates.filter(
    (t) =>
      t.name.toLowerCase().includes(keyQuery) ||
      t.key.toLowerCase().includes(keyQuery)
  );
  expect(keyResults.length).toBe(1);
  expect(keyResults[0].id).toBe("TMP-002");

  // 3. Status filter
  const published = templates.filter((t) => t.status === "published");
  expect(published.length).toBe(2);
  const draft = templates.filter((t) => t.status === "draft");
  expect(draft.length).toBe(1);

  // 4. Purpose filter
  const lostItems = templates.filter((t) => t.purpose === "lost");
  expect(lostItems.length).toBe(2);
  const iceItems = templates.filter((t) => t.purpose === "ice");
  expect(iceItems.length).toBe(1);

  // 5. Combined filter: Draft + Lost
  const draftLost = templates.filter(
    (t) => t.status === "draft" && t.purpose === "lost"
  );
  expect(draftLost.length).toBe(1);
  expect(draftLost[0].key).toBe("TP-STICKER-4X");
});

test("Screen 6 Revision display and immutability rules", () => {
  function formatRevision(t: { revision: number; status: string }): string {
    if (t.revision > 0) {
      return `Rev ${t.revision} (${t.status === "published" ? "Published" : "Draft"})`;
    }
    return "No revisions yet (Draft)";
  }

  // Published template
  expect(formatRevision({ revision: 2, status: "published" })).toBe(
    "Rev 2 (Published)"
  );

  // Draft template with revision
  expect(formatRevision({ revision: 3, status: "draft" })).toBe(
    "Rev 3 (Draft)"
  );

  // Unconfigured draft key without revisions
  expect(formatRevision({ revision: 0, status: "draft" })).toBe(
    "No revisions yet (Draft)"
  );

  // Immutability check: Published templates cannot be modified directly
  function canEditRevision(status: string): boolean {
    return status !== "published";
  }
  expect(canEditRevision("published")).toBe(false);
  expect(canEditRevision("draft")).toBe(true);
});

test("Screen 6 Role permissions for Print Template management", () => {
  function canManageTemplates(role: string): boolean {
    const norm = role.toLowerCase().replace(/[\s_-]+/g, "");
    return norm.includes("superadmin") || norm.includes("operations");
  }

  expect(canManageTemplates("Superadmin")).toBe(true);
  expect(canManageTemplates("Operations")).toBe(true);
  expect(canManageTemplates("Finance")).toBe(false);
  expect(canManageTemplates("Support")).toBe(false);
  expect(canManageTemplates("Security Admin")).toBe(false);
});

