const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const ts = require("typescript");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

function compile(file, dependency) {
  const module = { exports: {} };
  const source = ts.transpileModule(fs.readFileSync(file, "utf8"), { fileName: file, compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022,
  } }).outputText;
  vm.runInNewContext(source, { exports: module.exports, require: dependency });
  return module.exports;
}
const inventory = compile("lib/inventory-contract.ts", () => { throw Error(); });
const independent = compile("lib/independent-qr.ts", () => inventory);
const id = "00000000-0000-4000-8000-000000000001";
let authorized = true, failQR = false;
const requests = [];
const api = token => async path => {
  assert.equal(token, "fixture");
  requests.push(path);
  if (path === "/me/independent-qr?limit=100") {
    if (failQR) throw Error("PRIVATE_CANARY");
    return { items: [{ logical_item_id: id, qr_id: id, order_id: id, product_name_snapshot: "Purchased QR", tag_type: "lost",
      ownership_status: "unclaimed", public_status: "unactivated", revision: 1, activated_at: null, can_activate: false }], next_cursor: null, activation_released: false };
  }
  if (path === "/me/orders?limit=20") return { items: [4,3,2,1].map(n => ({
    id: String(n), order_number: "SR-" + n, payment_status: "under_review", fulfillment_status: "unallocated", total_pkr: "120.00",
    currency_code: "PKR", created_at: "2026-08-0" + n + "T09:00:00Z",
  })), next_cursor: null };
  assert.equal(path, "/me/finder-messages?status=new&limit=5");
  return { items: [], next_cursor: null };
};
const { readCustomerDashboard } = compile("lib/customer-dashboard.ts", name => {
  if (name === "server-only") return {};
  if (name === "react") return React;
  if (name === "next/navigation") return { redirect: path => { throw Error(path); } };
  if (name === "./auth/server") return {
    verifiedSession: async () => authorized ? { token: "fixture", user: { user_metadata: {} } } : null,
    accountRequest: async token => { assert.equal(token, "fixture"); return { display_name: " Amina Khan " }; },
  };
  if (name === "./qr-server") return { ownerApi: api };
  if (name === "./independent-qr") return independent;
  throw Error(name);
});
const icon = compile("components/customer-icon.tsx", require);
const statuses = compile("lib/order-status.ts", require);
const { DashboardOverview } = compile("components/dashboard-overview.tsx", name => {
  if (name === "react/jsx-runtime") return require(name);
  if (name === "next/link") return { default: ({ href, children }) => React.createElement("a", { href }, children) };
  if (name === "./dashboard-retry") return { DashboardRetry: () => React.createElement("button", null, "Try again") };
  if (name === "./customer-icon") return icon;
  if (name === "../lib/order-status") return statuses;
  throw Error(name);
});

(async () => {
  const render = async () => renderToStaticMarkup(React.createElement(DashboardOverview, { ur: false, data: await readCustomerDashboard() }));
  let html = await render();
  for (const label of ["Amina", "Purchased QR", "SR-4", "SR-2", "Payment Under Review", "0 Ready to Activate"]) assert(html.includes(label), label);
  assert(!html.includes("SR-1") && !html.includes("Paid"));
  assert.equal(requests.length, 3);
  assert.equal(new Set(requests).size, 3);
  failQR = true;
  html = await render();
  assert(html.includes("Try again") && html.includes("SR-4") && !html.includes("PRIVATE_CANARY"));
  authorized = false;
  await assert.rejects(readCustomerDashboard, /login/);
  assert.equal(requests.length, 6);
  console.log("PASS authenticated dashboard reads, metrics, latest orders, account name, partial failure and login redirect.");
})().catch(error => { console.error(error); process.exitCode = 1; });
