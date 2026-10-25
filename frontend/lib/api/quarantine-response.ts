import {NextResponse} from 'next/server';
export function quarantineResponse(){return NextResponse.json({error:{code:'OPERATION_QUARANTINED'}},{status:403,headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'}});}
