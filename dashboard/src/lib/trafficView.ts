export const TRAFFIC_VIEWS = ['live', 'policies', 'threats', 'audit'] as const;
export type TrafficView = (typeof TRAFFIC_VIEWS)[number];

/** The sub-tab named in a URL query string (`?view=policies`); the default is Live traffic. Unknown values are ignored. */
export function viewFromSearch(search: string): TrafficView {
  const raw = new URLSearchParams(search).get('view');
  // `signins` is the readable alias of the tab that used to be called Audit log; `audit` stays the canonical value so old links keep working.
  const value = raw === 'signins' ? 'audit' : raw;
  return (TRAFFIC_VIEWS as readonly string[]).includes(value ?? '') ? (value as TrafficView) : 'live';
}

/** The query string for a sub-tab. The default view has no parameter, so the plain URL stays clean. */
export function searchForView(view: TrafficView): string {
  return view === 'live' ? '' : `?view=${view}`;
}

/** Threat feed entries the SOC still has to look at. */
export function threatsNeedingAttention(entries: readonly { action: string }[]): number {
  return entries.filter(entry => (entry.action || '').toLowerCase() === 'notify_soc').length;
}
