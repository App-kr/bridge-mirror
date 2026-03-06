'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Wrench, Pencil } from 'lucide-react'

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
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 9999,
      background: 'linear-gradient(90deg, #fef3c7, #fde68a)',
      borderTop: '2px solid #f59e0b',
      padding: '10px 24px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      fontSize: '14px',
      fontWeight: 500,
      color: '#92400e',
      boxShadow: '0 -2px 12px rgba(0,0,0,0.12)',
    }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Wrench size={14} /> Admin Mode — inline edit/delete available
      </span>
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
        Exit
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
        padding: '2px 6px',
        borderRadius: '4px',
        marginLeft: '8px',
        opacity: 0.7,
        display: 'inline-flex',
        alignItems: 'center',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.opacity = '1' }}
      onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.7' }}
      title="Edit"
    >
      <Pencil size={16} />
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
      + New Post
    </Link>
  )
}
