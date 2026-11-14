import { expect, test } from "@playwright/test";
import {
  INITIAL_SEED_DATA,
  getPrintTemplateByKey,
  createPrintTemplateKey,
  createDraftRevision,
  updateDraftRevision,
  getPrintTemplatesCount,
  getTemplateRevisionsCount,
  resetAdminMockData,
  loadAdminMockData,
  type MockAdminDatabase,
} from "../lib/admin-mock-data";

test.describe("Screen 8: Template Details, Draft Revisions and Preview Readiness", () => {
  test.beforeEach(() => {
    resetAdminMockData();
  });

  test("Screen 8 resolves template details correctly by key and detects missing keys", () => {
    // 1. Existing template lookup
    const template = getPrintTemplateByKey("TP-WRIST-V2");
    expect(template).toBeDefined();
    expect(template?.name).toBe("Standard Wristband Layout");
    expect(template?.purpose).toBe("ice");
    expect(template?.revision).toBe(2);
    expect(template?.status).toBe("published");
    expect(template?.size).toBe("20mm x 200mm");
    expect(template?.supportedTypes).toContain("Wristband");
    expect(template?.lastAuthor).toBe("ops_lead");

    // 2. Missing key lookup
    const missing = getPrintTemplateByKey("NONEXISTENT-KEY");
    expect(missing).toBeUndefined();
  });

  test("Screen 8 respects zero-revision keys and does not fabricate missing historical revisions", () => {
    // 1. Newly created draft key (Screen 7 API-301) has zero revisions
    const createdKeyRes = createPrintTemplateKey({
      key: "sr-clean-key",
      name: "Clean Zero-Rev Key",
      purpose: "lost",
    });
    expect(createdKeyRes.success).toBe(true);

    const freshTemplate = getPrintTemplateByKey("sr-clean-key");
    expect(freshTemplate?.revision).toBe(0);
    expect(freshTemplate?.revisions).toBeDefined();
    expect(freshTemplate?.revisions?.length).toBe(0);

    // 2. Existing template TP-WRIST-V2 reports Rev 2, but historical Rev 1 is NOT fabricated
    const wristbandTmpl = getPrintTemplateByKey("TP-WRIST-V2");
    expect(wristbandTmpl?.revision).toBe(2);
    expect(wristbandTmpl?.revisions?.length).toBe(1);
    expect(wristbandTmpl?.revisions?.[0].revisionNumber).toBe(2);
    expect(wristbandTmpl?.revisions?.[0].status).toBe("published");
    // Verify Rev 1 does not exist in mock array
    expect(wristbandTmpl?.revisions?.some((r) => r.revisionNumber === 1)).toBe(false);

    // 3. TP-STICKER-4X reports Rev 3, but Rev 1 & 2 are not fabricated
    const stickerTmpl = getPrintTemplateByKey("TP-STICKER-4X");
    expect(stickerTmpl?.revision).toBe(3);
    expect(stickerTmpl?.revisions?.length).toBe(1);
    expect(stickerTmpl?.revisions?.[0].revisionNumber).toBe(3);
    expect(stickerTmpl?.revisions?.[0].status).toBe("draft");
  });

  test("Screen 8 createDraftRevision calculates sequential revision, starts as draft, and logs audit event", () => {
    const prevRevs = getTemplateRevisionsCount(loadAdminMockData());

    // Create draft revision for TP-WRIST-V2 (currently Rev 2 published)
    const result = createDraftRevision(
      "TP-WRIST-V2",
      {
        versionNote: "Add bilingual emergency instructions and expand quiet zone",
        labelDimensions: "22mm x 205mm",
        supportedTypes: ["Wristband"],
      },
      "operations"
    );

    expect(result.success).toBe(true);
    expect(result.revision).toBeDefined();
    const rev = result.revision!;
    expect(rev.revisionNumber).toBe(3); // Next sequential revision
    expect(rev.status).toBe("draft"); // Strictly starts as draft
    expect(rev.versionNote).toBe("Add bilingual emergency instructions and expand quiet zone");
    expect(rev.labelDimensions).toBe("22mm x 205mm");
    expect(rev.author).toBe("operations");
    expect(rev.previewAvailable).toBe(false);

    // Verify template state was updated
    const updatedTmpl = getPrintTemplateByKey("TP-WRIST-V2");
    expect(updatedTmpl?.revision).toBe(3);
    expect(updatedTmpl?.status).toBe("draft");
    expect(updatedTmpl?.size).toBe("22mm x 205mm");
    expect(updatedTmpl?.revisions?.length).toBe(2); // Rev 3 and Rev 2

    // Revision count incremented
    const db = loadAdminMockData();
    expect(getTemplateRevisionsCount(db)).toBe(prevRevs + 1);

    // Verify synthetic audit log
    const topLog = db.auditLogs[0];
    expect(topLog.action).toBe("API-303 Draft Revision Created");
    expect(topLog.target).toBe("TP-WRIST-V2 Rev 3");
    expect(topLog.details).toContain("Draft revision metadata created; no artwork or renderer enrolled");
  });

  test("Screen 8 updateDraftRevision updates draft metadata while strictly enforcing published revision immutability", () => {
    // 1. Attempting to edit a published revision (TP-WRIST-V2 Rev 2) must be REJECTED
    const pubEditRes = updateDraftRevision(
      "TP-WRIST-V2",
      2,
      { versionNote: "Attempting to overwrite certified published revision" },
      "operations"
    );
    expect(pubEditRes.success).toBe(false);
    expect(pubEditRes.error).toContain("Published revisions are immutable (API-304)");

    // Ensure published revision was not mutated
    const tmplAfterFailedEdit = getPrintTemplateByKey("TP-WRIST-V2");
    expect(tmplAfterFailedEdit?.revisions?.find((r) => r.revisionNumber === 2)?.versionNote).toBe(
      "Initial certified wristband layout"
    );

    // 2. Editing an existing draft revision (TP-STICKER-4X Rev 3) succeeds
    const draftEditRes = updateDraftRevision(
      "TP-STICKER-4X",
      3,
      {
        versionNote: "Adjusted quad spacing to 105mm x 155mm for dementia care tags",
        labelDimensions: "105mm x 155mm",
        supportedTypes: ["Sticker Sheet"],
      },
      "operations"
    );
    expect(draftEditRes.success).toBe(true);
    expect(draftEditRes.revision?.versionNote).toBe(
      "Adjusted quad spacing to 105mm x 155mm for dementia care tags"
    );
    expect(draftEditRes.revision?.status).toBe("draft"); // Remains draft

    // Verify template reflects updated dimensions
    const stickerTmpl = getPrintTemplateByKey("TP-STICKER-4X");
    expect(stickerTmpl?.size).toBe("105mm x 155mm");
    expect(stickerTmpl?.status).toBe("draft");

    // Verify audit log
    const db = loadAdminMockData();
    const topLog = db.auditLogs[0];
    expect(topLog.action).toBe("API-304 Draft Revision Updated");
    expect(topLog.target).toBe("TP-STICKER-4X Rev 3");
  });

  test("Screen 8 role permissions: Operations and Superadmin allowed; Finance, Support, Security rejected", () => {
    // 1. Operations and Superadmin allowed
    const opsRes = createDraftRevision("TP-STICKER-4X", { versionNote: "Ops test" }, "Operations");
    expect(opsRes.success).toBe(true);

    const superRes = updateDraftRevision("TP-STICKER-4X", 4, { versionNote: "Super test" }, "Superadmin");
    expect(superRes.success).toBe(true);

    // 2. Restricted roles rejected
    const finRes = createDraftRevision("TP-STICKER-4X", { versionNote: "Finance attempt" }, "Finance");
    expect(finRes.success).toBe(false);
    expect(finRes.error).toContain("restricted from creating template revisions");

    const supRes = updateDraftRevision("TP-STICKER-4X", 4, { versionNote: "Support attempt" }, "Support");
    expect(supRes.success).toBe(false);
    expect(supRes.error).toContain("restricted from updating template revisions");

    const secRes = createDraftRevision("TP-STICKER-4X", { versionNote: "Security attempt" }, "Security Admin");
    expect(secRes.success).toBe(false);
    expect(secRes.error).toContain("restricted from creating template revisions");
  });

  test("Screen 8 resetAdminMockData restores original benchmark revisions and cleans custom revisions", () => {
    // Create new draft revision
    createDraftRevision("TP-TAG-MINI-V1", { versionNote: "Experimental mini tag" });
    expect(getPrintTemplateByKey("TP-TAG-MINI-V1")?.revision).toBe(2);

    // Reset demo database
    resetAdminMockData();

    // Verify original benchmark state restored
    const db = loadAdminMockData();
    const tagTmpl = db.printTemplates.find((t) => t.key === "TP-TAG-MINI-V1");
    expect(tagTmpl?.revision).toBe(1);
    expect(tagTmpl?.status).toBe("published");
    expect(tagTmpl?.revisions?.length).toBe(1);
    expect(tagTmpl?.revisions?.[0].revisionNumber).toBe(1);
    expect(getTemplateRevisionsCount(db)).toBe(3);
  });
});


