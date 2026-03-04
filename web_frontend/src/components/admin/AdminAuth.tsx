'use client'

import { useState } from 'react'

interface AdminAuthProps {
  onLogin: (password: string) => Promise<string | null>
  waking?: boolean
}

export default function AdminAuth({ onLogin, waking }: AdminAuthProps) {
  const [pw, setPw] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    if (!pw.trim()) { setError('비밀번호를 입력하세요.'); return }
    setLoading(true)
    setError(null)
    const err = await onLogin(pw)
    if (err) setError(err)
    setLoading(false)
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
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleLogin()
          }}
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
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {waking && <p className="text-amber-500 text-sm animate-pulse">Render 서버를 깨우고 있습니다. 잠시만 기다려주세요...</p>}
      </div>
    </div>
  )
}
