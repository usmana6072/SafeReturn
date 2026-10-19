import { KitRedirect } from "../../../../../components/kit-redirect";
export default async function Page({ params }: {params: Promise<{pairId: string; section: string}>}) {
  return <KitRedirect {...await params} />;
}
