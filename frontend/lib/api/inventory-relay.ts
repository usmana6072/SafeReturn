import 'server-only';
import {NextRequest, NextResponse} from 'next/server';
export async function inventoryRelay(_request:NextRequest){
 return NextResponse.json({items:[],success:true},{status:200,headers:{'Cache-Control':'private, no-store'}});
}
