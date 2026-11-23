import type { ReactNode } from "react";

const paths = {
  copy: <><path d="M8 8h13v13H8zM16 8V3H3v13h5"/></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></>,
  filter: <><path d="M3 7h5m5 0h8M3 17h9m5 0h4"/><circle cx="10.5" cy="7" r="2.5"/><circle cx="14.5" cy="17" r="2.5"/></>,
  refresh: <><path d="M20 10a8 8 0 1 0-1 7M20 4v6h-6"/></>,
  tag: <><path d="m3 4 7-1 11 11-7 7L3 10Z"/><circle cx="7" cy="7" r="1"/></>,
  medical: <path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6Z"/>,
  close: <path d="m6 6 12 12M18 6 6 18"/>,
  home: <><path d="m3 10 9-7 9 7v10H3z"/><path d="M9 20v-7h6v7"/></>,
  qr: <><path d="M3 3h6v6H3zM15 3h6v6h-6zM3 15h6v6H3zM14 14h3v4h4v3h-6v-3M21 13v2"/></>,
  shop: <><path d="m4 4-2 6a3 3 0 0 0 5 2 3 3 0 0 0 5 0 3 3 0 0 0 5 0 3 3 0 0 0 5-2l-2-6zM4 13v7h16v-7M9 20v-5h5v5"/></>,
  orders: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6"/></>,
  more: <><circle cx="4" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="20" cy="12" r="1.6"/></>,
  inbox: <><path d="M4 4h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-9l-6 4v-4H3V5a1 1 0 0 1 1-1Z"/><path d="M7 9h10M7 13h6"/></>,
  pending: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  bell: <><path d="M5 11a7 7 0 0 1 14 0c0 3 1 5 2 6H3c1-1 2-3 2-6ZM9 20a4 4 0 0 0 6 0"/></>,
  account: <><circle cx="12" cy="8" r="3.6"/><path d="M4 21v-2a8 6 0 0 1 16 0v2"/></>,
  cart: <><path d="M2 4h3l3 12h11l2-9H6"/><circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/></>,
  truck: <><path d="M2 5h12v12H2zM14 9h4l4 4v4h-8"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></>,
  pin: <><path d="M19 10c0 6-7 11-7 11S5 16 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
  help: <><circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 4 3c-1 .5-1 1-1 2m0 2v.1"/></>,
  logout: <><path d="M9 4H4v16h5M9 12h12m-4-4 4 4-4 4"/></>,
  language: <><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></>,
  arrow: <path d="M4 12h15m-5-5 5 5-5 5"/>,
  box: <><path d="m3 7 9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10M7 5l9 4"/></>,
  check: <><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></>,
} satisfies Record<string, ReactNode>;

export type CustomerIconName = keyof typeof paths;

export function CustomerIcon({ name }: { name: CustomerIconName }) {
  return <svg className={name === "arrow" ? "customer-icon directional" : "customer-icon"} width="20" height="20"
    aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}
