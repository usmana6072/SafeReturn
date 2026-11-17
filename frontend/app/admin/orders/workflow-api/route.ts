import { NextRequest, NextResponse } from 'next/server';
import { guardedBackendFetch } from '../../../../lib/api/quarantine';
import { validateOrigin } from '../../../../lib/api/transport';
import { authConfig } from '../../../../lib/auth/config';
import { verifiedSession } from '../../../../lib/auth/server';
import { staffState, StaffAccessError } from '../../../../lib/auth/staff';
import { uuid } from '../../../../lib/qr-contract';
import { workflowErrors } from '../../../../lib/fulfillment-workflow';

const headers = {
  'Cache-Control': 'private, no-store',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
};

async function bodyText(request: NextRequest) {
  const reader = request.body?.getReader();
  if (!reader) throw Error();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let size = 0, body = '';
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) return body + decoder.decode();
      size += value.byteLength;
      if (size > 16000) throw Error();
      body += decoder.decode(value, { stream: true });
    }
  } finally {
    await reader.cancel();
  }
}

async function relay(request: NextRequest) {
  const fail = (status: number, code: string) => NextResponse.json({ error: { code } }, { status, headers });
  try {
    const method = request.method;
    const write = method !== 'GET';
    const origin = request.headers.get('origin');
    if (request.headers.get('sec-fetch-site') === 'cross-site' || (write || origin) && origin !== authConfig().origin)
      return fail(403, 'FORBIDDEN');
    const params = request.nextUrl.searchParams;
    const scope = params.get('scope'), id = params.get('id');
    if (params.size !== 2 || !id || !uuid(id) || !['order', 'shipment', 'qa'].includes(scope ?? ''))
      return fail(422, 'VALIDATION_ERROR');
    if (scope === 'order' && write || scope === 'qa' && method === 'PATCH') return fail(405, 'METHOD_NOT_ALLOWED');

    const session = await verifiedSession();
    if (!session) return fail(401, 'AUTH_REQUIRED');
    const staff = await staffState(session.token);
    const capability = scope === 'order' ? 'orders.read' : scope === 'qa' ? 'printing.manage' : 'fulfillment.manage';
    if (!staff.mfa_verified || !staff.capabilities.includes(capability) ||
        !(staff.roles.includes('operations') || scope === 'order' && staff.roles.includes('finance')))
      return fail(403, 'FORBIDDEN');

    const upstreamHeaders: Record<string, string> = { Authorization: `Bearer ${session.token}`, Accept: 'application/json' };
    let body: string | undefined;
    if (write) {
      const key = request.headers.get('idempotency-key') ?? '';
      if (!/^[A-Za-z0-9._:-]{8,160}$/.test(key) || request.headers.get('content-encoding') ||
          request.headers.get('content-type')?.split(';')[0].trim() !== 'application/json')
        return fail(422, 'VALIDATION_ERROR');
      try { body = await bodyText(request); } catch { return fail(422, 'VALIDATION_ERROR'); }
      upstreamHeaders['Content-Type'] = 'application/json';
      upstreamHeaders['Idempotency-Key'] = key;
    }
    const path = scope === 'qa' ? `/admin/print-jobs/${id}/physical-qa` : `/admin/orders/${id}/${scope === 'order' ? 'summary' : 'shipment'}`;
    const response = await guardedBackendFetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '')}/api/v1${path}`, {
      method, cache: 'no-store', signal: AbortSignal.timeout(20000), headers: upstreamHeaders, body,
    });
    if (!response.ok) {
      const value = await response.json().catch(() => null);
      const code = value?.error?.code ?? value?.detail?.code;
      const status = [401, 403, 404, 409, 410, 412, 422, 429].includes(response.status) ? response.status : 503;
      const generic = { 401: 'AUTH_REQUIRED', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 412: 'VERSION_MISMATCH', 422: 'VALIDATION_ERROR' } as Record<number, string>;
      return fail(status, typeof code === 'string' && Object.hasOwn(workflowErrors, code) ? code : generic[status] ?? 'SERVICE_UNAVAILABLE');
    }
    return NextResponse.json(await response.json(), { status: response.status, headers });
  } catch (error) {
    if (error instanceof StaffAccessError && error.status === 401) return fail(401, 'AUTH_REQUIRED');
    if (error instanceof StaffAccessError && error.status === 403) return fail(403, 'FORBIDDEN');
    return fail(503, 'SERVICE_UNAVAILABLE');
  }
}

export const GET = relay;
export const POST = relay;
export const PATCH = relay;
