import { NextRequest, NextResponse } from 'next/server';
import { uuid } from '../../../../lib/admin-print-jobs-contract';
import { guardedBackendFetch } from '../../../../lib/api/quarantine';
import { validateOrigin } from '../../../../lib/api/transport';
import { authConfig } from '../../../../lib/auth/config';
import { verifiedSession } from '../../../../lib/auth/server';
import { staffState, StaffAccessError } from '../../../../lib/auth/staff';

const headers = {
    'Cache-Control': 'private, no-store',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': 'sandbox',
};

async function hasRequestBody(request: NextRequest) {
    if (request.headers.has('content-encoding') || Number(request.headers.get('content-length') ?? 0) !== 0)
        return true;
    if (!request.body) return false;
    // Next.js wraps POSTs in a stream even when the browser sent no bytes.
    const reader = request.body.getReader();
    try {
        for (;;) {
            const { done, value } = await reader.read();
            if (done) return false;
            if (value.byteLength) return true;
        }
    } finally {
        await reader.cancel();
    }
}

export async function POST(request: NextRequest) {
    const fail = (status: number) => NextResponse.json({ error: 'Print download unavailable' }, { status, headers });
    try {
        if (request.headers.get('origin') !== authConfig().origin || request.headers.get('sec-fetch-site') === 'cross-site')
            return fail(403);
        if (request.nextUrl.searchParams.size !== 2 || await hasRequestBody(request)) return fail(422);
        let job: string, artifact: string;
        try {
            job = uuid(request.nextUrl.searchParams.get('job'));
            artifact = uuid(request.nextUrl.searchParams.get('artifact'));
        } catch { return fail(422); }
        const session = await verifiedSession();
        if (!session) return fail(401);
        const staff = await staffState(session.token);
        if (!staff.mfa_verified || !staff.roles.includes('operations') || !staff.capabilities.includes('printing.manage'))
            return fail(403);
        const origin = validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '');
        const result = await guardedBackendFetch(`${origin}/api/v1/admin/print-jobs/${job}/artifacts/${artifact}/download`, {
            method: 'POST', cache: 'no-store', signal: AbortSignal.timeout(30000),
            headers: { Authorization: `Bearer ${session.token}`, Accept: 'application/pdf' },
        });
        if (!result.ok) return fail([401, 403, 404, 409, 410, 429].includes(result.status) ? result.status : 503);
        if (result.status !== 200 || result.headers.get('content-type')?.split(';')[0].trim() !== 'application/pdf' || !result.body) return fail(503);
        return new Response(result.body, { headers: { ...headers, 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="SR-print.pdf"' } });
    } catch (error) {
        return fail(error instanceof StaffAccessError && [401, 403].includes(error.status) ? error.status : 503);
    }
}
