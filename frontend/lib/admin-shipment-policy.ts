export function canManageDemoShipments(roles: readonly string[]) {
  return roles.some(role => role === "operations" || role === "superadmin");
}

// Limited demo subset of ShipmentDiscovery's existing transition map.
// No creation, packing or dispatch transition is offered by this screen.
export const demoShipmentTransitions: Readonly<Record<string, readonly string[]>> = {
  dispatched: ["delivered", "exception", "returned"],
  exception: ["returned"],
};

export const demoShipmentLabels: Readonly<Record<string, string>> = {
  dispatched: "Mock Dispatched", delivered: "Mock Delivered", exception: "Mock Delivery Issue", returned: "Mock Returned",
};
