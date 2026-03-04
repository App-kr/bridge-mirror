'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

/**
 * EditModeBar — 관리자 로그인 시 페이지 상단에 노란 바 표시
 * 쿠키 'bridge_admin' 존재 시 편집 모드 활성화
 */
export function useEditMode(): boolean {
  const [editMode, setEditMode] = useState(false)

  useEffect(() => {
    // 쿠키에서 bridge_admin 확인
    const hasCookie = document.cookie.split(';').some((c) =>
      c.trim().startsWith('bridge_admin=')
    )
    // URL 파라미터 ?edit=true 확인
    const params = new URLSearchParams(window.location.search)
    const hasParam = params.get('edit') === 'true'

    setEditMode(hasCookie || hasParam)
  }, [])

  return editMode
}

export default function EditModeBar() {
  const editMode = useEditMode()

  if (!editMode) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-[9999] bg-[#FFC107] text-[#1d1d1f] text-xs font-medium py-1.5 px-4 flex items-center justify-between shadow-sm">
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-[#1d1d1f] animate-pulse" />
        <span>관리자 모드</span>
      </div>
      <Link
        href="/admin"
        className="text-[#1d1d1f] hover:underline font-semibold"
      >
        Admin Panel →
      </Link>
    </div>
  )
}

/** 게시물 수정 버튼 — 편집 모드일 때만 표시 */
export function EditButton({ postId, board }: { postId: number; board?: string }) {
  const editMode = useEditMode()
  if (!editMode) return null

  return (
    <Link
      href={`/admin?tab=community&edit=${postId}${board ? `&board=${board}` : ''}`}
      className="inline-flex items-center gap-1 px-3 py-1.5 bg-[#FFC107] text-[#1d1d1f] text-xs font-medium rounded-full hover:bg-[#FFB300] transition-colors"
    >
      ✏️ 수정
    </Link>
  )
}

/** 새 게시물 버튼 — 편집 모드일 때만 표시 */
export function NewPostButton({ board }: { board: string }) {
  const editMode = useEditMode()
  if (!editMode) return null

  return (
    <Link
      href={`/community/${board}/new`}
      className="inline-flex items-center gap-1 px-4 py-2 bg-[#0071e3] text-white text-sm font-medium rounded-full hover:bg-[#0077ED] transition-colors"
    >
      + 새 게시물
    </Link>
  )
}
