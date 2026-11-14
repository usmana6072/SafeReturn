"use client";

import React, { useState, useMemo, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import styles from "./admin-qa.module.css";
import { AdminIcon } from "./admin-icons";
import {
  useAdminMockData,
  getQAPairById,
  recordQAPass,
  recordQAQuarantine,
  getQASummary,
  type MockQAPair,
  type MockQAInspection,
} from "../lib/admin-mock-data";
import { useAdminRole } from "./admin-shell";
import { useAdminToast } from "./admin-toast";
import { AdminEmptyState } from "./admin-ui";

export interface AdminQAProps {
  ur?: boolean;
}

const REJECTION_REASONS = [
  "Print quality issue",
  "QR readability issue",
  "Physical damage",
  "Other inspection concern",
] as const;

export function AdminQA({ ur = false }: AdminQAProps) {
  const { data, refresh } = useAdminMockData();
  const { effectiveRole, selectedRole, authenticatedRoles } = useAdminRole();
  const { showToast } = useAdminToast();

  // Role permissions check
  const isAuthorized = selectedRole === "authenticated" &&
    authenticatedRoles.some(role => role === "operations" || role === "superadmin");

  // Inspection form states
  const [selectedBatchId, setSelectedBatchId] = useState<string>("all");
  const [pairInput, setPairInput] = useState<string>("");
  const [selectedPair, setActivePair] = useState<MockQAPair | null>(null);
  const activePair = data.qaPairs.find(pair => pair.id === selectedPair?.id) || null;
  const [lookupError, setLookupError] = useState<string | null>(null);

  // Modal dialog states
  const [quarantineModalPair, setQuarantineModalPair] = useState<MockQAPair | null>(null);
  const [detailsModalInspection, setDetailsModalInspection] = useState<MockQAInspection | null>(null);

  // Inspection history filter states
  const [historySearchQuery, setHistorySearchQuery] = useState("");
  const [historyOutcomeFilter, setHistoryOutcomeFilter] = useState("all");
  const [historyBatchFilter, setHistoryBatchFilter] = useState("all");

  // Summary counts derived dynamically from stored mock pairs
  const summary = useMemo(() => {
    return getQASummary();
  }, [data.qaPairs]);

  // Available batches list from mock database
  const availableBatches = useMemo(() => {
    return (data.qrBatches || []).map((b) => b.id);
  }, [data.qrBatches]);

  // Available pairs for selected batch (for quick selection)
  const availablePairsForBatch = useMemo(() => {
    return (data.qaPairs || []).filter(pair => selectedBatchId === "all" || pair.batchId === selectedBatchId);
  }, [selectedBatchId, data.qaPairs]);

  // Lookup handler
  const handleLookup = useCallback(
    (targetId?: string) => {
      setLookupError(null);
      const idToLookup = (targetId || pairInput).trim();
      if (!idToLookup) {
        setLookupError(
          ur
            ? "براہ کرم ڈیمو جوڑے کی شناخت (ID) درج کریں یا منتخب کریں۔"
            : "Please enter or select a demo pair ID."
        );
        setActivePair(null);
        return;
      }

      const found = getQAPairById(idToLookup);
      if (!found) {
        setLookupError(
          ur
            ? `ڈیمو جوڑا '${idToLookup}' نہیں ملا۔ موجودہ مصنوعی جوڑوں میں سے منتخب کریں۔`
            : `Demo pair '${idToLookup}' not found. Select an existing synthetic pair from the available mock records.`
        );
        setActivePair(null);
        return;
      }

      // Check batch scope if specific batch selected
      if (
        selectedBatchId !== "all" &&
        found.batchId.toLowerCase() !== selectedBatchId.toLowerCase()
      ) {
        setLookupError(
          ur
            ? `جوڑا '${found.id}' بیچ '${found.batchId}' سے تعلق رکھتا ہے، منتخب کردہ بیچ '${selectedBatchId}' سے نہیں۔`
            : `Pair '${found.id}' belongs to batch '${found.batchId}', not the currently selected batch '${selectedBatchId}'.`
        );
        setActivePair(null);
        return;
      }

      setActivePair(found);
      setPairInput(found.id);
    },
    [pairInput, selectedBatchId, ur]
  );

  // Quick select a pair chip
  const handleQuickSelect = (pair: MockQAPair) => {
    setPairInput(pair.id);
    setLookupError(null);
    setActivePair(pair);
  };

  // Pass QA Action
  const handlePassQA = () => {
    if (!isAuthorized) {
      showToast(
        ur
          ? "رسائی مسترد: کیو اے معائنہ ریکارڈ کرنے کی اجازت صرف آپریشنز اور سپر ایڈمن کو ہے۔"
          : "Access Denied: Only Operations and Superadmin can record QA inspection outcomes.",
        "error"
      );
      return;
    }

    if (!activePair) return;

    const result = recordQAPass({
      pairId: activePair.id,
      inspector: effectiveRole,
    });

    if (!result.success) {
      showToast(result.error, "error");
      return;
    }

    showToast(
      ur
        ? `ڈیمو جوڑا '${activePair.id}' کیو اے پاس کے طور پر ریکارڈ کر لیا گیا۔`
        : "Demo QA result recorded as Passed.",
      "success"
    );

    setActivePair(result.pair);
    refresh();
  };

  // Reject & Quarantine Action Trigger
  const handleOpenQuarantine = () => {
    if (!isAuthorized) {
      showToast(
        ur
          ? "رسائی مسترد: کیو اے معائنہ ریکارڈ کرنے کی اجازت صرف آپریشنز اور سپر ایڈمن کو ہے۔"
          : "Access Denied: Only Operations and Superadmin can record QA inspection outcomes.",
        "error"
      );
      return;
    }

    if (!activePair) return;
    setQuarantineModalPair(activePair);
  };

  // Filtered Inspection History
  const filteredInspections = useMemo(() => {
    const list = data.qaInspections || [];
    return [...list].sort((a, b) => b.timestamp.localeCompare(a.timestamp)).filter((ins) => {
      const q = historySearchQuery.trim().toLowerCase();
      const matchesSearch =
        !q ||
        ins.pairId.toLowerCase().includes(q) ||
        ins.batchId.toLowerCase().includes(q) ||
        (ins.rejectionReason && ins.rejectionReason.toLowerCase().includes(q));

      const matchesOutcome =
        historyOutcomeFilter === "all" ||
        ins.outcome.toLowerCase() === historyOutcomeFilter.toLowerCase();

      const matchesBatch =
        historyBatchFilter === "all" ||
        ins.batchId.toLowerCase() === historyBatchFilter.toLowerCase();

      return matchesSearch && matchesOutcome && matchesBatch;
    });
  }, [data.qaInspections, historySearchQuery, historyOutcomeFilter, historyBatchFilter]);

  const hasActiveHistoryFilters =
    historySearchQuery.trim() !== "" ||
    historyOutcomeFilter !== "all" ||
    historyBatchFilter !== "all";

  const handleClearHistoryFilters = () => {
    setHistorySearchQuery("");
    setHistoryOutcomeFilter("all");
    setHistoryBatchFilter("all");
  };

  return (
    <div className={styles.screen + " space-y-4 min-w-0"} dir={ur ? "rtl" : "ltr"}>
      {/* 1. Header Card */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
              <AdminIcon name="check-circle-2" className="w-5 h-5" />
            </span>
            <h1 className="font-bold text-slate-800 text-lg sm:text-xl">
              {ur ? "کیو آر کوالٹی ایشورنس (فزیکل انسپیکشن)" : "QR Quality Assurance"}
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {ur
              ? "تیار کردہ کیو آر جوڑوں کے لیے بصری معائنہ اور اسکین تصدیق کی جانچ کریں۔"
              : "Record simulated physical inspection results for demonstration QR pairs."}
          </p>
        </div>

        <Link
          href="/admin/batches"
          className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-1.5"
        >
          <AdminIcon name="boxes" className="w-3.5 h-3.5 text-slate-500" />
          <span>{ur ? "کیو آر بیچز دیکھیں" : "View QR Batches"}</span>
        </Link>
      </div>

      {/* 2. Demonstration Information Notice */}
      <div className="bg-sky-50 border border-sky-200 rounded-xl p-4 flex items-start gap-3">
        <span className="text-sky-600 mt-0.5 shrink-0">
          <AdminIcon name="info" className="w-5 h-5" />
        </span>
        <div className="text-xs text-sky-950 space-y-1">
          <p className="font-semibold">
            {ur ? "کیو اے ڈیمو ماحول کی حدود:" : "Demo Quality Assurance Notice:"}
          </p>
          <p className="text-sky-800 leading-relaxed">
            {ur
              ? "کیو اے کے نتائج فرنٹ اینڈ ڈیمو ماحول میں محفوظ کیے جاتے ہیں۔ یہ حقیقی کیو آر کریڈینشلز کی تصدیق نہیں کرتے، فزیکل پروڈکشن کی منظوری نہیں دیتے اور نہ ہی لائیو انوینٹری جاری کرتے ہیں۔"
              : "QA results are stored in the frontend demo environment. They do not verify real QR credentials, approve physical production or release stock."}
          </p>
        </div>
      </div>

      {!isAuthorized && <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs">Role preview cannot grant inspection rights. Use your authenticated Operations or Superadmin role.</p>}
      {availableBatches.length === 0 && <p role="status">No synthetic batches available.</p>}
      {availablePairsForBatch.length === 0 && <p role="status">No demo pairs are materialized for this batch.</p>}
      {/* 3. Top Row Grid: Inspection Form & QA Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Physical Inspection Form Card (7 cols) */}
        <div className="lg:col-span-7 bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="p-1.5 bg-sky-50 text-sky-600 rounded-lg">
              <AdminIcon name="search" className="w-4 h-4" />
            </span>
            <h2 className="font-bold text-slate-800 text-sm">
              {ur ? "فزیکل انسپیکشن اور اسکین" : "Demo Physical Inspection"}
            </h2>
          </div>

          <div className="space-y-4">
            {/* Batch Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                {ur ? "مینوفیکچرنگ بیچ (Batch Scope)" : "Manufacturing Batch"}
              </label>
              <select
                aria-label="Batch" value={selectedBatchId}
                onChange={(e) => {
                  setSelectedBatchId(e.target.value);
                  setActivePair(null);
                  setLookupError(null);
                }}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
              >
                <option value="all">{ur ? "تمام بیچز (All Batches)" : "All Batches"}</option>
                {availableBatches.map((bId) => (
                  <option key={bId} value={bId}>
                    {bId}
                  </option>
                ))}
              </select>
            </div>

            {/* Pair Tag ID Input & Lookup */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                {ur ? "پیئر ٹیگ آئی ڈی اسکین یا درج کریں *" : "Scan or Enter Pair Tag ID *"}
              </label>
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="text"
                  aria-label="Pair Tag ID" value={pairInput}
                  onChange={(e) => {
                    setPairInput(e.target.value);
                    setActivePair(null);
                    if (lookupError) setLookupError(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleLookup();
                    }
                  }}
                  placeholder="Scan or enter demo pair ID..."
                  className="min-w-0 flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition"
                />
                <button
                  type="button"
                  onClick={() => handleLookup()}
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm cursor-pointer"
                >
                  <AdminIcon name="search" className="w-3.5 h-3.5" />
                  <span>{ur ? "تلاش کریں" : "Lookup Demo Pair"}</span>
                </button>
              </div>

              {/* Quick Pick Chips for Available Pairs */}
              {availablePairsForBatch.length > 0 && (
                <div className="mt-2 space-y-1">
                  <span className="text-[11px] text-slate-500">
                    {ur ? "دستیاب ڈیمو جوڑے (فوری انتخاب):" : "Available demo pairs for batch:"}
                  </span>
                  <div className="flex flex-wrap gap-1.5 pt-0.5">
                    {availablePairsForBatch.slice(0, 6).map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => handleQuickSelect(p)}
                        className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors flex items-center gap-1 border ${
                          activePair?.id === p.id
                            ? "bg-sky-100 text-sky-800 border-sky-300 font-bold"
                            : "bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200"
                        }`}
                      >
                        <span>{p.id}</span>
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            p.status === "Passed"
                              ? "bg-emerald-500"
                              : p.status === "Quarantined"
                              ? "bg-rose-500"
                              : "bg-sky-500"
                          }`}
                        />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Lookup Error Message */}
            {lookupError && (
              <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-lg p-3 text-xs flex items-start gap-2 animate-in fade-in">
                <span className="text-rose-600 mt-0.5 shrink-0">
                  <AdminIcon name="alert-circle" className="w-4 h-4" />
                </span>
                <span>{lookupError}</span>
              </div>
            )}

            {/* Active Pair Details Card */}
            {activePair && (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3 animate-in fade-in duration-150">
                <div className="flex flex-wrap gap-2 items-center justify-between border-b border-slate-200 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-900 text-sm">
                      {activePair.id}
                    </span>
                    <span className="text-slate-400">·</span>
                    <span className="font-mono text-xs text-slate-600">
                      {activePair.batchId}
                    </span>
                  </div>
                  <QAPairStatusBadge status={activePair.status} ur={ur} />
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-500 block text-[11px]">
                      {ur ? "کیو اے کی موجودہ حالت" : "Inspection State"}
                    </span>
                    <span className="font-semibold text-slate-800">{activePair.status}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[11px]">
                      {ur ? "آخری معائنہ کنندہ" : "Last Inspector"}
                    </span>
                    <span className="text-slate-800">{activePair.inspector || "—"}</span>
                  </div>
                  {activePair.lastInspectedAt && (
                    <div className="col-span-2">
                      <span className="text-slate-500 block text-[11px]">
                        {ur ? "معائنہ کا وقت" : "Inspected At"}
                      </span>
                      <span className="font-mono text-slate-700">{activePair.lastInspectedAt}</span>
                    </div>
                  )}
                  {activePair.rejectionReason && (
                    <div className="col-span-2 bg-rose-50 border border-rose-200 rounded p-2 text-rose-800">
                      <span className="font-semibold block text-[11px]">
                        {ur ? "قرنطینہ کی وجہ:" : "Quarantine Reason:"}
                      </span>
                      <span>{activePair.rejectionReason}</span>
                      {activePair.notes && (
                        <p className="text-[11px] text-rose-700 mt-1">{activePair.notes}</p>
                      )}
                    </div>
                  )}
                </div>

                {/* Already Inspected Warning Notice */}
                {activePair.status !== "Awaiting QA" && (
                  <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded p-2.5 text-xs flex items-center gap-2">
                    <AdminIcon name="alert-triangle" className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>
                      {ur
                        ? "اس ڈیمو ورک فلو میں دوبارہ معائنہ (Reinspection) دستیاب نہیں ہے۔"
                        : "Reinspection is not available in this demo workflow."}
                    </span>
                  </div>
                )}

                {/* Action Buttons: Pass QA / Reject & Quarantine */}
                <div className="pt-2 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={handlePassQA}
                    disabled={activePair.status !== "Awaiting QA" || !isAuthorized}
                    className="flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 shadow-sm cursor-pointer"
                  >
                    <AdminIcon name="check" className="w-3.5 h-3.5" />
                    <span>{ur ? "کیو اے منظور کریں (Pass QA)" : "Pass QA"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleOpenQuarantine}
                    disabled={activePair.status !== "Awaiting QA" || !isAuthorized}
                    className="flex-1 py-2 px-3 bg-rose-600 hover:bg-rose-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 shadow-sm cursor-pointer"
                  >
                    <AdminIcon name="alert-triangle" className="w-3.5 h-3.5" />
                    <span>{ur ? "مسترد اور قرنطینہ کریں" : "Reject & Quarantine"}</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: QA Summary & Metrics Card (5 cols) */}
        <div className="lg:col-span-5 bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg">
              <AdminIcon name="activity" className="w-4 h-4" />
            </span>
            <h2 className="font-bold text-slate-800 text-sm">
              {ur ? "کیو اے سمری کا جائزہ" : "QA Inspection Summary"}
            </h2>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Total Inspected */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
              <span className="text-[11px] font-medium text-slate-500">
                {ur ? "معائنہ شدہ جوڑے" : "Inspected Demo Pairs"}
              </span>
              <p className="text-2xl font-bold text-slate-900">{summary.totalInspected}</p>
              <span className="text-[10px] text-slate-400">Stored inspections</span>
            </div>

            {/* Passed */}
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1">
              <span className="text-[11px] font-medium text-emerald-700">
                {ur ? "پاس شدہ (Passed)" : "Passed"}
              </span>
              <p className="text-2xl font-bold text-emerald-800">{summary.passed}</p>
              <span className="text-[10px] text-emerald-600">Simulated pass</span>
            </div>

            {/* Quarantined */}
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-1">
              <span className="text-[11px] font-medium text-rose-700">
                {ur ? "قرنطینہ شدہ" : "Quarantined"}
              </span>
              <p className="text-2xl font-bold text-rose-800">{summary.quarantined}</p>
              <span className="text-[10px] text-rose-600">Defects flagged</span>
            </div>

            {/* Awaiting Inspection */}
            <div className="p-4 bg-sky-50 border border-sky-200 rounded-xl space-y-1">
              <span className="text-[11px] font-medium text-sky-700">
                {ur ? "منتظر معائنہ" : "Awaiting Inspection"}
              </span>
              <p className="text-2xl font-bold text-sky-800">{summary.awaiting}</p>
              <span className="text-[10px] text-sky-600">Available sample pool</span>
            </div>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-600 text-[11px] leading-relaxed">
            <p className="font-semibold text-slate-800 mb-0.5">
              {ur ? "آپریشنل تعلق:" : "Operational Relationship:"}
            </p>
            <p>
              {ur
                ? "جوڑے کی سطح پر کیو اے کے نتائج پورے بیچ کو خودکار طریقے سے پاس یا فیل نہیں کرتے۔ بیچ کی منظوری کے لیے آزادانہ تصدیق درکار ہوتی ہے۔"
                : "Pair-level inspection outcomes do not automatically change overall batch status or release warehouse inventory."}
            </p>
          </div>
        </div>
      </div>

      {/* 4. Bottom Row: Recent QA Inspections Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <h2 className="font-bold text-slate-800 text-sm">
              {ur ? "حالیہ کیو اے معائنہ جات" : "Recent QA Inspections"}
            </h2>
            <p className="text-xs text-slate-500">
              {ur
                ? "اس براؤزر سیشن میں ریکارڈ شدہ تمام مصنوعی معائنہ جات کی تاریخ۔"
                : "Log of recorded synthetic physical inspection outcomes."}
            </p>
          </div>

          {/* Filter Toolbar */}
          <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
            {/* Search Pair ID */}
            <div className="relative flex-1 sm:w-44">
              <span className="absolute inset-y-0 start-0 flex items-center ps-2.5 pointer-events-none text-slate-400">
                <AdminIcon name="search" className="w-3.5 h-3.5" />
              </span>
              <input
                type="text"
                aria-label="Search inspection pair ID" value={historySearchQuery}
                onChange={(e) => setHistorySearchQuery(e.target.value)}
                placeholder={ur ? "تلاش پیئر آئی ڈی..." : "Search Pair ID..."}
                className="w-full ps-8 pe-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>

            {/* Outcome Filter */}
            <select
              aria-label="Inspection outcome" value={historyOutcomeFilter}
              onChange={(e) => setHistoryOutcomeFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="all">{ur ? "تمام نتائج" : "All Outcomes"}</option>
              <option value="Passed">{ur ? "پاس" : "Passed"}</option>
              <option value="Quarantined">{ur ? "قرنطینہ" : "Quarantined"}</option>
            </select>

            {/* Batch Filter */}
            <select
              aria-label="Inspection batch" value={historyBatchFilter}
              onChange={(e) => setHistoryBatchFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
            >
              <option value="all">{ur ? "تمام بیچز" : "All Batches"}</option>
              {availableBatches.map((bId) => (
                <option key={bId} value={bId}>
                  {bId}
                </option>
              ))}
            </select>

            {/* Clear Filters */}
            {hasActiveHistoryFilters && (
              <button
                type="button"
                onClick={handleClearHistoryFilters}
                className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
                title={ur ? "فلٹرز صاف کریں" : "Clear filters"}
              >
                <AdminIcon name="x" className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Table / Empty State */}
        {filteredInspections.length === 0 ? (
          <div className="py-8">
            <AdminEmptyState
              title={ur ? "کوئی معائنہ ریکارڈ نہیں ملا" : "No Inspections Found"}
              description={
                hasActiveHistoryFilters
                  ? ur
                    ? "آپ کے فلٹرز سے کوئی معائنہ ریکارڈ مطابقت نہیں رکھتا۔"
                    : "No inspection records match the selected filters."
                  : ur
                    ? "ابھی تک کوئی کیو اے معائنہ ریکارڈ نہیں ہوا ہے۔"
                    : "No synthetic QA inspection records exist in the mock store."
              }
              action={
                hasActiveHistoryFilters ? (
                  <button
                    type="button"
                    onClick={handleClearHistoryFilters}
                    className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
                  >
                    {ur ? "فلٹرز صاف کریں" : "Clear Filters"}
                  </button>
                ) : undefined
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <th className="py-2.5 px-3">{ur ? "پیئر آئی ڈی" : "Pair ID"}</th>
                  <th className="py-2.5 px-3">{ur ? "بیچ" : "Batch"}</th>
                  <th className="py-2.5 px-3">{ur ? "نتیجہ" : "Result"}</th>
                  <th className="py-2.5 px-3">{ur ? "معائنہ کار" : "Inspector"}</th>
                  <th className="py-2.5 px-3">{ur ? "تاریخ و وقت" : "Inspected At"}</th>
                  <th className="py-2.5 px-3">{ur ? "وجہ / نوٹس" : "Reason / Notes"}</th>
                  <th className="py-2.5 px-3 text-end">{ur ? "کارروائی" : "Actions"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredInspections.map((ins) => (
                  <tr key={ins.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">
                      {ins.pairId}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-600">{ins.batchId}</td>
                    <td className="py-2.5 px-3">
                      <QAPairStatusBadge status={ins.outcome} ur={ur} />
                    </td>
                    <td className="py-2.5 px-3 text-slate-700">{ins.inspector}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                      {ins.timestamp}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 max-w-xs truncate">
                      {ins.rejectionReason ? (
                        <span className="text-rose-700 font-medium">
                          {ins.rejectionReason}
                          {ins.notes ? ` · ${ins.notes}` : ""}
                        </span>
                      ) : (
                        <span>{ins.notes || "—"}</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-end whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => setDetailsModalInspection(ins)}
                        className="px-2.5 py-1 text-xs font-semibold text-sky-600 hover:text-sky-800 hover:bg-sky-50 rounded transition-colors"
                      >
                        {ur ? "تفصیل دیکھیں" : "View Details"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Reject & Quarantine Confirmation Dialog */}
      {quarantineModalPair && (
        <QRRejectDialog
          pair={quarantineModalPair}
          ur={ur}
          actor={effectiveRole}
          onClose={() => setQuarantineModalPair(null)}
          onSuccess={(updatedPair) => {
            setQuarantineModalPair(null);
            setActivePair(updatedPair);
            refresh();
          }}
        />
      )}

      {/* Modal: View Inspection Details Dialog */}
      {detailsModalInspection && (
        <QRInspectionDetailsDialog
          inspection={detailsModalInspection}
          ur={ur}
          onClose={() => setDetailsModalInspection(null)}
        />
      )}
    </div>
  );
}

/* =========================================================================
   Component: QA Pair Status Badge
   ========================================================================= */
export function QAPairStatusBadge({
  status,
  ur = false,
}: {
  status: MockQAPair["status"];
  ur?: boolean;
}) {
  switch (status) {
    case "Passed":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
          <AdminIcon name="check-circle-2" className="w-3 h-3" />
          <span>{ur ? "پاس" : "Passed"}</span>
        </span>
      );
    case "Quarantined":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
          <AdminIcon name="alert-triangle" className="w-3 h-3" />
          <span>{ur ? "قرنطینہ" : "Quarantined"}</span>
        </span>
      );
    case "Awaiting QA":
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-sky-100 text-sky-800 border border-sky-200">
          <AdminIcon name="info" className="w-3 h-3" />
          <span>{ur ? "منتظر معائنہ" : "Awaiting QA"}</span>
        </span>
      );
  }
}

/* =========================================================================
   Component: Reject & Quarantine Modal Dialog
   ========================================================================= */
interface QRRejectDialogProps {
  pair: MockQAPair;
  ur?: boolean;
  actor: string;
  onClose: () => void;
  onSuccess: (updatedPair: MockQAPair) => void;
}

export function QRRejectDialog({
  pair,
  ur = false,
  actor,
  onClose,
  onSuccess,
}: QRRejectDialogProps) {
  const { showToast } = useAdminToast();
  const [selectedReason, setSelectedReason] = useState<string>("");
  const dialogRef = useQADialog();
  const { selectedRole, authenticatedRoles } = useAdminRole();
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!selectedReason.trim()) {
      setErrorMessage(
        ur ? "براہ کرم مسترد کرنے کی وجہ منتخب کریں۔" : "Please select a rejection reason."
      );
      return;
    }

    if (selectedRole !== "authenticated" || !authenticatedRoles.some(role => role === "operations" || role === "superadmin")) { setErrorMessage("Authenticated Operations or Superadmin role required."); return; }
    setIsSubmitting(true);
    const result = recordQAQuarantine({
      pairId: pair.id,
      rejectionReason: selectedReason,
      notes: notes.trim() || undefined,
      inspector: actor,
    });

    if (!result.success) {
      setErrorMessage(result.error);
      setIsSubmitting(false);
      return;
    }

    showToast(
      ur
        ? `ڈیمو جوڑا '${pair.id}' کو قرنطینہ کے طور پر نشان زد کر دیا گیا۔`
        : "Demo pair marked as Quarantined.",
      "success"
    );

    onSuccess(result.pair);
  };

  return (
    <dialog
      className="fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-md rounded-xl p-0 border-0 backdrop:bg-slate-900/50 overflow-y-auto"
      ref={dialogRef} onCancel={onClose}
      aria-modal="true"
      aria-labelledby="modal-quarantine-title"
      dir={ur ? "rtl" : "ltr"}
    >
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-150">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-rose-50 text-rose-900">
          <div className="flex items-center gap-2">
            <span className="p-1.5 bg-rose-100 text-rose-700 rounded-lg">
              <AdminIcon name="alert-triangle" className="w-4 h-4" />
            </span>
            <h2 id="modal-quarantine-title" className="font-bold text-sm">
              {ur ? "ڈیمو جوڑے کو قرنطینہ میں ڈالیں" : "Reject & Quarantine Demo Pair"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-rose-400 hover:text-rose-600 rounded-lg p-1 transition-colors"
            aria-label="Close dialog"
          >
            <AdminIcon name="x" className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs flex justify-between">
            <span className="text-slate-500 font-medium">{ur ? "ہدف جوڑا:" : "Target Pair:"}</span>
            <span className="font-mono font-bold text-slate-800">
              {pair.id} ({pair.batchId})
            </span>
          </div>

          {errorMessage && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-lg p-3 text-xs flex items-start gap-2">
              <AdminIcon name="alert-circle" className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              {ur ? "قرنطینہ کی بنیادی وجہ *" : "Defect Reason Category *"}
            </label>
            <select
              aria-label="Rejection reason" value={selectedReason}
              onChange={(e) => setSelectedReason(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500"
            >
              <option value="">Select a demo rejection reason</option>
              {REJECTION_REASONS.map((reason) => (
                <option key={reason} value={reason}>
                  {reason}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              {ur ? "انسپکشن نوٹ (اختیاری)" : "Inspection Notes (Optional)"}
            </label>
            <textarea
              rows={3} maxLength={500}
              aria-label="Inspection notes" value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Sub-millimeter quiet zone clipping on ICE tag"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:bg-white transition"
            />
            <p className="text-[11px] text-slate-400 mt-0.5">
              {ur
                ? "کوئی حساس یا ذاتی معلومات داخل نہ کریں۔"
                : "Do not record personal customer data in inspection notes."}
            </p>
          </div>

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
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:bg-slate-300 rounded-lg shadow-sm transition-colors cursor-pointer flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <span>{ur ? "پروسیسنگ..." : "Quarantining..."}</span>
              ) : (
                <>
                  <AdminIcon name="alert-triangle" className="w-3.5 h-3.5" />
                  <span>{ur ? "قرنطینہ کی تصدیق کریں" : "Confirm Quarantine"}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}

/* =========================================================================
   Component: Inspection Details Read-Only Dialog
   ========================================================================= */
interface QRInspectionDetailsDialogProps {
  inspection: MockQAInspection;
  ur?: boolean;
  onClose: () => void;
}

export function QRInspectionDetailsDialog({
  inspection,
  ur = false,
  onClose,
}: QRInspectionDetailsDialogProps) {
  const dialogRef = useQADialog();
  return (
    <dialog
      className="fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-md rounded-xl p-0 border-0 backdrop:bg-slate-900/50 overflow-y-auto"
      ref={dialogRef} onCancel={onClose}
      aria-modal="true"
      aria-labelledby="modal-details-title"
      dir={ur ? "rtl" : "ltr"}
    >
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-150">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-2">
            <span className="p-1.5 bg-sky-100 text-sky-700 rounded-lg">
              <AdminIcon name="eye" className="w-4 h-4" />
            </span>
            <h2 id="modal-details-title" className="font-bold text-slate-800 text-sm">
              {ur ? "کیو اے انسپیکشن کی تفصیلات" : "QA Inspection Details"}
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

        <div className="p-6 space-y-3 text-xs">
          <div className="flex justify-between py-1.5 border-b border-slate-100">
            <span className="text-slate-500">{ur ? "انسپیکشن آئی ڈی" : "Inspection ID"}</span>
            <span className="font-mono font-semibold text-slate-800">{inspection.id}</span>
          </div>

          <div className="flex justify-between py-1.5 border-b border-slate-100">
            <span className="text-slate-500">{ur ? "پیئر آئی ڈی" : "Pair ID"}</span>
            <span className="font-mono font-semibold text-slate-800">{inspection.pairId}</span>
          </div>

          <div className="flex justify-between py-1.5 border-b border-slate-100">
            <span className="text-slate-500">{ur ? "بیچ آئی ڈی" : "Batch ID"}</span>
            <span className="font-mono text-slate-800">{inspection.batchId}</span>
          </div>

          <div className="flex justify-between py-1.5 border-b border-slate-100">
            <span className="text-slate-500">{ur ? "معائنہ کا نتیجہ" : "Outcome"}</span>
            <QAPairStatusBadge status={inspection.outcome} ur={ur} />
          </div>

          <div className="flex justify-between py-1.5 border-b border-slate-100">
            <span className="text-slate-500">{ur ? "انسپکٹر" : "Inspector"}</span>
            <span className="font-medium text-slate-800">{inspection.inspector}</span>
          </div>

          <div className="flex justify-between py-1.5 border-b border-slate-100">
            <span className="text-slate-500">{ur ? "تاریخ و وقت" : "Timestamp"}</span>
            <span className="font-mono text-slate-700">{inspection.timestamp}</span>
          </div>

          {inspection.rejectionReason && (
            <div className="py-1.5 border-b border-slate-100 space-y-1">
              <span className="text-slate-500 block">{ur ? "خرابی کی قسم" : "Defect Reason"}</span>
              <span className="font-semibold text-rose-700">{inspection.rejectionReason}</span>
            </div>
          )}

          {inspection.notes && (
            <div className="py-1.5 space-y-1">
              <span className="text-slate-500 block">{ur ? "انسپکشن نوٹس" : "Inspection Notes"}</span>
              <p className="text-slate-700 bg-slate-50 p-2 rounded border border-slate-200">
                {inspection.notes}
              </p>
            </div>
          )}

          <div className="pt-3 flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
            >
              {ur ? "بند کریں" : "Close"}
            </button>
          </div>
        </div>
      </div>
    </dialog>
  );
}


function useQADialog() {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.showModal();
    return () => { previous?.focus(); };
  }, []);
  return ref;
}
