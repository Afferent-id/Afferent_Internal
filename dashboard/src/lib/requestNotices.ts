export interface AnsweredRequest { id: string; domain: string; status: 'open' | 'allowed' | 'denied'; decision_note?: string | null }

/** Answered requests that have not been announced yet in this browser, oldest answers last, at most `limit`. */
export function requestsToAnnounce<T extends AnsweredRequest>(requests: readonly T[], announcedRaw: string, limit = 3): T[] {
  const announced = new Set(announcedRaw.split(',').filter(Boolean));
  return requests.filter(item => item.status !== 'open' && !announced.has(item.id)).slice(0, limit);
}

/** Remembers announced ids, keeping only the latest 50 so the stored text stays small. */
export function rememberAnnounced(announcedRaw: string, ids: readonly string[]): string {
  const merged = [...announcedRaw.split(',').filter(Boolean), ...ids.filter(id => !announcedRaw.split(',').includes(id))];
  return merged.slice(-50).join(',');
}

/** Protection is only worth showing once we know it is off: nothing while checking, nothing when it works. */
export function protectionBlockVisible(state: { booting: boolean; failedToLoad: boolean; registered: boolean; probe: 'checking' | 'connected' | 'disconnected' }): boolean {
  if (state.booting && !state.failedToLoad) return false;
  if (state.registered && state.probe === 'checking') return false;
  if (state.registered && state.probe === 'connected') return false;
  return true;
}
