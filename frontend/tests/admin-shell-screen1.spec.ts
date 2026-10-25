import { expect, test } from "@playwright/test";
import {
  ALL_ADMIN_MODULES,
  ADMIN_SECTIONS,
  DEMO_ROLES,
  DEMO_PERMISSIONS,
} from "../lib/admin-navigation";

test("Screen 1 Admin Navigation metadata defines all 19 prototype modules", () => {
  expect(ALL_ADMIN_MODULES.length).toBe(21); // prototype modules, ready-to-ship and separate staff MFA entry

  const expectedIds = [
    "overview",
    "products",
    "templates",
    "inventory",
    "qr_batches",
    "qa",
    "orders",
    "payments",
    "print_jobs",
    "shipments",
    "ready_to_ship",
    "users",
    "support",
    "notifications",
    "staff_permissions",
    "privacy_requests",
    "finance_sync",
    "storage",
    "audit",
    "monitoring",
  ];

  for (const id of expectedIds) {
    const found = ALL_ADMIN_MODULES.find((m) => m.id === id);
    expect(found, `Module ${id} must exist`).toBeDefined();
    expect(found?.path.startsWith("/admin")).toBe(true);
    expect(found?.labelEn.length).toBeGreaterThan(0);
    expect(found?.labelUr.length).toBeGreaterThan(0);
  }
});

test("Screen 1 Admin Navigation defines 5 logical sections", () => {
  expect(ADMIN_SECTIONS.map((s) => s.id)).toEqual([
    "general",
    "catalog",
    "commerce",
    "users",
    "governance",
  ]);

  // Every module must belong to one of the 5 sections
  const sectionIds = new Set(ADMIN_SECTIONS.map((s) => s.id));
  for (const mod of ALL_ADMIN_MODULES) {
    expect(sectionIds.has(mod.section)).toBe(true);
  }
});

test("Screen 1 Demo Roles matrix matches prototype permissions", () => {
  expect(DEMO_ROLES).toEqual([
    "Superadmin",
    "Operations",
    "Finance",
    "Support",
    "Security Admin",
  ]);

  // Superadmin has access to all pages
  expect(DEMO_PERMISSIONS.Superadmin.pages.length).toBe(ALL_ADMIN_MODULES.filter(m => m.id !== "staff_security").length);

  // Operations cannot access payments, finance sync, users, support, audit, privacy
  expect(DEMO_PERMISSIONS.Operations.pages).toContain("products");
  expect(DEMO_PERMISSIONS.Operations.pages).toContain("shipments");
  expect(DEMO_PERMISSIONS.Operations.pages).not.toContain("payments");
  expect(DEMO_PERMISSIONS.Operations.pages).not.toContain("finance_sync");

  // Finance only accesses finance/orders/audit/overview
  expect(DEMO_PERMISSIONS.Finance.pages).toContain("orders");
  expect(DEMO_PERMISSIONS.Finance.pages).toContain("payments");
  expect(DEMO_PERMISSIONS.Finance.pages).toContain("finance_sync");
  expect(DEMO_PERMISSIONS.Finance.pages).not.toContain("products");
  expect(DEMO_PERMISSIONS.Finance.pages).not.toContain("shipments");

  // Support only accesses support/users/orders/notifications/overview
  expect(DEMO_PERMISSIONS.Support.pages).toContain("support");
  expect(DEMO_PERMISSIONS.Support.pages).toContain("users");
  expect(DEMO_PERMISSIONS.Support.pages).not.toContain("products");
  expect(DEMO_PERMISSIONS.Support.pages).not.toContain("payments");

  // Security Admin only accesses security/governance/users/overview/monitoring
  expect(DEMO_PERMISSIONS["Security Admin"].pages).toContain("staff_permissions");
  expect(DEMO_PERMISSIONS["Security Admin"].pages).toContain("privacy_requests");
  expect(DEMO_PERMISSIONS["Security Admin"].pages).toContain("audit");
  expect(DEMO_PERMISSIONS["Security Admin"].pages).not.toContain("products");
  expect(DEMO_PERMISSIONS["Security Admin"].pages).not.toContain("payments");
});


