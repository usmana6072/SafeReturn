import type { MockOrder, MockPrintJob } from "./admin-mock-data";

// No record in this demo has independently established production release gates.
export function demoShipmentReadiness(order: MockOrder) {
  return order.payment && order.payment !== "Verified" ? "Blocked" : "Unknown";
}

export function demoOrderPrintQA(orderId: string, jobs: MockPrintJob[]) {
  const linked = jobs.filter(job => job.orderId === orderId);
  return linked.length ? "Not verified — demo print metadata only" : "Not available";
}
