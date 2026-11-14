import "server-only";
import { authConfig } from "./config";
import { verifiedSession } from "./server";

const project = "https://fhuxryfkfrvycsojkzvq.supabase.co";
const email = "usmana6072@gmail.com";

export function supportOnboardingEnabled() {
  if (process.env.NODE_ENV !== "development"
    || process.env.SAFERETURN_SUPPORT_DEV_ONBOARDING !== "true") return false;
  try {
    const config = authConfig();
    const origin = new URL(config.origin);
    return ["localhost", "127.0.0.1", "[::1]"].includes(origin.hostname)
      && config.url === project;
  } catch { return false; }
}

export async function supportOnboardingSession(requireBound = true) {
  if (!supportOnboardingEnabled()) throw new Error("unavailable");
  const session = await verifiedSession();
  if (!session || session.user.email !== email || !session.user.email_confirmed_at
    || session.user.is_anonymous) throw new Error("denied");
  const bound = process.env.SAFERETURN_SUPPORT_DEV_SUBJECT_ID;
  if (requireBound && (!bound || session.user.id !== bound)) throw new Error("unbound");
  return session;
}
