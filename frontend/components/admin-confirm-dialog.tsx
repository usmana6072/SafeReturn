"use client";

import React, { useEffect, useRef } from "react";
import { AdminIcon } from "./admin-icons";

export interface AdminConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function AdminConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "primary",
  loading = false,
  onConfirm,
  onCancel,
}: AdminConfirmDialogProps) {
  const cancelBtnRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    // Focus cancel button on open for safety, and keep keyboard focus inside.
    cancelBtnRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        if (!loading) onCancel();
      }
      if (e.key === "Tab") {
        const controls = panelRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]');
        if (!controls?.length) { e.preventDefault(); return; }
        const first = controls[0], last = controls[controls.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => { window.removeEventListener("keydown", handleKeyDown); previousFocus?.focus(); };
  }, [isOpen, onCancel, loading]);

  if (!isOpen) return null;

  const isDanger = variant === "danger";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-desc"
    >
      <div ref={panelRef} className="w-full max-w-md max-h-[90dvh] bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-y-auto p-6 space-y-4">
        <div className="flex items-start gap-4">
          <div
            className={`p-2.5 rounded-xl shrink-0 ${
              isDanger ? "bg-red-50 text-red-600" : "bg-sky-50 text-sky-600"
            }`}
          >
            <AdminIcon
              name={isDanger ? "alert-triangle" : "info"}
              className="w-5 h-5"
            />
          </div>
          <div className="space-y-1">
            <h2 id="confirm-dialog-title" className="text-base font-bold text-slate-900">
              {title}
            </h2>
            <p id="confirm-dialog-desc" className="text-xs text-slate-600 leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            ref={cancelBtnRef}
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-200 transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className={`px-4 py-2 text-xs font-semibold text-white rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 ${
              isDanger
                ? "bg-red-600 hover:bg-red-700 focus:ring-2 focus:ring-red-500/20"
                : "bg-[#0A756E] hover:bg-[#075D57] focus:ring-2 focus:ring-[#0A756E]/20"
            }`}
          >
            {loading && <span className="inline-block animate-spin">⏳</span>}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

