'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

export function useEditMode(): boolean {
  const [editMode, setEditMode] = useState(false)

  useEffect(() => {
    setEditMode(document.cookie.includes('bridge_edit_mode=true'))
  }, [])

  return editMode
}

export default function EditModeBar() {
  const editMode = useEditMode()

  if (!editMode) return null

  const exit = () => {
    document.cookie = 'bridge_edit_mode=; path=/; max-age=0'
    window.location.reload()
  }

  return (
    <div style={{
      position: 'sticky',
      top: 0,
      zIndex: 9999,
      background: 'linear-gradient(90deg, #fef3c7, #fde68a)',
      borderBottom: '2px solid #f59e0b',
      padding: '10px 24px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      fontSize: '14px',
      fontWeight: 500,
      color: '#92400e',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    }}>
      <span>🔧 관리자 모드 — 게시물 제목 옆 ✏️ 를 클릭하여 편집</span>
      <button onClick={exit} type="button" style={{
        background: '#fff',
        border: '1px solid #d1d5db',
        borderRadius: '6px',
        padding: '6px 16px',
        cursor: 'pointer',
        fontSize: '13px',
        fontWeight: 600,
        color: '#374151',
      }}>
        편집 종료
      </button>
    </div>
  )
}

export function EditButton({ postId, board }: { postId: number | string; board?: string }) {
  const editMode = useEditMode()
  if (!editMode) return null

  return (
    <button
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        window.open(`/admin/posts?edit=${postId}${board ? `&board=${board}` : ''}`, '_blank')
      }}
      type="button"
      style={{
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        fontSize: '16px',
        padding: '2px 6px',
        borderRadius: '4px',
        marginLeft: '8px',
        opacity: 0.7,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.opacity = '1' }}
      onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.7' }}
      title="편집"
    >
      ✏️
    </button>
  )
}

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
