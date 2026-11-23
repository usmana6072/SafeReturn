import { Suspense } from "react";
import { getLanguage } from "../lib/i18n";
import { customerSession, unreadMessages } from "../lib/customer-dashboard";
import { IndependentQRs } from "./independent-qr";
import { QRLibrarySkeleton, type FinderHints } from "./qr-library-cards";

async function Library({ ur }: { ur: boolean }) {
  const finder: FinderHints = {};
  const session = await customerSession();
  if (session) {
    // Reuse the shell's unread page and send only counts to the cards.
    const page = await unreadMessages(session.token).catch(() => null);
    for (const message of page?.items ?? []) {
      const hint = finder[message.qr_id];
      if (hint) hint.count++;
      else finder[message.qr_id] = { count: 1, partial: !!page?.more };
    }
  }
  return <IndependentQRs ur={ur} finder={finder}/>;
}

export async function QRLibraryPage() {
  const ur = await getLanguage() === "ur";
  return <Suspense fallback={<QRLibrarySkeleton ur={ur}/>}><Library ur={ur}/></Suspense>;
}
