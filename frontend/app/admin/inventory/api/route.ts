import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';
const unavailable = () => NextResponse.json({ error: { code: 'NOT_IMPLEMENTED' } }, {
  status: 503, headers: { 'Cache-Control': 'private, no-store' },
});
export const GET = unavailable;
export const POST = unavailable;
export const PUT = unavailable;
export const PATCH = unavailable;
export const DELETE = unavailable;
export const HEAD = () => new NextResponse(null, { status: 503, headers: { 'Cache-Control': 'private, no-store' } });
export const OPTIONS = () => new NextResponse(null, { status: 405 });
