"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const destinations = [
  ["/dashboard", "dashboard", "Dashboard", "ڈیش بورڈ"],
  ["/my-qr", "qrs", "My QR codes", "میرے QR کوڈز"],
  ["/shop", "store", "Available products", "دستیاب مصنوعات"],
  ["/cart", "cart", "Shopping cart", "کارٹ"],
  ["/orders", "orders", "Orders & payment", "آرڈرز اور ادائیگی"],
  ["/shipments", "orders", "Shipments", "ترسیلات"],
  ["/inbox", "inbox", "Finder inbox", "فائنڈر اِن باکس"],
  ["/account/shipping-addresses", "addresses", "Delivery addresses", "ترسیل کے پتے"],
  ["/account", "account", "Account & privacy", "اکاؤنٹ اور رازداری"],
] as const;

export function CustomerNavigation({ ur }: { ur: boolean }) {
  const pathname = usePathname();
  return <nav className="portal-nav" aria-label={ur ? "اکاؤنٹ مینو" : "Customer navigation"}>
    {destinations.map(([href, icon, en, translated]) => {
      const active = href === "/account" ? pathname === href || pathname.startsWith("/settings") || pathname.startsWith("/account/privacy")
        : href === "/my-qr" ? pathname.startsWith(href) || pathname.startsWith("/independent-qr")
        : href === "/orders" ? pathname.startsWith(href) || pathname.startsWith("/payments/")
        : href === "/cart" ? pathname === href || pathname === "/checkout"
        : pathname === href || pathname.startsWith(href + "/");
      return <Link key={href} href={href} data-go={icon} className={active ? "active" : undefined} aria-current={active ? "page" : undefined}>{ur ? translated : en}</Link>;
    })}
  </nav>;
}
