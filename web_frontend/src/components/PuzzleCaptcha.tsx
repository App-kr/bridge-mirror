'use client'

import { useState, useRef, useEffect, useCallback } from 'react'

interface Piece {
  x: number
  y: number
  targetX: number
  targetY: number
  color: string
  label: string
}

interface PuzzleCaptchaProps {
  onVerified: (token: string) => void
  onError?: (error: string) => void
}

const CW = 420
const CH = 280
const PW = 68
const PH = 68
const TARGETS: { x: number; y: number }[] = [
  { x: 50, y: 104 },
  { x: 176, y: 104 },
  { x: 302, y: 104 },
]
const PIECE_COLORS = ['#e74c3c', '#27ae60', '#2980b9']
const INIT_POSITIONS = [
  { x: 20, y: 195 },
  { x: 170, y: 185 },
  { x: 315, y: 198 },
]

export default function PuzzleCaptcha({ onVerified }: PuzzleCaptchaProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isVerified, setIsVerified] = useState(false)
  const piecesRef = useRef<Piece[]>([])
  const dragRef = useRef<{ idx: number; ox: number; oy: number } | null>(null)

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 배경 그라디언트
    const bg = ctx.createLinearGradient(0, 0, CW, CH)
    bg.addColorStop(0, '#667eea')
    bg.addColorStop(1, '#764ba2')
    ctx.fillStyle = bg
    ctx.fillRect(0, 0, CW, CH)

    // 안내 텍스트
    ctx.fillStyle = 'rgba(255,255,255,0.75)'
    ctx.font = '13px Arial'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('아래 색상 블록을 같은 번호의 빈칸에 끌어다 놓으세요', CW / 2, 82)

    // 타겟 홀 (점선 박스)
    TARGETS.forEach((t, i) => {
      ctx.save()
      ctx.setLineDash([5, 4])
      ctx.strokeStyle = 'rgba(255,255,255,0.7)'
      ctx.lineWidth = 2
      ctx.strokeRect(t.x, t.y, PW, PH)
      ctx.restore()

      ctx.fillStyle = 'rgba(0,0,0,0.18)'
      ctx.fillRect(t.x, t.y, PW, PH)

      // 번호
      ctx.fillStyle = 'rgba(255,255,255,0.45)'
      ctx.font = 'bold 22px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(String(i + 1), t.x + PW / 2, t.y + PH / 2)
    })

    // 구분선
    ctx.strokeStyle = 'rgba(255,255,255,0.25)'
    ctx.lineWidth = 1
    ctx.setLineDash([])
    ctx.beginPath()
    ctx.moveTo(10, 185)
    ctx.lineTo(CW - 10, 185)
    ctx.stroke()

    // 조각 그리기 (드래그 중인 것은 맨 위)
    const pieces = piecesRef.current
    const dragIdx = dragRef.current?.idx ?? -1
    const drawOrder = [...pieces.keys()].filter((i) => i !== dragIdx)
    if (dragIdx !== -1) drawOrder.push(dragIdx)

    drawOrder.forEach((i) => {
      const p = pieces[i]
      const dragging = i === dragIdx

      ctx.save()
      if (dragging) {
        ctx.shadowColor = 'rgba(0,0,0,0.45)'
        ctx.shadowBlur = 12
      }

      // 조각 배경 (roundRect 폴백 — arcTo로 구형 Safari 대응)
      const r = 6
      ctx.fillStyle = p.color
      ctx.beginPath()
      ctx.moveTo(p.x + r, p.y)
      ctx.lineTo(p.x + PW - r, p.y)
      ctx.arcTo(p.x + PW, p.y, p.x + PW, p.y + r, r)
      ctx.lineTo(p.x + PW, p.y + PH - r)
      ctx.arcTo(p.x + PW, p.y + PH, p.x + PW - r, p.y + PH, r)
      ctx.lineTo(p.x + r, p.y + PH)
      ctx.arcTo(p.x, p.y + PH, p.x, p.y + PH - r, r)
      ctx.lineTo(p.x, p.y + r)
      ctx.arcTo(p.x, p.y, p.x + r, p.y, r)
      ctx.closePath()
      ctx.fill()

      // 조각 테두리
      ctx.strokeStyle = dragging ? '#fff' : 'rgba(255,255,255,0.55)'
      ctx.lineWidth = dragging ? 3 : 1.5
      ctx.setLineDash([])
      ctx.stroke()

      // 번호
      ctx.fillStyle = 'white'
      ctx.font = 'bold 26px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(p.label, p.x + PW / 2, p.y + PH / 2)

      ctx.restore()
    })
  }, [])

  useEffect(() => {
    piecesRef.current = TARGETS.map((t, i) => ({
      x: INIT_POSITIONS[i].x,
      y: INIT_POSITIONS[i].y,
      targetX: t.x,
      targetY: t.y,
      color: PIECE_COLORS[i],
      label: String(i + 1),
    }))
    draw()
  }, [draw])

  const getXY = (
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
    canvas: HTMLCanvasElement
  ) => {
    const rect = canvas.getBoundingClientRect()
    const sx = CW / rect.width
    const sy = CH / rect.height
    if ('touches' in e) {
      return {
        x: (e.touches[0].clientX - rect.left) * sx,
        y: (e.touches[0].clientY - rect.top) * sy,
      }
    }
    return {
      x: (e.clientX - rect.left) * sx,
      y: (e.clientY - rect.top) * sy,
    }
  }

  const hitTest = (x: number, y: number) => {
    const pieces = piecesRef.current
    for (let i = pieces.length - 1; i >= 0; i--) {
      const p = pieces[i]
      if (x >= p.x && x <= p.x + PW && y >= p.y && y <= p.y + PH) return i
    }
    return -1
  }

  const onDown = (
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>
  ) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const { x, y } = getXY(e, canvas)
    const idx = hitTest(x, y)
    if (idx === -1) return
    const p = piecesRef.current[idx]
    dragRef.current = { idx, ox: x - p.x, oy: y - p.y }
    draw()
  }

  const onMove = (
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>
  ) => {
    if (!dragRef.current) return
    e.preventDefault()
    const canvas = canvasRef.current
    if (!canvas) return
    const { x, y } = getXY(e, canvas)
    const { idx, ox, oy } = dragRef.current
    const pieces = piecesRef.current
    pieces[idx] = {
      ...pieces[idx],
      x: Math.max(0, Math.min(CW - PW, x - ox)),
      y: Math.max(0, Math.min(CH - PH, y - oy)),
    }
    draw()
  }

  const onUp = () => {
    if (!dragRef.current) return
    dragRef.current = null
    const TOL = 22
    const allCorrect = piecesRef.current.every(
      (p) =>
        Math.abs(p.x - p.targetX) <= TOL && Math.abs(p.y - p.targetY) <= TOL
    )
    if (allCorrect) {
      // 조각을 정확한 위치에 스냅
      piecesRef.current = piecesRef.current.map((p) => ({
        ...p,
        x: p.targetX,
        y: p.targetY,
      }))
      draw()
      setIsVerified(true)
      const token = `puzzle_${Date.now()}_${Math.random().toString(36).substring(7)}`
      onVerified(token)
      // 성공 오버레이
      setTimeout(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        ctx.fillStyle = 'rgba(0,0,0,0.65)'
        ctx.fillRect(0, 0, CW, CH)
        ctx.fillStyle = '#4caf50'
        ctx.font = 'bold 34px Arial'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText('✓ Verified!', CW / 2, CH / 2)
      }, 50)
    } else {
      draw()
    }
  }

  return (
    <div className="my-6 p-4 border border-gray-300 rounded-lg bg-white">
      <label className="block text-sm font-medium text-gray-700 mb-3">
        🧩 Puzzle CAPTCHA — Drag pieces to complete the puzzle
      </label>

      <canvas
        ref={canvasRef}
        width={CW}
        height={CH}
        onMouseDown={onDown}
        onMouseMove={onMove}
        onMouseUp={onUp}
        onMouseLeave={onUp}
        onTouchStart={onDown}
        onTouchMove={onMove}
        onTouchEnd={onUp}
        className="border-2 border-gray-400 rounded-lg cursor-grab active:cursor-grabbing w-full max-w-md mx-auto block"
        style={{ touchAction: 'none', userSelect: 'none' }}
      />

      {isVerified ? (
        <div className="mt-3 p-2 bg-green-100 border border-green-400 text-green-700 rounded text-center text-sm">
          ✓ CAPTCHA verified successfully
        </div>
      ) : (
        <div className="mt-3 p-2 bg-blue-100 border border-blue-400 text-blue-700 rounded text-center text-sm">
          👆 Drag all 3 pieces to their correct positions to continue
        </div>
      )}

      <input
        type="hidden"
        name="captcha_token"
        value={
          isVerified
            ? `puzzle_${Date.now()}_${Math.random().toString(36).substring(7)}`
            : ''
        }
      />
    </div>
  )
}
