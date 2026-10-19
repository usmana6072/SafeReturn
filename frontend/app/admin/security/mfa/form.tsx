"use client";
import { useActionState } from "react";
import { mfaAction, type MfaState } from "./actions";
export function MfaForm({ factors, returnTo }: { factors: { id: string; status: string }[]; returnTo: string }) {
  const [state, action, pending] = useActionState<MfaState, FormData>(mfaAction, {});
  return <form action={action}>
    <input type="hidden" name="returnTo" value={returnTo}/>
    {state.error && <p role="alert">{state.error}</p>}
    {state.secret && <div><p>Add this setup key to your authenticator. It is shown only for this setup; keep it private.</p><code>{state.secret}</code></div>}
    {factors.length || state.factor ? <>
      <label>Authenticator <select name="factor" defaultValue={state.factor ?? factors[0]?.id}>
        {state.factor && !factors.some(f => f.id === state.factor) && <option value={state.factor}>New authenticator</option>}
        {factors.map(f => <option key={f.id} value={f.id}>Authenticator ({f.status})</option>)}
      </select></label>
      <label>Six-digit code <input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required/></label>
      <p>Use the six-digit code for this SafeReturn authenticator, not the setup key. Set your phone's date and time automatically, and enter a fresh code before its timer ends.</p>
      <button name="mode" value="verify" disabled={pending}>Verify authenticator</button>
    </> : <button name="mode" value="enroll" disabled={pending}>Set up authenticator</button>}
  </form>;
}
