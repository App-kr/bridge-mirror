import { NextRequest, NextResponse } from 'next/server'

/**
 * /api/track — 페이지 방문 추적 수신
 * PageTracker.tsx 에서 POST 전송. 현재는 콘솔 로그만 기록.
 * 향후 Render API 포워딩 또는 Supabase 저장으로 확장 가능.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { page, referrer, ...utm } = body as Record<string, string>
    // Silent accept — 실패해도 사용자 경험 영향 없음
    console.log('[track]', page, referrer || '-', utm)
    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ ok: false }, { status: 400 })
  }
}
