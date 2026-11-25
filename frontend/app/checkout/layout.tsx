import { StorefrontShell } from "../../components/storefront-shell";
import "../../components/shopping-cart.css";
import "../../components/checkout.css";

export const viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };

export default async function Layout({ children }: { children: React.ReactNode }) {
  return <StorefrontShell>{children}</StorefrontShell>;
}
