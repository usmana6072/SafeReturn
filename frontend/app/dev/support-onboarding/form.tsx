"use client";
import { useActionState } from "react";
import { onboardingAction, type OnboardingState } from "./actions";

export function OnboardingForm({ factors }: { factors: { id: string; status: string }[] }) {
  const [state, action, pending] = useActionState<OnboardingState, FormData>(onboardingAction, {});
  if (state.verified) return <p role="status">Provider MFA verified for this session. Support permissions and live API acceptance are still pending.</p>;
  return <form action={action}>
    {state.error && <p role="alert">{state.error}</p>}
    {state.qr && <div>
      <p>Scan this private provider enrollment image with your authenticator. Never share or capture it.</p>
      {/* Provider SVG is an image, never inserted as executable markup. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={state.qr} alt="Private authenticator enrollment" width={240} height={240}/>
    </div>}
    {factors.length || state.factor ? <>
      <label>Authenticator <select name="factor" defaultValue={state.factor ?? factors[0]?.id}>
        {state.factor && !factors.some(f => f.id === state.factor) && <option value={state.factor}>New authenticator</option>}
        {factors.map(f => <option key={f.id} value={f.id}>Authenticator ({f.status})</option>)}
      </select></label>
      <label>Authenticator code <input name="code" type="password" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required/></label>
      <p>Enter it only in this private browser form. Never send it in chat or an approval packet.</p>
      <button name="mode" value="verify" disabled={pending}>Verify authenticator</button>
    </> : <button name="mode" value="enroll" disabled={pending}>Enroll authenticator</button>}
  </form>;
}
