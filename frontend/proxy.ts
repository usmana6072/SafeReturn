import { createAuthClient } from "./lib/auth/client";
import { NextRequest, NextResponse } from "next/server";
import { authConfig } from "./lib/auth/config";

export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });
  response.headers.set("Cache-Control", "private, no-store");
  try {
    const config = authConfig();
    const client = createAuthClient(config, {
        getAll: () => request.cookies.getAll(),
        setAll: (items) => {
          items.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          response.headers.set("Cache-Control", "private, no-store");
          items.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
        },
    });
    await client.auth.getUser();
  } catch { /* Pages/actions render a safe unavailable state; never authorize here. */ }
  return response;
}

export const config = { matcher: ["/inbox/:path*", "/settings", "/payments/:path*", "/checkout/:path*", "/admin/:path*", "/dashboard/:path*", "/my-qr/:path*", "/kits/:path*", "/activate", "/account/:path*", "/login", "/signup", "/auth/continue", "/auth/sign-in", "/auth/sign-up", "/auth/reset-password"] };
