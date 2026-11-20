"use server";

import { ownerApi } from "../../../lib/qr-server";
import { ApiError } from "../../../lib/api/transport";

export async function submitFinderMessage(
  token: string,
  _state: string,
  formData: FormData,
) {
  const email = String(formData.get("finder_email") ?? "").trim();
  const phone = String(formData.get("finder_phone") ?? "").trim().replace(/[\s()-]/g, "");
  if (!email && !phone) return JSON.stringify({ status: "invalid_contact" });
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
    const receipt = await ownerApi()<{ status: string }>(`/public/qr/${token}/finder-messages`, "POST", {
      finder_name: String(formData.get("finder_name") ?? "").trim() || null,
      finder_email: email || null,
      finder_phone: phone || null,
      preferred_contact: formData.get("preferred_contact") || null,
      message: formData.get("message"),
      consent_version: "finder-public-v1",
      contact_consent_accepted: formData.get("contact_consent_accepted") === "on",
      location,
      location_consent: formData.get("location_consent") === "on",
      turnstile_token: formData.get("cf-turnstile-response") || null,
    }, undefined, String(formData.get("idempotency_key") ?? ""));
    return JSON.stringify({ status: receipt.status === "accepted" ? "accepted" : "unavailable" });
  } catch (error) {
    return JSON.stringify({ status: error instanceof ApiError && error.status === 422 ? "invalid_contact" : "unavailable" });
  }
}
