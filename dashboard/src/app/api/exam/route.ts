import { NextRequest, NextResponse } from 'next/server';
import { fetchFlaskBackend } from '@/lib/backendClient';
import { AUTH_SESSION_COOKIE } from '@/lib/authSession';
import { isSameOrigin } from '@/lib/sameOrigin';

async function forward(request: NextRequest) {
  if (!request.cookies.get(AUTH_SESSION_COOKIE)?.value) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  if (request.method === 'POST' && !isSameOrigin(request)) return NextResponse.json({ error: 'Cross-origin requests are not allowed.' }, { status: 403 });
  try {
    const response = await fetchFlaskBackend('/api/exam', { method: request.method,
      ...(request.method === 'POST' ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(await request.json()) } : {}) }, 15000);
    return NextResponse.json(await response.json(), { status: response.status });
  } catch { return NextResponse.json({ error: 'Assessment service is unavailable. Please retry.' }, { status: 503 }); }
}
export const GET = forward;
export const POST = forward;
