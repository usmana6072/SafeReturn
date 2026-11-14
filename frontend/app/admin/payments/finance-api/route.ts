import {NextResponse} from 'next/server';
// Deliberately closed pending approved migration, authorization acceptance and
// minimal quarantine release. No upstream request can be sent by this relay.
export async function POST(){return NextResponse.json({error:{code:'INDEPENDENT_FINANCE_NOT_RELEASED'}},{status:503,headers:{'Cache-Control':'private, no-store'}});}
