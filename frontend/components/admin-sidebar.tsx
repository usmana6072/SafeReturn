"use client";

import React from "react";
import Link from "next/link";
import { AdminIcon } from "./admin-icons";
import { ADMIN_SECTIONS, type AdminNavigationItem } from "../lib/admin-navigation";

export interface AdminSidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  currentPath: string;
  ur: boolean;
  items: AdminNavigationItem[];
  onResetDemoData: () => void;
  onItemClick?: () => void;
  showCollapseControl?: boolean;
}

export function AdminSidebar({
  collapsed,
  onToggleCollapse,
  currentPath,
  ur,
  items,
  onResetDemoData,
  onItemClick,
  showCollapseControl = true,
}: AdminSidebarProps) {
  // Group items by section to preserve logical hierarchy
  const sections = ADMIN_SECTIONS.map((sec) => ({
    ...sec,
    items: items.filter((item) => item.section === sec.id),
  })).filter((sec) => sec.items.length > 0);

  return (
    <aside
      className={`bg-slate-900 text-slate-300 ${
        collapsed ? "w-16" : "w-64"
      } transition-all duration-200 flex flex-col h-full z-20 border-r border-slate-800 shrink-0`}
      aria-label={ur ? "سائیڈ بار" : "Sidebar"}
    >
      {/* 1. Header Branding & Collapse Control */}
      <div className="h-14 flex items-center justify-between px-3.5 border-b border-slate-800 text-white shrink-0">
        <Link
          href="/admin"
          prefetch={false}
          className={`flex items-center space-x-2 font-bold text-base truncate ${
            collapsed ? "hidden" : "flex"
          }`}
          onClick={onItemClick}
        >
          <span className="bg-sky-500 text-white p-1.5 rounded-lg flex items-center justify-center shrink-0">
            <AdminIcon name="shield" className="w-4 h-4" />
          </span>
          <span className="tracking-tight flex items-center gap-1.5">
            <span>SafeReturn</span>
            <span className="text-[11px] font-medium text-sky-400 bg-sky-950/70 border border-sky-800/60 px-1.5 py-0.5 rounded">
              ADMIN
            </span>
          </span>
        </Link>

        {collapsed && (
          <Link
            href="/admin"
            prefetch={false}
            className="mx-auto bg-sky-500 text-white p-1.5 rounded-lg flex items-center justify-center"
            title="SafeReturn Admin"
            onClick={onItemClick}
          >
            <AdminIcon name="shield" className="w-4 h-4" />
          </Link>
        )}

        {showCollapseControl && <button
          type="button"
          onClick={onToggleCollapse}
          className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          title={
            collapsed
              ? ur
                ? "سائیڈ بار کھولیں"
                : "Expand sidebar"
              : ur
              ? "سائیڈ بار سکیڑیں"
              : "Collapse sidebar"
          }
          aria-label={
            collapsed
              ? ur
                ? "سائیڈ بار کھولیں"
                : "Expand sidebar"
              : ur
              ? "سائیڈ بار سکیڑیں"
              : "Collapse sidebar"
          }
        >
          <AdminIcon
            name={collapsed ? "chevron-right" : "chevron-left"}
            className="w-4 h-4"
          />
        </button>}
      </div>

      {/* 2. Scrollable Navigation List */}
      <nav
        aria-label={ur ? "عملے کا مینو" : "Staff navigation"}
        className="flex-1 overflow-y-auto p-2 space-y-4"
      >
        {sections.map((section) => (
          <div key={section.id} className="space-y-1">
            {!collapsed && (
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-3 pt-1 pb-1">
                {ur ? section.labelUr : section.labelEn}
              </div>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const isActive =
                  currentPath === item.path ||
                  (item.path !== "/admin" && currentPath.startsWith(item.path + "/"));

                const label = ur ? item.labelUr : item.labelEn;

                return (
                  <Link
                    key={item.path}
                    href={item.path}
                    prefetch={false}
                    aria-current={isActive ? "page" : undefined}
                    onClick={onItemClick}
                    title={collapsed ? label : undefined}
                    className={`w-full flex items-center ${
                      collapsed ? "justify-center px-2" : "justify-start px-3"
                    } py-2 rounded-lg text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-sky-600 text-white font-semibold shadow-xs"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                    }`}
                  >
                    <AdminIcon
                      name={item.icon}
                      className={`w-4 h-4 shrink-0 ${
                        isActive ? "text-white" : "text-slate-400"
                      }`}
                    />
                    {!collapsed && <span className="ml-3 truncate">{label}</span>}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* 3. Footer Action: Reset Demo Data */}
      <div className="p-3 border-t border-slate-800 shrink-0">
        <button
          type="button"
          onClick={onResetDemoData}
          className={`w-full flex items-center ${
            collapsed ? "justify-center" : "justify-start px-3"
          } py-2 rounded-lg text-xs font-medium bg-red-950/40 hover:bg-red-900/60 text-red-300 border border-red-800/50 transition-colors`}
          title={ur ? "ڈیمو ڈیٹا ری سیٹ کریں" : "Reset Demo Data"}
          aria-label={ur ? "ڈیمو ڈیٹا ری سیٹ کریں" : "Reset Demo Data"}
        >
          <AdminIcon name="rotate-ccw" className="w-4 h-4 shrink-0 text-red-400" />
          {!collapsed && (
            <span className="ml-2.5 truncate">
              {ur ? "ڈیمو ڈیٹا ری سیٹ" : "Reset Demo Data"}
            </span>
          )}
        </button>
      </div>
    </aside>
  );
}

