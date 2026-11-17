'use client';

import { useEffect, useTransition } from 'react';
import { useRouter } from 'next/navigation';

export function ShipmentRefresh({ ur }: { ur: boolean }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    if (pending) return;
    const refresh = () => {
      if (!document.hidden) startTransition(() => router.refresh());
    };
    const timer = window.setInterval(refresh, 6000);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, [router, pending]);

  return <button className="button secondary" type="button" disabled={pending}
    onClick={() => startTransition(() => router.refresh())}>
    {ur ? 'ترسیلات تازہ کریں' : 'Refresh shipments'}
  </button>;
}
