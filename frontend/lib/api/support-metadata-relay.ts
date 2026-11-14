import {guardedBackendFetch} from './quarantine';
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { supportMetadataAdmitted } from '../support-metadata-gate';
import { verifiedSession } from '../auth/server';
import { staffState, StaffAccessError } from '../auth/staff';
import { authConfig } from '../auth/config';
import { validateOrigin } from './transport';
import { caseId, supportQuery, supportPage, supportDetail, supportHistory, type MetadataKind } from '../admin-support-metadata';
const headers = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
export async function supportMetadataRelay(r: NextRequest, kind: MetadataKind, id?: string) {
  const fail = (status: number, code?: string) => NextResponse.json({error:{code:code ?? ({401:'AUTH_REQUIRED',403:'FORBIDDEN',404:'NOT_FOUND',409:'VERSION_MISMATCH',422:'VALIDATION_ERROR',405:'METHOD_NOT_ALLOWED',429:'RATE_LIMITED'} as Record<number,string>)[status] ?? 'PROVIDER_UNAVAILABLE'}},{status,headers});
  // Must precede session verification/staff lookup/fetch, including direct API use.
  if (!supportMetadataAdmitted()) return fail(503,'SUPPORT_METADATA_NOT_ADMITTED');
  try {
    if (r.method !== 'GET') return fail(405);
    if (r.headers.get('sec-fetch-site') === 'cross-site' || r.headers.has('origin') && r.headers.get('origin') !== authConfig().origin) return fail(403);
    let q: URLSearchParams;
    try {
      if (r.body || r.headers.has('content-encoding') || r.headers.has('transfer-encoding') || (r.headers.get('content-length') ?? '0') !== '0') throw Error();
      q = supportQuery(r.nextUrl.searchParams,kind);
      if (kind !== 'list') id = caseId(id);
    } catch { return fail(422); }
    const session = await verifiedSession();
    if (!session) return fail(401);
    const permitted = (s: Awaited<ReturnType<typeof staffState>>) => s.mfa_verified && s.roles.includes('support') && s.capabilities.includes('support.manage');
    if (!permitted(await staffState(session.token))) return fail(403);
    const path = '/api/v1/admin/support-case-metadata' + (kind === 'list' ? '' : '/' + id + (kind === 'history' ? '/history' : ''));
    const response = await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '') + path + (q.size ? '?' + q : ''), {method:'GET',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(10000),headers:{Authorization:'Bearer ' + session.token,Accept:'application/json'}});
    if (!response.ok) return fail([400,401,403,404,409,422,429].includes(response.status) ? response.status : 503);
    if (response.status !== 200 || response.headers.get('content-type')?.split(';')[0].trim() !== 'application/json') throw Error();
    const reader = response.body?.getReader(); if (!reader) throw Error();
    let size = 0, body = ''; const decoder = new TextDecoder('utf-8',{fatal:true});
    try { for (;;) { const {done,value} = await reader.read(); if (done) break; size += value.byteLength; if (size > 262144) throw Error(); body += decoder.decode(value,{stream:true}); } body += decoder.decode(); }
    finally { await reader.cancel(); }
    const raw: unknown = JSON.parse(body), limit = Number(q.get('limit') ?? 20);
    const result = kind === 'list' ? supportPage(raw,limit) : kind === 'detail' ? supportDetail(raw) : supportHistory(raw,limit);
    if (kind !== 'list' && 'case_id' in result && result.case_id !== id) throw Error();
    if (!permitted(await staffState(session.token))) return fail(403);
    return NextResponse.json(result,{headers});
  } catch (e) { return fail(e instanceof StaffAccessError && [401,403].includes(e.status) ? e.status : 503); }
}
