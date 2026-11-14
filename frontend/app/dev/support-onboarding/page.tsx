import Link from "next/link";
import { notFound } from "next/navigation";
import { supportOnboardingEnabled, supportOnboardingSession } from "../../../lib/auth/support-onboarding";
import { OnboardingForm } from "./form";

export const dynamic = "force-dynamic";
export const metadata = { title: "Development Support onboarding | SafeReturn", robots: { index: false, follow: false } };

export default async function SupportOnboardingPage() {
  if (!supportOnboardingEnabled()) notFound();
  try {
    const session = await supportOnboardingSession(false);
    if (process.env.SAFERETURN_SUPPORT_DEV_SUBJECT_ID !== session.user.id) {
      return <main><h1>Support account identity verification</h1>
        <p>Email confirmed. Provider account ID: <code>{session.user.id}</code></p>
        <p>The exact dedicated account must be reviewed and bound by the local operator before MFA enrollment. Existing accounts must not be adopted as test fixtures. No role or MFA change has occurred here.</p></main>;
    }
    const factors = await session.client.auth.mfa.listFactors();
    if (factors.error) throw new Error();
    return <main><h1>Development Support account setup</h1>
      <p>Email confirmed. Complete genuine provider MFA in your own browser. This page does not grant Support permissions.</p>
      <OnboardingForm factors={factors.data.all.filter(f => f.factor_type === "totp").map(f => ({ id: f.id, status: f.status }))}/>
      <p>No existing factor is removed. Lost-factor recovery requires the controlled recovery procedure.</p>
      <Link href="/account">Back to account</Link></main>;
  } catch {
    return <main><h1>Support onboarding unavailable</h1>
      <p>Use only the approved dedicated development account. Complete the official signup and email-confirmation flow before continuing. No test privileges have been granted.</p>
      <Link href="/signup">Sign up</Link> <Link href="/login">Sign in</Link></main>;
  }
}
