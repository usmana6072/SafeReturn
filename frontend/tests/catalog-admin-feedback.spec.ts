import { test, expect } from '@playwright/test';
import { catalogFailure } from '../lib/catalog-admin-feedback';

test('catalog errors use fixed actionable guidance and discard private details', async () => {
  const messages: Record<string,string> = { CREATE_AS_DRAFT:'draft first', FUTURE_PRODUCT_DISABLED:'active QR Stickers', PHYSICAL_CATALOG_APPROVAL_REQUIRED:'reviewed template key/version', VERIFIED_PUBLIC_IMAGE_REQUIRED:'server verification', ARCHIVED_PRODUCT:'cannot be republished', CATALOG_CONFLICT:'slug or SKU', INVALID_PUBLIC_ASSET:'could not be verified', PUBLIC_ASSET_FOLDER_REQUIRED:'configured catalog folder', IDEMPOTENCY_KEY_REUSED:'earlier command' };
  for (const [code,text] of Object.entries(messages)) {
    const body = {error:{code,message:'PRIVATE_CANARY_PROVIDER_SECRET',details:{token:'PRIVATE_CANARY_TOKEN'}}};
    const message = await catalogFailure(Response.json(body,{status:422}),false);
    expect(message).toContain(text);expect(message).not.toContain('PRIVATE_CANARY');
    expect(await catalogFailure(Response.json(body,{status:422}),true)).toMatch(/[\u0600-\u06ff]/);
  }
});
test('session, MFA, stale and unavailable responses take safe status precedence', async () => {
  for(const [status,text] of [[401,'session expired'],[403,'current MFA'],[412,'entries remain'],[503,'does not confirm']] as const) {
    expect(await catalogFailure(Response.json({error:{code:'CREATE_AS_DRAFT'}},{status}),false)).toContain(text);
  }
});
test('unknown and malformed errors never become HTML or raw messages', async () => {
  for(const code of ['PRIVATE_CANARY','__proto__','constructor']) {
    expect(await catalogFailure(Response.json({error:{code,message:'PRIVATE_CANARY'}},{status:422}),false)).toContain('required fields');
  }
  expect(await catalogFailure(new Response('<html>PRIVATE_CANARY</html>',{status:502}),false)).not.toContain('PRIVATE_CANARY');
});
