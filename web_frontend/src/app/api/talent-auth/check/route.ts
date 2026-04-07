/**
 * GET /api/talent-auth/check
 * bridge_talent_session 쿠키 → Render 세션 검증 → { valid, email }
 */
import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { API_URL } from '@/lib/api'

export async function GET(req: NextRequest) {
  const cookieStore = await cookies()
  const session_token = cookieStore.get('bridge_talent_session')?.value

  if (!session_token) {
    return NextResponse.json({ valid: false })
  }

  try {
    const res = await fetch(`${API_URL}/api/public/talent-auth/check-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_token }),
      cache: 'no-store',
    })
    const data = await res.json()
    const inner = data?.data ?? data
    return NextResponse.json({
      valid: inner?.valid === true,
      email: inner?.email ?? null,
    })
  } catch {
    return NextResponse.json({ valid: false })
  }
}
