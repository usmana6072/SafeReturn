import React, { type ReactNode } from "react";
import Link from "next/link";
import { AdminIcon, type AdminIconName } from "./admin-icons";

// --- 1. STATUS BADGE ---
export type AdminBadgeVariant = "success" | "warning" | "danger" | "info" | "neutral";

export interface AdminStatusBadgeProps {
  label: string;
  variant?: AdminBadgeVariant;
  dot?: boolean;
  className?: string;
}

export function AdminStatusBadge({
  label,
  variant = "neutral",
  dot = true,
  className = "",
}: AdminStatusBadgeProps) {
  let style = "bg-slate-100 text-slate-700 border-slate-200";
  let dotColor = "bg-slate-400";

  switch (variant) {
    case "success":
      style = "bg-emerald-50 text-emerald-800 border-emerald-200";
      dotColor = "bg-emerald-500";
      break;
    case "warning":
      style = "bg-amber-50 text-amber-800 border-amber-200";
      dotColor = "bg-amber-500";
      break;
    case "danger":
      style = "bg-red-50 text-red-800 border-red-200";
      dotColor = "bg-red-500";
      break;
    case "info":
      style = "bg-sky-50 text-sky-800 border-sky-200";
      dotColor = "bg-sky-500";
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${style} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColor}`} />}
      <span>{label}</span>
    </span>
  );
}

// --- 2. CARD PRIMITIVE ---
export function AdminCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden ${className}`}
    >
      {children}
    </div>
  );
}

// --- 3. PAGE CONTAINER ---
export function AdminPageContainer({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`w-full max-w-7xl mx-auto space-y-6 ${className}`}>{children}</div>;
}

// --- 4. PAGE HEADER ---
export interface AdminPageHeaderProps {
  title: string;
  description?: string;
  badge?: ReactNode;
  actions?: ReactNode;
}

export function AdminPageHeader({
  title,
  description,
  badge,
  actions,
}: AdminPageHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
      <div className="space-y-1">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-slate-900">
            {title}
          </h1>
          {badge}
        </div>
        {description && <p className="text-xs text-slate-500 max-w-2xl">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
    </div>
  );
}

// --- 5. EMPTY / NOTICE STATE ---
export interface AdminEmptyStateProps {
  icon?: AdminIconName;
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}

export function AdminEmptyState({
  icon = "info",
  title,
  description,
  action,
  className = "",
}: AdminEmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center rounded-xl border border-dashed border-slate-300 bg-white space-y-3 ${className}`}
    >
      <div className="p-3 bg-slate-100 text-slate-500 rounded-full">
        <AdminIcon name={icon} className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-bold text-slate-800">{title}</h3>
      <p className="text-xs text-slate-500 max-w-sm leading-relaxed">{description}</p>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}

// --- 6. PLACEHOLDER FOR UPCOMING SCREENS ---
export interface AdminPlaceholderProps {
  screenNumber?: number;
  screenName: string;
  description?: string;
}

export function AdminPlaceholder({
  screenNumber,
  screenName,
  description,
}: AdminPlaceholderProps) {
  return (
    <AdminPageContainer>
      <AdminPageHeader
        title={screenName}
        description={description || "Administrative console module."}
        badge={
          <AdminStatusBadge
            label={screenNumber ? `Screen ${screenNumber} · Upcoming` : "Upcoming Screen"}
            variant="info"
          />
        }
      />

      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-4 shadow-xs">
        <div className="mx-auto w-12 h-12 bg-sky-50 text-sky-600 rounded-xl flex items-center justify-center">
          <AdminIcon name="layout-dashboard" className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-900">
            {screenName} is ready for implementation
          </h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            The shared admin shell and design system foundation are active. This module will be
            implemented in a subsequent step per the implementation plan.
          </p>
        </div>
        <div className="pt-2">
          <Link
            href="/admin"
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-200 transition-colors"
          >
            <AdminIcon name="chevron-left" className="w-3.5 h-3.5" />
            <span>Return to Staff Workspace</span>
          </Link>
        </div>
      </div>
    </AdminPageContainer>
  );
}

