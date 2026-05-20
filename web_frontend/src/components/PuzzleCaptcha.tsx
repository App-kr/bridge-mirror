'use client'

import { useState, useRef, useEffect, useCallback } from 'react'

// ── Constants ────────────────────────────────────────────────────────────────
const CW = 420
const CH = 260

type CaptchaType = 'slide' | 'rotate' | 'order'

interface PuzzleCaptchaProps {
  onVerified: (token: string) => void
  onError?: (error: string) => void
}

function genToken() {
  return `puzzle_${Date.now()}_${Math.random().toString(36).substring(7)}`
}

function rnd(min: number, max: number) {
  return Math.floor(Math.random() * (max - min)) + min
}

// rounded rect via arcTo (universal browser support)
function rrect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number
) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.arcTo(x + w, y, x + w, y + r, r)
  ctx.lineTo(x + w, y + h - r)
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r)
  ctx.lineTo(x + r, y + h)
  ctx.arcTo(x, y + h, x, y + h - r, r)
  ctx.lineTo(x, y + r)
  ctx.arcTo(x, y, x + r, y, r)
  ctx.closePath()
}

// ── TYPE A: SLIDE ─────────────────────────────────────────────────────────────
interface SlideState {
  pieceX: number      // current x of sliding piece
  targetX: number     // x where hole is
  targetY: number     // y of hole
  PW: number          // piece width
  PH: number          // piece height
  bgSnap: ImageData | null
  dragging: boolean
  startMX: number
  startPX: number
}

function initSlide(): SlideState {
  return {
    pieceX: 12,
    targetX: rnd(150, 320),
    targetY: rnd(60, 140),
    PW: 64,
    PH: 64,
    bgSnap: null,
    dragging: false,
    startMX: 0,
    startPX: 0,
  }
}

function drawSlide(ctx: CanvasRenderingContext2D, s: SlideState) {
  // Background gradient
  const bg = ctx.createLinearGradient(0, 0, CW, CH)
  bg.addColorStop(0, '#4158D0')
  bg.addColorStop(0.46, '#C850C0')
  bg.addColorStop(1, '#FFCC70')
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, CW, CH)

  // Decorative circles
  ;[
    [60, 55, 38], [340, 80, 50], [200, 30, 28],
    [310, 170, 40], [95, 160, 22], [160, 120, 18],
  ].forEach(([cx, cy, r]) => {
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(255,255,255,0.08)'
    ctx.fill()
  })

  // Instruction
  ctx.fillStyle = 'rgba(255,255,255,0.85)'
  ctx.font = '13px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  // 캔버스 내 안내 텍스트 제거 — 아래 HINT 영역만 사용 (사용자 요청)

  // Snapshot background at hole position (once)
  if (!s.bgSnap) {
    s.bgSnap = ctx.getImageData(s.targetX, s.targetY, s.PW, s.PH)
  }

  // Draw hole (dark cutout)
  ctx.fillStyle = 'rgba(0,0,0,0.45)'
  rrect(ctx, s.targetX, s.targetY, s.PW, s.PH, 6)
  ctx.fill()
  ctx.strokeStyle = 'rgba(255,255,255,0.6)'
  ctx.lineWidth = 1.5
  ctx.setLineDash([5, 4])
  ctx.stroke()
  ctx.setLineDash([])

  // Draw sliding piece (image extracted from hole area)
  if (s.bgSnap) {
    ctx.putImageData(s.bgSnap, s.pieceX, s.targetY)
  }
  rrect(ctx, s.pieceX, s.targetY, s.PW, s.PH, 6)
  ctx.strokeStyle = s.dragging ? '#fff' : 'rgba(255,255,255,0.7)'
  ctx.lineWidth = s.dragging ? 2.5 : 1.5
  ctx.setLineDash([])
  ctx.stroke()

  // Slide track bar (bottom)
  const trackY = CH - 40
  ctx.fillStyle = 'rgba(0,0,0,0.25)'
  rrect(ctx, 8, trackY, CW - 16, 30, 15)
  ctx.fill()

  // Track fill (progress)
  const progress = Math.max(0, s.pieceX - 8)
  if (progress > 0) {
    ctx.save()
    ctx.beginPath()
    rrect(ctx, 8, trackY, progress + s.PW * 0.5, 30, 15)
    ctx.clip()
    ctx.fillStyle = 'rgba(255,255,255,0.18)'
    ctx.fillRect(8, trackY, CW - 16, 30)
    ctx.restore()
  }

  // Track handle
  rrect(ctx, s.pieceX, trackY, s.PW, 30, 15)
  ctx.fillStyle = s.dragging
    ? 'rgba(255,255,255,0.95)'
    : 'rgba(255,255,255,0.80)'
  ctx.fill()
  ctx.fillStyle = '#555'
  ctx.font = 'bold 13px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('▶▶', s.pieceX + s.PW / 2, trackY + 15)
}

// ── TYPE B: ROTATE ────────────────────────────────────────────────────────────
interface RotateState {
  angle: number
  target: number
  dragging: boolean
  startMA: number   // start mouse angle
  startA: number    // start arrow angle
  cx: number
  cy: number
}

function initRotate(): RotateState {
  const target = (rnd(0, 8) * 45 * Math.PI) / 180
  return {
    angle: target + Math.PI * 0.6 + Math.random() * Math.PI,
    target,
    dragging: false,
    startMA: 0,
    startA: 0,
    cx: CW / 2,
    cy: CH / 2 + 5,
  }
}

function drawRotate(ctx: CanvasRenderingContext2D, s: RotateState) {
  // Dark bg
  ctx.fillStyle = '#0f172a'
  ctx.fillRect(0, 0, CW, CH)

  // Dot grid
  for (let x = 15; x < CW; x += 28) {
    for (let y = 15; y < CH; y += 28) {
      ctx.beginPath()
      ctx.arc(x, y, 1, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(255,255,255,0.05)'
      ctx.fill()
    }
  }

  const { cx, cy, angle, target } = s

  // Outer ring
  ctx.beginPath()
  ctx.arc(cx, cy, 88, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(255,255,255,0.1)'
  ctx.lineWidth = 1
  ctx.stroke()

  // Tick marks
  for (let i = 0; i < 8; i++) {
    const a = (i * Math.PI) / 4
    const r1 = 88, r2 = i % 2 === 0 ? 78 : 82
    ctx.beginPath()
    ctx.moveTo(cx + r1 * Math.cos(a), cy + r1 * Math.sin(a))
    ctx.lineTo(cx + r2 * Math.cos(a), cy + r2 * Math.sin(a))
    ctx.strokeStyle = 'rgba(255,255,255,0.3)'
    ctx.lineWidth = 1.5
    ctx.stroke()
  }

  // Ghost target arrow
  ctx.save()
  ctx.translate(cx, cy)
  ctx.rotate(target)
  ctx.beginPath()
  ctx.moveTo(0, -62); ctx.lineTo(12, -30)
  ctx.lineTo(5, -30); ctx.lineTo(5, 62)
  ctx.lineTo(-5, 62); ctx.lineTo(-5, -30)
  ctx.lineTo(-12, -30); ctx.closePath()
  ctx.fillStyle = 'rgba(255,255,255,0.10)'
  ctx.fill()
  ctx.restore()

  // Accuracy glow
  const diff = ((angle - target) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2)
  const norm = Math.min(diff, Math.PI * 2 - diff)
  const glow = Math.max(0, 1 - norm / 0.35)
  if (glow > 0) {
    ctx.save()
    ctx.beginPath()
    ctx.arc(cx, cy, 88, 0, Math.PI * 2)
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 88)
    g.addColorStop(0, `rgba(74,222,128,${glow * 0.25})`)
    g.addColorStop(1, `rgba(74,222,128,0)`)
    ctx.fillStyle = g
    ctx.fill()
    ctx.restore()
  }

  // Main arrow
  ctx.save()
  ctx.translate(cx, cy)
  ctx.rotate(angle)
  const ag = ctx.createLinearGradient(0, -70, 0, 70)
  ag.addColorStop(0, '#ef4444')
  ag.addColorStop(0.5, '#f97316')
  ag.addColorStop(1, '#3b82f6')
  ctx.beginPath()
  ctx.moveTo(0, -65); ctx.lineTo(14, -25)
  ctx.lineTo(6, -25); ctx.lineTo(6, 65)
  ctx.lineTo(-6, 65); ctx.lineTo(-6, -25)
  ctx.lineTo(-14, -25); ctx.closePath()
  ctx.fillStyle = ag
  ctx.fill()
  ctx.strokeStyle = 'rgba(255,255,255,0.35)'
  ctx.lineWidth = 1
  ctx.stroke()
  // Center hub
  ctx.beginPath()
  ctx.arc(0, 0, 9, 0, Math.PI * 2)
  ctx.fillStyle = '#fff'
  ctx.fill()
  ctx.restore()

  // Instruction
  ctx.fillStyle = 'rgba(255,255,255,0.75)'
  ctx.font = '13px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  // 캔버스 내 안내 텍스트 제거 — 아래 HINT 영역만 사용
}

// ── TYPE C: CLICK ORDER ───────────────────────────────────────────────────────
const SHAPES = ['circle', 'tri', 'star', 'diamond', 'penta', 'cross'] as const
type Shape = typeof SHAPES[number]
const COLORS6 = ['#ef4444', '#22c55e', '#3b82f6', '#f59e0b', '#a855f7', '#06b6d4']
const SYM: Record<Shape, string> = {
  circle: '●', tri: '▲', star: '★', diamond: '◆', penta: '⬠', cross: '✚',
}

interface OrderItem { x: number; y: number; shape: Shape; color: string }
interface OrderState {
  items: OrderItem[]
  seq: number[]     // correct click order
  done: number[]    // indices clicked so far
}

function initOrder(): OrderState {
  const pick = [...Array(6).keys()].sort(() => Math.random() - 0.5).slice(0, 5)
  const items: OrderItem[] = pick.map((si, i) => ({
    x: 42 + i * 68 + rnd(0, 18),
    y: 100 + rnd(0, 70),
    shape: SHAPES[si],
    color: COLORS6[si],
  }))
  const seq = [...Array(items.length).keys()].sort(() => Math.random() - 0.5).slice(0, 3)
  return { items, seq, done: [] }
}

function drawShapeAt(ctx: CanvasRenderingContext2D, shape: Shape, cx: number, cy: number, r: number) {
  ctx.beginPath()
  switch (shape) {
    case 'circle':
      ctx.arc(cx, cy, r, 0, Math.PI * 2)
      break
    case 'tri':
      ctx.moveTo(cx, cy - r)
      ctx.lineTo(cx + r * 0.866, cy + r * 0.5)
      ctx.lineTo(cx - r * 0.866, cy + r * 0.5)
      ctx.closePath()
      break
    case 'star':
      for (let i = 0; i < 5; i++) {
        const ao = (i * 4 * Math.PI) / 5 - Math.PI / 2
        const ai = ao + (2 * Math.PI) / 5
        const p = i === 0 ? ctx.moveTo.bind(ctx) : ctx.lineTo.bind(ctx)
        p(cx + r * Math.cos(ao), cy + r * Math.sin(ao))
        ctx.lineTo(cx + r * 0.4 * Math.cos(ai - Math.PI / 5), cy + r * 0.4 * Math.sin(ai - Math.PI / 5))
      }
      ctx.closePath()
      break
    case 'diamond':
      ctx.moveTo(cx, cy - r)
      ctx.lineTo(cx + r * 0.65, cy)
      ctx.lineTo(cx, cy + r)
      ctx.lineTo(cx - r * 0.65, cy)
      ctx.closePath()
      break
    case 'penta':
      for (let i = 0; i < 5; i++) {
        const a = (i * 2 * Math.PI) / 5 - Math.PI / 2
        const p = i === 0 ? ctx.moveTo.bind(ctx) : ctx.lineTo.bind(ctx)
        p(cx + r * Math.cos(a), cy + r * Math.sin(a))
      }
      ctx.closePath()
      break
    case 'cross': {
      const t = r * 0.38
      ctx.moveTo(cx - t, cy - r)
      ctx.lineTo(cx + t, cy - r)
      ctx.lineTo(cx + t, cy - t)
      ctx.lineTo(cx + r, cy - t)
      ctx.lineTo(cx + r, cy + t)
      ctx.lineTo(cx + t, cy + t)
      ctx.lineTo(cx + t, cy + r)
      ctx.lineTo(cx - t, cy + r)
      ctx.lineTo(cx - t, cy + t)
      ctx.lineTo(cx - r, cy + t)
      ctx.lineTo(cx - r, cy - t)
      ctx.lineTo(cx - t, cy - t)
      ctx.closePath()
      break
    }
  }
}

function drawOrder(ctx: CanvasRenderingContext2D, s: OrderState) {
  ctx.fillStyle = '#0c1445'
  ctx.fillRect(0, 0, CW, CH)

  // Star field
  for (let i = 0; i < 60; i++) {
    ctx.beginPath()
    ctx.arc(rnd(0, CW), rnd(48, CH), Math.random() < 0.3 ? 1.5 : 1, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(255,255,255,${0.05 + Math.random() * 0.12})`
    ctx.fill()
  }

  // Header bar — shape sequence만 표시 (텍스트 안내는 아래 HINT 영역으로)
  const HEADER_H = 50
  ctx.fillStyle = 'rgba(255,255,255,0.07)'
  ctx.fillRect(0, 0, CW, HEADER_H)

  // Sequence preview — 헤더 가운데 정렬
  const SEQ_GAP = 70
  const SEQ_TOTAL = (s.seq.length - 1) * SEQ_GAP
  const SEQ_START = (CW - SEQ_TOTAL) / 2
  const SEQ_Y = 25
  s.seq.forEach((itemIdx, pos) => {
    const item = s.items[itemIdx]
    const isDone = s.done.includes(itemIdx)
    const cx = SEQ_START + pos * SEQ_GAP

    ctx.save()
    ctx.translate(cx, SEQ_Y)
    drawShapeAt(ctx, item.shape, 0, 0, 11)
    ctx.fillStyle = isDone ? 'rgba(255,255,255,0.2)' : item.color
    ctx.fill()
    ctx.strokeStyle = isDone ? 'rgba(255,255,255,0.2)' : 'white'
    ctx.lineWidth = 1.5
    ctx.stroke()
    ctx.restore()

    if (pos < s.seq.length - 1) {
      ctx.fillStyle = 'rgba(255,255,255,0.4)'
      ctx.font = '12px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('→', cx + SEQ_GAP / 2, SEQ_Y)
    }
  })

  // Items
  s.items.forEach((item, i) => {
    const isDone = s.done.includes(i)
    const clickPos = s.done.indexOf(i)

    // Glow bg
    if (!isDone) {
      ctx.save()
      const g = ctx.createRadialGradient(item.x, item.y, 0, item.x, item.y, 30)
      g.addColorStop(0, item.color + '33')
      g.addColorStop(1, 'transparent')
      ctx.fillStyle = g
      ctx.fillRect(item.x - 30, item.y - 30, 60, 60)
      ctx.restore()
    }

    drawShapeAt(ctx, item.shape, item.x, item.y, 22)
    ctx.fillStyle = isDone ? 'rgba(100,100,100,0.5)' : item.color
    ctx.fill()
    ctx.strokeStyle = isDone ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.8)'
    ctx.lineWidth = 2
    ctx.stroke()

    if (isDone) {
      ctx.fillStyle = 'rgba(255,255,255,0.9)'
      ctx.font = 'bold 14px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(String(clickPos + 1), item.x, item.y)
    }
  })
}

// ── MAIN COMPONENT ─────────────────────────────────────────────────────────────
export default function PuzzleCaptcha({ onVerified }: PuzzleCaptchaProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isVerified, setIsVerified] = useState(false)

  const [type] = useState<CaptchaType>(() => {
    const opts: CaptchaType[] = ['slide', 'rotate', 'order']
    return opts[Math.floor(Math.random() * opts.length)]
  })

  const slideS = useRef<SlideState>(initSlide())
  const rotateS = useRef<RotateState>(initRotate())
  const orderS = useRef<OrderState>(initOrder())

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    if (type === 'slide') drawSlide(ctx, slideS.current)
    else if (type === 'rotate') drawRotate(ctx, rotateS.current)
    else drawOrder(ctx, orderS.current)
  }, [type])

  useEffect(() => { draw() }, [draw])

  // ── coordinate helper ──────────────────────────────────────────────────────
  const xy = (
    e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
    canvas: HTMLCanvasElement
  ) => {
    const rect = canvas.getBoundingClientRect()
    const sx = CW / rect.width, sy = CH / rect.height
    const src =
      'touches' in e
        ? (e.touches[0] ?? (e as React.TouchEvent).changedTouches[0])
        : e
    return { x: (src.clientX - rect.left) * sx, y: (src.clientY - rect.top) * sy }
  }

  // ── verified ───────────────────────────────────────────────────────────────
  const verify = useCallback(() => {
    setIsVerified(true)
    onVerified(genToken())
    setTimeout(() => {
      const canvas = canvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.fillStyle = 'rgba(0,0,0,0.65)'
      ctx.fillRect(0, 0, CW, CH)
      ctx.fillStyle = '#4ade80'
      ctx.font = 'bold 36px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('✓ Verified!', CW / 2, CH / 2)
    }, 60)
  }, [onVerified])

  // ── slide handlers ─────────────────────────────────────────────────────────
  const sDown = (x: number) => {
    const s = slideS.current
    const trackY = CH - 40
    // Hit on track handle
    if (x >= s.pieceX && x <= s.pieceX + s.PW) {
      s.dragging = true; s.startMX = x; s.startPX = s.pieceX
    }
    // Also hit on piece image in canvas
    if (x >= s.pieceX && x <= s.pieceX + s.PW) {
      s.dragging = true; s.startMX = x; s.startPX = s.pieceX
    }
    void trackY
  }
  const sMove = (x: number) => {
    const s = slideS.current
    if (!s.dragging) return
    s.pieceX = Math.max(12, Math.min(CW - s.PW - 12, s.startPX + (x - s.startMX)))
    draw()
  }
  const sUp = () => {
    const s = slideS.current
    if (!s.dragging) return
    s.dragging = false
    if (Math.abs(s.pieceX - s.targetX) <= 22) { s.pieceX = s.targetX; draw(); verify() }
    else draw()
  }

  // ── rotate handlers ────────────────────────────────────────────────────────
  const rDown = (x: number, y: number) => {
    const s = rotateS.current
    const dx = x - s.cx, dy = y - s.cy
    if (Math.sqrt(dx * dx + dy * dy) > 92) return
    s.dragging = true
    s.startMA = Math.atan2(dy, dx)
    s.startA = s.angle
  }
  const rMove = (x: number, y: number) => {
    const s = rotateS.current
    if (!s.dragging) return
    s.angle = s.startA + (Math.atan2(y - s.cy, x - s.cx) - s.startMA)
    draw()
  }
  const rUp = () => {
    const s = rotateS.current
    if (!s.dragging) return
    s.dragging = false
    const diff = ((s.angle - s.target) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2)
    if (Math.min(diff, Math.PI * 2 - diff) <= 0.22) verify()
    else draw()
  }

  // ── order handler ──────────────────────────────────────────────────────────
  const oClick = (x: number, y: number) => {
    const s = orderS.current
    for (let i = 0; i < s.items.length; i++) {
      if (s.done.includes(i)) continue
      const it = s.items[i]
      if (Math.abs(x - it.x) < 26 && Math.abs(y - it.y) < 26) {
        if (i === s.seq[s.done.length]) {
          s.done = [...s.done, i]
          draw()
          if (s.done.length === s.seq.length) setTimeout(verify, 180)
        } else {
          s.done = []   // wrong order — reset
          draw()
        }
        return
      }
    }
  }

  // ── unified events ─────────────────────────────────────────────────────────
  const onDown = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (isVerified) return
    const canvas = canvasRef.current; if (!canvas) return
    const { x, y } = xy(e, canvas)
    if (type === 'slide') sDown(x)
    else if (type === 'rotate') rDown(x, y)
    else oClick(x, y)
  }

  const onMove = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (isVerified || type === 'order') return
    e.preventDefault()
    const canvas = canvasRef.current; if (!canvas) return
    const { x, y } = xy(e, canvas)
    if (type === 'slide') sMove(x)
    else rMove(x, y)
  }

  const onUp = () => {
    if (isVerified) return
    if (type === 'slide') sUp()
    else if (type === 'rotate') rUp()
  }

  const HINT: Record<CaptchaType, { ko: string; en: string }> = {
    slide:  {
      ko: '조각을 오른쪽으로 드래그하여 구멍에 끼워 넣으세요',
      en: 'Drag the piece to the right and fit it into the hole',
    },
    rotate: {
      ko: '화살표를 드래그하여 투명 방향에 정확히 맞추세요',
      en: 'Drag to rotate the arrow until it matches the transparent guide',
    },
    order:  {
      ko: '위에 표시된 순서대로 도형을 클릭하세요',
      en: 'Click the shapes in the order shown above',
    },
  }

  // ── 새로고침 (멈춤 복구) ──────────────────────────────────────────────────
  const refresh = useCallback(() => {
    if (isVerified) return
    if (type === 'slide')  slideS.current  = initSlide()
    if (type === 'rotate') rotateS.current = initRotate()
    if (type === 'order')  orderS.current  = initOrder()
    draw()
  }, [type, isVerified, draw])

  return (
    <div className="my-4 p-4 border border-gray-200 rounded-xl bg-white">
      <div className="flex items-center justify-between mb-3">
        <label className="block text-sm font-medium text-gray-700">
          🔐 Security Check / 보안 확인
        </label>
        {!isVerified && (
          <button
            type="button"
            onClick={refresh}
            className="text-xs px-2 py-1 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-600 transition"
            aria-label="새로고침 / Refresh"
            title="문제가 보이지 않거나 멈춘 경우 / Click if puzzle is stuck or not visible"
          >
            🔄 새로고침 / Refresh
          </button>
        )}
      </div>

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
        className="border border-gray-200 rounded-xl w-full max-w-md mx-auto block bg-slate-900"
        style={{
          touchAction: 'none',
          userSelect: 'none',
          cursor: type === 'order' ? 'pointer' : 'grab',
        }}
      />

      {isVerified ? (
        <div className="mt-3 p-2 bg-green-100 border border-green-400 text-green-700 rounded text-center text-sm">
          ✓ 인증 완료 / CAPTCHA verified successfully
        </div>
      ) : (
        <div className="mt-3 p-3 bg-slate-50 border border-slate-200 text-slate-700 rounded text-center text-sm leading-relaxed">
          <div className="font-medium">{HINT[type].ko}</div>
          <div className="text-xs text-slate-500 mt-0.5">{HINT[type].en}</div>
          <div className="text-[11px] text-slate-400 mt-1.5">
            화면이 흰색으로 멈췄으면 위 “새로고침” 버튼을 눌러주세요
            <br />
            If the puzzle is stuck or blank, press the “Refresh” button above
          </div>
        </div>
      )}

      <input type="hidden" name="captcha_token" value={isVerified ? genToken() : ''} />
    </div>
  )
}
