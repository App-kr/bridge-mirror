'use client'

import { useEffect, useRef, useState } from 'react'
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
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const [mounted, setMounted] = useState(false)
  const dragging = useRef(false)
  const offset = useRef({ x: 0, y: 0 })
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setPos({ x: window.innerWidth - 180, y: Math.floor(window.innerHeight / 2) })
    setMounted(true)
  }, [])

  const onMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).tagName === 'BUTTON') return
    dragging.current = true
    offset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y }
    e.preventDefault()
  }

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return
      setPos({ x: e.clientX - offset.current.x, y: e.clientY - offset.current.y })
    }
    const onUp = () => { dragging.current = false }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [])

  if (!editMode || !mounted) return null

  const exit = () => {
    document.cookie = 'bridge_edit_mode=; path=/; max-age=0'
    window.location.reload()
  }

  return (
    <div
      ref={ref}
      onMouseDown={onMouseDown}
      style={{
        position: 'fixed',
        left: pos.x,
        top: pos.y,
        zIndex: 9999,
        background: 'rgba(239, 68, 68, 0.08)',
        border: '1.5px solid rgba(239, 68, 68, 0.5)',
        borderRadius: '12px',
        padding: '8px 12px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '6px',
        fontSize: '11px',
        fontWeight: 600,
        color: '#dc2626',
        cursor: 'grab',
        userSelect: 'none',
        backdropFilter: 'blur(8px)',
        boxShadow: '0 2px 12px rgba(239,68,68,0.15)',
        minWidth: '80px',
      }}
    >
      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        <Wrench size={11} /> ADMIN
      </span>
      <button onClick={exit} type="button" style={{
        background: 'rgba(239,68,68,0.15)',
        border: '1px solid rgba(239,68,68,0.4)',
        borderRadius: '6px',
        padding: '3px 10px',
        cursor: 'pointer',
        fontSize: '11px',
        fontWeight: 600,
        color: '#dc2626',
        width: '100%',
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
