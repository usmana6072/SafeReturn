import "server-only";

import { ApiError, createApiClient } from "./transport";

export function getServerApiClient() {
  const origin = process.env.SAFERETURN_API_ORIGIN
    ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : undefined);
  if (!origin) throw new ApiError("configuration");
  return createApiClient({ origin });
}
