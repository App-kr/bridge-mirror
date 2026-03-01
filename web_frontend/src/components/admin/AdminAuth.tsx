'use client'

import { useState } from 'react'

interface AdminAuthProps {
  onLogin: (key: string) => void
  error?: string | null
}

export default function AdminAuth({ onLogin, error }: AdminAuthProps) {
  const [keyInput, setKeyInput] = useState('')

  return (
    <div className="max-w-sm mx-auto mt-32 space-y-6 text-center">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">관리자 인증</h1>
        <p className="text-gray-500 text-sm mt-1">ADMIN_API_KEY를 입력하세요</p>
      </div>
      <div className="space-y-3">
        <input
          type="password"
          className="input text-center w-full"
          placeholder="Admin key"
          value={keyInput}
          onChange={(e) => setKeyInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onLogin(keyInput)
          }}
        />
        <button
          type="button"
          className="btn-primary w-full"
          onClick={() => onLogin(keyInput)}
        >
          접속
        </button>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <p className="text-xs text-gray-400">
          ADMIN_API_KEY 미설정 시 빈 채로 접속
        </p>
      </div>
    </div>
  )
}
