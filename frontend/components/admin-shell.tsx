"use client";

import React, { useRef, useState, useEffect, createContext, useContext, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type StaffSecurityState } from "../lib/auth/staff-contract";
import {
  ALL_ADMIN_MODULES,
  DEMO_PERMISSIONS,
  type AdminNavigationItem,
  type DemoRoleName,
} from "../lib/admin-navigation";
import { AdminSidebar } from "./admin-sidebar";
import { AdminHeader } from "./admin-header";
import { AdminToastProvider, useAdminToast } from "./admin-toast";
import { AdminConfirmDialog } from "./admin-confirm-dialog";
import { resetAdminMockData } from "../lib/admin-mock-data";
import { AdminIcon } from "./admin-icons";
import styles from "./admin-workspace.module.css";

export interface AdminRoleContextType {
  selectedRole: DemoRoleName | "authenticated";
  effectiveRole: string;
  setSelectedRole: (role: DemoRoleName | "authenticated") => void;
  authenticatedRoles: string[];
}

export const AdminRoleContext = createContext<AdminRoleContextType | null>(null);

export function useAdminRole(): AdminRoleContextType {
  const ctx = useContext(AdminRoleContext);
  if (!ctx) {
    return {
      selectedRole: "authenticated",
      effectiveRole: "Staff",
      setSelectedRole: () => {},
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
  const router = useRouter();
  const { showToast } = useAdminToast();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedRole, setSelectedRole] = useState<DemoRoleName | "authenticated">("authenticated");
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);

  const dialogRef = useRef<HTMLDialogElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  // Determine permitted modules based on authenticated state or demo preview
  let visibleModules: AdminNavigationItem[] = [];

  if (selectedRole === "authenticated") {
    // Real authenticated mode: use security contract capabilities

    visibleModules = ALL_ADMIN_MODULES.filter((m) =>
      m.id === "staff_permissions"
        ? security.roles.includes("security_admin") && security.capabilities.includes("users.manage")
        : (security.mfa_verified && !!m.capability && security.capabilities.includes(m.capability)) || m.id === "overview" || m.id === "staff_security"
    );
  } else {
    // Demo preview mode: filter according to mock permissions matrix
    const allowedIds = DEMO_PERMISSIONS[selectedRole]?.pages || [];
    visibleModules = ALL_ADMIN_MODULES.filter((m) => allowedIds.includes(m.id));
  }

  // These legacy workspaces have no admitted operation. Preview roles cannot
  // restore their navigation; direct pages and server adapters are also inert.
  visibleModules=visibleModules.filter(m=>!['inventory','qr_batches','qa','ready_to_ship'].includes(m.id));
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

  // Handle demo role switching
  const handleRoleChange = (role: DemoRoleName | "authenticated") => {
    setSelectedRole(role);
    if (role === "authenticated") {
      showToast(
        ur
          ? "اصل تصدیق شدہ سیشن پر واپس آ گئے"
          : "Switched back to your authenticated role",
        "info"
      );
    } else {
      showToast(
        ur
          ? `پیش نظارہ: ${role} کا منظر فعال ہے`
          : `Viewing console as ${role} (Demo Preview)`,
        "info"
      );

      // Check if current page is allowed for the newly selected role
      const allowedPages = DEMO_PERMISSIONS[role]?.pages || [];
      if (currentItem && !allowedPages.includes(currentItem.id)) {
        router.push("/admin");
      }
    }
  };

  // Handle demo data reset
  const handleConfirmReset = () => {
    setResetLoading(true);
    try {
      if (typeof window !== "undefined") {
        // Only clear safereturn_admin_* keys and normalize demo db; never wipe all localStorage/auth
        const keysToRemove: string[] = [];
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key && key.startsWith("safereturn_admin_")) {
            keysToRemove.push(key);
          }
        }
        keysToRemove.forEach((k) => localStorage.removeItem(k));
        localStorage.removeItem("safereturn_demo_db");
        resetAdminMockData();
      }

      showToast(
        ur
          ? "ڈیمو ڈیٹا کامیابی سے ری سیٹ ہو گیا!"
          : "Demo data reset to initial benchmark state!",
        "success"
      );
    } catch {
      showToast(
        ur ? "ڈیٹا ری سیٹ کرنے میں خرابی ہوئی" : "Failed to reset demo data",
        "error"
      );
    } finally {
      setResetLoading(false);
      setResetDialogOpen(false);
    }
  };

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

  const effectiveRole =
    selectedRole === "authenticated"
      ? security.roles[0]
        ? security.roles[0].charAt(0).toUpperCase() + security.roles[0].slice(1).replace("_", " ")
        : "Staff"
      : selectedRole;

  return (
    <AdminRoleContext.Provider
      value={{
        selectedRole,
        effectiveRole,
        setSelectedRole: handleRoleChange,
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
            onResetDemoData={() => setResetDialogOpen(true)}
          />
        </div>

        {/* Main Application Area (Header + Scrollable Content) */}
        <div className="flex flex-col flex-1 h-full min-w-0 overflow-hidden">
          <AdminHeader pageTitle={pageTitle} currentPath={path} ur={ur}
            selectedRole={selectedRole} onRoleChange={handleRoleChange}
            authenticatedRoles={security.roles} onOpenMobileMenu={handleOpenMobileMenu}
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
              onResetDemoData={() => {
                handleCloseMobileMenu();
                setResetDialogOpen(true);
              }}
              onItemClick={handleCloseMobileMenu}
            />
          </div>
        </div>
      </dialog>

      {/* Reset Demo Data Confirmation Dialog */}
      <AdminConfirmDialog
        isOpen={resetDialogOpen}
        title={ur ? "ڈیمو ڈیٹا ری سیٹ کریں؟" : "Reset Demo Data?"}
        message={
          ur
            ? "اس سے لوکل ایڈمن کے فرضی ریکارڈز ابتدائی معیار پر بحال ہو جائیں گے۔ آپ کے اصلی سیشن اور گاہکوں کے ڈیٹا پر کوئی اثر نہیں پڑے گا۔"
            : "This will reset all local admin demo records (products, templates, batches, and mock audit logs) to initial benchmark values. Your real account session and customer data will not be affected."
        }
        confirmLabel={ur ? "ری سیٹ کریں" : "Reset Data"}
        cancelLabel={ur ? "منسوخ کریں" : "Cancel"}
        variant="danger"
        loading={resetLoading}
        onConfirm={handleConfirmReset}
        onCancel={() => setResetDialogOpen(false)}
      />
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
