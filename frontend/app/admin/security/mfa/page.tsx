import Link from "next/link";
import { staffSecurity } from "../../../../lib/auth/staff";
import { mfaReturn } from "../../../../lib/auth/mfa-return";
import { MfaForm } from "./form";
export const metadata = { title: "Staff security | SafeReturn", robots: { index: false, follow: false } };
export const dynamic = "force-dynamic";
export default async function MfaPage({ searchParams }: { searchParams: Promise<{ returnTo?: string }> }) {
  try {
    const session = await staffSecurity();
    const result = await session.client.auth.mfa.listFactors();
    if (result.error) throw new Error();
    return <main><h1>Staff security</h1>
      <p>{session.security.mfa_verified ? "MFA verified for this session." : "Verify an authenticator to continue to staff tools."}</p>
      <MfaForm factors={result.data.all.filter(f => f.factor_type === "totp").map(f => ({ id: f.id, status: f.status }))} returnTo={mfaReturn((await searchParams).returnTo)}/>
      <h2>Lost your authenticator?</h2><p>Stop and contact your designated security owner through your established trusted channel. They must independently verify your identity and review recovery under the staff security policy. No access is restored here. Password recovery does not replace MFA. Never send a setup key or one-time code to support.</p>
      <p>An unfinished setup cannot be recovered from this page after leaving. Ask your security owner for controlled assistance; existing factors are never removed here.</p>
      <Link href="/account">Back to account</Link></main>;
  } catch { return <main><h1>Staff security unavailable</h1><p>A verified active staff account is required. Sign in again, or contact your security owner.</p><Link href="/login">Sign in</Link></main>; }
}
