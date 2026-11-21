"use client";

import React from "react";
import Link from "next/link";
import { AdminIcon } from "./admin-icons";
import { adminLanguage } from "../app/admin/actions";
import { logout } from "../app/auth/actions";

export interface AdminHeaderProps {
  pageTitle: string;
  currentPath: string;
  ur: boolean;
  authenticatedRoles: string[];
  onOpenMobileMenu: () => void;
  menuButtonRef?: React.Ref<HTMLButtonElement>;
}

export function AdminHeader({
  pageTitle,
  currentPath,
  ur,
  authenticatedRoles,
  onOpenMobileMenu,
  menuButtonRef,
}: AdminHeaderProps) {
  const displayRole = authenticatedRoles.includes("owner") ? "Owner" : authenticatedRoles.join(", ") || "Staff";

  const initial = displayRole.charAt(0).toUpperCase();

  return (
    <header className="min-h-14 bg-white border-b border-slate-200 px-3 py-2 md:px-6 flex flex-wrap items-center justify-between gap-2 z-10 shrink-0">
      {/* 1. Page Title & Breadcrumb */}
      <div className="flex items-center space-x-3 overflow-hidden">
        {/* Mobile Hamburger Button */}
        <button
          ref={menuButtonRef}
          type="button"
          onClick={onOpenMobileMenu}
          className="md:hidden p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 border border-slate-200"
          aria-haspopup="dialog"
          aria-label={ur ? "مینو" : "Menu"}
        >
          <span className="sr-only">{ur ? "مینو" : "Menu"}</span>
          <AdminIcon name="menu" className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 truncate">
          <nav
            aria-label={ur ? "راستہ" : "Breadcrumb"}
            className="hidden sm:flex items-center text-xs text-slate-400 gap-1.5"
          >
            <Link href="/admin" prefetch={false} className="hover:text-slate-700">
              {ur ? "عملہ" : "Staff"}
            </Link>
            <span aria-hidden="true">/</span>
          </nav>
          <h1 className="font-semibold text-slate-800 text-sm md:text-base truncate">
            {pageTitle}
          </h1>
        </div>

      </div>

      {/* 2. Controls: User Identity, Language, Logout */}
      <div className="flex items-center space-x-2 md:space-x-3 shrink-0">
        {/* Language Form Switcher */}
        <form action={adminLanguage}>
          <input type="hidden" name="language" value={ur ? "en" : "ur"} />
          <input type="hidden" name="returnTo" value={currentPath} />
          <button
            type="submit"
            className="px-2.5 py-1 text-xs font-semibold rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-colors"
            lang={ur ? "en" : "ur"}
          >
            {ur ? "English" : "اردو"}
          </button>
        </form>

        {/* User Identity Pill */}
        <div className="flex items-center space-x-2">
          <div
            className="w-7 h-7 rounded-full bg-sky-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-xs"
            title={`Active role: ${displayRole}`}
          >
            {initial}
          </div>
          <span className="text-xs font-medium text-slate-700 hidden lg:inline max-w-[120px] truncate">
            {displayRole}
          </span>
        </div>

        {/* Logout Action */}
        <form action={logout} className="hidden sm:inline-block">
          <button
            type="submit"
            className="px-2.5 py-1 text-xs font-semibold rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
          >
            {ur ? "لاگ آؤٹ" : "Log out"}
          </button>
        </form>
      </div>
    </header>
  );
}

