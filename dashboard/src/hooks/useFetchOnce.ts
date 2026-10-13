'use client';

import { useCallback, useEffect, useState } from 'react';
import { loadState, type LoadState } from '@/lib/loadState';

/** One request for a list that does not need polling. Keeps what it has when a retry fails. */
export function useFetchOnce<T>(url: string, pick: (json: unknown) => T, empty: T): { data: T; state: LoadState } {
  const [data, setData] = useState<T>(empty);
  const [hasData, setHasData] = useState(false);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    fetch(url, { cache: 'no-store' })
      .then(async res => { if (!res.ok) throw new Error(); return res.json(); })
      .then(json => { if (active) { setData(pick(json)); setHasData(true); setError(false); } })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
    // `pick` is a stable module-level function at every call site.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, attempt]);

  const retry = useCallback(() => { setLoading(true); setError(false); setAttempt(n => n + 1); }, []);
  return { data, state: loadState(loading, error, hasData, retry) };
}
