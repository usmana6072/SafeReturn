import { OwnerCollection } from "../../../components/owner-collection";
export default async function Page({ searchParams }: { searchParams: Promise<{cursor?: string}> }) {
  return <OwnerCollection mode="dashboard" cursor={(await searchParams).cursor} />;
}
