import type { Capability } from "./auth/staff-contract";
import type { AdminIconName } from "../components/admin-icons";

export type AdminSectionId = "general" | "catalog" | "commerce" | "users" | "governance";

export interface AdminSection {
  id: AdminSectionId;
  labelEn: string;
  labelUr: string;
}

export const ADMIN_SECTIONS: AdminSection[] = [
  { id: "general", labelEn: "General", labelUr: "عمومی" },
  { id: "catalog", labelEn: "Catalog & Production", labelUr: "مصنوعات اور پیداوار" },
  { id: "commerce", labelEn: "Commerce & Fulfillment", labelUr: "تجارت اور ترسیل" },
  { id: "users", labelEn: "Users & Communication", labelUr: "صارفین اور رابطہ" },
  { id: "governance", labelEn: "Governance & Administration", labelUr: "انتظامی امور اور سکیورٹی" },
];

export interface AdminNavigationItem {
  id: string;
  path: string;
  labelEn: string;
  labelUr: string;
  section: AdminSectionId;
  icon: AdminIconName;
  capability?: Capability;
  descriptionEn: string;
  descriptionUr: string;
  badge?: string;
}

export const ALL_ADMIN_MODULES: AdminNavigationItem[] = [
  {
    id: "overview",
    path: "/admin",
    labelEn: "Overview",
    labelUr: "عملی جائزہ",
    section: "general",
    icon: "layout-dashboard",
    descriptionEn: "High-level summary, metrics and quick access.",
    descriptionUr: "اہم اعداد و شمار اور فوری رسائی۔",
  },
  {
    id: "products",
    path: "/admin/products",
    labelEn: "Products",
    labelUr: "مصنوعات",
    section: "catalog",
    icon: "package",
    capability: "catalog.manage",
    descriptionEn: "Manage catalog items, pricing, templates and publication status.",
    descriptionUr: "مصنوعات، قیمتوں اور اشاعت کی حالت کا انتظام کریں۔",
  },
  {
    id: "templates",
    path: "/admin/templates",
    labelEn: "Print Templates",
    labelUr: "پرنٹ سانچے",
    section: "catalog",
    icon: "printer",
    capability: "printing.manage",
    descriptionEn: "Layout blueprints, safe margins, and vector print asset bindings.",
    descriptionUr: "پرنٹ کے خدوخال اور محفوظ مارجن کے سانچے دیکھیں۔",
  },
  {
    id: "inventory",
    path: "/admin/inventory",
    labelEn: "Inventory",
    labelUr: "ذخیرہ",
    section: "catalog",
    icon: "boxes",
    capability: "inventory.manage",
    descriptionEn: "Track paired sticker sheets, warehouse stock and low-inventory warnings.",
    descriptionUr: "اسٹیکر شیٹس، گودام کے اسٹاک اور انتباہات دیکھیں۔",
  },
  {
    id: "qr_batches",
    path: "/admin/batches",
    labelEn: "QR Batches",
    labelUr: "بیچ",
    section: "catalog",
    icon: "qr-code",
    capability: "inventory.manage",
    descriptionEn: "Mint cryptographic QR batches and monitor generation runs.",
    descriptionUr: "کیو آر بیچ تیار کریں اور پیداوار کی جانچ کریں۔",
  },
  {
    id: "qa",
    path: "/admin/qa",
    labelEn: "QR Quality Assurance",
    labelUr: "کوالٹی چیک",
    section: "catalog",
    icon: "check-circle-2",
    capability: "inventory.manage",
    descriptionEn: "Scan physical samples and certify scan readability before release.",
    descriptionUr: "جسمانی نمونے اسکین کر کے ترسیل سے پہلے تصدیق کریں۔",
  },
  {
    id: "orders",
    path: "/admin/orders",
    labelEn: "Orders",
    labelUr: "آرڈر",
    section: "commerce",
    icon: "shopping-cart",
    capability: "orders.read",
    descriptionEn: "Search customer orders, items, shipping addresses and status.",
    descriptionUr: "گاہکوں کے آرڈر، پتے اور حالت دیکھیں۔",
  },
  {
    id: "payments",
    path: "/admin/payments",
    labelEn: "Payments",
    labelUr: "ادائیگیاں",
    section: "commerce",
    icon: "credit-card",
    capability: "payments.review",
    descriptionEn: "Review payment proofs, Raast/bank transfers and reconcile claims.",
    descriptionUr: "بینک ٹرانسفر اور راست ثبوتوں کا جائزہ لیں۔",
  },
  {
    id: "print_jobs",
    path: "/admin/print-jobs",
    labelEn: "Print job metadata",
    labelUr: "پرنٹ کام کی معلومات",
    section: "commerce",
    icon: "file-text",
    capability: "printing.manage",
    descriptionEn: "Inspect vector rendering queue, PDF outputs and batch prints.",
    descriptionUr: "پی ڈی ایف پرنٹ کام اور کیو آر فائلز دیکھیں۔",
  },
  {
    id: "shipments",
    path: "/admin/shipments",
    labelEn: "Shipments",
    labelUr: "ترسیلات",
    section: "commerce",
    icon: "truck",
    capability: "fulfillment.manage",
    descriptionEn: "Courier dispatch, tracking codes and delivery confirmations.",
    descriptionUr: "کورئیر ترسیل، ٹریکنگ اور تصدیق کی جانچ کریں۔",
  },
  {
    id: "ready_to_ship",
    path: "/admin/ready-to-ship",
    labelEn: "Ready to ship",
    labelUr: "ترسیل کے لیے تیار",
    section: "commerce",
    icon: "package",
    capability: "fulfillment.manage",
    descriptionEn: "Packing station queue for verified orders with generated print packs.",
    descriptionUr: "پیکنگ اور روانگی کے لیے تیار آرڈرز۔",
  },
  {
    id: "users",
    path: "/admin/users",
    labelEn: "User directory",
    labelUr: "صارفین کی فہرست",
    section: "users",
    icon: "users",
    capability: "users.manage",
    descriptionEn: "Customer accounts, emergency contacts, tag counts and account state.",
    descriptionUr: "اکاؤنٹ، ایمرجنسی رابطے اور کیو آر تعداد دیکھیں۔",
  },
  {
    id: "support",
    path: "/admin/support",
    labelEn: "Support cases",
    labelUr: "معاونت کے معاملات",
    section: "users",
    icon: "life-buoy",
    capability: "support.manage",
    descriptionEn: "Inbound customer assistance, recovery escalations and tickets.",
    descriptionUr: "صارفین کی معاونت اور رابطہ کے پیغامات۔",
  },
  {
    id: "notifications",
    path: "/admin/notifications",
    labelEn: "Notifications",
    labelUr: "اطلاعات",
    section: "users",
    icon: "bell",
    capability: "notifications.manage",
    descriptionEn: "Transactional SMS, email dispatches, and system alerts queue.",
    descriptionUr: "ای میل اور ایس ایم ایس پیغامات کا ریکارڈ۔",
  },
  {
    id: "staff_permissions",
    path: "/admin/staff-permissions",
    labelEn: "Staff Permissions",
    labelUr: "عملے کی اجازتیں",
    section: "governance",
    icon: "shield-check",
    capability: "users.manage",
    descriptionEn: "Read-only demo navigation matrix and synthetic staff inspection.",
    descriptionUr: "عملے کے فرضی کرداروں اور رسائی کا جائزہ۔",
  },
  {
    id: "staff_security",
    path: "/admin/security/mfa",
    labelEn: "Security / MFA",
    labelUr: "سکیورٹی / MFA",
    section: "governance",
    icon: "shield-check",
    descriptionEn: "Staff authentication credentials, MFA enrollment and session status.",
    descriptionUr: "عملے کی سکیورٹی اور تصدیق کا عمل۔",
  },
  {
    id: "privacy_requests",
    path: "/admin/privacy/exports",
    labelEn: "Privacy Requests",
    labelUr: "رازداری کی درخواستیں",
    section: "governance",
    icon: "file-lock-2",
    capability: "privacy.exports",
    descriptionEn: "Synthetic privacy-request oversight and internal review notes.",
    descriptionUr: "رازداری کی درخواستوں اور داخلی جائزے کا پیش نظارہ۔",
  },
  {
    id: "finance_sync",
    path: "/admin/finance/sheet-sync",
    labelEn: "Finance mirror",
    labelUr: "مالیاتی آئینہ",
    section: "governance",
    icon: "refresh-cw",
    capability: "finance.mirror",
    descriptionEn: "Synthetic finance synchronization records and integration availability.",
    descriptionUr: "گوگل شیٹس پر مالیاتی مطابقت کی جانچ۔",
  },
  {
    id: "storage",
    path: "/admin/storage",
    labelEn: "Storage and retention",
    labelUr: "ذخیرہ اور برقرار رکھنا",
    section: "governance",
    icon: "hard-drive",
    capability: "storage.metadata",
    descriptionEn: "Artifact retention policies, cloud buckets and evidence purge.",
    descriptionUr: "فائلوں کے برقرار رکھنے کی پالیسی اور اسٹوریج۔",
  },
  {
    id: "audit",
    path: "/admin/audit",
    labelEn: "Audit Logs",
    labelUr: "آڈٹ تلاش",
    section: "governance",
    icon: "file-spreadsheet",
    capability: "audit.search",
    descriptionEn: "Read-only synthetic administrative event metadata; production integrity is not implied.",
    descriptionUr: "انتظامی کارروائیوں اور سکیورٹی لاگ کی تلاش۔",
  },
  {
    id: "monitoring",
    path: "/admin/system",
    labelEn: "System Monitoring",
    labelUr: "نظام کے مشاہدات",
    section: "governance",
    icon: "activity",
    capability: "notifications.manage",
    descriptionEn: "Read-only demo monitoring availability and stored operational metadata.",
    descriptionUr: "ورکرز، نظام کی صحت اور سروس کی رفتار۔",
  },
];

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

