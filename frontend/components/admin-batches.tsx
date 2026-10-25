"use client";

import React, { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { AdminIcon } from "./admin-icons";
import {
  useAdminMockData,
  createDemoQRBatch,
  getQRBatchById,
  type MockQRBatch,
} from "../lib/admin-mock-data";
import { useAdminRole } from "./admin-shell";
import { useAdminToast } from "./admin-toast";
import { AdminEmptyState } from "./admin-ui";

export interface AdminQRBatchesListProps {
  ur?: boolean;
}

export function AdminQRBatchesList({ ur = false }: AdminQRBatchesListProps) {
  const { data, refresh } = useAdminMockData();
  const { authenticatedRoles } = useAdminRole();
  const effectiveRole = authenticatedRoles.join(" ");
  const { showToast } = useAdminToast();

  // Role permissions: Operations and Superadmin have full access
  const normalizedRole = effectiveRole.toLowerCase().replace(/[\s_-]+/g, "");
  const isAuthorized =
    normalizedRole.includes("superadmin") || normalizedRole.includes("operations");

  // Filter & Search states
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Modal dialog states
  const [isGenerateOpen, setIsGenerateOpen] = useState(false);
  const [exportNoticeBatch, setExportNoticeBatch] = useState<MockQRBatch | null>(null);

  // Filter batches
  const batches = useMemo(() => {
    const list = data.qrBatches || [];
    return list.filter((b) => {
      const q = searchQuery.trim().toLowerCase();
      const matchesSearch = !q || b.id.toLowerCase().includes(q);
      const matchesStatus =
        statusFilter === "all" ||
        b.status.toLowerCase() === statusFilter.toLowerCase();
      return matchesSearch && matchesStatus;
    });
  }, [data.qrBatches, searchQuery, statusFilter]);

  const hasActiveFilters = searchQuery.trim() !== "" || statusFilter !== "all";

  const handleClearFilters = useCallback(() => {
    setSearchQuery("");
    setStatusFilter("all");
  }, []);

  const handleOpenGenerate = useCallback(() => {
    if (!isAuthorized) {
      showToast(
        ur
          ? "رسائی مسترد: کیو آر بیچ بنانے کی اجازت صرف آپریشنز اور سپر ایڈمن کو ہے۔"
          : "Access Denied: Only Operations and Superadmin roles can generate demo QR batches.",
        "error"
      );
      return;
    }
    setIsGenerateOpen(true);
  }, [isAuthorized, showToast, ur]);

  return (
    <div className="space-y-6" dir={ur ? "rtl" : "ltr"}>
      {/* 1. Header Card */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-sky-50 text-sky-600 rounded-lg">
              <AdminIcon name="qr-code" className="w-5 h-5" />
            </span>
            <h1 className="font-bold text-slate-800 text-lg sm:text-xl">
              {ur ? "کیو آر کوڈ بیچ مینوفیکچرنگ" : "QR Batches"}
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {ur
              ? "کیو آر بیچ ریکارڈز کا نظم کریں اور تیاری کی تیاری کا جائزہ لیں۔ (API-090)"
              : "Manage QR batch records and review manufacturing readiness. (API-090)"}
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenGenerate}
          disabled={!isAuthorized}
          className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm ${
            isAuthorized
              ? "bg-sky-600 hover:bg-sky-700 text-white cursor-pointer"
              : "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
          }`}
          aria-label={ur ? "ڈیمو بیچ بنائیں" : "Generate Demo Batch"}
        >
          <AdminIcon name="plus" className="w-4 h-4" />
          <span>{ur ? "+ ڈیمو بیچ بنائیں" : "+ Generate Demo Batch"}</span>
        </button>
      </div>

      {/* 2. Demonstration Information Notice */}
      <div className="bg-sky-50 border border-sky-200 rounded-xl p-4 flex items-start gap-3">
        <span className="text-sky-600 mt-0.5 shrink-0">
          <AdminIcon name="info" className="w-5 h-5" />
        </span>
        <div className="text-xs text-sky-950 space-y-1">
          <p className="font-semibold">
            {ur
              ? "محفوظ ریٹرن ایڈمن پروٹو ٹائپ فعال ہے:"
              : "SafeReturn Admin Demonstration Environment:"}
          </p>
          <p className="text-sky-800 leading-relaxed">
            {ur
              ? "یہ اسکرین صرف مصنوعی ڈیمو بیچ میٹا ڈیٹا بناتی ہے۔ کوئی حقیقی کرپٹوگرافک کیز، ریکوری ٹوکنز، ایکٹیویشن سیکرٹس یا پروڈکشن کیو آر کوڈز جنریٹ نہیں کیے جاتے۔ اسکرین 9 انوینٹری میں کوئی خودکار تبدیلی نہیں ہوگی۔"
              : "This screen manages synthetic batch records and QA readiness. No real cryptographic keypairs, recovery tokens, activation secrets or printable manufacturing payloads are generated. Screen 9 inventory allocations remain independent."}
          </p>
        </div>
      </div>

      {/* 3. Search & Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div className="flex-1 flex flex-col sm:flex-row gap-3">
          {/* Search by Batch ID */}
          <div className="relative flex-1">
            <span className="absolute inset-y-0 start-0 flex items-center ps-3 pointer-events-none text-slate-400">
              <AdminIcon name="search" className="w-4 h-4" />
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={ur ? "بیچ آئی ڈی تلاش کریں..." : "Search batch ID..."}
              className="w-full ps-9 pe-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition"
              aria-label={ur ? "بیچ تلاش کریں" : "Search batch ID"}
            />
          </div>

          {/* Filter by QA Status */}
          <div className="relative w-full sm:w-48">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition cursor-pointer appearance-none"
              aria-label={ur ? "کیو اے کی حیثیت فلٹر" : "Filter by QA Status"}
            >
              <option value="all">{ur ? "تمام حیثیتیں (All)" : "All Statuses"}</option>
              <option value="QA Passed">{ur ? "کیو اے پاس (QA Passed)" : "QA Passed"}</option>
              <option value="In QA">{ur ? "کیو اے جاری (In QA)" : "In QA"}</option>
              <option value="Awaiting QA">{ur ? "کیو اے کے منتظر (Awaiting QA)" : "Awaiting QA"}</option>
              <option value="Rejected">{ur ? "مسترد شدہ (Rejected)" : "Rejected"}</option>
            </select>
            <span className="absolute inset-y-0 end-0 flex items-center pe-2.5 pointer-events-none text-slate-400">
              <AdminIcon name="filter" className="w-3.5 h-3.5" />
            </span>
          </div>
        </div>

        {/* Clear Filters Button */}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={handleClearFilters}
            className="px-3 py-2 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors flex items-center justify-center gap-1.5"
            aria-label={ur ? "فلٹرز صاف کریں" : "Clear filters"}
          >
            <AdminIcon name="x" className="w-3.5 h-3.5" />
            <span>{ur ? "فلٹرز صاف کریں" : "Clear Filters"}</span>
          </button>
        )}
      </div>

      {/* 4. Batches Data Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {batches.length === 0 ? (
          <div className="p-8">
            <AdminEmptyState
              title={ur ? "کوئی بیچ نہیں ملا" : "No Batches Found"}
              description={
                hasActiveFilters
                  ? ur
                    ? "آپ کے تلاش اور فلٹر کے معیارات سے کوئی بیچ ریکارڈ مطابقت نہیں رکھتا۔"
                    : "No batch records matched your search query or status filter."
                  : ur
                    ? "کوئی کیو آر بیچ میٹا ڈیٹا موجود نہیں ہے۔"
                    : "No QR batch records exist in the current mock store."
              }
              action={
                hasActiveFilters ? (
                  <button
                    type="button"
                    onClick={handleClearFilters}
                    className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
                  >
                    {ur ? "فلٹرز صاف کریں" : "Clear Filters"}
                  </button>
                ) : isAuthorized ? (
                  <button
                    type="button"
                    onClick={handleOpenGenerate}
                    className="px-3 py-1.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm transition-colors cursor-pointer"
                  >
                    {ur ? "پہلا ڈیمو بیچ بنائیں" : "Generate First Demo Batch"}
                  </button>
                ) : undefined
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4">{ur ? "بیچ آئی ڈی" : "Batch ID"}</th>
                  <th className="py-3 px-4">{ur ? "کل ٹیگز (مقدار)" : "Quantity"}</th>
                  <th className="py-3 px-4">{ur ? "جوڑے (Pairs)" : "Pairs"}</th>
                  <th className="py-3 px-4">{ur ? "تاریخ تیاری" : "Generated"}</th>
                  <th className="py-3 px-4">{ur ? "کیو اے کی حیثیت" : "QA Status"}</th>
                  <th className="py-3 px-4">{ur ? "ایکسپورٹ میٹا ڈیٹا" : "Export Status"}</th>
                  <th className="py-3 px-4 text-end">{ur ? "کارروائی" : "Actions"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {batches.map((b) => (
                  <tr
                    key={b.id}
                    className="hover:bg-slate-50/80 transition-colors group"
                  >
                    {/* Batch ID */}
                    <td className="py-3 px-4">
                      <Link
                        href={`/admin/batches/${b.id}`}
                        className="font-mono font-semibold text-sky-600 hover:text-sky-800 hover:underline flex items-center gap-1.5"
                      >
                        <span>{b.id}</span>
                        {b.isDemo && (
                          <span className="text-[10px] px-1.5 py-0.2 font-sans font-medium text-slate-500 bg-slate-100 rounded">
                            Demo
                          </span>
                        )}
                      </Link>
                    </td>

                    {/* Quantity (Tags) */}
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {b.size.toLocaleString()} {ur ? "ٹیگز" : "tags"}
                    </td>

                    {/* Pairs Count */}
                    <td className="py-3 px-4 text-slate-600">
                      {b.pairsCount.toLocaleString()} {ur ? "جوڑے" : "pairs"}
                    </td>

                    {/* Generated Date */}
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap font-mono text-[11px]">
                      {b.generatedAt}
                    </td>

                    {/* QA Status Badge */}
                    <td className="py-3 px-4">
                      <BatchQAStatusBadge status={b.status} ur={ur} />
                    </td>

                    {/* Export Status */}
                    <td className="py-3 px-4">
                      {b.exported ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                          <AdminIcon name="check" className="w-3 h-3" />
                          <span>{ur ? "ایکسپورٹ شدہ (ماک)" : "Exported (Mock)"}</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
                          <span>{ur ? "غیر ایکسپورٹ شدہ" : "Not Exported"}</span>
                        </span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-end whitespace-nowrap">
                      <div className="inline-flex items-center gap-2 justify-end">
                        <Link
                          href={`/admin/batches/${b.id}`}
                          className="px-2.5 py-1 text-xs font-medium text-sky-600 hover:text-sky-800 hover:bg-sky-50 rounded transition-colors"
                          aria-label={`View details for ${b.id}`}
                        >
                          {ur ? "تفصیلات دیکھیں" : "View Details"}
                        </Link>
                        <button
                          type="button"
                          onClick={() => setExportNoticeBatch(b)}
                          className="px-2 py-1 text-xs text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors flex items-center gap-1"
                          title={
                            ur
                              ? "پروڈکشن ایکسپورٹ پروٹو ٹائپ میں دستیاب نہیں ہے"
                              : "Production credential export unavailable in frontend mock"
                          }
                        >
                          <AdminIcon name="file-lock-2" className="w-3.5 h-3.5 text-slate-400" />
                          <span>{ur ? "ایکسپورٹ پی لوڈ" : "Export Payload"}</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 5. Informational Boundaries Footer */}
      <div className="bg-slate-100 border border-slate-200 rounded-xl p-4 text-xs text-slate-600 flex items-start gap-3">
        <span className="text-slate-400 mt-0.5 shrink-0">
          <AdminIcon name="shield-check" className="w-4 h-4" />
        </span>
        <div className="space-y-1">
          <p className="font-semibold text-slate-800">
            {ur
              ? "کیو آر بیچ مینوفیکچرنگ اور سیکیورٹی گائیڈ لائنز (API-090):"
              : "API-090 QR Batch Manufacturing & Security Guidelines:"}
          </p>
          <p className="text-slate-500 leading-relaxed">
            {ur
              ? "ہر جوڑا دو فزیکل ٹیگز (گمشدگی ٹیگ اور ہنگامی آئی سی ای ٹیگ) پر مشتمل ہوتا ہے۔ محفوظ ریٹرن میں تمام پروڈکشن کیو آر کیز ہارڈ ویئر سیکیورٹی ماڈیولز (HSM) اور سخت ڈوئل کسٹڈی کے تحت بنائی جاتی ہیں۔ فرنٹ اینڈ ماک میں کوئی بھی خفیہ کلید یا پرنٹ ایبل ایسٹس محفوظ نہیں کیے جاتے۔"
              : "Each pair comprises two distinct physical tags (Lost Tag + ICE Tag). Production CSPRNG key generation is handled via secure hardware security modules under strict dual-custody control. Demonstration batches are recorded as metadata only and do not modify physical warehouse inventory."}
          </p>
        </div>
      </div>

      {/* Modal: Generate Demo Batch Dialog */}
      {isGenerateOpen && (
        <GenerateDemoBatchDialog
          ur={ur}
          actor={effectiveRole}
          onClose={() => setIsGenerateOpen(false)}
          onSuccess={() => {
            setIsGenerateOpen(false);
            refresh();
          }}
        />
      )}

      {/* Modal: Production Export Unavailable Notice */}
      {exportNoticeBatch && (
        <QRBatchExportNoticeDialog
          batch={exportNoticeBatch}
          ur={ur}
          onClose={() => setExportNoticeBatch(null)}
        />
      )}
    </div>
  );
}

/* =========================================================================
   Component: Batch QA Status Badge
   ========================================================================= */
export function BatchQAStatusBadge({
  status,
  ur = false,
}: {
  status: MockQRBatch["status"];
  ur?: boolean;
}) {
  switch (status) {
    case "QA Passed":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
          <AdminIcon name="check-circle-2" className="w-3 h-3" />
          <span>{ur ? "کیو اے پاس" : "QA Passed"}</span>
        </span>
      );
    case "In QA":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
          <AdminIcon name="activity" className="w-3 h-3" />
          <span>{ur ? "کیو اے جاری" : "In QA"}</span>
        </span>
      );
    case "Awaiting QA":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-sky-100 text-sky-800 border border-sky-200">
          <AdminIcon name="info" className="w-3 h-3" />
          <span>{ur ? "کیو اے کے منتظر" : "Awaiting QA"}</span>
        </span>
      );
    case "Rejected":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
          <AdminIcon name="alert-triangle" className="w-3 h-3" />
          <span>{ur ? "مسترد شدہ" : "Rejected"}</span>
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
          <span>{status}</span>
        </span>
      );
  }
}

/* =========================================================================
   Component: Generate Demo Batch Dialog
   ========================================================================= */
interface GenerateDemoBatchDialogProps {
  ur?: boolean;
  actor: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function GenerateDemoBatchDialog({
  ur = false,
  actor,
  onClose,
  onSuccess,
}: GenerateDemoBatchDialogProps) {
  const { showToast } = useAdminToast();
  const [pairsCountInput, setPairsCountInput] = useState("250");
  const [batchLabelInput, setBatchLabelInput] = useState("");
  const [printMaterial, setPrintMaterial] = useState("synthetic-waterproof");
  const [intendedEnvironment, setIntendedEnvironment] = useState<"indoor" | "outdoor">("indoor");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Compute calculated tag count: 1 pair = 2 tags
  const parsedPairs = parseInt(pairsCountInput, 10);
  const calculatedTags = !isNaN(parsedPairs) && parsedPairs > 0 ? parsedPairs * 2 : 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const count = parseInt(pairsCountInput, 10);
    if (isNaN(count) || count < 1 || count > 1000) {
      setValidationError(
        ur
          ? "جوڑوں کی تعداد 1 اور 1,000 کے درمیان ایک مثبت عدد ہونی چاہیے۔"
          : "Number of QR pairs must be an integer between 1 and 1,000."
      );
      return;
    }

    setIsSubmitting(true);
    const result = createDemoQRBatch({
      pairsCount: count,
      batchLabel: batchLabelInput.trim() || undefined,
      printMaterial,
      intendedEnvironment,
      notes: notes.trim() || undefined,
      actor,
    });

    if (!result.success) {
      setValidationError(result.error);
      setIsSubmitting(false);
      return;
    }

    showToast(
      ur
        ? `ڈیمو کیو آر بیچ '${result.batch.id}' کامیابی سے بن گیا۔`
        : "Demo QR batch record created.",
      "success"
    );
    onSuccess();
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-generate-title"
      dir={ur ? "rtl" : "ltr"}
    >
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-2">
            <span className="p-1.5 bg-sky-100 text-sky-700 rounded-lg">
              <AdminIcon name="qr-code" className="w-4 h-4" />
            </span>
            <h2 id="modal-generate-title" className="font-bold text-slate-800 text-sm">
              {ur ? "نیا ڈیمو کیو آر بیچ بنائیں" : "Generate Demo QR Batch"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 rounded-lg p-1 transition-colors"
            aria-label="Close dialog"
          >
            <AdminIcon name="x" className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Informational Callout */}
          <div className="bg-sky-50 border border-sky-200 rounded-lg p-3 text-xs text-sky-900 flex items-start gap-2">
            <span className="text-sky-600 mt-0.5 shrink-0">
              <AdminIcon name="info" className="w-4 h-4" />
            </span>
            <p className="leading-relaxed">
              {ur
                ? "یہ فارم صرف مصنوعی بیچ ریکارڈ بناتا ہے۔ کوئی اصل کیو آر سیکرٹس، ایکٹیویشن ٹوکنز یا پرنٹ ایبل فائلیں تیار نہیں کی جاتیں۔"
                : "This creates synthetic batch metadata only. No QR secrets, activation credentials, printable QR codes or manufacturing files will be generated."}
            </p>
          </div>

          {/* Validation Error Message */}
          {validationError && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-lg p-3 text-xs flex items-start gap-2">
              <span className="text-rose-600 mt-0.5 shrink-0">
                <AdminIcon name="alert-circle" className="w-4 h-4" />
              </span>
              <span>{validationError}</span>
            </div>
          )}

          {/* Number of QR Pairs */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              {ur ? "کیو آر جوڑوں کی تعداد (Pairs Count) *" : "Number of QR Pairs *"}
            </label>
            <input
              type="number"
              min="1"
              max="1000"
              required
              value={pairsCountInput}
              onChange={(e) => setPairsCountInput(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition"
              aria-label={ur ? "جوڑوں کی تعداد" : "Number of QR pairs"}
            />
            <p className="text-[11px] text-slate-500 mt-1">
              {ur ? "کم از کم 1، زیادہ سے زیادہ 1,000 جوڑے۔" : "Permitted mock bounds: 1 to 1,000 pairs."}
            </p>
          </div>

          {/* Calculated Tag Count Display */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex justify-between items-center text-xs">
            <span className="text-slate-600 font-medium">
              {ur ? "حساب شدہ فزیکل ٹیگز (1 جوڑا = 2 ٹیگز):" : "Calculated Tag Count (1 pair = 2 tags):"}
            </span>
            <span className="font-mono font-bold text-sky-700">
              {calculatedTags.toLocaleString()} {ur ? "ٹیگز" : "tags"}
            </span>
          </div>

          {/* Custom Batch Label (Optional) */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              {ur ? "کسٹم بیچ آئی ڈی / لیبل (اختیاری)" : "Custom Batch Identifier (Optional)"}
            </label>
            <input
              type="text"
              value={batchLabelInput}
              onChange={(e) => setBatchLabelInput(e.target.value)}
              placeholder="e.g. BATCH-2026-11"
              maxLength={40}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              {ur
                ? "خالی چھوڑنے پر خودکار طریقے سے BATCH-YYYY-NN نمبر تفویض کیا جائے گا۔"
                : "Leave empty to automatically assign sequential BATCH-YYYY-NN."}
            </p>
          </div>

          {/* Print Material & Environment */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                {ur ? "پرنٹ میٹریل" : "Print Material"}
              </label>
              <select
                value={printMaterial}
                onChange={(e) => setPrintMaterial(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="synthetic-waterproof">Synthetic Waterproof</option>
                <option value="polyester-matte">Polyester Matte</option>
                <option value="vinyl-outdoor">Outdoor Vinyl</option>
                <option value="silicone-band">Silicone Band</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                {ur ? "ماحول" : "Environment"}
              </label>
              <select
                value={intendedEnvironment}
                onChange={(e) => setIntendedEnvironment(e.target.value as "indoor" | "outdoor")}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="indoor">Indoor (Min 30mm)</option>
                <option value="outdoor">Outdoor (Min 35mm)</option>
              </select>
            </div>
          </div>

          {/* Form Actions */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            >
              {ur ? "منسوخ کریں" : "Cancel"}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || calculatedTags === 0}
              className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 disabled:bg-slate-300 disabled:cursor-not-allowed rounded-lg shadow-sm transition-colors cursor-pointer flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <span>{ur ? "بنایا جا رہا ہے..." : "Creating..."}</span>
              ) : (
                <>
                  <AdminIcon name="check" className="w-3.5 h-3.5" />
                  <span>{ur ? "ڈیمو بیچ بنائیں" : "Create Demo Batch"}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* =========================================================================
   Component: Production Export Unavailable Notice Dialog
   ========================================================================= */
interface QRBatchExportNoticeDialogProps {
  batch: MockQRBatch;
  ur?: boolean;
  onClose: () => void;
}

export function QRBatchExportNoticeDialog({
  batch,
  ur = false,
  onClose,
}: QRBatchExportNoticeDialogProps) {
  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-export-title"
      dir={ur ? "rtl" : "ltr"}
    >
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-lg w-full overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-150">
        <div className="p-6 space-y-4">
          <div className="flex items-center gap-3 text-amber-600">
            <span className="p-2 bg-amber-50 rounded-lg">
              <AdminIcon name="file-lock-2" className="w-6 h-6" />
            </span>
            <div>
              <h3 id="modal-export-title" className="font-bold text-slate-800 text-sm">
                {ur ? "پروڈکشن ایکسپورٹ فیچر غیر دستیاب ہے" : "Production Export Unavailable"}
              </h3>
              <p className="text-xs text-slate-500 font-mono">{batch.id}</p>
            </div>
          </div>

          <div className="space-y-3 text-xs text-slate-600 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200">
            <p>
              {ur
                ? "پروڈکشن کیو آر کوڈ کے کریڈینشلز میں حساس کرپٹوگرافک سیکرٹس (API-090) شامل ہوتے ہیں۔ کیپیئر جنریشن کے لیے ہارڈ ویئر CSPRNG اور ایکسپورٹ کے لیے ڈوئل کسٹڈی اتھارٹی اور انکرپٹڈ پے لوڈز کی ضرورت ہوتی ہے۔"
                : "Production QR credentials contain sensitive cryptographic keypairs (API-090). Generating and exporting production manufacturing payloads requires server-side HSM approval, dual-custody authorization, tamper-evident seals, and signed audit records."}
            </p>
            <p className="font-medium text-slate-800">
              {ur
                ? "براؤزر پروٹو ٹائپ کی پابندیاں:"
                : "Browser Mock Environment Safeguard:"}
            </p>
            <ul className="list-disc ps-5 space-y-1 text-slate-600">
              <li>
                {ur
                  ? "کوئی فرضی یا غیر محفوظ کرپٹوگرافک فائل ڈاؤن لوڈ نہیں کی جائے گی۔"
                  : "No insecure or placeholder credential files will be downloaded."}
              </li>
              <li>
                {ur
                  ? "ایکسپورٹ کے کلک سے ایکسپورٹ اسٹیٹس غلط طور پر تبدیل نہیں ہوگا۔"
                  : "Export status is preserved as metadata only and will not be falsely altered."}
              </li>
              <li>
                {ur
                  ? "حقیقی پروڈکشن مینوفیکچرنگ کی انٹیگریشن کوڈیکس کے ذریعے الگ کی جائے گی۔"
                  : "Production print manufacturing handoffs are handled independently by backend services."}
              </li>
            </ul>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
            >
              {ur ? "سمجھ گیا (بند کریں)" : "Understood (Close)"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* =========================================================================
   Component: Admin QR Batch Details (Screen 10 Details View)
   ========================================================================= */
export interface AdminQRBatchDetailsProps {
  batchId: string;
  ur?: boolean;
}

export function AdminQRBatchDetails({ batchId, ur = false }: AdminQRBatchDetailsProps) {
  const { data } = useAdminMockData();
  const [isExportNoticeOpen, setIsExportNoticeOpen] = useState(false);

  // Look up batch in mock store
  const batch = useMemo(() => {
    return getQRBatchById(batchId);
  }, [batchId, data.qrBatches]);

  // Handle invalid / non-existent batch ID
  if (!batch) {
    return (
      <div className="space-y-6" dir={ur ? "rtl" : "ltr"}>
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <AdminEmptyState
            title={ur ? "بیچ نہیں ملا" : "Batch Not Found"}
            description={
              ur
                ? `آئی ڈی '${batchId}' کے ساتھ کوئی کیو آر بیچ ریکارڈ نہیں ملا۔`
                : `No QR batch record was found for identifier '${batchId}'.`
            }
            action={
              <Link
                href="/admin/batches"
                className="px-3 py-1.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm transition-colors inline-block"
              >
                {ur ? "بیچز فہرست پر واپس جائیں" : "Back to QR Batches"}
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" dir={ur ? "rtl" : "ltr"}>
      {/* 1. Breadcrumbs & Header Card */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Link
            href="/admin/batches"
            className="text-sky-600 hover:text-sky-800 hover:underline flex items-center gap-1"
          >
            <AdminIcon name="chevron-left" className="w-3.5 h-3.5 rtl:rotate-180" />
            <span>{ur ? "کیو آر بیچز" : "QR Batches"}</span>
          </Link>
          <span>/</span>
          <span className="font-mono text-slate-700 font-medium">{batch.id}</span>
        </div>

        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pt-2 border-t border-slate-100">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-mono font-bold text-slate-900 text-lg sm:text-xl">
                {batch.id}
              </h1>
              <BatchQAStatusBadge status={batch.status} ur={ur} />
              {batch.isDemo && (
                <span className="text-[11px] px-2 py-0.5 font-sans font-medium text-slate-600 bg-slate-100 border border-slate-200 rounded-full">
                  {ur ? "ڈیمو ریکارڈ" : "Demo Reference"}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {ur
                ? `تیار کردہ: ${batch.generatedAt} — مصنوعی بیچ میٹا ڈیٹا`
                : `Generated on ${batch.generatedAt} — Synthetic Demonstration Batch`}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/admin/batches"
              className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              {ur ? "← فہرست پر واپس" : "← Back to Batches"}
            </Link>
            <button
              type="button"
              onClick={() => setIsExportNoticeOpen(true)}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <AdminIcon name="file-lock-2" className="w-3.5 h-3.5 text-slate-400" />
              <span>{ur ? "ایکسپورٹ پی لوڈ" : "Export Payload"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Three Details Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card A: Batch Metadata & Specifications */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="p-1.5 bg-sky-50 text-sky-600 rounded-lg">
              <AdminIcon name="boxes" className="w-4 h-4" />
            </span>
            <h2 className="font-bold text-slate-800 text-sm">
              {ur ? "بیچ کی معلومات" : "Batch Information"}
            </h2>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500">{ur ? "بیچ آئی ڈی" : "Batch ID"}</span>
              <span className="font-mono font-semibold text-slate-800">{batch.id}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500">{ur ? "کل فزیکل ٹیگز" : "Total Tags"}</span>
              <span className="font-semibold text-slate-800">
                {batch.size.toLocaleString()} {ur ? "ٹیگز" : "tags"}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500">{ur ? "کیو آر جوڑے" : "QR Pairs"}</span>
              <span className="font-semibold text-slate-800">
                {batch.pairsCount.toLocaleString()} {ur ? "جوڑے (1 جوڑا = 2 ٹیگز)" : "pairs (1:2 ratio)"}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500">{ur ? "تاریخ تیاری" : "Created Date"}</span>
              <span className="font-mono text-slate-700">{batch.generatedAt}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500">{ur ? "پرنٹ میٹریل" : "Print Material"}</span>
              <span className="capitalize text-slate-800">{batch.printMaterial || "synthetic-waterproof"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500">{ur ? "ای سی سی لیول" : "ECC Level"}</span>
              <span className="font-mono font-semibold text-slate-800">
                Level {batch.eccLevel || "Q"} (ISO 18004)
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500">{ur ? "ماحول" : "Environment"}</span>
              <span className="capitalize text-slate-800">{batch.intendedEnvironment || "indoor"}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-500">{ur ? "ایکسپورٹ کا درجہ" : "Export Metadata"}</span>
              <span className="font-medium text-slate-800">
                {batch.exported ? "Exported (Mock Flag)" : "Not Exported"}
              </span>
            </div>
          </div>
        </div>

        {/* Card B: QA Readiness & Inspection Status */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg">
              <AdminIcon name="shield-check" className="w-4 h-4" />
            </span>
            <h2 className="font-bold text-slate-800 text-sm">
              {ur ? "کیو اے کی تیاری اور انسپیکشن" : "QA Readiness & Inspection"}
            </h2>
          </div>

          <div className="space-y-3 text-xs">
            {batch.status === "QA Passed" ? (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-emerald-900 space-y-2">
                <div className="flex items-center gap-1.5 font-semibold text-emerald-800">
                  <AdminIcon name="check-circle-2" className="w-4 h-4 text-emerald-600" />
                  <span>{ur ? "کیو اے انسپیکشن پاس" : "QA Inspection Approved"}</span>
                </div>
                <p className="text-emerald-700 leading-relaxed">
                  {batch.qaMetadata?.notes ||
                    (ur
                      ? "پروٹو ٹائپ فکسچر: گمشدگی اور ایمرجنسی دونوں ٹیگز پر کامیاب اسکیننگ تصدیق شدہ ہے۔"
                      : "Prototype fixture: verified contrast, quiet zone and pair matching across sample pairs.")}
                </p>
                {batch.qaMetadata?.inspectedAt && (
                  <p className="text-[11px] text-emerald-600 font-mono">
                    Inspected: {batch.qaMetadata.inspectedAt} (by {batch.qaMetadata.inspector || "QA Lead"})
                  </p>
                )}
              </div>
            ) : batch.status === "In QA" ? (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-amber-900 space-y-2">
                <div className="flex items-center gap-1.5 font-semibold text-amber-800">
                  <AdminIcon name="activity" className="w-4 h-4 text-amber-600" />
                  <span>{ur ? "کیو اے مرحلہ جاری ہے" : "QA Inspection In Progress"}</span>
                </div>
                <p className="text-amber-800 leading-relaxed">
                  {batch.qaMetadata?.notes ||
                    (ur
                      ? "نمونہ اسکین جاری ہیں؛ کنٹراسٹ اور بائلنگوئل لیبلز کی تصدیق کی جا رہی ہے۔"
                      : "Sample scans in progress; contrast, quiet zones and dual-tag identity verification underway.")}
                </p>
              </div>
            ) : (
              <div className="bg-sky-50 border border-sky-200 rounded-lg p-3 text-sky-900 space-y-2">
                <div className="flex items-center gap-1.5 font-semibold text-sky-800">
                  <AdminIcon name="info" className="w-4 h-4 text-sky-600" />
                  <span>{ur ? "فزیکل کیو اے کے منتظر" : "Awaiting Physical QA (Screen 11)"}</span>
                </div>
                <p className="text-sky-800 leading-relaxed">
                  {ur
                    ? "یہ بیچ ابھی فزیکل انسپیکشن کے منتظر ہے۔ جب تک اسکرین 11 پر کوالٹی ایشورنس مکمل نہیں ہو جاتی، یہ ٹیگز گاہکوں کے لیے جاری نہیں ہو سکتے۔"
                    : "This demonstration batch has not been physically inspected. Tags cannot be authorized for order fulfillment until physical QA approval is completed."}
                </p>
              </div>
            )}

            <div className="pt-2">
              <Link
                href="/admin/qa"
                className="w-full inline-flex justify-center items-center gap-1.5 py-2 px-3 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold transition-colors"
              >
                <span>{ur ? "کوالٹی ایشورنس ماڈیول پر جائیں (Screen 11)" : "Navigate to QA Module (Screen 11)"}</span>
                <AdminIcon name="chevron-right" className="w-3.5 h-3.5 rtl:rotate-180" />
              </Link>
            </div>
          </div>
        </div>

        {/* Card C: Production Export Availability & Security Notice */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="p-1.5 bg-amber-50 text-amber-600 rounded-lg">
              <AdminIcon name="file-lock-2" className="w-4 h-4" />
            </span>
            <h2 className="font-bold text-slate-800 text-sm">
              {ur ? "ایکسپورٹ سیکیورٹی اور رسائی" : "Export Security & Availability"}
            </h2>
          </div>

          <div className="space-y-3 text-xs">
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2 text-slate-600">
              <p className="font-semibold text-slate-800">
                {ur ? "پروڈکشن ایکسپورٹ غیر دستیاب ہے" : "Production Export Unavailable"}
              </p>
              <p className="leading-relaxed">
                {ur
                  ? "سیکیورٹی ضوابط (API-090) کے تحت کیو آر سیکرٹس کو فرنٹ اینڈ یا غیر محفوظ ڈاؤن لوڈز کے لیے کبھی بھی نہیں کھولا جاتا۔"
                  : "Cryptographic credentials and recovery tokens are sealed within hardware vaults (API-090). Frontend mock exports are strictly disabled to prevent exposure of sensitive secrets."}
              </p>
            </div>

            <button
              type="button"
              onClick={() => setIsExportNoticeOpen(true)}
              className="w-full py-2 px-3 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <AdminIcon name="info" className="w-4 h-4 text-slate-500" />
              <span>{ur ? "سیکیورٹی تقاضے دیکھیں" : "Review Export Safeguards"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Modal: Production Export Unavailable Notice */}
      {isExportNoticeOpen && (
        <QRBatchExportNoticeDialog
          batch={batch}
          ur={ur}
          onClose={() => setIsExportNoticeOpen(false)}
        />
      )}
    </div>
  );
}

