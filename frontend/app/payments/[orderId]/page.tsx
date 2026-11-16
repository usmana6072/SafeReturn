import { notFound, redirect } from "next/navigation";
import { uuid } from "../../../lib/qr-contract";

export default async function Payment({ params }: { params: Promise<{ orderId: string }> }) {
    const { orderId } = await params;
    if (!uuid(orderId)) notFound();
    redirect(`/checkout?orderId=${orderId}`);
}
