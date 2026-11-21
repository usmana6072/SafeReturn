export {ALL_ADMIN_MODULES, ADMIN_SECTIONS} from "../../../../lib/admin-navigation";
export type DemoRoleName = "Superadmin" | "Operations" | "Finance" | "Support" | "Security Admin";

export const DEMO_ROLES: DemoRoleName[] = [
  "Superadmin",
  "Operations",
  "Finance",
  "Support",
  "Security Admin",
];

export const DEMO_PERMISSIONS: Record<DemoRoleName, { pages: string[] }> = {
  Superadmin: {
    pages: [
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
    ],
  },
  Operations: {
    pages: [
      "overview",
      "products",
      "templates",
      "inventory",
      "qr_batches",
      "qa",
      "orders",
      "print_jobs",
      "shipments",
      "ready_to_ship",
      "notifications",
      "monitoring",
    ],
  },
  Finance: {
    pages: ["overview", "orders", "payments", "finance_sync", "audit"],
  },
  Support: {
    pages: ["overview", "users", "orders", "support", "notifications"],
  },
  "Security Admin": {
    pages: [
      "overview",
      "users",
      "staff_permissions",
      "privacy_requests",
      "storage",
      "audit",
      "monitoring",
    ],
  },
};
