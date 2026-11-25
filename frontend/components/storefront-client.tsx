"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { readItemCart } from "../lib/item-cart";
import { readCart } from "../lib/cart";
import { CustomerIcon } from "./customer-icon";

export function StoreCartBadge({ ur }: { ur: boolean }) {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    const update = () => {
      try {
        const total = readItemCart().length + readCart().filter(row => row.lost + row.ice > 0).length;
        setCount(total);
      } catch {
        setCount(0);
      }
    };
    update();
    window.addEventListener("pageshow", update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener("pageshow", update);
      window.removeEventListener("storage", update);
    };
  }, []);

  return (
    <Link className="shop-cart storefront-cart-btn" href="/cart" aria-label={ur ? "خریداری کی ٹوکری" : "Shopping Cart"}>
      <CustomerIcon name="cart" />
      <span>{ur ? "کارٹ" : "Cart"}</span>
      {count !== null && count > 0 && <span className="cart-badge">{count}</span>}
    </Link>
  );
}

export function StoreMenu({ ur, session }: { ur: boolean; session: boolean }) {
  const menu = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape" && menu.current?.open) {
        menu.current.open = false;
        menu.current.querySelector("summary")?.focus();
      }
    }
    function outside(event: PointerEvent) {
      if (menu.current?.open && event.target instanceof Node && !menu.current.contains(event.target)) {
        menu.current.open = false;
      }
    }
    document.addEventListener("keydown", escape);
    document.addEventListener("pointerdown", outside);
    return () => {
      document.removeEventListener("keydown", escape);
      document.removeEventListener("pointerdown", outside);
    };
  }, []);

  return (
    <details className="mobile-menu storefront-mobile-menu" ref={menu}>
      <summary aria-label={ur ? "مینو" : "Menu"}>
        <span />
        <span />
        <span />
      </summary>
      <nav
        aria-label={ur ? "موبائل مینو" : "Mobile menu"}
        onClick={event => {
          if ((event.target as Element).closest("a") && menu.current) {
            menu.current.open = false;
          }
        }}
      >
        <Link href="/">{ur ? "ہوم" : "Home"}</Link>
        <Link href="/shop">{ur ? "دکان" : "Shop"}</Link>
        <Link href="/cart">{ur ? "کارٹ" : "Cart"}</Link>
        <Link href="/#how-it-works">{ur ? "طریقہ کار" : "How it works"}</Link>
        <Link href="/help">{ur ? "مدد" : "Help"}</Link>
        {session ? (
          <Link href="/dashboard">{ur ? "کسٹمر پورٹل" : "Customer Portal"}</Link>
        ) : (
          <Link href="/login">{ur ? "لاگ اِن" : "Log in"}</Link>
        )}
      </nav>
    </details>
  );
}
