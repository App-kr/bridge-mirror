'use client'

/**
 * /admin/diagnose — 영속성 진단 + 응급 복구
 * "값이 사라진다" 호소 시 한 번 클릭으로 원인 파악 + 자동 복구
 */

import { useCallback, useEffect, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

interface DiagData {
  timestamp: string
  render_env: {
    DRIVE_OAUTH_TOKEN_JSON_set: boolean
    DRIVE_OAUTH_TOKEN_JSON_len: number
    GCP_SA_JSON_B64_set: boolean
    ADMIN_API_KEY_set: boolean
    BRIDGE_FIELD_KEY_set: boolean
    DB_PATH: string
  }
  db: Record<string, number | string>
  drive_backups: Array<{ name: string; size_kb: number; created: string }>
  drive_error?: string
  db_error?: string
  auto_restore_capable: boolean
  recommended_action: string
}

export default function DiagnosePage() {
  const { authed, headers } = useAdminAuth()
  const [data, setData] = useState<DiagData | null>(null)
  const [loading, setLoading] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [error, setError] = useState('')
  const [restoreResult, setRestoreResult] = useState('')

  const fetchDiag = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const r = await fetch(`${API}/api/admin/diag/persistence`, {
        headers: headers(),
        cache: 'no-store',
      })
      const j = await r.json()
      if (!r.ok) throw new Error(j?.error?.message || `HTTP ${r.status}`)
      setData(j.data || j)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [headers])

  const triggerRestore = useCallback(async () => {
    if (!confirm('Drive에서 master.db를 복원합니다. 현재 DB는 백업됩니다. 계속할까요?')) return
    setRestoring(true)
    setRestoreResult('')
    try {
      const r = await fetch(`${API}/api/admin/diag/auto-restore`, {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
      })
      const j = await r.json()
      if (!r.ok) throw new Error(j?.error?.message || `HTTP ${r.status}`)
      setRestoreResult(`✅ 복원 완료: ${JSON.stringify(j.data?.counts || {})}`)
      fetchDiag()
    } catch (e) {
      setRestoreResult(`❌ ${e}`)
    } finally {
      setRestoring(false)
    }
  }, [fetchDiag, headers])

  useEffect(() => {
    if (authed) fetchDiag()
  }, [authed, fetchDiag])

  if (!authed) return (
    <div className="p-8">
      <p>관리자 로그인이 필요합니다. /admin 페이지에서 먼저 로그인해 주세요.</p>
    </div>
  )

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">영속성 진단 + 응급 복구</h1>
        <button
          onClick={fetchDiag}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          {loading ? '진단 중...' : '새로고침'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-300 text-red-800 rounded">
          ❌ {error}
        </div>
      )}

      {data && (
        <>
          {/* 권장 조치 */}
          <div className={`mb-6 p-4 rounded border ${
            data.recommended_action.startsWith('🚨') ? 'bg-red-50 border-red-300' :
            data.recommended_action.startsWith('🔄') ? 'bg-amber-50 border-amber-300' :
            data.recommended_action.startsWith('⚠️') ? 'bg-yellow-50 border-yellow-300' :
            'bg-green-50 border-green-300'
          }`}>
            <div className="font-bold mb-1">권장 조치</div>
            <div>{data.recommended_action}</div>
          </div>

          {/* 응급 복구 */}
          {data.auto_restore_capable && (
            <div className="mb-6 p-4 border-2 border-blue-500 rounded">
              <h2 className="font-bold mb-2">응급 복구 — Drive에서 master.db 즉시 복원</h2>
              <button
                onClick={triggerRestore}
                disabled={restoring}
                className="px-6 py-3 bg-blue-600 text-white rounded font-bold disabled:opacity-50"
              >
                {restoring ? '복원 중...' : '🔄 Drive에서 즉시 복원'}
              </button>
              {restoreResult && (
                <div className="mt-3 p-2 bg-gray-50 font-mono text-sm">{restoreResult}</div>
              )}
            </div>
          )}

          {/* DB 카운트 */}
          <div className="mb-6 p-4 border rounded">
            <h2 className="font-bold mb-2">DB 테이블 카운트</h2>
            <table className="w-full text-sm">
              <tbody>
                {Object.entries(data.db).map(([k, v]) => (
                  <tr key={k} className="border-b">
                    <td className="py-1 font-mono">{k}</td>
                    <td className="py-1 text-right">
                      {typeof v === 'number' ? v.toLocaleString() : v}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.db_error && (
              <div className="mt-2 text-red-600 text-sm">DB 오류: {data.db_error}</div>
            )}
          </div>

          {/* Render 환경변수 */}
          <div className="mb-6 p-4 border rounded">
            <h2 className="font-bold mb-2">Render 환경변수 상태</h2>
            <table className="w-full text-sm">
              <tbody>
                {Object.entries(data.render_env).map(([k, v]) => (
                  <tr key={k} className="border-b">
                    <td className="py-1 font-mono">{k}</td>
                    <td className="py-1 text-right">
                      {typeof v === 'boolean' ? (
                        v ? <span className="text-green-600">✅ 설정됨</span> : <span className="text-red-600">❌ 미설정</span>
                      ) : v}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data.render_env.DRIVE_OAUTH_TOKEN_JSON_set && (
              <div className="mt-3 p-3 bg-red-50 border border-red-300 rounded text-sm">
                <strong>🚨 DRIVE_OAUTH_TOKEN_JSON 미설정</strong>
                <p className="mt-1">자동 복원이 작동하지 않습니다. Render Dashboard → Environment → Add Variable로 등록 필요.</p>
              </div>
            )}
          </div>

          {/* Drive 백업 목록 */}
          {data.drive_backups.length > 0 && (
            <div className="mb-6 p-4 border rounded">
              <h2 className="font-bold mb-2">Drive 백업 (최신 5건)</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="py-1 text-left">파일명</th>
                    <th className="py-1 text-right">크기</th>
                    <th className="py-1 text-right">생성</th>
                  </tr>
                </thead>
                <tbody>
                  {data.drive_backups.map((b, i) => (
                    <tr key={i} className="border-b">
                      <td className="py-1 font-mono text-xs">{b.name}</td>
                      <td className="py-1 text-right">{b.size_kb.toLocaleString()} KB</td>
                      <td className="py-1 text-right text-xs">{b.created}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data.drive_error && (
            <div className="p-3 bg-red-50 border border-red-300 rounded text-sm">
              Drive 오류: {data.drive_error}
            </div>
          )}

          <div className="text-xs text-gray-500 mt-4">진단 시각: {data.timestamp}</div>
        </>
      )}
    </div>
  )
}
