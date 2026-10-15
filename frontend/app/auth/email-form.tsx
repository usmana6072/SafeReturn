"use client";

import { useActionState } from "react";
import { requestEmail, resetPassword, type FormState } from "./actions";

export function EmailForm({ mode, ur }: { mode: "resend" | "recovery" | "reset"; ur: boolean }) {
  const action = mode === "reset" ? resetPassword : requestEmail.bind(null, mode);
  const [state, submit, pending] = useActionState(action, { status: "idle" } as FormState);
  return <form action={submit} className="account-form">
    <label>{mode === "reset" ? (ur ? "نیا پاس ورڈ" : "New password") : (ur ? "ای میل" : "Email address")}
      <input name={mode === "reset" ? "password" : "email"} type={mode === "reset" ? "password" : "email"}
        required autoComplete={mode === "reset" ? "new-password" : "email"}
        minLength={mode === "reset" ? 12 : undefined} maxLength={mode === "reset" ? 128 : 254} /></label>
    {state.status === "confirmation" && <p role="status">{ur ? "اگر مناسب اکاؤنٹ موجود ہے تو لنک ای میل کر دیا جائے گا۔ اسی براؤزر میں کھولیں۔"
      : "If an eligible account exists, a link will be emailed. Open it in this browser."}</p>}
    {state.status === "error" && <p role="status">{ur ? "درخواست مکمل نہیں ہوئی۔ معلومات یا لنک چیک کریں اور دوبارہ کوشش کریں۔"
      : "Unable to complete the request. Check your details or recovery link, then try again."}</p>}
    <button className="button" disabled={pending}>{pending ? (ur ? "انتظار کریں…" : "Please wait…")
      : mode === "reset" ? (ur ? "پاس ورڈ محفوظ کریں" : "Save new password")
        : mode === "resend" ? (ur ? "تصدیقی لنک دوبارہ بھیجیں" : "Resend confirmation") : (ur ? "ری سیٹ لنک بھیجیں" : "Send reset link")}</button>
  </form>;
}
