'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

/** A campaign click queues an assessment server-side; switching pages cannot dismiss it. */
export default function ExamGate() {
  const { user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  useEffect(() => {
    if (user?.role !== 'employee' || pathname === '/exam') return;
    const controller = new AbortController();
    let inFlight = false;
    const check = async () => {
      if (inFlight || document.hidden) return;
      inFlight = true;
      try {
        const education = pathname === '/simulation/education';
        const response = await fetch('/api/exam', { cache: 'no-store', signal: controller.signal,
          ...(education ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'check_campaign' }) } : {}) });
        const body = await response.json();
        if (!controller.signal.aborted && response.ok && body.exam) router.replace('/exam');
      } catch { /* Durable campaign sync retries; do not alter proxy connectivity. */ }
      finally { inFlight = false; }
    };
    void check();
    const timer = window.setInterval(check, pathname === '/simulation/education' ? 3000 : 15000);
    document.addEventListener('visibilitychange', check);
    return () => { controller.abort(); window.clearInterval(timer); document.removeEventListener('visibilitychange', check); };
  }, [user?.role, pathname, router]);
  return null;
}
