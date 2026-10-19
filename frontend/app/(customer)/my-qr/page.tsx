import { OwnerCollection } from "../../../components/owner-collection";
export default async function Page({ searchParams }: { searchParams: Promise<{cursor?: string; search?: string; filter?: string}> }) {
  return <OwnerCollection mode="my-qr" {...await searchParams} />;
}
