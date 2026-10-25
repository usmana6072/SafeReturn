import { NextResponse } from "next/server";
// Quarantined original Support API: never forward to its backend routes.
const unavailable = () => NextResponse.json({error:{code:"SUPPORT_ROUTE_NOT_ADMITTED"}},{status:503,headers:{"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer"}});
export const GET = unavailable;
export const POST = unavailable;
export const PATCH = unavailable;
export const HEAD = unavailable;
export const OPTIONS = unavailable;
