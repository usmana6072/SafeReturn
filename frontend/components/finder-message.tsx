"use client";

import { useActionState, useId, useRef, useState } from "react";
import { submitFinderMessage } from "../app/q/[token]/finder-message";
import { ContactChallenge } from "./contact-challenge";

type FinderState = { status: "idle" | "accepted" | "unavailable" };

function parse(value: string): FinderState {
  try {
    return JSON.parse(value) as FinderState;
  } catch {
    return { status: "unavailable" };
  }
}

export function FinderMessageForm({
  token,
  ur,
  siteKey,
  binding,
}: {
  token: string;
  ur: boolean;
  siteKey: string;
  binding: string;
}) {
  const [raw, action, pending] = useActionState(
    async (previous: string, data: FormData) => {
      retryKey.current ??= crypto.randomUUID();
      data.set("idempotency_key", retryKey.current);
      let result: string;
      try {
        result = await submitFinderMessage(token, previous, data);
      } catch {
        result = JSON.stringify({ status: "unavailable" });
      }
      setProof("");
      setAttempt((value) => value + 1);
      return result;
    },
    JSON.stringify({ status: "idle" }),
  );
  const state = parse(raw);
  const [locationError, setLocationError] = useState(false);
  const [locationPending, setLocationPending] = useState(false);
  const [proof, setProof] = useState("");
  const [attempt, setAttempt] = useState(0);
  const retryKey = useRef<string | null>(null);
  const [fields, setFields] = useState({ finder_name: "", finder_email: "", finder_phone: "", preferred_contact: "", message: "" });
  const [contactConsent, setContactConsent] = useState(false);
  const locationHelpId = useId();
  function updateField(name: keyof typeof fields, value: string) {
    retryKey.current = null;
    setFields((current) => ({ ...current, [name]: value }));
  }
  const locationRequest = useRef(0);
  const [location, setLocation] = useState<GeolocationCoordinates | null>(null);
  const [locationConsent, setLocationConsent] = useState(false);

  function requestLocation(checked: boolean) {
    const attempt = ++locationRequest.current;
    setLocationConsent(checked);
    retryKey.current = null;
    setLocation(null);
    setLocationError(false);
    setLocationPending(false);
    if (!checked) return;
    if (!navigator.geolocation) {
      setLocationConsent(false);
      setLocationError(true);
      return;
    }
    setLocationPending(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (locationRequest.current !== attempt) return;
        setLocationPending(false);
        setLocationError(false);
        setLocation(position.coords);
      },
      () => {
        if (locationRequest.current !== attempt) return;
        setLocationPending(false);
        setLocationError(true);
        setLocationConsent(false);
        setLocation(null);
      },
      { enableHighAccuracy: false, maximumAge: 0, timeout: 10000 },
    );
  }

  if (state.status === "accepted") {
    return (
      <p role="status" className="form-notice">
        {ur
          ? "آپ کا پیغام محفوظ ہو گیا ہے۔ ای میل اطلاع کی ضمانت نہیں ہے۔"
          : "Your message is saved. Email notification is not guaranteed."}
      </p>
    );
  }

  return (
    <form
      action={action}
      onReset={(event) => event.preventDefault()}
      className="public-action finder-form"
      data-finder-message
    >
      <h2>
        {ur ? "مالک کو محفوظ پیغام بھیجیں" : "Send the owner a secure message"}
      </h2>
      <label>
        {ur ? "نام" : "Name"}
        <input
          name="finder_name"
          value={fields.finder_name}
          onChange={(event) => updateField("finder_name", event.target.value)}
          disabled={pending}
          maxLength={80}
          placeholder={ur ? "آپ کا نام (اختیاری)" : "Your name (optional)"}
        />
      </label>
      <label>
        {ur ? "ای میل" : "Email"}
        <input
          name="finder_email"
          value={fields.finder_email}
          onChange={(event) => updateField("finder_email", event.target.value)}
          disabled={pending}
          type="email"
          maxLength={254}
          placeholder={ur ? "ای میل" : "Email"}
        />
      </label>
      <label>
        {ur ? "فون نمبر" : "Phone"}
        <input
          name="finder_phone"
          value={fields.finder_phone}
          onChange={(event) => updateField("finder_phone", event.target.value)}
          disabled={pending}
          inputMode="tel"
          dir="ltr"
          maxLength={16}
          placeholder={ur ? "فون نمبر" : "Phone number"}
        />
      </label>
      <label>
        {ur ? "رابطے کی ترجیح" : "Preferred contact"}
        <select name="preferred_contact" value={fields.preferred_contact} onChange={(event) => updateField("preferred_contact", event.target.value)} disabled={pending}>
          <option value="">
            {ur ? "رابطے کی ترجیح (اختیاری)" : "Preferred contact (optional)"}
          </option>
          <option value="email">{ur ? "ای میل" : "Email"}</option>
          <option value="phone">{ur ? "فون" : "Phone"}</option>
        </select>
      </label>
      <label>
        {ur ? "پیغام" : "Message"}
        <textarea
          name="message"
          value={fields.message}
          onChange={(event) => updateField("message", event.target.value)}
          disabled={pending}
          required
          minLength={10}
          maxLength={1000}
          placeholder={ur ? "پیغام" : "Message"}
        />
      </label>
      <label>
        <input
          type="checkbox"
          name="location_consent"
          aria-describedby={locationHelpId}
          checked={locationConsent}
          disabled={pending}
          onChange={(event) => requestLocation(event.target.checked)}
        />
        {ur
          ? "ایک بار کا مقام بھی شیئر کریں (اختیاری)"
          : "Share my one-time location (optional)"}
      </label>
      <p id={locationHelpId} className="form-help">
        {ur
          ? "چیز واپس کرنے میں مدد کے لیے مقام صرف ایک بار اس کے مالک سے شیئر ہوگا۔ مقام شیئر کیے بغیر بھی پیغام بھیج سکتے ہیں۔"
          : "Your location is shared once with this item's owner to help return it. You can send a message without sharing location."}
      </p>
      <input type="hidden" name="latitude" value={location?.latitude ?? ""} />
      <input type="hidden" name="longitude" value={location?.longitude ?? ""} />
      <input type="hidden" name="accuracy_m" value={location?.accuracy ?? ""} />
      <label>
        <input type="checkbox" name="contact_consent_accepted" required checked={contactConsent} disabled={pending} onChange={(event) => { retryKey.current = null; setContactConsent(event.target.checked); }} />
        {ur
          ? "میں اپنی رابطے کی معلومات اس چیز کے مالک کے ساتھ شیئر کرنے پر رضامند ہوں۔"
          : "I consent to sharing my contact details with this item's owner."}
      </label>
      {locationError && (
        <p role="status" className="form-notice">
          {ur
            ? "مقام دستیاب نہیں؛ مقام کے بغیر پیغام بھیج سکتے ہیں۔"
            : "Location is unavailable; you can submit without it."}
        </p>
      )}
      {state.status === "unavailable" && (
        <p role="alert" className="form-notice">
          {ur
            ? "پیغام ابھی نہیں بھیجا جا سکا۔"
            : "The message could not be submitted right now."}
        </p>
      )}
      <button
        className="button secondary"
        disabled={pending || locationPending || !proof}
      >
        {pending
          ? ur
            ? "بھیجا جا رہا ہے…"
            : "Sending…"
          : locationPending
            ? ur
              ? "مقام حاصل کیا جا رہا ہے…"
              : "Getting location…"
            : ur
              ? "محفوظ پیغام بھیجیں"
              : "Send secure message"}
      </button>
      <input type="hidden" name="cf-turnstile-response" value={proof} />
      {siteKey && <ContactChallenge key={attempt} siteKey={siteKey} action="finder_message" binding={binding} ur={ur} onToken={setProof} />}
      {!siteKey && <p role="alert">{ur ? "تصدیق فی الحال دستیاب نہیں ہے۔" : "Verification is currently unavailable."}</p>}
    </form>
  );
}
