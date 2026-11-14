import {financeStorageRelay} from '../../../../lib/api/finance-storage-relay';
import {NextRequest} from 'next/server';
export const dynamic='force-dynamic';
const relay=(request:NextRequest)=>financeStorageRelay(request,true);
export const GET=relay;
export const POST=relay;
export const PUT=relay;
export const PATCH=relay;
export const DELETE=relay;
export const HEAD=relay;
export const OPTIONS=relay;

