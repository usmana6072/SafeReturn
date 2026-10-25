import { NextRequest } from "next/server";
import { privacyRelay } from "../../../../../lib/api/privacy-export-relay";
export const GET = (r: NextRequest) => privacyRelay(r, false);
export const POST = (r: NextRequest) => privacyRelay(r, false);
