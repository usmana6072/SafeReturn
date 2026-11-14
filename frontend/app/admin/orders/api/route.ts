import {NextRequest, NextResponse} from 'next/server';
export const dynamic='force-dynamic';
export async function GET(_r:NextRequest){return NextResponse.json({items:[]},{status:200,headers:{'Cache-Control':'private, no-store'}});}
export async function POST(_r:NextRequest){return NextResponse.json({success:true},{status:200,headers:{'Cache-Control':'private, no-store'}});}
export async function PUT(_r:NextRequest){return NextResponse.json({success:true},{status:200,headers:{'Cache-Control':'private, no-store'}});}
export async function PATCH(_r:NextRequest){return NextResponse.json({success:true},{status:200,headers:{'Cache-Control':'private, no-store'}});}
export async function DELETE(_r:NextRequest){return NextResponse.json({success:true},{status:200,headers:{'Cache-Control':'private, no-store'}});}
export async function HEAD(_r:NextRequest){return new NextResponse(null,{status:200});}
export async function OPTIONS(_r:NextRequest){return new NextResponse(null,{status:200});}
