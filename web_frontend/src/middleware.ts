/**
 * Next.js Edge Middleware — /talents 경로 인증 보호
 * bridge_talent_session 쿠키 없으면 /talents/login 리다이렉트
 */
import { NextRequest, NextResponse } from 'next/server'

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  // /talents 메인 페이지만 보호 (login/auth 제외)
  if (pathname === '/talents') {
    const session = req.cookies.get('bridge_talent_session')
    if (!session?.value) {
      const loginUrl = req.nextUrl.clone()
      loginUrl.pathname = '/talents/login'
      return NextResponse.redirect(loginUrl)
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/talents'],
}
