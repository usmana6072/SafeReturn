import {guardedBackendFetch} from './quarantine';
import { NextRequest, NextResponse } from 'next/server';
import { verifiedSession } from '../auth/server';
import { validateOrigin } from './transport';
import { parseTemplateChoices, templatePath } from '../catalog-template-choices';

export async function catalogTemplateRelay(request: NextRequest) {
  let requestId = crypto.randomUUID().replaceAll('-', '');
  const headers = () => ({'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','X-Request-ID':requestId});
  const fail = (status: number, code: string) => NextResponse.json({error:{code,message:'Catalog template choices are unavailable or the request is invalid.',message_ur:'کیٹلاگ ٹیمپلیٹس دستیاب نہیں یا درخواست درست نہیں۔',request_id:requestId,details:{}}},{status,headers:{...headers(),...(status===401?{'WWW-Authenticate':'Bearer'}:{}),...(status===405?{'Allow':'GET'}:{})}});
  try {
    const session = await verifiedSession();
    if (!session) return fail(401,'AUTH_REQUIRED');
    if (request.method !== 'GET') return fail(405,'METHOD_NOT_ALLOWED');
    if ([...request.nextUrl.searchParams.keys()].some(k=>k!=='path') || request.nextUrl.searchParams.getAll('path').length!==1 || request.nextUrl.searchParams.get('path')!==templatePath || (await request.arrayBuffer()).byteLength) return fail(422,'VALIDATION_ERROR');
    const response = await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '')+'/api/v1'+templatePath, {
      method:'GET',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(15000),headers:{Authorization:`Bearer ${session.token}`,Accept:'application/json'},
    });
    const correlation = response.headers.get('x-request-id');
    if (correlation && /^[a-f0-9]{32}$/.test(correlation)) requestId = correlation;
    if (!response.ok) {
      const codes: Record<number,string> = {401:'AUTH_REQUIRED',403:'FORBIDDEN',422:'VALIDATION_ERROR'};
      return fail(codes[response.status]?response.status:503,codes[response.status]??'PROVIDER_UNAVAILABLE');
    }
    return NextResponse.json(parseTemplateChoices(await response.json()),{headers:headers()});
  } catch { return fail(503,'PROVIDER_UNAVAILABLE'); }
}
