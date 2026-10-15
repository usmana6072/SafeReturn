import { NextRequest, NextResponse } from "next/server";
import { authClient } from "../../../lib/auth/server";
import { authConfig } from "../../../lib/auth/config";
import { recoveryTicket } from "../../../lib/auth/recovery";
import { cookies } from "next/headers";

export async function GET(request: NextRequest) {
  let target = "/login?confirmation=failed";
  try {
    const codes = request.nextUrl.searchParams.getAll("code");
    if (codes.length === 1 && /^[A-Za-z0-9_-]{1,1024}$/.test(codes[0])) {
      const client = await authClient();
      let recovery = false;
      const { data: { subscription } } = client.auth.onAuthStateChange((event) => {
        if (event === "PASSWORD_RECOVERY") recovery = true;
      });
      const { data, error } = await client.auth.exchangeCodeForSession(codes[0]);
      subscription.unsubscribe();
      if (!error && data.session) {
        target = "/account";
        if (recovery) {
          (await cookies()).set("sr-recovery", recoveryTicket(data.session.access_token), {
            httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 600,
          });
          target = "/auth/reset-password";
        }
      }
    }
    return NextResponse.redirect(new URL(target, authConfig().origin), {
      headers: { "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" },
    });
  } catch {
    return new NextResponse("Confirmation unavailable. Return to login and try again.", {
      status: 503, headers: { "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" },
    });
  }
}
