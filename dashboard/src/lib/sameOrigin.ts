import type { NextRequest } from 'next/server';

/** Use the browser-facing Host; Next's internal URL may use a container hostname. */
export function isSameOrigin(request: NextRequest): boolean {
  const host = request.headers.get('host');
  const protocol = request.headers.get('x-forwarded-proto') ?? request.nextUrl.protocol.slice(0, -1);
  if (!host || /[\s/\\@?#]/.test(host) || !['http', 'https'].includes(protocol)) return false;
  try { return request.headers.get('origin') === new URL(`${protocol}://${host}`).origin; }
  catch { return false; }
}
