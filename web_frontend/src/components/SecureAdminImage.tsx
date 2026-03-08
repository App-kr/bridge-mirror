'use client'

/**
 * SecureAdminImage — 관리자 전용 보안 이미지 컴포넌트
 *
 * 동작 원리:
 *   1. /api/files/ 엔드포인트에 x-admin-key 헤더로 파일 요청
 *   2. 응답 blob → objectURL 생성 → <img src={blobUrl}> 표시
 *   3. 403 응답 시 블랙스크린 오버레이 표시 + 우클릭 차단
 *   4. 컴포넌트 언마운트 시 objectURL 자동 해제
 *
 * 사용법:
 *   <SecureAdminImage
 *     fileUrl="/uploads/candidates/cnd_xxx/photo.jpg"
 *     adminKey={adminKey}
 *     apiBase="https://bridge-n7hk.onrender.com"
 *     width={38} height={38}
 *     className="rounded-full object-cover"
 *   />
 */

import { useEffect, useRef, useState, CSSProperties } from 'react'
import { API_URL } from '@/lib/api'

interface SecureAdminImageProps {
  fileUrl: string            // /uploads/... 경로 또는 절대 URL
  adminKey: string
  apiBase?: string
  width?: number | string
  height?: number | string
  className?: string
  style?: CSSProperties
  alt?: string
  fallback?: React.ReactNode // 로딩 실패 시 대체 렌더링
  onError?: () => void
}

// /uploads/candidates/cnd_xxx/photo.jpg → candidates/cnd_xxx/photo.jpg
function toRelPath(url: string): string {
  if (!url) return ''
  // 절대 URL에서 /uploads/ 이후 추출
  const m = url.match(/\/uploads\/(.+)/)
  return m ? m[1] : ''
}

// rel_path → /api/files/{rel_path}
function toFileApiPath(relPath: string, apiBase: string): string {
  return `${apiBase}/api/files/${relPath}`
}

export default function SecureAdminImage({
  fileUrl,
  adminKey,
  apiBase = API_URL,
  width = 38,
  height = 38,
  className = '',
  style,
  alt = '',
  fallback,
  onError,
}: SecureAdminImageProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [status, setStatus] = useState<'loading' | 'ok' | 'error' | 'forbidden'>('loading')
  const prevBlobUrl = useRef<string | null>(null)

  useEffect(() => {
    if (!fileUrl || !adminKey) {
      setStatus('error')
      return
    }

    const relPath = toRelPath(fileUrl)
    if (!relPath) {
      // 외부 URL인 경우 직접 사용 (서명 불필요)
      setBlobUrl(fileUrl)
      setStatus('ok')
      return
    }

    let cancelled = false
    setStatus('loading')

    const fetchFile = async () => {
      try {
        const res = await fetch(toFileApiPath(relPath, apiBase), {
          headers: { 'x-admin-key': adminKey },
          cache: 'no-store',
        })

        if (cancelled) return

        if (res.status === 403) {
          setStatus('forbidden')
          onError?.()
          return
        }
        if (!res.ok) {
          setStatus('error')
          onError?.()
          return
        }

        const blob = await res.blob()
        if (cancelled) return

        // 이전 objectURL 해제
        if (prevBlobUrl.current) {
          URL.revokeObjectURL(prevBlobUrl.current)
        }
        const url = URL.createObjectURL(blob)
        prevBlobUrl.current = url
        setBlobUrl(url)
        setStatus('ok')
      } catch {
        if (!cancelled) {
          setStatus('error')
          onError?.()
        }
      }
    }

    fetchFile()
    return () => {
      cancelled = true
    }
  }, [fileUrl, adminKey, apiBase, onError])

  // 컴포넌트 언마운트 시 objectURL 정리
  useEffect(() => {
    return () => {
      if (prevBlobUrl.current) {
        URL.revokeObjectURL(prevBlobUrl.current)
      }
    }
  }, [])

  const sizeStyle: CSSProperties = {
    width,
    height,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    ...style,
  }

  // 403 — 블랙스크린 오버레이
  if (status === 'forbidden') {
    return (
      <div
        style={{ ...sizeStyle, background: '#000', borderRadius: 4, position: 'relative', overflow: 'hidden' }}
        className={className}
        onContextMenu={(e) => e.preventDefault()}
        title="파일 접근 권한 없음"
      >
        <span style={{ color: '#ff4444', fontSize: 10, fontWeight: 700, textAlign: 'center', lineHeight: 1.2, padding: 2 }}>
          🔒
        </span>
      </div>
    )
  }

  // 로딩 중
  if (status === 'loading') {
    return (
      <div
        style={{ ...sizeStyle, background: '#e5e7eb', borderRadius: 4, animation: 'pulse 1.5s infinite' }}
        className={className}
      />
    )
  }

  // 오류
  if (status === 'error' || !blobUrl) {
    return fallback ? (
      <>{fallback}</>
    ) : (
      <div
        style={{ ...sizeStyle, background: '#f3f4f6', borderRadius: 4 }}
        className={className}
      />
    )
  }

  // 성공 — 우클릭 차단 + drag 금지
  return (
    <img
      src={blobUrl}
      alt={alt}
      width={typeof width === 'number' ? width : undefined}
      height={typeof height === 'number' ? height : undefined}
      className={className}
      style={style}
      onContextMenu={(e) => e.preventDefault()}
      draggable={false}
      onDragStart={(e) => e.preventDefault()}
    />
  )
}
