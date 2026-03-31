'use client'

import { useState, useRef, useEffect } from 'react'

interface PuzzleCaptchaProps {
  onVerified: (token: string) => void
  onError?: (error: string) => void
}

export default function PuzzleCaptcha({ onVerified, onError }: PuzzleCaptchaProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isVerified, setIsVerified] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [puzzleState, setPuzzleState] = useState<{
    pieces: Array<{ x: number; y: number; correctX: number; correctY: number; img?: ImageData }>
    draggedPieceIdx: number | null
    offsetX: number
    offsetY: number
  }>({
    pieces: [],
    draggedPieceIdx: null,
    offsetX: 0,
    offsetY: 0,
  })

  // 퍼즐 초기화
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 캔버스 크기: 400x300
    canvas.width = 400
    canvas.height = 300
    ctx.fillStyle = '#e3f2fd'
    ctx.fillRect(0, 0, 400, 300)

    // 테스트 그래디언트 배경
    const gradient = ctx.createLinearGradient(0, 0, 400, 300)
    gradient.addColorStop(0, '#667eea')
    gradient.addColorStop(1, '#764ba2')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 400, 300)

    // 텍스트
    ctx.fillStyle = 'white'
    ctx.font = 'bold 24px Arial'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('Drag pieces below', 200, 150)

    // 퍼즐 조각 3개 생성
    const pieceWidth = 80
    const pieceHeight = 80
    const pieces = [
      { x: 50, y: 50, correctX: 0, correctY: 0 },
      { x: 250, y: 80, correctX: 120, correctY: 0 },
      { x: 100, y: 200, correctX: 240, correctY: 0 },
    ]

    // 각 조각을 ImageData로 추출
    const piecesWithImg = pieces.map((p) => ({
      ...p,
      img: ctx.getImageData(p.correctX, p.correctY, pieceWidth, pieceHeight),
    }))

    setPuzzleState({
      pieces: piecesWithImg,
      draggedPieceIdx: null,
      offsetX: 0,
      offsetY: 0,
    })

    // 스크램블된 위치에 조각 그리기
    ctx.strokeStyle = '#333'
    ctx.lineWidth = 2
    piecesWithImg.forEach((piece, idx) => {
      ctx.strokeRect(piece.x - 2, piece.y - 2, pieceWidth + 4, pieceHeight + 4)
      ctx.fillStyle = 'rgba(255,255,255,0.1)'
      ctx.fillRect(piece.x - 2, piece.y - 2, pieceWidth + 4, pieceHeight + 4)
    })
  }, [])

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // 어느 조각을 클릭했나 확인
    const pieceWidth = 80
    const pieceHeight = 80
    for (let i = 0; i < puzzleState.pieces.length; i++) {
      const p = puzzleState.pieces[i]
      if (
        x >= p.x - 2 &&
        x <= p.x + pieceWidth + 2 &&
        y >= p.y - 2 &&
        y <= p.y + pieceHeight + 2
      ) {
        setIsDragging(true)
        setPuzzleState((prev) => ({
          ...prev,
          draggedPieceIdx: i,
          offsetX: x - p.x,
          offsetY: y - p.y,
        }))
        return
      }
    }
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging || puzzleState.draggedPieceIdx === null) return

    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    setPuzzleState((prev) => {
      const newPieces = [...prev.pieces]
      newPieces[prev.draggedPieceIdx!] = {
        ...newPieces[prev.draggedPieceIdx!],
        x: x - prev.offsetX,
        y: y - prev.offsetY,
      }
      return { ...prev, pieces: newPieces }
    })

    // 실시간 재렌더링
    redrawCanvas()
  }

  const handleMouseUp = () => {
    if (puzzleState.draggedPieceIdx === null) return

    setIsDragging(false)

    // 모든 조각이 올바른 위치에 있는지 확인
    const tolerance = 15
    const allCorrect = puzzleState.pieces.every(
      (p) =>
        Math.abs(p.x - p.correctX) <= tolerance &&
        Math.abs(p.y - p.correctY) <= tolerance
    )

    if (allCorrect) {
      setIsVerified(true)
      // 검증 토큰 생성 (서버에서 검증됨)
      const token = generateCaptchaToken()
      onVerified(token)
      showSuccessMessage()
    }

    setPuzzleState((prev) => ({
      ...prev,
      draggedPieceIdx: null,
    }))
  }

  const redrawCanvas = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 배경 다시 그리기
    const gradient = ctx.createLinearGradient(0, 0, 400, 300)
    gradient.addColorStop(0, '#667eea')
    gradient.addColorStop(1, '#764ba2')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 400, 300)

    ctx.fillStyle = 'white'
    ctx.font = 'bold 24px Arial'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('Drag pieces', 200, 150)

    // 현재 조각 위치로 그리기
    const pieceWidth = 80
    puzzleState.pieces.forEach((piece) => {
      if (piece.img) {
        ctx.putImageData(piece.img, Math.round(piece.x), Math.round(piece.y))
      }
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.strokeRect(piece.x, piece.y, pieceWidth, 80)
    })
  }

  const generateCaptchaToken = (): string => {
    // 서버에서 검증할 토큰 (클라이언트에서는 간단히 생성)
    const timestamp = Date.now()
    const nonce = Math.random().toString(36).substring(7)
    return `puzzle_${timestamp}_${nonce}`
  }

  const showSuccessMessage = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.fillStyle = 'rgba(0,0,0,0.7)'
    ctx.fillRect(0, 0, 400, 300)

    ctx.fillStyle = '#4caf50'
    ctx.font = 'bold 32px Arial'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('✓ Verified!', 200, 150)
  }

  return (
    <div className="my-6 p-4 border border-gray-300 rounded-lg bg-white">
      <label className="block text-sm font-medium text-gray-700 mb-3">
        🧩 Puzzle CAPTCHA — Drag pieces to complete the puzzle
      </label>

      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => setIsDragging(false)}
        className="border-2 border-gray-400 rounded-lg cursor-move w-full max-w-md mx-auto block"
        style={{ touchAction: 'none', userSelect: 'none' }}
      />

      {isVerified && (
        <div className="mt-3 p-2 bg-green-100 border border-green-400 text-green-700 rounded text-center text-sm">
          ✓ CAPTCHA verified successfully
        </div>
      )}

      {!isVerified && (
        <div className="mt-3 p-2 bg-blue-100 border border-blue-400 text-blue-700 rounded text-center text-sm">
          👆 Drag all 3 pieces to their correct positions to continue
        </div>
      )}

      <input type="hidden" name="captcha_token" value={isVerified ? generateCaptchaToken() : ''} />
    </div>
  )
}
