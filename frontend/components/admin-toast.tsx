"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { AdminIcon } from "./admin-icons";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
  toasts: ToastMessage[];
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function AdminToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = "success") => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const newToast: ToastMessage = { id, message, type };
      setToasts((prev) => [...prev, newToast]);

      setTimeout(() => {
        dismissToast(id);
      }, 3500);
    },
    [dismissToast]
  );

  return (
    <ToastContext.Provider value={{ showToast, toasts, dismissToast }}>
      {children}
      <AdminToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

export function useAdminToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Graceful fallback if invoked outside provider
    return {
      showToast: (message: string, type: ToastType = "info") => {
        console.log(`[Toast ${type}]: ${message}`);
      },
      toasts: [],
      dismissToast: () => {},
    };
  }
  return ctx;
}

export function AdminToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 end-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none p-2"
      aria-live="polite"
    >
      {toasts.map((toast) => {
        let bg = "bg-white border-slate-200 text-slate-800";
        let iconName: "check" | "alert-circle" | "alert-triangle" | "info" = "info";
        let iconColor = "text-sky-600";

        if (toast.type === "success") {
          bg = "bg-emerald-50 border-emerald-200 text-emerald-950";
          iconName = "check";
          iconColor = "text-emerald-600";
        } else if (toast.type === "error") {
          bg = "bg-red-50 border-red-200 text-red-950";
          iconName = "alert-circle";
          iconColor = "text-red-600";
        } else if (toast.type === "warning") {
          bg = "bg-amber-50 border-amber-200 text-amber-950";
          iconName = "alert-triangle";
          iconColor = "text-amber-600";
        } else {
          bg = "bg-sky-50 border-sky-200 text-sky-950";
          iconName = "info";
          iconColor = "text-sky-600";
        }

        return (
          <div
            key={toast.id}
            role={toast.type === "error" ? "alert" : "status"}
            className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border shadow-lg text-xs transition-all duration-200 ${bg}`}
          >
            <span className={`shrink-0 mt-0.5 ${iconColor}`}>
              <AdminIcon name={iconName} className="w-4 h-4" />
            </span>
            <span className="flex-1 font-medium leading-relaxed">{toast.message}</span>
            <button
              type="button"
              onClick={() => onDismiss(toast.id)}
              className="shrink-0 p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-black/5"
              aria-label="Dismiss notification"
            >
              <AdminIcon name="x" className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

