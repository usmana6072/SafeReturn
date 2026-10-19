"use server";

import { ownerApi } from "../../../lib/qr-server";

export async function submitFinderMessage(
  token: string,
  _state: string,
  formData: FormData,
) {
  const latitude = formData.get("latitude");
  const longitude = formData.get("longitude");
  const location =
    formData.get("location_consent") === "on" && latitude && longitude
      ? {
          latitude: Number(latitude),
          longitude: Number(longitude),
          accuracy_m: formData.get("accuracy_m")
            ? Number(formData.get("accuracy_m"))
            : null,
        }
      : null;
  try {
    await ownerApi()(`/public/qr/${token}/finder-messages`, "POST", {
      finder_name: formData.get("finder_name") || null,
      finder_email: formData.get("finder_email") || null,
      finder_phone: formData.get("finder_phone") || null,
      preferred_contact: formData.get("preferred_contact") || null,
      message: formData.get("message"),
      consent_version: "finder-public-v1",
      contact_consent_accepted: formData.get("contact_consent_accepted") === "on",
      location,
      location_consent: formData.get("location_consent") === "on",
      turnstile_token: formData.get("cf-turnstile-response") || null,
    }, undefined, String(formData.get("idempotency_key") ?? ""));
    return JSON.stringify({ status: "accepted" });
  } catch {
    return JSON.stringify({ status: "unavailable" });
  }
}
