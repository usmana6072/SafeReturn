import { createServerClient, type CookieMethodsServer } from "@supabase/ssr";

// One maintained SDK adapter for proxy, actions and callback; no browser client.
export function createAuthClient(configuration: { url: string; key: string },
  cookies: CookieMethodsServer, fetchImpl: typeof fetch = fetch) {
  return createServerClient(configuration.url, configuration.key, {
    cookieOptions: { httpOnly: true, secure: process.env.NODE_ENV === "production",
      sameSite: "lax", path: "/" },
    cookies,
    global: { fetch: async (input, init) => {
      const response = await fetchImpl(input, {
        ...init, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(8000),
      });
      if (!response.ok && (process.env.NODE_ENV === "development"
        || process.env.SAFERETURN_AUTH_TEST_DIAGNOSTICS === "1")) {
        // Explicit local test diagnostics: never emit URLs, bodies, emails or tokens.
        const safeCodes = new Set(["over_email_send_rate_limit", "email_address_not_authorized",
          "email_exists", "signup_disabled", "email_provider_disabled", "unexpected_failure",
          "over_request_rate_limit", "weak_password", "validation_failed",
          "invalid_credentials", "email_not_confirmed"]);
        let code = "other";
        try {
          const data = await response.clone().json();
          if (safeCodes.has(data.code)) code = data.code;
        } catch { /* Diagnostics must not affect provider handling. */ }
        console.info(`Auth test provider rejection: status=${response.status}, code=${code}`);
      }
      return response;
    } },
  });
}
