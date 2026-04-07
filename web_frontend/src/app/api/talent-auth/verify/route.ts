/**
 * POST /api/talent-auth/verify
 * magic_token 검증 → session_token → HttpOnly cookie 설정
 */
import { NextRequest, NextResponse } from 'next/server'
import { API_URL } from '@/lib/api'
const SESSION_MAX_AGE = 60 * 60 * 24 * 30 // 30일

export async function POST(req: NextRequest) {
  let token: string
  try {
    const body = await req.json()
    token = (body?.token || '').trim()
  } catch {
    return NextResponse.json({ success: false, message: '잘못된 요청입니다.' }, { status: 400 })
  }

  if (!token) {
    return NextResponse.json({ success: false, message: '토큰이 없습니다.' }, { status: 400 })
  }

  // Render 백엔드로 토큰 검증
  let data: { status: string; data?: { session_token: string; email: string; expires_at: string } }
  try {
    const res = await fetch(`${API_URL}/api/public/talent-auth/verify-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
    data = await res.json()

    if (!res.ok || data?.status !== 'success' || !data?.data?.session_token) {
      const msg = (data as { detail?: string })?.detail || '유효하지 않은 링크입니다.'
      return NextResponse.json({ success: false, message: msg }, { status: res.ok ? 400 : res.status })
    }
  } catch {
    return NextResponse.json({ success: false, message: '서버 연결 오류입니다.' }, { status: 503 })
  }

  const { session_token } = data.data!

  // HttpOnly 쿠키 설정 (Same-Origin — Vercel에서 설정됨)
  const response = NextResponse.json({ success: true })
  response.cookies.set('bridge_talent_session', session_token, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    maxAge: SESSION_MAX_AGE,
    path: '/',
  })
  return response
}
