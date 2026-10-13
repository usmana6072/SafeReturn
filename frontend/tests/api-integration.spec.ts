import { expect, test } from "@playwright/test";
import { createApiClient } from "../lib/api/transport";

const origin = process.env.SAFERETURN_TEST_API_ORIGIN;

test("typed frontend transport reaches real FastAPI liveness", async () => {
  test.skip(!origin || process.env.SAFERETURN_TEST_API_OFFLINE === "1", "Requires live local FastAPI");
  expect(await createApiClient({ origin: origin! }).getLiveness()).toEqual({ status: "ok" });
});

test("Next.js server route reflects real backend availability safely", async ({ request, page }) => {
  test.skip(!origin, "Requires explicit local integration environment");
  const response = await request.get("/api/health/live");
  const offline = process.env.SAFERETURN_TEST_API_OFFLINE === "1";
  expect(response.status()).toBe(offline ? 503 : 200);
  expect(await response.json()).toEqual({ status: offline ? "unavailable" : "ok" });
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect(await response.text()).not.toContain(origin!);
  expect((await request.get("/api/health/ready")).status()).toBe(404);
  await page.goto("/");
  const browserResponse = await page.evaluate(async () => {
    const response = await fetch("/api/health/live");
    return { status: response.status, payload: await response.json() };
  });
  expect(browserResponse).toEqual({ status: offline ? 503 : 200, payload: { status: offline ? "unavailable" : "ok" } });
});
