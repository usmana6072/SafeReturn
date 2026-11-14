import { NextRequest } from 'next/server';
import { supportMetadataRelay } from '../../../../lib/api/support-metadata-relay';
export const dynamic = 'force-dynamic';
export const GET = (r: NextRequest) => supportMetadataRelay(r,'list');
// Explicit HEAD avoids Next's automatic GET fallback.
export const HEAD = GET;
export const OPTIONS = GET;
