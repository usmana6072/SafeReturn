import { NextRequest } from 'next/server';
import { supportMetadataRelay } from '../../../../../../lib/api/support-metadata-relay';
export const dynamic = 'force-dynamic';
export async function GET(r: NextRequest, context: {params: Promise<{caseId: string}>}) {
  return supportMetadataRelay(r,'history',(await context.params).caseId);
}
export const HEAD = GET;
export const OPTIONS = GET;
