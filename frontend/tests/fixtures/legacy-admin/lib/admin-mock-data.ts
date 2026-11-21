"use client";

import { useState, useEffect, useCallback } from "react";
import { canReviewDemoPayments } from "./admin-payment-access";
export { canReviewDemoPayments } from "./admin-payment-access";
import { canInspectDemoPrintJobs, demoPrintReasons } from "./admin-print-policy";
import { canManageDemoShipments, demoShipmentTransitions } from "./admin-shipment-policy";
import { canGovernDemoUsers } from "./admin-user-list";
import { canManageDemoSupport, demoSupportNextStates, isDemoSupportCase } from "./admin-support-policy";
import { canReviewDemoPrivacy, isMockPrivacyRequest } from "./admin-privacy-policy";

export interface MockStorageRecord {
  id: string;
  category?: string;
  sizeBytes?: number;
  createdAt?: string;
  lifecycle?: string;
  onHold?: boolean;
  activity?: { id: string; timestamp: string; kind: "review_noted" }[];
}
// Safe metadata only: no file, object key, bucket, URL, customer or secret payload.
export const INITIAL_STORAGE_RECORDS: MockStorageRecord[] = [
  { id: "DEMO-STORAGE-001", category: "print_artifact", sizeBytes: 204800, createdAt: "2026-10-01T09:00:00Z", lifecycle: "retained", onHold: true, activity: [{ id: "DEMO-STORAGE-EVENT-001", timestamp: "2026-10-23T12:00:00Z", kind: "review_noted" }] },
  { id: "DEMO-STORAGE-002", category: "payment_evidence", createdAt: "2026-10-02T09:00:00Z", lifecycle: "retained", activity: [] },
  { id: "DEMO-STORAGE-003", category: "print_artifact", sizeBytes: 102400, createdAt: "2026-10-03T09:00:00Z", lifecycle: "quarantined", onHold: false, activity: [] },
];

export interface MockFinanceSync {
  id: string;
  orderId?: string;
  paymentId?: string;
  amount?: number | string;
  currency?: string;
  status?: string;
  createdAt?: string;
  errorCode?: string;
  attempts?: { id: string; timestamp: string; result: string; errorCode?: string }[];
}

// Historical totals match the existing legacy order fixtures. Their currency is
// unspecified; neither current catalog pricing nor PKR is inferred here.
export const INITIAL_FINANCE_SYNC: MockFinanceSync[] = [
  { id: "DEMO-SYNC-001", orderId: "ORD-9021", amount: "29.99", status: "pending", createdAt: "2026-10-23T11:00:00Z", attempts: [] },
  { id: "DEMO-SYNC-002", orderId: "ORD-9023", amount: "39.98", status: "synced", createdAt: "2026-10-23T11:10:00Z", attempts: [{ id: "DEMO-SYNC-ATTEMPT-002", timestamp: "2026-10-23T11:11:00Z", result: "synced" }] },
  { id: "DEMO-SYNC-003", orderId: "ORD-9021", amount: "29.99", status: "failed", errorCode: "destination_unavailable", createdAt: "2026-10-23T11:20:00Z", attempts: [{ id: "DEMO-SYNC-ATTEMPT-003", timestamp: "2026-10-23T11:21:00Z", result: "failed", errorCode: "destination_unavailable" }] },
];

export interface MockPrivacyRequest {
  id: string;
  customerId?: string;
  type?: string;
  status?: string;
  verification?: string;
  submittedAt?: string;
  updatedAt?: string;
  summary?: string;
  // A fictional review scenario; not a case-specific production authority.
  demoReviewEnabled: boolean;
  revision: number;
  notes: { id: string; text: string; author: string; timestamp: string }[];
  activity: { id: string; description: string; actor: string; timestamp: string }[];
}

export const INITIAL_PRIVACY_REQUESTS: MockPrivacyRequest[] = [
  { id: "DEMO-PRIV-001", customerId: "USR-8821", type: "access", status: "requested", verification: "not_established", submittedAt: "2026-10-23T10:00:00Z", updatedAt: "2026-10-23T10:00:00Z", summary: "Synthetic data-access review scenario. No customer records were collected or authorized for disclosure.", demoReviewEnabled: true, revision: 1, notes: [], activity: [] },
  { id: "DEMO-PRIV-002", customerId: "USR-8822", type: "deletion", status: "reviewing", verification: "not_established", submittedAt: "2026-10-23T10:10:00Z", updatedAt: "2026-10-23T10:10:00Z", summary: "Synthetic deletion-request review scenario. No deletion, unpublication, session change or customer notification has occurred.", demoReviewEnabled: true, revision: 1, notes: [], activity: [] },
  { id: "DEMO-PRIV-003", customerId: "USR-8823", type: "access", status: "held", submittedAt: "2026-10-23T10:20:00Z", updatedAt: "2026-10-23T10:20:00Z", summary: "Synthetic review awaiting approved prerequisites. Held is a fixture state, not evidence of an actual legal hold or retention deadline. No reviewer is configured for this example.", demoReviewEnabled: false, revision: 1, notes: [], activity: [] },
  { id: "DEMO-PRIV-004", customerId: "USR-8821", type: "deletion", status: "requested", verification: "not_established", submittedAt: "2026-10-23T10:30:00Z", updatedAt: "2026-10-23T10:30:00Z", summary: "Synthetic request awaiting review. Identity, policy and retention prerequisites remain unverified.", demoReviewEnabled: true, revision: 1, notes: [], activity: [] },
];

export interface MockNotification {
  id: string;
  event?: string;
  category?: string;
  channel?: string;
  status?: string;
  recipientId?: string;
  maskedDestination?: string;
  related?: { kind: "order" | "case" | "shipment"; id: string };
  createdAt?: string;
  updatedAt?: string;
  templateRef?: string;
  title?: string;
  summary?: string;
  sensitive?: boolean;
  attempts?: { number: number; timestamp: string; outcome: string; errorCode?: string }[];
}

// Isolated monitoring scenarios, not generated by orders/cases or provider activity.
// Email and outbox states follow the documented contract; demo.* events/categories
// and related-record metadata do not declare new production notification triggers.
export const INITIAL_NOTIFICATIONS: MockNotification[] = [
  { id: "DEMO-NTF-001", event: "demo.order_notice", category: "Order demo", channel: "email", status: "pending", recipientId: "USR-8821", maskedDestination: "a•••@example.invalid", related: { kind: "order", id: "ORD-9021" }, createdAt: "2026-10-23T09:00:00Z", updatedAt: "2026-10-23T09:00:00Z", templateRef: "DEMO-TEMPLATE-ORDER", title: "Demo order notice", summary: "Synthetic order monitoring example. No message was created or sent.", attempts: [] },
  { id: "DEMO-NTF-002", event: "demo.case_notice", category: "Support demo", channel: "email", status: "dead", recipientId: "USR-8822", maskedDestination: "t•••@example.invalid", related: { kind: "case", id: "DEMO-CASE-002" }, createdAt: "2026-10-23T09:10:00Z", updatedAt: "2026-10-23T09:12:00Z", templateRef: "DEMO-TEMPLATE-SUPPORT", title: "Demo case notice", summary: "Synthetic terminal-failure example. No customer communication occurred.", attempts: [{ number: 1, timestamp: "2026-10-23T09:12:00Z", outcome: "failed", errorCode: "provider_failure" }] },
  { id: "DEMO-NTF-003", event: "demo.shipment_notice", category: "Shipment demo", channel: "email", status: "sent", recipientId: "USR-8821", maskedDestination: "a•••@example.invalid", related: { kind: "shipment", id: "DEMO-SHIP-001" }, createdAt: "2026-10-23T09:20:00Z", updatedAt: "2026-10-23T09:21:00Z", templateRef: "DEMO-TEMPLATE-SHIPMENT", title: "Demo shipment notice", summary: "Synthetic provider-acceptance scenario only. No provider was called and no delivery was confirmed.", attempts: [{ number: 1, timestamp: "2026-10-23T09:21:00Z", outcome: "sent" }] },
  { id: "DEMO-NTF-004", event: "finder_message.created", category: "Finder alert", channel: "email", status: "retry", recipientId: "USR-8823", maskedDestination: "b•••@example.invalid", sensitive: true, createdAt: "2026-10-23T09:30:00Z", updatedAt: "2026-10-23T09:31:00Z", attempts: [{ number: 1, timestamp: "2026-10-23T09:31:00Z", outcome: "failed", errorCode: "rate_limited" }] },
  { id: "DEMO-NTF-005", event: "demo.order_notice", category: "Order demo", channel: "email", status: "leased", recipientId: "USR-8823", maskedDestination: "b•••@example.invalid", related: { kind: "order", id: "ORD-9023" }, createdAt: "2026-10-23T09:40:00Z", updatedAt: "2026-10-23T09:40:00Z" },
];

export interface MockSupportCase {
  id: string;
  customerId?: string;
  subject?: string;
  description?: string;
  category: string;
  priority: string;
  status: string;
  // Explicit synthetic handling scenario, never an authenticated employee identity.
  demoScope: "assigned" | "unassigned" | "other";
  requiresEscalation: boolean;
  hasActiveHold: boolean;
  revision: number;
  createdAt?: string;
  updatedAt?: string;
  notes: { id: string; text: string; author: string; timestamp: string }[];
  activity: { id: string; event: string; actor: string; timestamp: string }[];
}

export const INITIAL_SUPPORT_CASES: MockSupportCase[] = [
  { id: "DEMO-CASE-001", customerId: "USR-8821", subject: "Product care guidance", description: "Synthetic request for general care instructions. No customer message was received.", category: "other", priority: "normal", status: "open", demoScope: "assigned", requiresEscalation: false, hasActiveHold: false, revision: 1, createdAt: "2026-10-23T08:00:00Z", updatedAt: "2026-10-23T08:00:00Z", notes: [], activity: [] },
  { id: "DEMO-CASE-002", customerId: "USR-8822", subject: "Lost tag guidance", description: "Synthetic lost-tag assistance scenario. No finder content or location is available.", category: "lost_tag", priority: "high", status: "investigating", demoScope: "assigned", requiresEscalation: false, hasActiveHold: false, revision: 1, createdAt: "2026-10-23T08:10:00Z", updatedAt: "2026-10-23T08:10:00Z", notes: [], activity: [] },
  { id: "DEMO-CASE-003", customerId: "USR-8823", subject: "General product question", description: "Synthetic resolved product-question scenario; no earlier conversation or resolution evidence is recorded.", category: "other", priority: "low", status: "resolved", demoScope: "assigned", requiresEscalation: false, hasActiveHold: false, revision: 1, createdAt: "2026-10-23T08:20:00Z", updatedAt: "2026-10-23T08:20:00Z", notes: [], activity: [] },
  { id: "DEMO-CASE-004", customerId: "USR-8821", subject: "Ownership review request", description: "Synthetic ownership-dispute scenario. Separate authorized governance review is required; no private QR data is included.", category: "ownership_dispute", priority: "urgent", status: "investigating", demoScope: "assigned", requiresEscalation: true, hasActiveHold: false, revision: 1, createdAt: "2026-10-23T08:30:00Z", updatedAt: "2026-10-23T08:30:00Z", notes: [], activity: [] },
  { id: "DEMO-CASE-005", category: "other", priority: "normal", status: "open", demoScope: "unassigned", requiresEscalation: false, hasActiveHold: false, revision: 1, createdAt: "2026-10-23T08:40:00Z", updatedAt: "2026-10-23T08:40:00Z", notes: [], activity: [] },
];

export interface MockShipmentEvent {
  id: string;
  status: string;
  timestamp: string;
  actor: string;
  note?: string;
}

export interface MockShipment {
  id: string;
  orderId: string;
  courier?: string;
  trackingReference?: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  // This optional value is synthetic-only, never fetched from customer profiles.
  delivery?: { recipient: string; address: string; city?: string };
  events: MockShipmentEvent[];
}

export const INITIAL_SHIPMENTS: MockShipment[] = [
  { id: "DEMO-SHIP-001", orderId: "ORD-9021", courier: "Demo Courier — no carrier service", trackingReference: "DEMO-NONFUNCTIONAL-TRACK-001", status: "dispatched", createdAt: "2026-10-23T09:00:00Z", updatedAt: "2026-10-23T09:00:00Z", events: [{ id: "DEMO-SHIP-EVENT-001", status: "dispatched", timestamp: "2026-10-23T09:00:00Z", actor: "Demo fixture", note: "Synthetic dispatched scenario; no courier booking or real handoff occurred." }] },
  { id: "DEMO-SHIP-002", orderId: "ORD-9023", trackingReference: "DEMO-NONFUNCTIONAL-TRACK-002", status: "exception", createdAt: "2026-10-23T09:10:00Z", updatedAt: "2026-10-23T09:10:00Z", events: [{ id: "DEMO-SHIP-EVENT-002", status: "exception", timestamp: "2026-10-23T09:10:00Z", actor: "Demo fixture", note: "Synthetic delivery-issue scenario only; not a report from a carrier." }] },
];

export interface MockPrintInspection {
  id: string;
  outcome: "Passed" | "Rejected";
  timestamp: string;
  inspector: string;
  reason?: string;
  note?: string;
}

export interface MockPrintJob {
  id: string;
  orderId?: string;
  legacySummary?: string;
  // Isolated tabletop example; never a fabricated purchase or live allocation.
  sampleItem?: {
    id: string;
    title: string;
    commerceModel: "single_qr";
    sizes: { label: string; copies: number }[];
  };
  status: "queued" | "ready";
  qaStatus: "Awaiting Review" | "Passed" | "Rejected";
  tabletopReviewEnabled: boolean;
  createdAt: string;
  updatedAt: string;
  inspections: MockPrintInspection[];
}

export const INITIAL_PRINT_JOBS: MockPrintJob[] = [
  { id: "DEMO-PRINT-001", orderId: "ORD-9023", legacySummary: "QR Sticker Set (x2)", status: "queued", qaStatus: "Awaiting Review", tabletopReviewEnabled: false, createdAt: "2026-10-23T08:00:00Z", updatedAt: "2026-10-23T08:00:00Z", inspections: [] },
  { id: "DEMO-PRINT-002", sampleItem: { id: "DEMO-ITEM-A", title: "Synthetic sticker inspection sample A", commerceModel: "single_qr", sizes: [{ label: "Example size A", copies: 2 }, { label: "Example size B", copies: 1 }] }, status: "ready", qaStatus: "Awaiting Review", tabletopReviewEnabled: true, createdAt: "2026-10-23T08:10:00Z", updatedAt: "2026-10-23T08:10:00Z", inspections: [] },
  { id: "DEMO-PRINT-003", sampleItem: { id: "DEMO-ITEM-B", title: "Synthetic sticker inspection sample B", commerceModel: "single_qr", sizes: [{ label: "Example size A", copies: 2 }] }, status: "ready", qaStatus: "Awaiting Review", tabletopReviewEnabled: true, createdAt: "2026-10-23T08:20:00Z", updatedAt: "2026-10-23T08:20:00Z", inspections: [] },
];

export function demoPrintCopies(job: MockPrintJob): number | undefined {
  const sizes = job.sampleItem?.sizes;
  if (!sizes?.length || sizes.some(size => !Number.isSafeInteger(size.copies) || size.copies <= 0)) return undefined;
  const copies = sizes.reduce((total, size) => total + size.copies, 0);
  return Number.isSafeInteger(copies) ? copies : undefined;
}

export function demoPrintReviewAvailable(job: MockPrintJob) {
  return job.tabletopReviewEnabled && job.status === "ready" && job.sampleItem?.commerceModel === "single_qr" &&
    !!job.sampleItem.id && demoPrintCopies(job) !== undefined && job.qaStatus === "Awaiting Review" && !job.inspections.length;
}

export interface MockProductImage {
  publicId?: string;
  url?: string;
  alt?: string;
  sortOrder?: number;
  primary?: boolean;
}

export interface MockProductVariant {
  id: string;
  sku: string;
  name: string;
  sizeMm?: string;
  material?: string;
  color?: string;
  currencyCode?: string;
  unitPrice: string | number;
  fulfillmentMethod?: string;
  templateKey?: string;
  templateVersion?: number;
  isActive?: boolean;
}

export interface MockProduct {
  id: string;
  name: string;
  sku: string;
  category: string;
  status: "published" | "draft" | "archived";
  price: number;
  price_per_copy?: string;
  max_order_copies?: number;
  stock: number;
  templateKey: string;
  variants: string[];
  updatedAt: string;
  slug?: string;
  description?: string;
  isFeatured?: boolean;
  featuredSortOrder?: number;
  allowsNewPair?: boolean;
  allowsExistingQr?: boolean;
  version?: number;
  images?: MockProductImage[];
  variantRecords?: MockProductVariant[];
  coverImage?: string;
}

export interface MockTemplateRevision {
  id: string;
  revisionNumber: number;
  status: "draft" | "published" | "retired";
  versionNote?: string;
  labelDimensions?: string;
  supportedTypes: string[];
  updatedAt: string;
  author: string;
  previewAvailable?: boolean;
  rowVersion?: number;
}

export interface MockPrintTemplate {
  id: string;
  key: string;
  name: string;
  revision: number;
  status: "published" | "draft";
  supportedTypes: string[];
  size?: string;
  lastAuthor: string;
  purpose?: string;
  rowVersion?: number;
  revisions?: MockTemplateRevision[];
}

export interface MockUser {
  id: string;
  name: string;
  email: string;
  role: string;
  status: "Active" | "Suspended";
  qrCount: number;
  registeredAt: string;
  mfaEnrolled: boolean;
  governanceRevision?: number;
  governanceHistory?: MockAccountGovernanceEvent[];
}

export interface MockAccountGovernanceEvent {
  id: string;
  action: "suspend" | "restore";
  reason: string;
  caseReference: string;
  actor: string;
  timestamp: string;
}

export interface MockOrder {
  id: string;
  customer: string;
  items: string;
  total: number;
  status: "Dispatched" | "Pending Review" | "Processing" | "Cancelled";
  payment: "Verified" | "Under Review" | "Failed";
  date: string;
  // Optional frontend display metadata, never reconstructed from today's catalog.
  currencyCode?: string;
  customerId?: string;
  lineItems?: MockOrderItemSnapshot[];
  subtotal?: number | string;
  shippingAmount?: number | string;
  shipmentStatus?: string;
  activity?: MockOrderActivity[];
  paymentMethod?: string;
  paymentSubmittedAt?: string;
  demoPaymentReviews?: MockPaymentReview[];
}

export interface MockPaymentReview {
  id: string;
  decision: "Follow-up required";
  reviewer: string;
  timestamp: string;
  note: string;
}

export interface MockOrderItemSnapshot {
  id: string;
  title: string;
  quantity: number;
  unitPrice?: number | string;
  lineTotal?: number | string;
}

export interface MockOrderActivity {
  id: string;
  type: string;
  timestamp: string;
  actor?: string;
  description?: string;
}

export interface MockAuditLog {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  target: string;
  details: string;
}

export interface MockQRBatch {
  id: string;
  size: number;
  pairsCount: number;
  generatedAt: string;
  status: "QA Passed" | "In QA" | "Awaiting QA" | "Rejected";
  exported: boolean;
  notes?: string;
  isDemo?: boolean;
  printMaterial?: string;
  eccLevel?: "M" | "Q";
  intendedEnvironment?: "indoor" | "outdoor";
  lostSymbolSizeMm?: string;
  iceSymbolSizeMm?: string;
  qaMetadata?: {
    inspectedAt?: string;
    inspector?: string;
    passedRounds?: number;
    notes?: string;
  };
}

export interface MockQAPair {
  id: string;
  batchId: string;
  status: "Awaiting QA" | "Passed" | "Quarantined";
  lastInspectedAt?: string;
  inspector?: string;
  rejectionReason?: string;
  notes?: string;
}

export interface MockQAInspection {
  id: string;
  pairId: string;
  batchId: string;
  outcome: "Passed" | "Quarantined";
  rejectionReason?: string;
  notes?: string;
  inspector: string;
  timestamp: string;
}

export interface MockAdminDatabase {
  monitoringJobs: import("./admin-monitoring").MockMonitoringJob[];
  monitoringAlerts: import("./admin-monitoring").MockMonitoringAlert[];
  storageRecords: MockStorageRecord[];
  financeSync: MockFinanceSync[];
  privacyRequests: MockPrivacyRequest[];
  notifications: MockNotification[];
  supportCases: MockSupportCase[];
  shipments: MockShipment[];
  printJobs: MockPrintJob[];
  products: MockProduct[];
  printTemplates: MockPrintTemplate[];
  users: MockUser[];
  orders: MockOrder[];
  auditLogs: MockAuditLog[];
  qrBatches: MockQRBatch[];
  qaPairs: MockQAPair[];
  qaInspections: MockQAInspection[];
}

export const INITIAL_SEED_DATA: MockAdminDatabase = {
  // No telemetry collector/job feed/alert lifecycle has been accepted. Never
  // turn notification, order, print or finance statuses into monitoring events.
  monitoringJobs: [],
  monitoringAlerts: [],
  storageRecords: INITIAL_STORAGE_RECORDS,
  financeSync: INITIAL_FINANCE_SYNC,
  privacyRequests: INITIAL_PRIVACY_REQUESTS,
  notifications: INITIAL_NOTIFICATIONS,
  supportCases: INITIAL_SUPPORT_CASES,
  shipments: INITIAL_SHIPMENTS,
  printJobs: INITIAL_PRINT_JOBS,
  products: [
    {
      id: "PROD-101",
      name: "SafeReturn Medical Wristband",
      sku: "SR-WB-MED-01",
      category: "Wearables",
      status: "published",
      price: 29.99,
      stock: 142,
      templateKey: "TP-WRIST-V2",
      variants: ["Red/ICE", "Blue/Medical"],
      updatedAt: "2026-10-18",
    },
    {
      id: "PROD-102",
      name: "Kids Safety Backpack Tag",
      sku: "SR-TG-KID-02",
      category: "Tags",
      status: "published",
      price: 14.5,
      stock: 88,
      templateKey: "TP-TAG-MINI-V1",
      variants: ["Neon Yellow", "Pink"],
      updatedAt: "2026-10-19",
    },
    {
      id: "PROD-103",
      name: "Dementia Care QR Sticker Set (4x)",
      sku: "SR-ST-DEM-04",
      category: "Stickers",
      status: "draft",
      price: 19.99,
      stock: 250,
      templateKey: "TP-STICKER-4X",
      variants: ["Standard Clear"],
      updatedAt: "2026-10-21",
    },
  ],
  printTemplates: [
    {
      id: "TMP-001",
      key: "TP-WRIST-V2",
      name: "Standard Wristband Layout",
      revision: 2,
      status: "published",
      supportedTypes: ["Wristband"],
      size: "20mm x 200mm",
      lastAuthor: "ops_lead",
      purpose: "ice",
      rowVersion: 1,
      revisions: [
        {
          id: "REV-TMP-001-2",
          revisionNumber: 2,
          status: "published",
          versionNote: "Initial certified wristband layout",
          labelDimensions: "20mm x 200mm",
          supportedTypes: ["Wristband"],
          updatedAt: "2026-10-15",
          author: "ops_lead",
          previewAvailable: false,
          rowVersion: 1,
        },
      ],
    },
    {
      id: "TMP-002",
      key: "TP-TAG-MINI-V1",
      name: "Compact Keyring Tag",
      revision: 1,
      status: "published",
      supportedTypes: ["Tag"],
      size: "30mm x 30mm",
      lastAuthor: "graphics_admin",
      purpose: "lost",
      rowVersion: 1,
      revisions: [
        {
          id: "REV-TMP-002-1",
          revisionNumber: 1,
          status: "published",
          versionNote: "Square keychain tag production release",
          labelDimensions: "30mm x 30mm",
          supportedTypes: ["Tag"],
          updatedAt: "2026-10-18",
          author: "graphics_admin",
          previewAvailable: false,
          rowVersion: 1,
        },
      ],
    },
    {
      id: "TMP-003",
      key: "TP-STICKER-4X",
      name: "4x Quad Sticker Sheet Layout",
      revision: 3,
      status: "draft",
      supportedTypes: ["Sticker Sheet"],
      size: "100mm x 150mm",
      lastAuthor: "product_team",
      purpose: "lost",
      rowVersion: 1,
      revisions: [
        {
          id: "REV-TMP-003-3",
          revisionNumber: 3,
          status: "draft",
          versionNote: "Draft quad sticker sheet spacing revision",
          labelDimensions: "100mm x 150mm",
          supportedTypes: ["Sticker Sheet"],
          updatedAt: "2026-10-21",
          author: "product_team",
          previewAvailable: false,
          rowVersion: 1,
        },
      ],
    },
  ],
  users: [
    {
      id: "USR-8821",
      name: "Amina Khan",
      email: "amina.k@example.com",
      role: "Customer",
      status: "Active",
      qrCount: 2,
      registeredAt: "2026-08-12",
      mfaEnrolled: true,
    },
    {
      id: "USR-8822",
      name: "Tariq Mahmood",
      email: "tariq.m@example.com",
      role: "Customer",
      status: "Suspended",
      qrCount: 1,
      registeredAt: "2026-09-01",
      mfaEnrolled: false,
    },
    {
      id: "USR-8823",
      name: "Dr. Bilal Ahmed",
      email: "bilal.ahmed@clinic.pk",
      role: "Customer",
      status: "Active",
      qrCount: 5,
      registeredAt: "2026-09-15",
      mfaEnrolled: true,
    },
    {
      id: "USR-9001",
      name: "Sarah Jenkins",
      email: "sarah.j@safereturn.org",
      role: "Operations Staff",
      status: "Active",
      qrCount: 0,
      registeredAt: "2026-01-10",
      mfaEnrolled: true,
    },
  ],
  orders: [
    {
      id: "ORD-9021",
      customer: "Amina Khan",
      items: "Medical Wristband (x1)",
      total: 29.99,
      status: "Dispatched",
      payment: "Verified",
      date: "2026-10-18",
    },
    {
      id: "ORD-9022",
      customer: "Tariq Mahmood",
      items: "Kids Backpack Tag (x2)",
      total: 29.0,
      status: "Pending Review",
      payment: "Under Review",
      date: "2026-10-20",
    },
    {
      id: "ORD-9023",
      customer: "Dr. Bilal Ahmed",
      items: "QR Sticker Set (x2)",
      total: 39.98,
      status: "Processing",
      payment: "Verified",
      date: "2026-10-21",
    },
  ],
  auditLogs: [
    {
      id: "LOG-551",
      timestamp: "2026-10-21 19:42:10",
      actor: "security_admin",
      action: "API-320 Account Suspended",
      target: "USR-8822",
      details: "Reason: Suspicious recovery escalation request",
    },
    {
      id: "LOG-550",
      timestamp: "2026-10-21 18:15:33",
      actor: "operations",
      action: "API-221 Product Draft Created",
      target: "PROD-103",
      details: "Dementia Care QR Sticker Set created",
    },
    {
      id: "LOG-549",
      timestamp: "2026-10-20 11:05:01",
      actor: "finance",
      action: "API-241 Payment Review Approved",
      target: "ORD-9021",
      details: "Settlement confirmed via manual review",
    },
  ],
  qrBatches: [
    {
      id: "BATCH-2026-09",
      size: 1000,
      pairsCount: 500,
      generatedAt: "2026-10-01",
      status: "QA Passed",
      exported: true,
      printMaterial: "synthetic-waterproof",
      eccLevel: "Q",
      intendedEnvironment: "indoor",
      isDemo: true,
      notes: "Initial prototype fixture: full pass across both lost and ICE tag pairs.",
      qaMetadata: {
        inspectedAt: "2026-10-01",
        inspector: "qa_operator_1",
        passedRounds: 1,
        notes: "Initial prototype fixture: full pass across both lost and ICE tag pairs.",
      },
    },
    {
      id: "BATCH-2026-10",
      size: 500,
      pairsCount: 250,
      generatedAt: "2026-10-15",
      status: "In QA",
      exported: false,
      printMaterial: "synthetic-waterproof",
      eccLevel: "Q",
      intendedEnvironment: "indoor",
      isDemo: true,
      notes: "First-round sample scans in progress; quiet zone and contrast verification underway.",
      qaMetadata: {
        inspectedAt: "2026-10-16",
        inspector: "qa_operator_2",
        passedRounds: 0,
        notes: "First-round sample scans in progress; quiet zone and contrast verification underway.",
      },
    },
  ],
  qaPairs: [
    {
      id: "PAIR-2026-001",
      batchId: "BATCH-2026-09",
      status: "Passed",
      lastInspectedAt: "2026-10-01 14:20:00",
      inspector: "sarah.j@safereturn.org",
      notes: "Visual contrast and quiet zone verified across both lost and ICE tags.",
    },
    {
      id: "PAIR-2026-002",
      batchId: "BATCH-2026-09",
      status: "Passed",
      lastInspectedAt: "2026-10-01 14:35:12",
      inspector: "sarah.j@safereturn.org",
      notes: "Sample scan passed under standard ambient lighting.",
    },
    {
      id: "PAIR-2026-003",
      batchId: "BATCH-2026-10",
      status: "Quarantined",
      lastInspectedAt: "2026-10-16 11:15:30",
      inspector: "operations",
      rejectionReason: "QR readability issue",
      notes: "Sub-millimeter quiet zone clipping on ICE tag; scanner camera failed decode.",
    },
    {
      id: "PAIR-2026-004",
      batchId: "BATCH-2026-10",
      status: "Awaiting QA",
    },
    {
      id: "PAIR-2026-005",
      batchId: "BATCH-2026-10",
      status: "Awaiting QA",
    },
    {
      id: "PAIR-2026-006",
      batchId: "BATCH-2026-10",
      status: "Awaiting QA",
    },
  ],
  qaInspections: [
    {
      id: "QA-INSP-101",
      pairId: "PAIR-2026-001",
      batchId: "BATCH-2026-09",
      outcome: "Passed",
      inspector: "Sarah Jenkins (Operations)",
      timestamp: "2026-10-01 14:20:00",
      notes: "Visual contrast and quiet zone verified across both lost and ICE tags.",
    },
    {
      id: "QA-INSP-102",
      pairId: "PAIR-2026-002",
      batchId: "BATCH-2026-09",
      outcome: "Passed",
      inspector: "Sarah Jenkins (Operations)",
      timestamp: "2026-10-01 14:35:12",
      notes: "Sample scan passed under standard ambient lighting.",
    },
    {
      id: "QA-INSP-103",
      pairId: "PAIR-2026-003",
      batchId: "BATCH-2026-10",
      outcome: "Quarantined",
      rejectionReason: "QR readability issue",
      inspector: "Operations Staff",
      timestamp: "2026-10-16 11:15:30",
      notes: "Sub-millimeter quiet zone clipping on ICE tag; scanner camera failed decode.",
    },
  ],
};

const STORAGE_KEY = "safereturn_demo_db";
const CHANGE_EVENT = "safereturn_admin_mock_data_change";

let memoryStore: MockAdminDatabase | null = null;

export function loadAdminMockData(): MockAdminDatabase {
  if (typeof window === "undefined") {
    return memoryStore
      ? JSON.parse(JSON.stringify(memoryStore))
      : JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
    }
    const parsed = JSON.parse(raw);
    return {
      monitoringJobs: Array.isArray(parsed.monitoringJobs) ? parsed.monitoringJobs : [],
      monitoringAlerts: Array.isArray(parsed.monitoringAlerts) ? parsed.monitoringAlerts : [],
      storageRecords: Array.isArray(parsed.storageRecords) ? parsed.storageRecords : INITIAL_STORAGE_RECORDS,
      financeSync: Array.isArray(parsed.financeSync) ? parsed.financeSync : INITIAL_FINANCE_SYNC,
      privacyRequests: Array.isArray(parsed.privacyRequests) ? parsed.privacyRequests : INITIAL_PRIVACY_REQUESTS,
      notifications: Array.isArray(parsed.notifications) ? parsed.notifications : INITIAL_NOTIFICATIONS,
      supportCases: Array.isArray(parsed.supportCases) ? parsed.supportCases : INITIAL_SUPPORT_CASES,
      shipments: Array.isArray(parsed.shipments) ? parsed.shipments : INITIAL_SHIPMENTS,
      printJobs: Array.isArray(parsed.printJobs) ? parsed.printJobs : INITIAL_PRINT_JOBS,
      products: Array.isArray(parsed.products) ? parsed.products : INITIAL_SEED_DATA.products,
      printTemplates: Array.isArray(parsed.printTemplates)
        ? parsed.printTemplates
        : INITIAL_SEED_DATA.printTemplates,
      users: Array.isArray(parsed.users) ? parsed.users : INITIAL_SEED_DATA.users,
      orders: Array.isArray(parsed.orders) ? parsed.orders : INITIAL_SEED_DATA.orders,
      auditLogs: Array.isArray(parsed.auditLogs) ? parsed.auditLogs : INITIAL_SEED_DATA.auditLogs,
      qrBatches: Array.isArray(parsed.qrBatches) ? parsed.qrBatches : INITIAL_SEED_DATA.qrBatches,
      qaPairs: Array.isArray(parsed.qaPairs) ? parsed.qaPairs : INITIAL_SEED_DATA.qaPairs,
      qaInspections: Array.isArray(parsed.qaInspections)
        ? parsed.qaInspections
        : INITIAL_SEED_DATA.qaInspections,
    };
  } catch {
    return JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  }
}

export function saveAdminMockData(data: MockAdminDatabase): void {
  memoryStore = JSON.parse(JSON.stringify(data));
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
  } catch {
    // Storage might be restricted
  }
}

export function resetAdminMockData(): void {
  memoryStore = JSON.parse(JSON.stringify(INITIAL_SEED_DATA));
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_SEED_DATA));
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
  } catch {
    throw new Error("Demo reset could not be persisted in browser storage.");
  }
}

// Selectors
export function addDemoPrivacyReviewNote(input: {
  requestId: string; note: string; expectedRevision: number; confirmed: boolean;
  authenticatedRoles: readonly string[]; previewRole: string;
}): { success: true } | { success: false; error: string } {
  if (!canReviewDemoPrivacy(input.authenticatedRoles) || input.previewRole !== "authenticated") return { success: false, error: "Explicit authenticated Security Admin is required. Role preview does not grant privacy-review authority." };
  const note = typeof input.note === "string" ? input.note.trim() : "";
  if (input.confirmed !== true || note.length < 4 || note.length > 1000 || !/\p{L}/u.test(note)) return { success: false, error: "Review and confirm a meaningful synthetic note of 4–1000 characters." };
  if (!Number.isSafeInteger(input.expectedRevision) || input.expectedRevision < 1) return { success: false, error: "A valid request revision is required." };
  try {
    if (typeof window !== "undefined") {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const value = JSON.parse(raw);
        if (!value || typeof value !== "object" || Array.isArray(value) || (value.privacyRequests !== undefined && (!Array.isArray(value.privacyRequests) || !value.privacyRequests.every(isMockPrivacyRequest))) || ["users", "auditLogs"].some(key => value[key] !== undefined && !Array.isArray(value[key]))) throw Error();
      }
    }
    const db: MockAdminDatabase = JSON.parse(JSON.stringify(loadAdminMockData()));
    const entry = db.privacyRequests.find(entry => entry?.id === input.requestId);
    const fixture = INITIAL_PRIVACY_REQUESTS.find(fixture => fixture.id === input.requestId);
    if (!entry || !isMockPrivacyRequest(entry) || !fixture || !fixture.demoReviewEnabled || !entry.demoReviewEnabled || entry.customerId !== fixture.customerId || entry.type !== fixture.type) return { success: false, error: "This synthetic review scenario is unavailable or has no configured demo reviewer." };
    if (entry.revision !== input.expectedRevision) return { success: false, error: "Request changed. Review the refreshed record and discard the stale draft before retrying." };
    if (!["requested", "reviewing", "held"].includes(entry.status ?? "") || !db.users.some(user => user?.id === entry.customerId && user.role === "Customer")) return { success: false, error: "A supported request state and valid synthetic customer reference are required." };
    const timestamp = new Date().toISOString();
    const id = `DEMO-PRIV-NOTE-${entry.id}-${entry.revision + 1}`;
    entry.notes.push({ id, text: note, author: "Demo Security Admin review scenario", timestamp });
    entry.activity.push({ id, description: "Internal demo review note added", actor: "Demo Security Admin review scenario", timestamp });
    entry.updatedAt = timestamp; entry.revision += 1;
    db.auditLogs.unshift({ id, timestamp, actor: "Demo Security Admin review scenario", action: "Internal demo privacy review note added", target: entry.id, details: "Synthetic review annotation only. Note text retained only in demo request. No verification, approval, export, erasure, closure or customer contact." });
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
    memoryStore = JSON.parse(JSON.stringify(db));
    if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
    return { success: true };
  } catch { return { success: false, error: "Unable to save demo review note. Browser storage is invalid, unavailable or full. No change was recorded." }; }
}

export function updateDemoSupportCase(input: {
  caseId: string; expectedRevision: number; action: "note" | "status"; note?: string; nextStatus?: string;
  confirmed: boolean; authenticatedRoles: readonly string[]; previewRole: string;
}): { success: true } | { success: false; error: string } {
  if (!canManageDemoSupport(input.authenticatedRoles) || input.previewRole !== "authenticated") return { success: false, error: "Authenticated Support is required. Role preview and other admin roles do not grant case rights." };
  if (!input.confirmed || !Number.isSafeInteger(input.expectedRevision) || input.expectedRevision < 1) return { success: false, error: "Confirm the demo change with a valid case revision." };
  if (!["note", "status"].includes(input.action)) return { success: false, error: "Unsupported case action. Assignment and escalation are unavailable." };
  const note = input.note?.trim() ?? "";
  if (input.action === "note" && (note.length < 4 || note.length > 2000 || !/\p{L}/u.test(note))) return { success: false, error: "Enter a meaningful internal demo note of 4–2000 characters." };
  try {
    if (typeof window !== "undefined") {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) { const value = JSON.parse(raw); if (!value || typeof value !== "object" || Array.isArray(value) || (value.supportCases !== undefined && (!Array.isArray(value.supportCases) || !value.supportCases.every(isDemoSupportCase)))) throw Error(); }
    }
    const db: MockAdminDatabase = JSON.parse(JSON.stringify(loadAdminMockData()));
    const entry = db.supportCases.find(entry => entry.id === input.caseId && entry.demoScope === "assigned");
    if (!entry || !isDemoSupportCase(entry)) return { success: false, error: "Assigned synthetic case not found. Unassigned or other-handler cases cannot be changed." };
    if (entry.revision !== input.expectedRevision) return { success: false, error: "Case changed. Review the refreshed case before retrying." };
    if (!["open", "investigating", "resolved"].includes(entry.status) || !["activation", "lost_tag", "payment", "privacy", "ownership_dispute", "other"].includes(entry.category)) return { success: false, error: "Closed or unsupported cases cannot be changed." };
    if (!db.users.some(user => user && user.id === entry.customerId && user.role === "Customer")) return { success: false, error: "A valid synthetic customer reference is required for case updates." };
    if (input.action === "status" && !demoSupportNextStates(entry).includes(input.nextStatus ?? "")) return { success: false, error: "This transition is unavailable. Sensitive cases and active holds cannot be resolved or closed here." };
    const timestamp = new Date().toISOString();
    const eventId = `DEMO-CASE-EVENT-${entry.id}-${entry.revision + 1}`;
    const event = input.action === "note" ? "Internal demo note added" : `Mock status updated: ${entry.status} → ${input.nextStatus}`;
    if (input.action === "note") entry.notes.push({ id: eventId, text: note, author: "Demo Support scenario", timestamp });
    else entry.status = input.nextStatus!;
    entry.revision += 1; entry.updatedAt = timestamp;
    entry.activity.push({ id: eventId, event, actor: "Demo Support scenario", timestamp });
    db.auditLogs.unshift({ id: eventId, timestamp, actor: "Demo Support scenario", action: event, target: entry.id, details: "Frontend synthetic case change only. Internal note content is not copied to audit; no customer contact, account, financial or QR action." });
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
    memoryStore = JSON.parse(JSON.stringify(db));
    if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
    return { success: true };
  } catch { return { success: false, error: "Unable to save demo case change. Browser storage is invalid, unavailable or full. No change was recorded." }; }
}

export function recordDemoAccountGovernance(input: {
  userId: string; action: "suspend" | "restore"; reason: string; caseReference: string;
  expectedRevision: number; expectedStatus: string; confirmed: boolean;
  authenticatedRoles: readonly string[]; previewRole: string;
}): { success: true } | { success: false; error: string } {
  if (input.previewRole !== "authenticated" || !canGovernDemoUsers(input.authenticatedRoles)) return { success: false, error: "Authenticated Security Admin is required. List access and role preview do not grant governance authority." };
  const reason = input.reason.trim();
  if (!input.confirmed || reason.length < 8 || reason.length > 500 || !/[a-zA-Z\u0600-\u06ff]/.test(reason)) return { success: false, error: "Enter a meaningful demo reason of 8–500 characters and confirm the action." };
  if (!["suspend", "restore"].includes(input.action)) return { success: false, error: "Unsupported demo account action." };
  if (!Number.isSafeInteger(input.expectedRevision) || input.expectedRevision < 1) return { success: false, error: "A valid demo account revision is required." };
  if (input.caseReference !== `DEMO-GOV-${input.userId}`) return { success: false, error: "The synthetic scenario reference does not match this account." };
  try {
    if (typeof window !== "undefined") {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) { const parsed = JSON.parse(raw); if (!parsed || !Array.isArray(parsed.users) || parsed.users.some((user: unknown) => !user || typeof user !== "object")) throw Error(); }
    }
    const db: MockAdminDatabase = JSON.parse(JSON.stringify(loadAdminMockData()));
    const user = db.users.find(user => user.id === input.userId);
    if (!user) return { success: false, error: "Synthetic account not found." };
    if (user.role !== "Customer" || !INITIAL_SEED_DATA.users.some(seed => seed.id === user.id && seed.role === "Customer")) return { success: false, error: "Only supplied synthetic Customer fixtures support demo governance. Staff accounts are unavailable." };
    if ((user.governanceRevision ?? 1) !== input.expectedRevision || user.status !== input.expectedStatus) return { success: false, error: "Account state changed. Close and reopen the dialog before retrying." };
    const requiredStatus = input.action === "suspend" ? "Active" : "Suspended";
    if (user.status !== requiredStatus) return { success: false, error: "This account is not eligible for the selected demo action." };
    const timestamp = new Date().toISOString();
    user.status = input.action === "suspend" ? "Suspended" : "Active";
    user.governanceRevision = (user.governanceRevision ?? 1) + 1;
    user.governanceHistory ??= [];
    user.governanceHistory.push({ id: `DEMO-GOV-EVENT-${Date.now()}-${user.governanceRevision}`, action: input.action, reason, caseReference: input.caseReference, actor: "Demo Security Admin", timestamp });
    db.auditLogs.unshift({ id: `DEMO-GOV-AUDIT-${Date.now()}-${user.governanceRevision}`, actor: "Demo Security Admin", action: input.action === "suspend" ? "Mock account suspended" : "Mock account restored", target: user.id, timestamp, details: "Synthetic customer status change only; no real authorization, session, recovery or QR ownership action. Reason retained only in demo governance history." });
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
    memoryStore = JSON.parse(JSON.stringify(db));
    if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
    return { success: true };
  } catch { return { success: false, error: "Unable to save demo account action. Browser storage is invalid, unavailable or full. No change was recorded." }; }
}

export function recordDemoShipmentTracking(input: {
  shipmentId: string; expectedStatus: string; status: string; note?: string; confirmed: boolean;
  authenticatedRoles: readonly string[]; previewRole: string;
}): { success: true } | { success: false; error: string } {
  if (input.previewRole !== "authenticated" || !canManageDemoShipments(input.authenticatedRoles)) return { success: false, error: "Authenticated Operations or Superadmin is required. Role preview cannot grant tracking rights." };
  if (!input.confirmed || (input.note?.length || 0) > 500) return { success: false, error: "Confirm the demo-only update and keep notes within 500 characters." };
  try {
    if (typeof window !== "undefined") {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const value = JSON.parse(raw);
        if (!value || typeof value !== "object" || Array.isArray(value) || (value.shipments !== undefined && !Array.isArray(value.shipments)) || (value.orders !== undefined && !Array.isArray(value.orders))) throw Error();
      }
    }
    const db: MockAdminDatabase = JSON.parse(JSON.stringify(loadAdminMockData()));
    const shipment = db.shipments.find(shipment => shipment.id === input.shipmentId);
    if (!shipment || !db.orders.some(order => order.id === shipment.orderId)) return { success: false, error: "Shipment or its associated demo order is unavailable. No tracking update was recorded." };
    if (shipment.status !== input.expectedStatus) return { success: false, error: "Shipment status changed. Reopen the tracking dialog before recording another update." };
    if (!demoShipmentTransitions[shipment.status]?.includes(input.status)) return { success: false, error: "This tracking transition is not supported by the demo workflow." };
    const timestamp = new Date().toISOString();
    const actor = input.authenticatedRoles.includes("operations") ? "Demo Operations" : "Demo Superadmin";
    shipment.status = input.status;
    shipment.updatedAt = timestamp;
    shipment.events.push({ id: `DEMO-TRACK-${Date.now()}-${shipment.events.length + 1}`, status: input.status, timestamp, actor, note: input.note?.trim() || undefined });
    db.auditLogs.unshift({ id: `DEMO-SHIP-AUDIT-${Date.now()}`, timestamp, actor, action: "Demo tracking update", target: shipment.id, details: `Synthetic tracking status: ${input.status}. No order, financial, QR, inventory or notification action performed.` });
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
    memoryStore = JSON.parse(JSON.stringify(db));
    if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
    return { success: true };
  } catch { return { success: false, error: "Unable to save demo tracking. Browser storage is invalid, unavailable or full. No update was recorded." }; }
}

export function recordDemoPrintInspection(input: {
  jobId: string; outcome: "Passed" | "Rejected"; reason?: string; note?: string;
  confirmed: boolean; authenticatedRoles: readonly string[]; previewRole: string;
}): { success: true } | { success: false; error: string } {
  if (input.previewRole !== "authenticated" || !canInspectDemoPrintJobs(input.authenticatedRoles)) return { success: false, error: "Authenticated Operations or Superadmin is required; preview cannot grant QA rights." };
  if (!input.confirmed) return { success: false, error: "Confirm this tabletop inspection only; no production release is authorized." };
  if (!["Passed", "Rejected"].includes(input.outcome)) return { success: false, error: "Unsupported demo inspection outcome." };
  if (input.outcome === "Rejected" && !demoPrintReasons.some(reason => reason === input.reason)) return { success: false, error: "Select a demonstration-only rejection reason." };
  if ((input.note?.length || 0) > 500) return { success: false, error: "Inspection notes must be at most 500 characters." };
  try {
    if (typeof window !== "undefined") {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || (parsed.printJobs !== undefined && !Array.isArray(parsed.printJobs))) throw Error();
      }
    }
    const db: MockAdminDatabase = JSON.parse(JSON.stringify(loadAdminMockData()));
    const job = db.printJobs.find(job => job.id === input.jobId);
    if (!job) return { success: false, error: "Demo print job not found." };
    if (!demoPrintReviewAvailable(job)) return { success: false, error: "Inspection unavailable: missing sample prerequisites or an inspection is already recorded. Reinspection is not supported." };
    const timestamp = new Date().toISOString();
    const inspector = input.authenticatedRoles.includes("operations") ? "Demo Operations" : "Demo Superadmin";
    job.inspections.push({ id: `DEMO-PRINT-QA-${Date.now()}`, outcome: input.outcome, timestamp, inspector, reason: input.outcome === "Rejected" ? input.reason : undefined, note: input.note?.trim() || undefined });
    job.qaStatus = input.outcome;
    job.updatedAt = timestamp;
    db.auditLogs.unshift({ id: `DEMO-PRINT-AUDIT-${Date.now()}`, timestamp, actor: inspector, action: `Mock print QA ${input.outcome}`, target: job.id, details: "Tabletop sample review only; no QR batch QA, financial, allocation, inventory or shipment changes." });
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
    memoryStore = JSON.parse(JSON.stringify(db));
    if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
    return { success: true };
  } catch { return { success: false, error: "Unable to save mock print QA. Browser storage is invalid, unavailable or full. No inspection was recorded." }; }
}

// Non-authoritative notes only: never verify settlement or initiate fulfillment.
export function recordDemoPaymentFollowUp(input: {
  orderId: string; note: string; confirmed: boolean;
  authenticatedRoles: readonly string[]; previewRole: string;
}): { success: true } | { success: false; error: string } {
  if (input.previewRole !== "authenticated" || !canReviewDemoPayments(input.authenticatedRoles)) {
    return { success: false, error: "Your authenticated Finance or Superadmin role is required. Role preview cannot grant review rights." };
  }
  const note = input.note.trim();
  if (!input.confirmed || !note || note.length > 500) return { success: false, error: "Confirm the demo-only action and enter a note of 1–500 characters." };
  try {
    // Refuse fallback-fixture writes if saved state is unreadable or malformed.
    if (typeof window !== "undefined") {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (!parsed || !Array.isArray(parsed.orders)) throw Error("Invalid demo store");
      }
    }
    const db: MockAdminDatabase = JSON.parse(JSON.stringify(loadAdminMockData()));
    const order = db.orders.find(order => order.id === input.orderId);
    if (!order) return { success: false, error: "Demo order not found. Refresh the payment list." };
    if (order.payment !== "Under Review") return { success: false, error: "This record is not awaiting review. No changes were made." };
    if (order.demoPaymentReviews?.length) return { success: false, error: "A demo follow-up is already recorded. Duplicate review is unavailable." };
    const timestamp = new Date().toISOString();
    const reviewer = input.authenticatedRoles.includes("finance") ? "Demo Finance" : "Demo Superadmin";
    const review: MockPaymentReview = { id: `DEMO-PAY-REVIEW-${Date.now()}`, decision: "Follow-up required", reviewer, timestamp, note };
    order.demoPaymentReviews = [review];
    db.auditLogs.unshift({ id: `DEMO-PAY-AUDIT-${Date.now()}`, timestamp, actor: reviewer,
      action: "Demo payment follow-up recorded", target: order.id,
      details: "Non-authoritative demo note only. Payment and fulfillment states unchanged." });
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
    memoryStore = JSON.parse(JSON.stringify(db));
    if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
    return { success: true };
  } catch {
    return { success: false, error: "Unable to save demo review. Browser storage is unavailable, invalid or full. No review was recorded." };
  }
}

export function archiveProduct(id: string, actor = "operations"): boolean {
  const db = loadAdminMockData();
  const prod = db.products.find((p) => p.id === id);
  if (!prod) return false;

  prod.status = "archived";
  prod.updatedAt = new Date().toISOString().substring(0, 10);

  const newLog: MockAuditLog = {
    id: `LOG-${Math.floor(100 + Math.random() * 900)}`,
    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
    actor,
    action: "API-222 Product Archived",
    target: id,
    details: `Product '${prod.name}' archived from active catalog`,
  };

  db.auditLogs.unshift(newLog);
  saveAdminMockData(db);
  return true;
}

export interface CreateProductDraftInput {
  name: string;
  category: string;
  price: number;
  max_order_copies?: number;
  description?: string;
  coverImage?: string;
  galleryImages?: string[];
}

export function createProductDraft(
  input: CreateProductDraftInput,
  actor = "operations"
): { success: boolean; product?: MockProduct; error?: string } {
  const db = loadAdminMockData();

  const name = input.name.trim();
  if (!name) {
    return { success: false, error: "Product name is required." };
  }
  if (!input.category) {
    return { success: false, error: "Category is required." };
  }

  if (!Number.isFinite(input.price) || input.price < 0 || input.price > 9999999999.99 || Math.abs(input.price * 100 - Math.round(input.price * 100)) > 0.0001) {
    return { success: false, error: "Enter a valid PKR price per copy with at most two decimal places." };
  }

  if (input.max_order_copies !== undefined && (!Number.isInteger(input.max_order_copies) || input.max_order_copies < 1 || input.max_order_copies > 100)) {
    return { success: false, error: "Maximum combined copies must be between 1 and 100." };
  }

  // Derive unique client-side slug for mock store
  let baseSlug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (!baseSlug) baseSlug = "product";
  let slug = baseSlug;
  let counter = 1;
  while (db.products.some((p) => p.slug === slug)) {
    slug = `${baseSlug}-${counter++}`;
  }

  // Stable mock ID
  const id = `PROD-${Date.now()}`;
  const sku = `SR-DRAFT-${Math.floor(100 + Math.random() * 900)}`;
  const updatedAt = new Date().toISOString().substring(0, 10);

  const defaultVariant: MockProductVariant = {
    id: `VAR-${id}`,
    sku,
    name: "Default",
    sizeMm: "35.00",
    material: input.category === "Stickers" ? "Vinyl" : "Standard",
    color: "",
    currencyCode: "PKR",
    unitPrice: String(input.price || 0),
    fulfillmentMethod: "pdf_label",
    templateKey: "",
    templateVersion: 1,
    isActive: true,
  };

  const images: MockProductImage[] = [];
  if (input.coverImage) {
    images.push({
      url: input.coverImage,
      alt: `${name} cover`,
      sortOrder: 0,
      primary: true,
    });
  }
  if (input.galleryImages && Array.isArray(input.galleryImages)) {
    input.galleryImages.forEach((imgUrl, idx) => {
      images.push({
        url: imgUrl,
        alt: `${name} gallery ${idx + 1}`,
        sortOrder: idx + 1,
        primary: false,
      });
    });
  }

  const newProduct: MockProduct = {
    id,
    name,
    sku,
    category: input.category,
    status: "draft",
    price: Number(input.price) || 0,
    price_per_copy: input.price.toFixed(2),
    max_order_copies: input.max_order_copies ?? 100,
    stock: 0,
    templateKey: "—",
    variants: ["Default"],
    updatedAt,
    slug,
    description: input.description || "",
    isFeatured: false,
    featuredSortOrder: 0,
    allowsNewPair: true,
    allowsExistingQr: false,
    version: 1,
    coverImage: input.coverImage,
    images,
    variantRecords: [defaultVariant],
  };

  db.products.unshift(newProduct);

  const newLog: MockAuditLog = {
    id: `LOG-${Math.floor(100 + Math.random() * 900)}`,
    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
    actor,
    action: "API-221 Mock Product Draft Created",
    target: id,
    details: `Mock product draft '${name}' created in category '${input.category}'`,
  };

  db.auditLogs.unshift(newLog);
  saveAdminMockData(db);

  return { success: true, product: newProduct };
}

export interface UpdateProductInput {
  name?: string;
  category?: string;
  price?: number;
  max_order_copies?: number;
  description?: string;
  coverImage?: string | null;
  galleryImages?: string[];
}

export function hasMultipleDistinctVariantPrices(prod: MockProduct): boolean {
  if (!prod.variantRecords || prod.variantRecords.length <= 1) return false;
  const firstPrice = String(prod.variantRecords[0].unitPrice);
  return prod.variantRecords.some((v) => String(v.unitPrice) !== firstPrice);
}

export function getProductById(id: string): MockProduct | undefined {
  const db = loadAdminMockData();
  return db.products.find((p) => p.id === id);
}

export function getPrintTemplateByKey(key: string): MockPrintTemplate | undefined {
  const db = loadAdminMockData();
  return db.printTemplates.find((t) => t.key === key);
}

export function getPrintTemplateById(id: string): MockPrintTemplate | undefined {
  const db = loadAdminMockData();
  return db.printTemplates.find((t) => t.id === id);
}

export interface CreatePrintTemplateKeyInput {
  key: string;
  name: string;
  purpose: "lost" | "ice";
}

export function createPrintTemplateKey(
  input: CreatePrintTemplateKeyInput,
  actor = "operations"
): { success: boolean; template?: MockPrintTemplate; error?: string } {
  const db = loadAdminMockData();

  // Role verification (matching prototype PERMISSIONS: Operations and Superadmin only)
  const normalizedActor = actor.toLowerCase().replace(/[\s_-]+/g, "");
  const isAuthorized =
    normalizedActor.includes("superadmin") || normalizedActor.includes("operations");
  if (!isAuthorized) {
    return {
      success: false,
      error: `Role '${actor}' is restricted from creating print template keys. Operations or Superadmin required.`,
    };
  }

  // 1. Key validation (ASCII letters, digits, period, underscore, hyphen; length 3-80)
  const rawKey = input.key ?? "";
  if (!rawKey || rawKey.trim() === "") {
    return { success: false, error: "Template key is required." };
  }
  const key = rawKey.trim();
  if (!/^[A-Za-z0-9._-]{3,80}$/.test(key)) {
    return {
      success: false,
      error:
        "Invalid template key. Must be 3–80 ASCII characters: letters, digits, period, underscore, or hyphen.",
    };
  }

  // 2. Case-sensitive uniqueness check against existing template keys
  if (db.printTemplates.some((t) => t.key === key)) {
    return { success: false, error: "Template key already exists." };
  }

  // 3. Name validation (trimmed, 1 to 100 characters)
  const name = (input.name ?? "").trim();
  if (!name) {
    return { success: false, error: "Template name is required." };
  }
  if (name.length > 100) {
    return {
      success: false,
      error: "Template name must not exceed 100 characters.",
    };
  }

  // 4. Purpose validation (lost or ice)
  if (input.purpose !== "lost" && input.purpose !== "ice") {
    return {
      success: false,
      error: "Please select a valid template purpose: Lost Item or Emergency / ICE.",
    };
  }

  // 5. Build synthetic draft template record (API-301 key creation only; 0 revisions)
  const newTemplate: MockPrintTemplate = {
    id: `TMP-${Date.now()}`,
    key,
    name,
    purpose: input.purpose,
    revision: 0,
    rowVersion: 1,
    status: "draft",
    supportedTypes: ["Sticker"],
    size: "Not configured — create revision",
    lastAuthor: actor.toLowerCase().replace(/[\s-]+/g, "_"),
    revisions: [],
  };

  // 6. Record synthetic audit log
  const newLog: MockAuditLog = {
    id: `LOG-${Math.floor(100 + Math.random() * 900)}`,
    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
    actor: actor.toLowerCase().replace(/[\s-]+/g, "_"),
    action: "API-301 Template Key Created",
    target: key,
    details: "Draft key only; no renderer or physical QA",
  };

  db.printTemplates.unshift(newTemplate);
  db.auditLogs.unshift(newLog);
  saveAdminMockData(db);

  return { success: true, template: newTemplate };
}

export interface CreateDraftRevisionInput {
  versionNote?: string;
  labelDimensions?: string;
  supportedTypes?: string[];
}

export function createDraftRevision(
  key: string,
  input: CreateDraftRevisionInput = {},
  actor = "operations"
): { success: boolean; template?: MockPrintTemplate; revision?: MockTemplateRevision; error?: string } {
  const db = loadAdminMockData();
  const template = db.printTemplates.find((t) => t.key === key);
  if (!template) {
    return { success: false, error: `Print template '${key}' not found.` };
  }

  // Role permissions: Operations or Superadmin only
  const normalizedActor = actor.toLowerCase().replace(/[\s_-]+/g, "");
  const isAuthorized =
    normalizedActor.includes("superadmin") || normalizedActor.includes("operations");
  if (!isAuthorized) {
    return {
      success: false,
      error: `Role '${actor}' is restricted from creating template revisions. Operations or Superadmin required.`,
    };
  }

  // Calculate next sequential revision number
  const nextRevNumber = (template.revision || 0) + 1;

  const newRevision: MockTemplateRevision = {
    id: `REV-${template.id}-${nextRevNumber}`,
    revisionNumber: nextRevNumber,
    status: "draft",
    versionNote: input.versionNote?.trim() || `Draft revision ${nextRevNumber}`,
    labelDimensions: input.labelDimensions?.trim() || template.size || "Not configured",
    supportedTypes:
      input.supportedTypes && input.supportedTypes.length > 0
        ? input.supportedTypes
        : template.supportedTypes,
    updatedAt: new Date().toISOString().substring(0, 10),
    author: actor.toLowerCase().replace(/[\s-]+/g, "_"),
    previewAvailable: false,
    rowVersion: 1,
  };

  if (!Array.isArray(template.revisions)) {
    template.revisions = [];
  }
  template.revisions.unshift(newRevision);

  // Update summary metadata on template
  template.revision = nextRevNumber;
  template.status = "draft";
  template.lastAuthor = actor.toLowerCase().replace(/[\s-]+/g, "_");
  if (input.labelDimensions?.trim()) {
    template.size = input.labelDimensions.trim();
  }
  if (input.supportedTypes && input.supportedTypes.length > 0) {
    template.supportedTypes = input.supportedTypes;
  }
  template.rowVersion = (template.rowVersion || 1) + 1;

  // Synthetic audit log for draft revision creation (API-303)
  const auditLog: MockAuditLog = {
    id: `LOG-${Math.floor(100 + Math.random() * 900)}`,
    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
    actor: actor.toLowerCase().replace(/[\s-]+/g, "_"),
    action: "API-303 Draft Revision Created",
    target: `${key} Rev ${nextRevNumber}`,
    details: "Draft revision metadata created; no artwork or renderer enrolled",
  };

  db.auditLogs.unshift(auditLog);
  saveAdminMockData(db);

  return { success: true, template, revision: newRevision };
}

export interface UpdateDraftRevisionInput {
  versionNote?: string;
  labelDimensions?: string;
  supportedTypes?: string[];
}

export function updateDraftRevision(
  key: string,
  revisionNumber: number,
  input: UpdateDraftRevisionInput,
  actor = "operations"
): { success: boolean; template?: MockPrintTemplate; revision?: MockTemplateRevision; error?: string } {
  const db = loadAdminMockData();
  const template = db.printTemplates.find((t) => t.key === key);
  if (!template) {
    return { success: false, error: `Print template '${key}' not found.` };
  }

  // Role permissions
  const normalizedActor = actor.toLowerCase().replace(/[\s_-]+/g, "");
  const isAuthorized =
    normalizedActor.includes("superadmin") || normalizedActor.includes("operations");
  if (!isAuthorized) {
    return {
      success: false,
      error: `Role '${actor}' is restricted from updating template revisions. Operations or Superadmin required.`,
    };
  }

  // Ensure revisions array exists
  if (!Array.isArray(template.revisions)) {
    template.revisions = [];
  }

  // Find target revision record
  let targetRev = template.revisions.find((r) => r.revisionNumber === revisionNumber);
  if (!targetRev) {
    // If template is at this revision and in draft, synthesize revision entry
    if (template.revision === revisionNumber && template.status === "draft") {
      targetRev = {
        id: `REV-${template.id}-${revisionNumber}`,
        revisionNumber,
        status: "draft",
        versionNote: "Draft revision",
        labelDimensions: template.size || "Not configured",
        supportedTypes: template.supportedTypes,
        updatedAt: new Date().toISOString().substring(0, 10),
        author: template.lastAuthor,
        previewAvailable: false,
        rowVersion: 1,
      };
      template.revisions.push(targetRev);
    } else {
      return { success: false, error: `Revision ${revisionNumber} not found for template '${key}'.` };
    }
  }

  // IMMUTABILITY CHECK: Published revisions can NEVER be edited (API-304)
  if (targetRev.status !== "draft") {
    return {
      success: false,
      error: `Revision ${revisionNumber} has status '${targetRev.status}'. Published revisions are immutable (API-304).`,
    };
  }

  // Update permitted draft fields only
  if (input.versionNote !== undefined) {
    const trimmed = input.versionNote.trim();
    if (!trimmed) {
      return { success: false, error: "Version note cannot be empty." };
    }
    targetRev.versionNote = trimmed;
  }

  if (input.labelDimensions !== undefined && input.labelDimensions.trim()) {
    targetRev.labelDimensions = input.labelDimensions.trim();
    template.size = input.labelDimensions.trim();
  }

  if (input.supportedTypes !== undefined && input.supportedTypes.length > 0) {
    targetRev.supportedTypes = input.supportedTypes;
    template.supportedTypes = input.supportedTypes;
  }

  targetRev.updatedAt = new Date().toISOString().substring(0, 10);
  targetRev.author = actor.toLowerCase().replace(/[\s-]+/g, "_");
  targetRev.rowVersion = (targetRev.rowVersion || 1) + 1;
  template.rowVersion = (template.rowVersion || 1) + 1;

  // Synthetic audit log for draft update (API-304)
  const auditLog: MockAuditLog = {
    id: `LOG-${Math.floor(100 + Math.random() * 900)}`,
    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
    actor: actor.toLowerCase().replace(/[\s-]+/g, "_"),
    action: "API-304 Draft Revision Updated",
    target: `${key} Rev ${revisionNumber}`,
    details: `Draft revision metadata updated by ${actor}`,
  };

  db.auditLogs.unshift(auditLog);
  saveAdminMockData(db);

  return { success: true, template, revision: targetRev };
}

export function updateProduct(
  id: string,
  input: UpdateProductInput,
  actor = "operations"
): { success: boolean; product?: MockProduct; error?: string } {
  const db = loadAdminMockData();
  const prod = db.products.find((p) => p.id === id);
  if (!prod) {
    return { success: false, error: "Product not found." };
  }

  if (input.price !== undefined && (!Number.isFinite(input.price) || input.price < 0 || input.price > 9999999999.99 || Math.abs(input.price * 100 - Math.round(input.price * 100)) > 0.0001)) {
    return { success: false, error: "Enter a valid PKR price per copy with at most two decimal places." };
  }

  if (input.max_order_copies !== undefined && (!Number.isInteger(input.max_order_copies) || input.max_order_copies < 1 || input.max_order_copies > 100)) {
    return { success: false, error: "Maximum combined copies must be between 1 and 100." };
  }

  // Preserve core fields and patch supported fields
  if (input.name !== undefined) {
    const trimmed = input.name.trim();
    if (!trimmed) {
      return { success: false, error: "Product name cannot be empty." };
    }
    prod.name = trimmed;
  }

  if (input.category !== undefined && input.category.trim()) {
    prod.category = input.category.trim();
  }

  if (input.description !== undefined) {
    prod.description = input.description.trim();
  }

  // v1.4: one product price applies to every size in this demo store.
  if (input.price !== undefined && Number.isFinite(input.price) && input.price >= 0) {
    prod.price = input.price;
    prod.price_per_copy = input.price.toFixed(2);
    prod.variantRecords?.forEach(v => { v.unitPrice = prod.price_per_copy!; });
  }

  if (input.max_order_copies !== undefined) prod.max_order_copies = input.max_order_copies;

  // Cover image update
  if (input.coverImage !== undefined) {
    prod.coverImage = input.coverImage || undefined;
    if (!prod.images) prod.images = [];
    const coverIdx = prod.images.findIndex((im) => im.primary);
    if (input.coverImage) {
      if (coverIdx >= 0) {
        prod.images[coverIdx].url = input.coverImage;
      } else {
        prod.images.unshift({
          url: input.coverImage,
          alt: `${prod.name} cover`,
          sortOrder: 0,
          primary: true,
        });
      }
    } else if (coverIdx >= 0) {
      prod.images.splice(coverIdx, 1);
    }
  }

  // Gallery images update
  if (input.galleryImages !== undefined) {
    const primaryImg = prod.images?.find((im) => im.primary);
    const newImages: MockProductImage[] = primaryImg ? [primaryImg] : [];
    input.galleryImages.forEach((imgUrl, idx) => {
      newImages.push({
        url: imgUrl,
        alt: `${prod.name} gallery ${idx + 1}`,
        sortOrder: idx + 1,
        primary: false,
      });
    });
    prod.images = newImages;
  }

  prod.version = (prod.version || 1) + 1;
  prod.updatedAt = new Date().toISOString().substring(0, 10);

  const newLog: MockAuditLog = {
    id: `LOG-${Math.floor(100 + Math.random() * 900)}`,
    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
    actor,
    action: "API-222 Mock Product Updated",
    target: prod.id,
    details: `Mock product '${prod.name}' updated by ${actor}`,
  };

  db.auditLogs.unshift(newLog);
  saveAdminMockData(db);

  return { success: true, product: prod };
}

export function getManagedProductsCount(db: MockAdminDatabase): number {
  return db.products.length;
}

export function getPrintTemplatesCount(db: MockAdminDatabase): number {
  return db.printTemplates.length;
}

export function getTemplateRevisionsCount(db: MockAdminDatabase): number {
  return db.printTemplates.reduce((acc, t) => acc + (t.revisions?.length ?? 0), 0);
}

export function getRegisteredAccountsCount(db: MockAdminDatabase): number {
  return db.users.length;
}

export function getActiveOrdersCount(db: MockAdminDatabase): number {
  return db.orders.filter(
    (o) => o.status === "Pending Review" || o.status === "Processing" || o.status === "Dispatched"
  ).length;
}

export function getRecentAuditLogs(db: MockAdminDatabase, limit = 4): MockAuditLog[] {
  return db.auditLogs.slice(0, limit);
}

export interface MockInventoryMetric {
  unassignedPairs: number;
  reservedPairs: number;
  lowStockThreshold: number;
  productLowStockThreshold: number;
}

export const INITIAL_INVENTORY_METRICS: MockInventoryMetric = {
  unassignedPairs: 4280,
  reservedPairs: 120,
  lowStockThreshold: 500,
  productLowStockThreshold: 100,
};

export function getProductStockStatus(
  stock: number | undefined | null,
  threshold = 100
): "In Stock" | "Low Stock" | "Out of Stock" | "Unknown" {
  if (stock === undefined || stock === null || isNaN(stock)) {
    return "Unknown";
  }
  if (stock <= 0) {
    return "Out of Stock";
  }
  if (stock < threshold) {
    return "Low Stock";
  }
  return "In Stock";
}

export function getOverallInventoryHealth(
  products: MockProduct[],
  qrUnassigned = 4280,
  qrThreshold = 500,
  productThreshold = 100
): "Healthy" | "Low Stock" | "Critical" | "Unknown" {
  if (!products || products.length === 0) {
    return "Unknown";
  }
  const hasMissingStock = products.some(
    (p) => p.stock === undefined || p.stock === null || isNaN(p.stock)
  );
  if (hasMissingStock) {
    return "Unknown";
  }
  const hasZeroStock = products.some((p) => p.stock <= 0);
  if (hasZeroStock || qrUnassigned <= 0) {
    return "Critical";
  }
  const hasLowProductStock = products.some((p) => p.stock < productThreshold);
  if (hasLowProductStock || qrUnassigned <= qrThreshold) {
    return "Low Stock";
  }
  return "Healthy";
}

// QR Batches Mock Selectors & Mutators (Screen 10 / API-090)
export function getQRBatches(): MockQRBatch[] {
  return loadAdminMockData().qrBatches || [];
}

export function getQRBatchById(id: string): MockQRBatch | undefined {
  if (!id) return undefined;
  const db = loadAdminMockData();
  const normalized = id.trim().toLowerCase();
  return (db.qrBatches || []).find((b) => b.id.toLowerCase() === normalized);
}

export interface CreateDemoQRBatchInput {
  pairsCount: number;
  batchLabel?: string;
  printMaterial?: string;
  eccLevel?: "M" | "Q";
  intendedEnvironment?: "indoor" | "outdoor";
  notes?: string;
  actor?: string;
}

export function createDemoQRBatch(
  input: CreateDemoQRBatchInput
): { success: true; batch: MockQRBatch } | { success: false; error: string } {
  // 1. Validate pair count (positive integer, 1 to 1000)
  if (
    !input.pairsCount ||
    typeof input.pairsCount !== "number" ||
    !Number.isInteger(input.pairsCount) ||
    input.pairsCount < 1 ||
    input.pairsCount > 1000
  ) {
    return {
      success: false,
      error: "Number of QR pairs must be an integer between 1 and 1,000.",
    };
  }

  const db = loadAdminMockData();
  if (!Array.isArray(db.qrBatches)) {
    db.qrBatches = [...INITIAL_SEED_DATA.qrBatches];
  }

  // 2. Validate or generate batch label / identifier
  let batchId = input.batchLabel?.trim();
  if (batchId) {
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{2,39}$/.test(batchId)) {
      return {
        success: false,
        error:
          "Batch ID must be 3-40 characters, start with alphanumeric, and contain only letters, numbers, hyphens, dots, or underscores.",
      };
    }
    const exists = db.qrBatches.some(
      (b) => b.id.toLowerCase() === batchId!.toLowerCase()
    );
    if (exists) {
      return {
        success: false,
        error: `A batch with identifier '${batchId}' already exists.`,
      };
    }
  } else {
    // Generate sequential batch ID: BATCH-YYYY-NN
    const year = new Date().getFullYear();
    let seq = 11;
    while (
      db.qrBatches.some(
        (b) => b.id === `BATCH-${year}-${seq.toString().padStart(2, "0")}`
      )
    ) {
      seq++;
    }
    batchId = `BATCH-${year}-${seq.toString().padStart(2, "0")}`;
  }

  const today = new Date().toISOString().substring(0, 10);
  const newBatch: MockQRBatch = {
    id: batchId,
    size: input.pairsCount * 2, // 1 pair = 2 tags (lost + ice)
    pairsCount: input.pairsCount,
    generatedAt: today,
    status: "Awaiting QA",
    exported: false,
    isDemo: true,
    printMaterial: input.printMaterial || "synthetic-waterproof",
    eccLevel: input.eccLevel || "Q",
    intendedEnvironment: input.intendedEnvironment || "indoor",
    notes:
      input.notes ||
      "Demonstration synthetic QR manufacturing batch metadata.",
    qaMetadata: {
      passedRounds: 0,
      notes:
        "Newly created synthetic demonstration batch. Awaiting physical QA inspection.",
    },
  };

  // 3. Add synthetic audit log (API-090 Demo Batch Created)
  const newLog: MockAuditLog = {
    id: `LOG-${Math.floor(100 + Math.random() * 900)}`,
    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
    actor: input.actor || "operations",
    action: "API-090 Demo Batch Created",
    target: batchId,
    details: `Synthetic demo batch '${batchId}' initialized (${input.pairsCount} pairs, ${newBatch.size} tags). No production secrets or printable assets generated.`,
  };

  db.qrBatches.unshift(newBatch);
  db.auditLogs.unshift(newLog);

  // CRITICAL CONSTRAINT: Screen 9 product stock is NOT modified
  saveAdminMockData(db);

  return { success: true, batch: newBatch };
}

// QR Quality Assurance Mock Selectors & Mutators (Screen 11 / API-091)
export function getQAPairs(batchId?: string): MockQAPair[] {
  const db = loadAdminMockData();
  const list = db.qaPairs || [];
  if (!batchId || batchId === "all") {
    return list;
  }
  const filtered = list.filter(
    (p) => p.batchId.toLowerCase() === batchId.toLowerCase()
  );
  return filtered;
}

export function getQAPairById(pairId: string): MockQAPair | undefined {
  if (!pairId) return undefined;
  const db = loadAdminMockData();
  const normalized = pairId.trim().toLowerCase();
  return (db.qaPairs || []).find((p) => p.id.toLowerCase() === normalized);
}

export function getQAInspections(): MockQAInspection[] {
  const db = loadAdminMockData();
  return db.qaInspections || [];
}

export function recordQAPass(input: {
  pairId: string;
  inspector?: string;
  notes?: string;
}): { success: true; inspection: MockQAInspection; pair: MockQAPair } | { success: false; error: string } {
  const db = loadAdminMockData();
  const normalized = input.pairId.trim().toLowerCase();
  const pair = (db.qaPairs || []).find((p) => p.id.toLowerCase() === normalized);

  if (!pair) {
    return {
      success: false,
      error: "Demo pair not found. Select an existing synthetic pair from the available mock records.",
    };
  }

  if (pair.status !== "Awaiting QA") {
    return {
      success: false,
      error: "Reinspection is not available in this demo workflow.",
    };
  }

  const timestamp = new Date().toISOString().replace("T", " ").substring(0, 19);
  const inspectorName = input.inspector || "Operations Staff";

  pair.status = "Passed";
  pair.lastInspectedAt = timestamp;
  pair.inspector = inspectorName;
  pair.notes = input.notes || "Simulated inspection only; no real scan verification.";

  const inspection: MockQAInspection = {
    id: `QA-INSP-${Date.now()}-${db.qaInspections.length + 1}`,
    pairId: pair.id,
    batchId: pair.batchId,
    outcome: "Passed",
    inspector: inspectorName,
    timestamp,
    notes: pair.notes,
  };

  const auditLog: MockAuditLog = {
    id: `LOG-${Math.floor(100 + Math.random() * 900)}`,
    timestamp,
    actor: input.inspector || "operations",
    action: "Demo QA Passed",
    target: pair.id,
    details: `Demo pair '${pair.id}' (Batch '${pair.batchId}') marked as QA Passed. No physical scan or production release performed.`,
  };

  db.qaInspections.unshift(inspection);
  db.auditLogs.unshift(auditLog);

  // CRITICAL: Batch status and inventory are not modified
  try {
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
    saveAdminMockData(db);
  } catch {
    return { success: false, error: "Unable to save demo inspection. Browser storage may be full or unavailable. Please retry." };
  }

  return { success: true, inspection, pair };
}

export function recordQAQuarantine(input: {
  pairId: string;
  rejectionReason: string;
  notes?: string;
  inspector?: string;
}): { success: true; inspection: MockQAInspection; pair: MockQAPair } | { success: false; error: string } {
  const db = loadAdminMockData();
  const normalized = input.pairId.trim().toLowerCase();
  const pair = (db.qaPairs || []).find((p) => p.id.toLowerCase() === normalized);

  if (!pair) {
    return {
      success: false,
      error: "Demo pair not found. Select an existing synthetic pair from the available mock records.",
    };
  }

  if (pair.status !== "Awaiting QA") {
    return {
      success: false,
      error: "Reinspection is not available in this demo workflow.",
    };
  }

  if (!input.rejectionReason || !input.rejectionReason.trim()) {
    return {
      success: false,
      error: "Rejection reason is required to quarantine a demo pair.",
    };
  }

  const timestamp = new Date().toISOString().replace("T", " ").substring(0, 19);
  const inspectorName = input.inspector || "Operations Staff";

  pair.status = "Quarantined";
  pair.lastInspectedAt = timestamp;
  pair.inspector = inspectorName;
  pair.rejectionReason = input.rejectionReason.trim();
  pair.notes = input.notes?.trim() || "Defect identified during simulated physical QA inspection.";

  const inspection: MockQAInspection = {
    id: `QA-INSP-${Date.now()}-${db.qaInspections.length + 1}`,
    pairId: pair.id,
    batchId: pair.batchId,
    outcome: "Quarantined",
    rejectionReason: pair.rejectionReason,
    inspector: inspectorName,
    timestamp,
    notes: pair.notes,
  };

  const auditLog: MockAuditLog = {
    id: `LOG-${Math.floor(100 + Math.random() * 900)}`,
    timestamp,
    actor: input.inspector || "operations",
    action: "Demo QA Quarantined",
    target: pair.id,
    details: `Demo pair '${pair.id}' (Batch '${pair.batchId}') marked as Quarantined. Reason: '${pair.rejectionReason}'.`,
  };

  db.qaInspections.unshift(inspection);
  db.auditLogs.unshift(auditLog);

  // CRITICAL: Batch status and inventory are not modified
  try {
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
    saveAdminMockData(db);
  } catch {
    return { success: false, error: "Unable to save demo inspection. Browser storage may be full or unavailable. Please retry." };
  }

  return { success: true, inspection, pair };
}

export function getQASummary(): {
  totalInspected: number;
  passed: number;
  quarantined: number;
  awaiting: number;
} {
  const db = loadAdminMockData();
  const pairs = db.qaPairs || [];
  return {
    totalInspected: pairs.filter((p) => p.status !== "Awaiting QA").length,
    passed: pairs.filter((p) => p.status === "Passed").length,
    quarantined: pairs.filter((p) => p.status === "Quarantined").length,
    awaiting: pairs.filter((p) => p.status === "Awaiting QA").length,
  };
}

// React hook for reactive mock data across screens
export function useAdminMockData() {
  // Match the server's seed on the first client render. Browser persistence is
  // applied after hydration, avoiding mismatches after a saved demo mutation.
  const [data, setData] = useState<MockAdminDatabase>(() => JSON.parse(JSON.stringify(INITIAL_SEED_DATA)));

  const refresh = useCallback(() => {
    setData(loadAdminMockData());
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    refresh();

    // Sync on custom event and window storage events
    window.addEventListener(CHANGE_EVENT, refresh);
    window.addEventListener("storage", refresh);

    return () => {
      window.removeEventListener(CHANGE_EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, [refresh]);

  return {
    data,
    refresh,
    saveData: saveAdminMockData,
    resetData: resetAdminMockData,
    counts: {
      products: getManagedProductsCount(data),
      templates: getPrintTemplatesCount(data),
      templateRevisions: getTemplateRevisionsCount(data),
      users: getRegisteredAccountsCount(data),
      activeOrders: getActiveOrdersCount(data),
      qrBatches: data.qrBatches ? data.qrBatches.length : 0,
      qaInspected: data.qaInspections ? data.qaInspections.length : 0,
    },
    recentAuditLogs: getRecentAuditLogs(data, 4),
  };
}


