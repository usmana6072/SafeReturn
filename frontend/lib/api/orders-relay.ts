import 'server-only';
import {NextRequest} from 'next/server';
import {quarantineResponse} from './quarantine-response';
export async function ordersRelay(_request:NextRequest){return quarantineResponse();}
