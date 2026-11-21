"use client";

import React, { useRef, useState, useEffect, createContext, useContext, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type StaffSecurityState } from "../lib/auth/staff-contract";
import {
  ALL_ADMIN_MODULES,
  type AdminNavigationItem,
} from "../lib/admin-navigation";
import { AdminSidebar } from "./admin-sidebar";
import { AdminHeader } from "./admin-header";
import { AdminToastProvider } from "./admin-toast";
import { AdminIcon } from "./admin-icons";
import styles from "./admin-workspace.module.css";

export interface AdminRoleContextType {
  effectiveRole: string;
  authenticatedRoles: string[];
}

export const AdminRoleContext = createContext<AdminRoleContextType | null>(null);

export function useAdminRole(): AdminRoleContextType {
  const ctx = useContext(AdminRoleContext);
  if (!ctx) {
    return {
      effectiveRole: "Staff",
      authenticatedRoles: [],
    };
  }
  return ctx;
}

export interface AdminShellProps {
  security: StaffSecurityState;
  ur: boolean;
  children: ReactNode;
}

function AdminShellContent({ security, ur, children }: AdminShellProps) {
  const path = usePathname();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const dialogRef = useRef<HTMLDialogElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  const visibleModules = ALL_ADMIN_MODULES.filter((module) =>
    !module.capability || security.capabilities.includes(module.capability)
  );

  // Active module title
  const currentItem = ALL_ADMIN_MODULES.find(
    (m) => m.path === path || (m.path !== "/admin" && path.startsWith(m.path + "/"))
  );
  const pageTitle = currentItem
    ? ur
      ? currentItem.labelUr
      : currentItem.labelEn
    : path.startsWith("/admin/print-jobs/")
    ? ur
      ? "پرنٹ کی تفصیل"
      : "Print job"
    : ur
    ? "عملے کا کنسول"
    : "Staff console";

  useEffect(() => {
    try { setSidebarCollapsed(localStorage.getItem("safereturn_admin_sidebar_collapsed") === "true"); } catch { /* Storage may be restricted. */ }
  }, []);

  // Toggle sidebar collapse (only writes to localStorage on explicit toggle)
  const handleToggleCollapse = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("safereturn_admin_sidebar_collapsed", String(next));
      } catch {
        // Storage might be restricted
      }
      return next;
    });
  };

  // Open mobile drawer dialog
  const handleOpenMobileMenu = () => {
    dialogRef.current?.showModal();
  };

  // Close mobile drawer dialog
  const handleCloseMobileMenu = () => {
    dialogRef.current?.close();
    menuButtonRef.current?.focus();
  };

  // Listen for Escape on mobile dialog to refocus menu button
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e: Event) => {
      // Standard browser dialog cancel event (fired on Escape)
      e.preventDefault();
      dialog.close();
      menuButtonRef.current?.focus();
    };

    dialog.addEventListener("cancel", handleCancel);
    return () => dialog.removeEventListener("cancel", handleCancel);
  }, []);

  const assignedRoles = security.assignedRoles ?? security.roles;
  const effectiveRole = assignedRoles.includes("owner") ? "Owner" : assignedRoles.join(", ");

  return (
    <AdminRoleContext.Provider
      value={{
        effectiveRole,
        authenticatedRoles: security.roles,
      }}
    >
      <div
        className={`${styles.frame} min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans`}
        dir={ur ? "rtl" : "ltr"}
      >
      {/* Skip to Content for screen reader / keyboard accessibility */}
      <a
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:start-2 focus:z-50 focus:p-3 focus:bg-white focus:text-slate-900 focus:ring-2 focus:ring-sky-500 focus:rounded-lg shadow-xl"
        href="#staff-content"
      >
        {ur ? "مواد پر جائیں" : "Skip to content"}
      </a>

      <div className="flex h-screen w-full overflow-hidden">
        {/* Desktop Sidebar (hidden on mobile) */}
        <div className="hidden md:flex h-full shrink-0">
          <AdminSidebar
            collapsed={sidebarCollapsed}
            onToggleCollapse={handleToggleCollapse}
            currentPath={path}
            ur={ur}
            items={visibleModules}
          />
        </div>

        {/* Main Application Area (Header + Scrollable Content) */}
        <div className="flex flex-col flex-1 h-full min-w-0 overflow-hidden">
          <AdminHeader pageTitle={pageTitle} currentPath={path} ur={ur}
            authenticatedRoles={assignedRoles} onOpenMobileMenu={handleOpenMobileMenu}
            menuButtonRef={menuButtonRef} />

          <main
            id="staff-content"
            tabIndex={-1}
            className="flex-1 overflow-y-auto p-4 md:p-6 bg-slate-50 focus:outline-hidden"
          >
            {children}
          </main>
        </div>
      </div>

      {/* Mobile Navigation Drawer Modal */}
      <dialog
        ref={dialogRef}
        aria-label={ur ? "عملے کا مینو" : "Staff menu"}
        className="fixed inset-0 m-0 start-auto h-full max-h-screen w-80 max-w-[85vw] p-0 bg-slate-900 text-slate-300 border-s border-slate-800 shadow-2xl backdrop:bg-slate-950/70"
      >
        <div className="flex flex-col h-full">
          <div className="h-14 flex items-center justify-between px-4 border-b border-slate-800 text-white shrink-0">
            <div className="flex items-center space-x-2 font-bold text-sm">
              <span className="bg-sky-500 text-white p-1 rounded-md flex items-center justify-center">
                <AdminIcon name="shield" className="w-3.5 h-3.5" />
              </span>
              <span>SafeReturn Admin</span>
            </div>
            <button
              type="button"
              onClick={handleCloseMobileMenu}
              className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white text-xs font-medium"
              aria-label={ur ? "مینو بند کریں" : "Close menu"}
            >
              {ur ? "بند کریں" : "Close"}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            <AdminSidebar
              collapsed={false}
              onToggleCollapse={() => {}}
              showCollapseControl={false}
              currentPath={path}
              ur={ur}
              items={visibleModules}
              onItemClick={handleCloseMobileMenu}
            />
          </div>
        </div>
      </dialog>

    </div>
    </AdminRoleContext.Provider>
  );
}

export function AdminShell(props: AdminShellProps) {
  return (
    <AdminToastProvider>
      <AdminShellContent {...props} />
    </AdminToastProvider>
  );
}
