import { KitRedirect } from "../../../../../../components/kit-redirect";
export default async function Page({ params }: {params: Promise<{pairId: string}>}) {
  return <KitRedirect pairId={(await params).pairId} section="ice" />;
}
