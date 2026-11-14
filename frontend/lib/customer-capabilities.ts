import { assertBackendOperation, QuarantinedOperation } from "./api/quarantine";

// Presentation follows the existing policy; it never changes the protected list.
export function customerOperationAvailable(method: string, path: string): boolean {
  try { assertBackendOperation(method, "/api/v1" + path); return true; }
  catch (error) { if (error instanceof QuarantinedOperation) return false; throw error; }
}
