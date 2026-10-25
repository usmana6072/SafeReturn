import 'server-only';
import {NextRequest,NextResponse} from 'next/server';
import {phase13Relay} from './phase13-relay';
export async function dashboardRelay(r:NextRequest){
if(r.method!=='GET')return phase13Relay(r,'summary');
const q=r.nextUrl.searchParams,kind=q.get('kind');
if(q.getAll('kind').length!==1||!['summary','trends'].includes(kind??''))return NextResponse.json({error:{code:'INVALID_QUERY'}},{status:422,headers:{'Cache-Control':'private, no-store'}});
const u=new URL(r.url);u.searchParams.delete('kind');return phase13Relay(new NextRequest(u,r),kind as 'summary'|'trends');
}
