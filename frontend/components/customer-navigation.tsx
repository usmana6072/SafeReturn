"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, useState, type ReactNode } from "react";
import { logout } from "../app/auth/actions";
import { customerLanguage } from "../app/customer-actions";
import { CustomerDialog } from "./customer-dialog";
import { CustomerIcon, type CustomerIconName } from "./customer-icon";

type Destination = readonly [string, CustomerIconName, string, string];
const primary: Destination[] = [
  ["/dashboard", "home", "Home", "ہوم"],
  ["/my-qr", "qr", "My QRs", "میرے QR"],
  ["/portal/shop", "shop", "Shop", "دکان"],
  ["/orders", "orders", "Orders", "آرڈرز"],
];
const more: Destination[] = [
  ["/inbox", "inbox", "Finder Messages", "فائنڈر پیغامات"],
  ["/shipments", "truck", "My Shipments", "میری ترسیلات"],
  ["/cart", "cart", "Shopping Cart", "خریداری کی ٹوکری"],
  ["/account/shipping-addresses", "pin", "Delivery Addresses", "ترسیل کے پتے"],
  ["/account", "account", "Account Settings", "اکاؤنٹ کی ترتیبات"],
  ["/help", "help", "Support", "مدد"],
];

function selectedDestination(path: string) {
  if (path.startsWith("/payments/")) return "/orders";
  if (path === "/checkout") return "/cart";
  if (/^\/(independent-qr|activate|kits)(\/|$)/.test(path)) return "/my-qr";
  if (path === "/settings") return "/account";
  return [...primary, ...more].find(([href]) => path === href || path.startsWith(href + "/"))?.[0];
}

export function CustomerNavigation({ ur, unread }: { ur: boolean; unread?: ReactNode }) {
  const path = usePathname();
  // Also close the sheet on browser back/forward between shared layouts.
  return <NavigationItems key={path + ur} ur={ur} unread={unread} path={path}/>;
}

function NavigationItems({ ur, unread, path }: { ur: boolean; unread?: ReactNode; path: string }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  function closeSheet() {
    setOpen(false);
    requestAnimationFrame(() => trigger.current?.focus({ preventScroll: true }));
  }
  const selected = selectedDestination(path);
  const showMore = more.some(([href]) => href === selected);
  function link([href, icon, en, translated]: Destination) {
    const active = href === selected;
    return <Link key={href} href={href} prefetch={false} onClick={() => setOpen(false)}
      aria-current={active ? "page" : undefined} className={active ? "active" : undefined}>
      <span className="nav-icon"><CustomerIcon name={icon}/>{href === "/inbox" && unread}</span>
      <span>{ur ? translated : en}</span>
    </Link>;
  }
  const accountActions = <>
    <form action={customerLanguage}><input type="hidden" name="language" value={ur ? "en" : "ur"}/>
      <button type="submit"><CustomerIcon name="language"/>{ur ? "English" : "اردو"}</button></form>
    <form action={logout}><button type="submit"><CustomerIcon name="logout"/>{ur ? "لاگ آؤٹ" : "Log out"}</button></form>
  </>;
  return <nav className="portal-nav" aria-label={ur ? "کسٹمر نیویگیشن" : "Customer navigation"}>
    {primary.map(link)}
    <button ref={trigger} type="button" className={`nav-more ${showMore || open ? "active" : ""}`}
      aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)}>
      <span className="nav-icon"><CustomerIcon name="more"/>{unread}</span>{ur ? "مزید" : "More"}
    </button>
    <div className="nav-secondary">{more.map(link)}<div className="nav-account">{accountActions}</div></div>
    {open && <CustomerDialog title={ur ? "مزید" : "More"} ur={ur} busy={false} onClose={closeSheet}>
      <div className="nav-sheet">{more.map(link)}<div className="nav-account">{accountActions}</div></div>
    </CustomerDialog>}
  </nav>;
}
