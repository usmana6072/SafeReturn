/** Only fixed categories may reach logs; never log provider messages or input. */
export function mfaFailure(error: { status?: number; code?: string }) {
  if (error.status === 429) return { reason: "rate_limited", message: "Too many verification attempts. Wait a few minutes before trying again." };
  if (error.status === 401) return { reason: "session_expired", message: "Your sign-in session expired. Sign in again before verifying." };
  if (error.code === "mfa_ip_address_mismatch") return { reason: "network_changed", message: "Your verification connection changed. Try again on a stable connection." };
  if (error.code === "mfa_verification_rejected") return { reason: "policy_denied", message: "Verification was denied by the authentication policy. Contact your security owner." };
  if (error.code === "mfa_factor_not_found") return { reason: "factor_missing", message: "This authenticator is no longer available. Sign in again or contact your security owner." };
  if (error.code === "mfa_challenge_expired") return { reason: "challenge_expired", message: "Verification expired. Wait for a fresh authenticator code and try again." };
  if (error.code === "mfa_verification_failed") return { reason: "code_rejected", message: "Code invalid or expired. Try a new code." };
  return { reason: "unavailable", message: "Authenticator verification is unavailable. Try again shortly; if it continues, contact your security owner." };
}
