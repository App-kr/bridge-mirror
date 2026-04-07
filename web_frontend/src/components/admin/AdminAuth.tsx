'use client'

import { useState, useEffect } from 'react'
import { API_URL } from '@/lib/api'

interface AdminAuthProps {
  onLogin: (password: string) => Promise<string | null>
  waking?: boolean
}

const KAKAO_ERROR_MSGS: Record<string, string> = {
  cancelled:      '카카오 로그인이 취소되었습니다.',
  not_configured: '카카오 로그인이 설정되지 않았습니다. (관리자 문의)',
  not_allowed:    '허가되지 않은 카카오 계정입니다.',
  token_failed:   '카카오 인증 토큰 발급 실패.',
  network_error:  '카카오 서버 연결 실패.',
}

export default function AdminAuth({ onLogin, waking }: AdminAuthProps) {
  const [pw, setPw] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [wakeSecs, setWakeSecs] = useState(0)

  // waking 중 경과 초 카운터
  useEffect(() => {
    if (!loading || !waking) { setWakeSecs(0); return }
    const t = setInterval(() => setWakeSecs(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [loading, waking])

  // URL의 kakao_error 파라미터 자동 처리
  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const kakaoErr = params.get('kakao_error')
    if (kakaoErr) {
      window.history.replaceState({}, '', window.location.pathname)
      setError(KAKAO_ERROR_MSGS[kakaoErr] || '카카오 로그인 오류가 발생했습니다.')
    }
  }, [])

  const handleLogin = async () => {
    if (!pw.trim()) { setError('비밀번호를 입력하세요.'); return }
    setLoading(true)
    setError(null)
    const err = await onLogin(pw)
    if (err) setError(err)
    setLoading(false)
  }

  const handleKakaoLogin = () => {
    window.location.href = `${API_URL}/api/admin/kakao/login`
  }

  return (
    <div className="max-w-sm mx-auto mt-32 space-y-6 text-center">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">관리자 인증</h1>
        <p className="text-gray-500 text-sm mt-1">관리자 비밀번호를 입력하세요</p>
      </div>
      <div className="space-y-3">
        <input
          type="password"
          className="input text-center w-full"
          placeholder="비밀번호"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleLogin() }}
          disabled={loading}
        />
        <button
          type="button"
          className="btn-primary w-full"
          onClick={handleLogin}
          disabled={loading}
        >
          {loading ? (waking ? '서버 깨우는 중...' : '로그인 중...') : '접속'}
        </button>

        {/* 구분선 */}
        <div className="flex items-center gap-3 my-1">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-xs text-gray-400">또는</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>

        {/* 카카오 로그인 버튼 */}
        <button
          type="button"
          onClick={handleKakaoLogin}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-medium text-[14px] text-[#191919] disabled:opacity-50 transition-opacity"
          style={{ backgroundColor: '#FEE500' }}
        >
          {/* 카카오 말풍선 아이콘 (SVG inline) */}
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path fillRule="evenodd" clipRule="evenodd" d="M9 1C4.582 1 1 3.91 1 7.5c0 2.332 1.476 4.38 3.71 5.558L3.86 16.14a.25.25 0 0 0 .366.285L8.19 13.97A9.47 9.47 0 0 0 9 14c4.418 0 8-2.91 8-6.5S13.418 1 9 1z" fill="#191919"/>
          </svg>
          카카오로 로그인
        </button>

        {error && <p className="text-red-500 text-sm">{error}</p>}
        {waking && (
          <div className="space-y-1.5">
            <p className="text-amber-500 text-sm">
              서버 기동 중... ({wakeSecs}초 / 최대 60초)
            </p>
            <div className="w-full h-1.5 bg-amber-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-400 rounded-full transition-all duration-1000"
                style={{ width: `${Math.min((wakeSecs / 60) * 100, 98)}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
