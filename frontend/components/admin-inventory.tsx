"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { AdminIcon } from "./admin-icons";
import {
  useAdminMockData,
  getProductStockStatus,
  getOverallInventoryHealth,
  INITIAL_INVENTORY_METRICS,
  type MockProduct,
} from "../lib/admin-mock-data";
import { useAdminRole } from "./admin-shell";
import { AdminEmptyState } from "./admin-ui";

export interface AdminInventoryManagementProps {
  ur?: boolean;
}

export function AdminInventoryManagement({ ur = false }: AdminInventoryManagementProps) {
  const { data } = useAdminMockData();
  const { authenticatedRoles } = useAdminRole();
  const effectiveRole = authenticatedRoles.join(" ");

  // Role permissions check
  const normalizedRole = effectiveRole.toLowerCase().replace(/[\s_-]+/g, "");
  const isAuthorized =
    normalizedRole.includes("superadmin") || normalizedRole.includes("operations");

  // Filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  // Extract unique categories from products
  const categories = useMemo(() => {
    const set = new Set<string>();
    data.products.forEach((p) => {
      if (p.category) set.add(p.category);
    });
    return Array.from(set).sort();
  }, [data.products]);

  // Evaluate overall health dynamically
  const overallHealth = useMemo(() => {
    return getOverallInventoryHealth(
      data.products,
      INITIAL_INVENTORY_METRICS.unassignedPairs,
      INITIAL_INVENTORY_METRICS.lowStockThreshold,
      INITIAL_INVENTORY_METRICS.productLowStockThreshold
    );
  }, [data.products]);

  // Filtered physical products
  const filteredProducts = useMemo(() => {
    return data.products.filter((p) => {
      // 1. Search by name or SKU
      const query = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !query ||
        p.name.toLowerCase().includes(query) ||
        (p.sku && p.sku.toLowerCase().includes(query));

      // 2. Category filter
      const matchesCategory =
        categoryFilter === "all" || p.category === categoryFilter;

      // 3. Status filter
      const status = getProductStockStatus(
        p.stock,
        INITIAL_INVENTORY_METRICS.productLowStockThreshold
      );
      let matchesStatus = true;
      if (statusFilter !== "all") {
        if (statusFilter === "in_stock") matchesStatus = status === "In Stock";
        else if (statusFilter === "low_stock") matchesStatus = status === "Low Stock";
        else if (statusFilter === "out_of_stock") matchesStatus = status === "Out of Stock";
        else if (statusFilter === "unknown") matchesStatus = status === "Unknown";
      }

      return matchesSearch && matchesCategory && matchesStatus;
    });
  }, [data.products, searchQuery, categoryFilter, statusFilter]);

  const hasActiveFilters =
    searchQuery !== "" || categoryFilter !== "all" || statusFilter !== "all";

  const handleClearFilters = () => {
    setSearchQuery("");
    setCategoryFilter("all");
    setStatusFilter("all");
  };

  return (
    <div className="space-y-6">
      {/* 1. TOP HEADER & HEALTH BADGE CARD */}
      <div className="bg-white p-5 md:p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-teal-50 text-[#0A756E]">
                <AdminIcon name="boxes" className="w-5 h-5" />
              </span>
              <h1 className="font-bold text-slate-900 text-base md:text-lg tracking-tight">
                {ur ? "جسمانی ذخیرہ اور کیو آر ٹیگ کی تقسیم" : "Physical Inventory & QR Tag Allocations"}
              </h1>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {ur
                ? "کم اسٹاک کی حدود، مصنوعات کی فہرست اور کیو آر جوڑوں کی نگرانی۔"
                : "Low-stock thresholds and pair distribution monitoring across catalog products."}
            </p>
          </div>

          {/* Dynamic Conditional Health Badge */}
          <div>
            {overallHealth === "Healthy" && (
              <span
                data-testid="inventory-health-badge"
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-800 text-xs font-semibold rounded-full border border-emerald-200"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>{ur ? "اسٹاک تسلی بخش (Healthy)" : "Stock Healthy"}</span>
              </span>
            )}
            {overallHealth === "Low Stock" && (
              <span
                data-testid="inventory-health-badge"
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-50 text-amber-800 text-xs font-semibold rounded-full border border-amber-200"
              >
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span>{ur ? "کم اسٹاک وارننگ (Low Stock)" : "Low Stock Alert"}</span>
              </span>
            )}
            {overallHealth === "Critical" && (
              <span
                data-testid="inventory-health-badge"
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-50 text-rose-800 text-xs font-semibold rounded-full border border-rose-200"
              >
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <span>{ur ? "انتہائی کم اسٹاک (Critical)" : "Critical Stock"}</span>
              </span>
            )}
            {overallHealth === "Unknown" && (
              <span
                data-testid="inventory-health-badge"
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 text-slate-700 text-xs font-semibold rounded-full border border-slate-200"
              >
                <span className="w-2 h-2 rounded-full bg-slate-400" />
                <span>{ur ? "نامعلوم کیفیت (Unknown)" : "Stock Status Unknown"}</span>
              </span>
            )}
          </div>
        </div>

        {/* 2. THREE SUMMARY METRIC CARDS (Prototype Reference) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Total Unassigned Pairs */}
          <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200 flex flex-col justify-between space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">
                {ur ? "کل غیر تفویض شدہ جوڑے" : "Total Unassigned Pairs"}
              </span>
              <span className="text-[10px] font-semibold bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded border border-slate-300">
                Demo reference
              </span>
            </div>
            <p className="text-xl md:text-2xl font-bold text-slate-900 mt-1 font-mono">
              {INITIAL_INVENTORY_METRICS.unassignedPairs.toLocaleString()} {ur ? "جوڑے" : "Pairs"}
            </p>
            <p className="text-[11px] text-slate-400">
              {ur
                ? "دستیاب فزیکل اسٹاک ماک بیلنس"
                : "Available manufactured pairs in demonstration storage"}
            </p>
          </div>

          {/* Card 2: Active Reserved Stock */}
          <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200 flex flex-col justify-between space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">
                {ur ? "فعال محفوظ اسٹاک" : "Active Reserved Stock"}
              </span>
              <span className="text-[10px] font-semibold bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded border border-slate-300">
                Demo reference
              </span>
            </div>
            <p className="text-xl md:text-2xl font-bold text-slate-900 mt-1 font-mono">
              {INITIAL_INVENTORY_METRICS.reservedPairs.toLocaleString()} {ur ? "جوڑے" : "Pairs"}
            </p>
            <p className="text-[11px] text-slate-400">
              {ur
                ? "زیر التواء آرڈرز اور جانچ پڑتال کے لیے مختص"
                : "Allocated to active checkouts and pending review queues"}
            </p>
          </div>

          {/* Card 3: Low-Stock Alert Level */}
          <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200 flex flex-col justify-between space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">
                {ur ? "کم اسٹاک الرٹ کی حد" : "Low-Stock Alert Level"}
              </span>
              <span className="text-[10px] font-semibold bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded border border-slate-300">
                Demo reference
              </span>
            </div>
            <p className="text-xl md:text-2xl font-bold text-slate-900 mt-1 font-mono">
              {INITIAL_INVENTORY_METRICS.lowStockThreshold.toLocaleString()} {ur ? "جوڑے" : "Pairs"}
            </p>
            <p className="text-[11px] text-slate-400">
              {ur
                ? "بیچ پروڈکشن شروع کرنے کی ترغیبی حد"
                : "Configured threshold triggering replenishment alerts"}
            </p>
          </div>
        </div>

        {/* Role restriction banner if viewing with restricted role */}
        {!isAuthorized && (
          <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5 text-xs text-amber-900">
            <AdminIcon name="alert-triangle" className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">{ur ? "محدود کردار رسائی:" : "Restricted Role Access:"}</span>{" "}
              <span>
                {ur
                  ? `آپ کا موجودہ کردار '${effectiveRole}' انوینٹری کی تفصیلی معلومات دیکھنے کا مجاز نہیں ہے۔ صرف آپریشنز یا سپر ایڈمن کو مکمل رسائی حاصل ہے۔`
                  : `Role '${effectiveRole}' has restricted view of Inventory Management (Operations or Superadmin required).`}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 3. PHYSICAL PRODUCT INVENTORY TABLE SECTION */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden space-y-4 p-5 md:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <AdminIcon name="package" className="w-4 h-4 text-slate-700" />
              <span>{ur ? "جسمانی مصنوعات کا ذخیرہ" : "Physical Product Inventory"}</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {ur
                ? "فعال کیٹلاگ میں درج شدہ مصنوعات کی موجودہ اسٹاک تعداد۔"
                : "Synthetic stock quantities derived from active catalog products."}
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {filteredProducts.length} {ur ? "مصنوعات" : "products"}
          </span>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-200">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <span className="absolute start-3 top-2.5 text-slate-400 pointer-events-none">
              <AdminIcon name="search" className="w-4 h-4" />
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={ur ? "پروڈکٹ کے نام یا SKU سے تلاش کریں..." : "Search products by title or SKU..."}
              aria-label={ur ? "پروڈکٹ تلاش کریں" : "Search products"}
              className="w-full ps-9 pe-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-teal-500 text-slate-900"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              aria-label={ur ? "کیٹیگری فلٹر" : "Filter by category"}
              className="bg-white text-slate-800 text-xs font-medium rounded-lg px-2.5 py-1.5 border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-teal-500 cursor-pointer"
            >
              <option value="all">{ur ? "تمام کیٹیگریز" : "All Categories"}</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label={ur ? "اسٹاک حالت فلٹر" : "Filter by stock status"}
              className="bg-white text-slate-800 text-xs font-medium rounded-lg px-2.5 py-1.5 border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-teal-500 cursor-pointer"
            >
              <option value="all">{ur ? "تمام حالتیں" : "All Stock Statuses"}</option>
              <option value="in_stock">{ur ? "دستیاب (In Stock)" : "In Stock"}</option>
              <option value="low_stock">{ur ? "کم اسٹاک (Low Stock)" : "Low Stock"}</option>
              <option value="out_of_stock">{ur ? "ختم شدہ (Out of Stock)" : "Out of Stock"}</option>
              <option value="unknown">{ur ? "نامعلوم (Unknown)" : "Unknown"}</option>
            </select>

            {/* Clear Filters Button */}
            <button
              type="button"
              onClick={handleClearFilters}
              disabled={!hasActiveFilters}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                hasActiveFilters
                  ? "bg-white border-slate-200 text-slate-700 hover:bg-slate-100 cursor-pointer"
                  : "bg-slate-100 border-slate-200 text-slate-400 cursor-not-allowed opacity-60"
              }`}
            >
              {ur ? "فلٹرز صاف کریں" : "Clear Filters"}
            </button>
          </div>
        </div>

        {/* Products Table */}
        <div className="overflow-x-auto">
          {filteredProducts.length === 0 ? (
            <div className="py-8">
              <AdminEmptyState
                icon="package"
                title={ur ? "کوئی پروڈکٹ نہیں ملی" : "No products match filters"}
                description={
                  ur
                    ? "آپ کے منتخب کردہ فلٹرز کے مطابق کوئی پروڈکٹ موجود نہیں ہے۔ فلٹرز صاف کر کے دوبارہ کوشش کریں۔"
                    : "No inventory records match the search query or active category/status filters."
                }
                action={
                  hasActiveFilters ? (
                    <button
                      type="button"
                      onClick={handleClearFilters}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-[#0A756E] text-white hover:bg-[#075D57] transition-colors cursor-pointer"
                    >
                      {ur ? "فلٹرز صاف کریں" : "Reset Filters"}
                    </button>
                  ) : undefined
                }
              />
            </div>
          ) : (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <th className="p-3 ps-4">{ur ? "پروڈکٹ" : "Product"}</th>
                  <th className="p-3">{ur ? "کیٹیگری" : "Category"}</th>
                  <th className="p-3 text-right">{ur ? "دستیاب اسٹاک" : "Available Stock"}</th>
                  <th className="p-3">{ur ? "اسٹاک کی حالت" : "Stock Status"}</th>
                  <th className="p-3">{ur ? "آخری اپ ڈیٹ" : "Updated"}</th>
                  <th className="p-3 pe-4 text-right">{ur ? "اقدامات" : "Actions"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredProducts.map((prod) => {
                  const status = getProductStockStatus(
                    prod.stock,
                    INITIAL_INVENTORY_METRICS.productLowStockThreshold
                  );
                  const isStockDefined = prod.stock !== undefined && prod.stock !== null && !isNaN(prod.stock);

                  return (
                    <tr key={prod.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="p-3 ps-4">
                        <div className="flex items-center gap-3">
                          {prod.coverImage ? (
                            <img
                              src={prod.coverImage}
                              alt={prod.name}
                              className="w-8 h-8 rounded-lg object-cover border border-slate-200 shrink-0"
                            />
                          ) : (
                            <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0 text-slate-500">
                              <AdminIcon name="package" className="w-4 h-4" />
                            </div>
                          )}
                          <div className="space-y-0.5">
                            <span className="font-semibold text-slate-900 block leading-snug">
                              {prod.name}
                            </span>
                            <span className="font-mono text-[11px] text-slate-400 block">
                              {prod.sku || prod.id}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td className="p-3">
                        <span className="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                          {prod.category}
                        </span>
                      </td>

                      <td className="p-3 text-right font-mono font-bold text-slate-900">
                        {isStockDefined ? `${prod.stock} ${ur ? "اکائیاں" : "Units"}` : (
                          <span className="text-slate-400 font-normal italic">
                            {ur ? "دستیاب نہیں" : "Not Available"}
                          </span>
                        )}
                      </td>

                      <td className="p-3">
                        {status === "In Stock" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            <span>{ur ? "دستیاب" : "In Stock"}</span>
                          </span>
                        )}
                        {status === "Low Stock" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                            <span>{ur ? "کم اسٹاک" : "Low Stock"}</span>
                          </span>
                        )}
                        {status === "Out of Stock" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-800 border border-rose-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                            <span>{ur ? "ختم شدہ" : "Out of Stock"}</span>
                          </span>
                        )}
                        {status === "Unknown" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                            <span>{ur ? "نامعلوم" : "Unknown"}</span>
                          </span>
                        )}
                      </td>

                      <td className="p-3 font-mono text-slate-500 text-[11px]">
                        {prod.updatedAt || "—"}
                      </td>

                      <td className="p-3 pe-4 text-right">
                        <Link
                          href={`/admin/products/${prod.id}`}
                          prefetch={false}
                          className="text-xs text-[#0A756E] hover:text-[#075D57] font-semibold hover:underline inline-flex items-center gap-1"
                        >
                          <span>{ur ? "تفصیلات" : "View"}</span>
                          <AdminIcon name="chevron-right" className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* 4. QR INVENTORY ARCHITECTURE & RECONCILIATION NOTICE */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 md:p-6 space-y-3">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-indigo-50 text-indigo-700 rounded-lg shrink-0 mt-0.5">
            <AdminIcon name="info" className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-slate-900">
              {ur ? "کیو آر ذخیرہ ماڈل اور تفریقی وضاحت" : "QR-Pair Inventory Architecture & Mock Reconciliation Notice"}
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              {ur
                ? "کیو آر جوڑوں کی دستیابی فی الوقت ڈیموسٹریشن کے اعداد و شمار پر مشتمل ہے۔ بیچ کی پیداوار اور گودام کے اسٹاک کے درمیان خودکار تصفیہ اس فرنٹ اینڈ ماک میں لاگو نہیں ہے۔"
                : "QR-pair availability is currently represented by demonstration figures. Batch-to-inventory reconciliation is not implemented in this frontend mock."}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-slate-700 pt-2 border-t border-slate-100">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
            <span className="font-semibold text-slate-900 block">
              {ur ? "1. کیٹلاگ مصنوعات کا ذخیرہ" : "1. Physical Catalog Inventory"}
            </span>
            <p className="text-[11px] text-slate-500 leading-snug">
              {ur
                ? "پروڈکٹ کی سطح پر اسٹاک انفرادی کیٹلاگ ریکارڈز سے حاصل ہوتا ہے۔"
                : "Tracked at product level in catalog state (Screens 3–5). Distinct from QR manufacturing."}
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
            <span className="font-semibold text-slate-900 block">
              {ur ? "2. کیو آر بیچ مینوفیکچرنگ" : "2. QR Batch Manufacturing"}
            </span>
            <p className="text-[11px] text-slate-500 leading-snug">
              {ur
                ? "کیو آر بیچ جنریشن اور کیو اے ٹیسٹنگ الگ ورک فلوز ہیں (API-090، اسکرین 10)۔"
                : "Batch generation and QA inspection operate under separate lifecycle workflows (API-090)."}
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
            <span className="font-semibold text-slate-900 block">
              {ur ? "3. کوئی غیر مجاز ایڈجسٹمنٹ نہیں" : "3. No Live Stock Adjustments"}
            </span>
            <p className="text-[11px] text-slate-500 leading-snug">
              {ur
                ? "اس اسکرین پر صرف معلوماتی ڈیش بورڈ ہے؛ کوئی نقلی لیجر یا خریداری لین دین نہیں ہوتے۔"
                : "Safe read-only overview. No arbitrary inventory adjustment or ledger mutations occur."}
            </p>
          </div>
        </div>

        <div className="pt-2 flex items-center justify-between text-xs text-slate-500">
          <span>
            {ur ? "کیو آر بیچ کا جائزہ لیں:" : "Explore manufacturing batches:"}
          </span>
          <Link
            href="/admin/batches"
            prefetch={false}
            className="text-xs font-semibold text-[#0A756E] hover:text-[#075D57] hover:underline inline-flex items-center gap-1"
          >
            <span>{ur ? "کیو آر بیچز پر جائیں (اسکرین 10)" : "View QR Batches (Screen 10)"}</span>
            <AdminIcon name="chevron-right" className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}

