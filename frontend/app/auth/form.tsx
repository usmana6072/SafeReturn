"use client";

import { useActionState, useState } from "react";
import Link from "next/link";
import { submitIdentity, FormState, saveAccount } from "./actions";
import type { Account } from "../../lib/auth/server";

const initial: FormState = { status: "idle" };
function Notice({ state, ur, signup = false }: { state: FormState; ur: boolean; signup?: boolean }) {
  if (state.status === "idle") return null;
  const messages = {
    invalid: ur ? "درست معلومات درج کریں۔" : "Check your details and try again.",
    denied: signup
      ? (ur ? "اکاؤنٹ نہیں بنایا جا سکا۔ معلومات چیک کریں یا موجودہ اکاؤنٹ سے لاگ اِن کریں۔" : "Unable to create an account. Check your details or sign in to an existing account.")
      : (ur ? "سائن اِن نہیں ہو سکا۔ معلومات اور ای میل کی تصدیق چیک کریں۔" : "Unable to sign in. Check your details and email confirmation."),
    unavailable: ur ? "سروس دستیاب نہیں۔ دوبارہ کوشش کریں۔" : "Service unavailable. Please try again.",
    limited: ur ? "کچھ دیر بعد دوبارہ کوشش کریں۔" : "Too many attempts. Please try again later.",
    email_limited: ur ? "ای میل بھیجنے کی حد پوری ہو گئی ہے۔ کچھ دیر بعد دوبارہ کوشش کریں۔" : "Email sending limit reached. Please try again later.",
    stale: ur ? "اکاؤنٹ بدل گیا ہے۔ صفحہ دوبارہ کھولیں۔" : "Account changed. Reload before saving again.",
  };
  return <p role="status" className="form-notice">{state.status === "confirmation"
    ? (ur ? "اپنی ای میل میں تصدیقی لنک کھولیں، پھر لاگ اِن کریں۔" : "Check your email for a confirmation link, then log in. If you already have an account, use Log in.")
    : messages[state.reason ?? "unavailable"]}</p>;
}

export function IdentityForm({ mode, ur }: { mode: "login" | "signup"; ur: boolean }) {
  const signup = mode === "signup";
  const [state, action, pending] = useActionState(submitIdentity.bind(null, mode), initial);
  const [visible, setVisible] = useState(false);
  return <>
    <form action={action} className="account-form">
      {signup && <label>{ur ? "پورا نام" : "Full name"}<input name="display_name"
        autoComplete="name" required maxLength={120} /></label>}
      <label>{ur ? "ای میل" : "Email address"}<input name="email" type="email"
        autoComplete="email" required maxLength={254} /></label>
      <label>{ur ? "پاس ورڈ" : "Password"}<span className="password-field">
        <input name="password" type={visible ? "text" : "password"} required
          minLength={signup ? 12 : 1} maxLength={128}
          autoComplete={signup ? "new-password" : "current-password"} />
        <button type="button" aria-pressed={visible} onClick={() => setVisible(!visible)}>
          {visible ? (ur ? "چھپائیں" : "Hide") : (ur ? "دکھائیں" : "Show")}</button>
      </span></label>
      {signup && <p className="form-help">{ur ? "کم از کم ۱۲ حروف۔ ای میل کی تصدیق ضروری ہے۔" : "Use at least 12 characters. Email confirmation is required."}</p>}
      <Notice state={state} ur={ur} signup={signup} />
      <button className="button" type="submit" disabled={pending}>
        {pending ? (ur ? "انتظار کریں…" : "Please wait…")
          : signup ? (ur ? "اکاؤنٹ بنائیں" : "Create account") : (ur ? "لاگ اِن" : "Log in")}
      </button>
    </form>
    {!signup && <p><Link className="text-link" href="/auth/forgot-password">{ur ? "پاس ورڈ بھول گئے؟" : "Forgot password?"}</Link></p>}
    {state.status === "confirmation" && <p><Link className="text-link" href="/auth/verify-email">{ur ? "تصدیق میں مدد" : "Confirmation help"}</Link></p>}
    <p>{signup ? (ur ? "پہلے سے اکاؤنٹ ہے؟ " : "Already have an account? ")
      : (ur ? "نیا اکاؤنٹ؟ " : "New to SafeReturn? ")}
      <Link className="text-link" href={signup ? "/auth/sign-in" : "/auth/sign-up"}>
        {signup ? (ur ? "لاگ اِن" : "Log in") : (ur ? "اکاؤنٹ بنائیں" : "Create an account")}</Link></p>
  </>;
}

export function AccountForm({ account, initialName, ur }: {
  account: Account; initialName: string; ur: boolean;
}) {
  const [state, action, pending] = useActionState(saveAccount, initial);
  return <form action={action} className="account-form">
    <input type="hidden" name="version" value={account.version} />
    <label>{ur ? "نام" : "Display name"}<input name="display_name" required maxLength={120}
      autoComplete="name" defaultValue={account.display_name ?? initialName} /></label>
    <label>{ur ? "زبان" : "Preferred language"}<select name="preferred_locale" defaultValue={account.preferred_locale}>
      <option value="en">English</option><option value="ur">اردو</option>
    </select></label>
    <Notice state={state} ur={ur} />
    <button className="button" type="submit" disabled={pending}>
      {pending ? (ur ? "انتظار کریں…" : "Saving…") : (ur ? "محفوظ کریں" : "Save changes")}</button>
  </form>;
}
