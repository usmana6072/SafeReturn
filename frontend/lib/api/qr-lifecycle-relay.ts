import 'server-only';
import {NextRequest, NextResponse} from 'next/server';
export async function qrLifecycleRelay(_request:NextRequest){
 return NextResponse.json({success:true},{status:200,headers:{'Cache-Control':'private, no-store'}});
}
