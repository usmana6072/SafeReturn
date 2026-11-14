import {assertBackendOperation} from './api/quarantine';
import { ApiError, validateOrigin } from "./api/transport";

export type Tag = { qr_id: string; pair_id: string | null; tag_type: "lost" | "ice";
  pair_reference: string | null;
  profile_label: string | null; public_status: string; published: boolean; editable: boolean;
  profile_version: number; preference_version: number;
  physical_products?: {product_name_snapshot: string; variant_name_snapshot: string; copies: number}[] };
export type Pair = { pair_id: string; pair_reference: string; ownership_status: string;
  inventory_status: string; activated_at: string | null; tags: Tag[] };
export type Page<T> = { items: T[]; next_cursor: string | null };
export type Profile = { version: number; published: boolean; item_label?: string | null;
  description?: string | null; reward_text?: string | null; return_instructions?: string | null;
  display_name?: string | null; blood_group?: string | null; emergency_instructions?: string | null;
  medical_notes?: string | null; medical_notes_redacted?: boolean; show_medical_notes?: boolean };
export type Contact = { contact_id: string; relationship_label: string; display_name: string | null;
  phone_masked: string | null; published: boolean; display_order: number };
export type Contacts = { version: number; contacts: Contact[] };
export type Preferences = { version: number; whatsapp_enabled: boolean; whatsapp_phone_masked: string | null };
export type Intent = { intent_id: string; pair_id: string; lost_qr_id: string; ice_qr_id: string; expires_at: string };
export const uuid = (value: string) => /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value);

// Dependency injection permits provider-failure contract tests without real credentials.
export function qrClient(origin: string, token?: string, transport: typeof fetch = fetch) {
  const base = validateOrigin(origin);
  return async function request<T>(path: string, method = "GET", body?: unknown, version?: number, key?: string): Promise<T> {
    if (!/^\/(me\/|public\/qr\/)/.test(path) || path.includes("..") || path.includes("#")) throw new ApiError("configuration");
    assertBackendOperation(method,"/api/v1"+path);
    const response = await transport(`${base}/api/v1${path}`, { method, cache: "no-store", redirect: "error",
      signal: AbortSignal.timeout(8000), headers: { Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(version !== undefined ? { "If-Match": `"${version}"` } : {}),
        ...(key ? { "Idempotency-Key": key } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) });
    if (!response.ok) throw new ApiError("http", response.status);
    if (response.status === 204) return undefined as T;
    return response.json();
  };
}
