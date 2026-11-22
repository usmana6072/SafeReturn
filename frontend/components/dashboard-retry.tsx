"use client";
import { useTransition } from "react";
import { useRouter } from "next/navigation";

export function DashboardRetry({ ur }: { ur: boolean }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return <div className="dash-error">
    <p role="status">{ur ? "یہ معلومات لوڈ نہیں ہو سکیں۔" : "We couldn’t load this information."}</p>
    <button type="button" className="secondary" disabled={pending} onClick={() => startTransition(() => router.refresh())}>
      {pending ? (ur ? "دوبارہ کوشش جاری ہے…" : "Retrying…") : (ur ? "دوبارہ کوشش کریں" : "Try again")}
    </button>
  </div>;
}
