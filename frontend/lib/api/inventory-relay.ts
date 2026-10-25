import 'server-only';
import {NextRequest} from 'next/server';
import {quarantineResponse} from './quarantine-response';
export async function inventoryRelay(_request:NextRequest){return quarantineResponse();}
