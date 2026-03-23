'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { Wrench, Pencil, ArrowUpDown, LogOut } from 'lucide-react'

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
  const [saveMsg, setSaveMsg] = useState<string | null>(null)
  const dragging = useRef(false)
  const offset = useRef({ x: 0, y: 0 })
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // 우측 중앙, 팝업 너비(320px) 감안해 배치
    setPos({ x: window.innerWidth - 340, y: Math.floor(window.innerHeight / 2) - 20 })
    setMounted(true)
  }, [])

  const onMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return
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
    document.cookie = 'bridge_edit_mode=; path=/; max-age=0; SameSite=Strict'
    window.location.reload()
  }

  const saveOrder = () => {
    // 현재 페이지의 순서 저장 이벤트 발행 — 각 페이지에서 bridge:saveOrder 이벤트 수신 후 처리
    const handled = document.dispatchEvent(new CustomEvent('bridge:saveOrder', { cancelable: true }))
    if (!handled) {
      setSaveMsg('저장 완료')
    } else {
      setSaveMsg('저장 중...')
    }
    setTimeout(() => setSaveMsg(null), 2000)
  }

  const btnBase: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    border: '1.5px solid rgba(220,38,38,0.5)',
    borderRadius: '7px',
    padding: '5px 12px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 700,
    whiteSpace: 'nowrap',
    transition: 'background 0.15s',
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
        background: 'rgba(220, 38, 38, 0.11)',
        border: '2px solid #dc2626',
        borderRadius: '12px',
        padding: '9px 14px',
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: '10px',
        cursor: 'grab',
        userSelect: 'none',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 0 0 1px rgba(239,68,68,0.25), 0 4px 24px rgba(220,38,38,0.28)',
        minWidth: '300px',
      }}
    >
      {/* 라벨 */}
      <span style={{
        display: 'flex',
        alignItems: 'center',
        gap: '5px',
        fontSize: '13px',
        fontWeight: 800,
        color: '#dc2626',
        letterSpacing: '0.02em',
        whiteSpace: 'nowrap',
      }}>
        <Wrench size={14} />
        ADMIN 편집모드
      </span>

      {/* 구분선 */}
      <div style={{ width: 1, height: 22, background: 'rgba(220,38,38,0.35)', flexShrink: 0 }} />

      {/* 순서 저장 버튼 */}
      <button
        onClick={saveOrder}
        type="button"
        style={{
          ...btnBase,
          background: saveMsg ? 'rgba(220,38,38,0.22)' : 'rgba(220,38,38,0.10)',
          color: '#dc2626',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(220,38,38,0.22)' }}
        onMouseLeave={(e) => { e.currentTarget.style.background = saveMsg ? 'rgba(220,38,38,0.22)' : 'rgba(220,38,38,0.10)' }}
        title="현재 페이지 게시물 순서를 저장합니다"
      >
        <ArrowUpDown size={12} />
        {saveMsg ?? '순서 저장'}
      </button>

      {/* Exit 버튼 */}
      <button
        onClick={exit}
        type="button"
        style={{
          ...btnBase,
          background: 'rgba(220,38,38,0.10)',
          color: '#dc2626',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(220,38,38,0.22)' }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(220,38,38,0.10)' }}
        title="편집모드 종료"
      >
        <LogOut size={12} />
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

/** Section-level edit button — shows a small labeled edit link in edit mode */
export function SectionEditLink({ href, label, dark }: { href: string; label: string; dark?: boolean }) {
  const editMode = useEditMode()
  if (!editMode) return null

  const bg = dark
    ? 'bg-amber-500/90 hover:bg-amber-600 text-white'
    : 'bg-amber-500/90 hover:bg-amber-600 text-white'

  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded-lg transition-colors shadow-lg ${bg}`}
      onClick={(e) => e.stopPropagation()}
    >
      <Pencil size={11} />
      {label}
    </Link>
  )
}
