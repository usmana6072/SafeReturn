export type ProductLine = { product_name_snapshot: string; quantity: number };

export type Shipment = {
  id: string;
  carrier: string | null;
  tracking_reference: string | null;
  status: string;
  packed_at: string | null;
  dispatched_at: string | null;
  delivered_at: string | null;
};

export type OrderSummary = {
  id: string;
  order_number: string;
  order_status: string;
  payment_status: string;
  fulfillment_status: string;
  currency_code: string;
  total_pkr: string;
  created_at: string;
  order_items: ProductLine[];
};

export type OrderShipment = {
  id: string;
  order_number: string;
  payment_status: string;
  print_job_id: string | null;
  print_status: string | null;
  eligible: boolean;
  shipment: Shipment | null;
  next_statuses: string[];
};

export type PhysicalQA = {
  job_id: string;
  order_id: string;
  status: string;
  artifact_sha256: string;
  inspection_items: { id: string; product_name_snapshot: string; qr_type_snapshot: string }[];
  expected: { tag_type: string; symbol_mm: string; copies: number }[];
};

export type BuyerShipment = Shipment & {
  order_id: string;
  order_number: string;
  currency_code: string;
  total_pkr: string;
  order_items: ProductLine[];
};

export const workflowErrors: Record<string, string> = {
  AUTH_REQUIRED: 'Sign in again to continue.',
  FORBIDDEN: 'Your current role or MFA session does not permit this action.',
  NOT_FOUND: 'The selected order, print job, or shipment could not be found.',
  ORDER_NOT_READY_TO_SHIP: 'The order needs verified payment, allocation, and physical approval of its current print job.',
  SHIPMENT_EXISTS: 'A shipment already exists for this order. Refresh to manage it.',
  SHIPMENT_CONFLICT: 'The shipment could not be saved. Refresh the order and check its current status.',
  SHIPPING_SNAPSHOT_MISSING: 'The order is missing the delivery address saved at checkout.',
  PRINT_REVISION_CHANGED: 'A newer print job exists. Open the latest revision for inspection.',
  PRINT_NOT_READY: 'The print PDF must be ready before recording physical inspection.',
  PRINT_QA_ALREADY_PASSED: 'This print revision has already passed physical inspection.',
  PHYSICAL_QA_MISMATCH: 'Check the PDF checksum, copy counts, sizes, and inspection confirmations.',
  ITEM_QA_MISMATCH: 'Confirm inspection for every order item.',
  ARTIFACT_UNAVAILABLE: 'The current PDF is unavailable.',
  ARTIFACT_EXPIRED: 'The print PDF has expired.',
  ARTIFACT_DELETED: 'The print PDF is unavailable.',
  VERSION_MISMATCH: 'The shipment changed. Refresh before applying another update.',
  INVALID_SHIPMENT_TRANSITION: 'That status change is unavailable from the current shipment status.',
  PACKING_CONFIRMATION_REQUIRED: 'Confirm the parcel contents before marking this shipment packed.',
  TRACKING_REQUIRED: 'Enter the tracking number before dispatch.',
  FINANCIAL_HOLD: 'Resolve the order’s financial hold before continuing.',
  VALIDATION_ERROR: 'Check the required fields and try again.',
  IDEMPOTENCY_KEY_REUSED: 'This submission already used different details. Refresh before retrying.',
};

export async function workflowRequest<T>(scope: 'order' | 'shipment' | 'qa', id: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/admin/orders/workflow-api?${new URLSearchParams({ scope, id })}`, {
    cache: 'no-store', redirect: 'error', ...options,
  });
  if (!response.ok) {
    const code = (await response.json().catch(() => null))?.error?.code;
    throw new Error(Object.hasOwn(workflowErrors, code) ? workflowErrors[code] : 'The request could not be completed. Refresh before retrying.');
  }
  return response.json();
}
