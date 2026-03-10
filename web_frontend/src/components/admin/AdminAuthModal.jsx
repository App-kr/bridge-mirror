'use client'
import { useState, useCallback } from 'react'

// ═══════════════════════════════════════════════
// ▶ 설정값 — 필요시 수정
// ═══════════════════════════════════════════════
const CORRECT_PASSWORD = 'bridge2024'  // ← 실제 비밀번호로 교체

const IMAGE_SETS = [
  {
    question: '🐕 강아지 사진을 클릭하세요',
    correct: 'https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=240&h=240&fit=crop',
    wrong: [
      'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=240&h=240&fit=crop',
      'https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?w=240&h=240&fit=crop',
      'https://images.unsplash.com/photo-1444464666168-49d633b86797?w=240&h=240&fit=crop',
    ],
  },
  {
    question: '🌊 바다 사진을 클릭하세요',
    correct: 'https://images.unsplash.com/photo-1505118380757-91f5f5632de0?w=240&h=240&fit=crop',
    wrong: [
      'https://images.unsplash.com/photo-1448375240586-882707db888b?w=240&h=240&fit=crop',
      'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=240&h=240&fit=crop',
      'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=240&h=240&fit=crop',
    ],
  },
]

const PUZZLE_SETS = [
  {
    question: '빈 칸에 들어갈 조각을 선택하세요',
    imageUrl: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=480&h=480&fit=crop',
  },
  {
    question: '빈 칸에 들어갈 조각을 선택하세요',
    imageUrl: 'https://images.unsplash.com/photo-1501854140801-50d01698950b?w=480&h=480&fit=crop',
  },
]
// ═══════════════════════════════════════════════

function shuffle(arr) {
  return [...arr].sort(() => Math.random() - 0.5)
}

// 이미지의 특정 사분면(quadrant)을 보여주는 컴포넌트
// quadrant: 0=좌상, 1=우상, 2=좌하, 3=우하
function Quadrant({ src, quadrant, size }) {
  const col = quadrant % 2
  const row = Math.floor(quadrant / 2)
  return (
    <div style={{ width: size, height: size, overflow: 'hidden', position: 'relative', flexShrink: 0 }}>
      <img
        src={src}
        alt=""
        draggable={false}
        style={{
          position: 'absolute',
          width: size * 2,
          height: size * 2,
          left: -col * size,
          top: -row * size,
          userSelect: 'none',
          pointerEvents: 'none',
        }}
      />
    </div>
  )
}

function ErrorBox({ message }) {
  if (!message) return null
  return (
    <div className="bg-red-50 border-2 border-red-500 rounded-xl py-3 px-4 text-center">
      <p className="text-red-600 font-extrabold text-lg">⚠️ {message}</p>
    </div>
  )
}

export default function AdminAuthModal({ onClose }) {
  const [step, setStep] = useState('password') // 'password' | 'captcha' | 'success'
  const [password, setPassword] = useState('')
  const [pwError, setPwError] = useState('')
  const [captchaType, setCaptchaType] = useState(null) // 'image' | 'puzzle'
  const [captchaError, setCaptchaError] = useState('')
  const [imageSet, setImageSet] = useState(null)
  const [shuffledImages, setShuffledImages] = useState([])
  const [puzzleSet, setPuzzleSet] = useState(null)
  const [shuffledPieces, setShuffledPieces] = useState([])
  const [locked, setLocked] = useState(false) // 오답 후 1.5초 잠금

  const initCaptcha = useCallback(() => {
    const type = Math.random() < 0.5 ? 'image' : 'puzzle'
    setCaptchaType(type)
    setCaptchaError('')
    setLocked(false)

    if (type === 'image') {
      const set = IMAGE_SETS[Math.floor(Math.random() * IMAGE_SETS.length)]
      setImageSet(set)
      setShuffledImages(
        shuffle([
          { url: set.correct, isCorrect: true },
          ...set.wrong.map(url => ({ url, isCorrect: false })),
        ])
      )
    } else {
      const set = PUZZLE_SETS[Math.floor(Math.random() * PUZZLE_SETS.length)]
      setPuzzleSet(set)
      // 빠진 칸 = 우하(3번) → 정답 조각은 quadrant 3
      setShuffledPieces(
        shuffle([0, 1, 2, 3].map(q => ({ quadrant: q, isCorrect: q === 3 })))
      )
    }
  }, [])

  const handlePasswordSubmit = () => {
    if (!password.trim()) { setPwError('비밀번호를 입력하세요.'); return }
    if (password !== CORRECT_PASSWORD) { setPwError('비밀번호가 올바르지 않습니다.'); return }
    setPwError('')
    setStep('captcha')
    initCaptcha()
  }

  const handleCaptchaResult = (isCorrect) => {
    if (locked) return
    if (isCorrect) {
      setStep('success')
      setTimeout(() => onClose(true), 1500)
    } else {
      setLocked(true)
      setCaptchaError('틀렸습니다! 다시 시도하세요.')
      setTimeout(() => initCaptcha(), 1500)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">

        {/* 헤더 */}
        <div className="bg-gray-950 px-6 py-4 flex items-center justify-between">
          <span className="text-white font-bold tracking-widest text-sm uppercase">Bridge Admin</span>
          <button
            onClick={() => onClose(false)}
            className="text-gray-500 hover:text-white text-xl leading-none transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="p-6">

          {/* ─── STEP 1: 비밀번호 ─── */}
          {step === 'password' && (
            <div className="space-y-4">
              <div className="text-center space-y-1">
                <div className="text-5xl mb-2">🔐</div>
                <h2 className="text-xl font-bold text-gray-900">비밀번호 입력</h2>
                <p className="text-gray-400 text-sm">관리자 비밀번호를 입력하세요</p>
              </div>
              <input
                type="password"
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-center text-lg focus:outline-none focus:border-gray-900 transition-colors"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handlePasswordSubmit()}
                autoFocus
              />
              <ErrorBox message={pwError} />
              <button
                onClick={handlePasswordSubmit}
                className="w-full bg-gray-950 hover:bg-gray-800 active:scale-95 text-white font-bold py-3 rounded-xl transition-all text-base"
              >
                접속
              </button>
            </div>
          )}

          {/* ─── STEP 2A: 이미지 CAPTCHA ─── */}
          {step === 'captcha' && captchaType === 'image' && imageSet && (
            <div className="space-y-4">
              <div className="text-center space-y-1">
                <div className="text-5xl mb-2">🖼️</div>
                <h2 className="text-xl font-bold text-gray-900">{imageSet.question}</h2>
                <p className="text-gray-400 text-sm">4장 중 올바른 사진을 클릭하세요</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {shuffledImages.map((img, i) => (
                  <button
                    key={i}
                    onClick={() => handleCaptchaResult(img.isCorrect)}
                    disabled={locked}
                    className="relative aspect-square overflow-hidden rounded-xl border-2 border-gray-100 hover:border-blue-400 hover:scale-[1.03] active:scale-95 transition-all focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    <img src={img.url} alt="" className="w-full h-full object-cover" draggable={false} />
                  </button>
                ))}
              </div>
              <ErrorBox message={captchaError} />
            </div>
          )}

          {/* ─── STEP 2B: 퍼즐 CAPTCHA ─── */}
          {step === 'captcha' && captchaType === 'puzzle' && puzzleSet && (
            <div className="space-y-4">
              <div className="text-center space-y-1">
                <div className="text-5xl mb-2">🧩</div>
                <h2 className="text-xl font-bold text-gray-900">{puzzleSet.question}</h2>
                <p className="text-gray-400 text-sm">? 에 들어갈 조각을 아래에서 클릭하세요</p>
              </div>

              {/* 퍼즐 2x2 그리드 — 우하(BR) 비어있음 */}
              <div
                className="mx-auto grid gap-0.5 rounded-xl overflow-hidden border-2 border-gray-200"
                style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', width: 'fit-content' }}
              >
                {[0, 1, 2].map(q => (
                  <Quadrant key={q} src={puzzleSet.imageUrl} quadrant={q} size={130} />
                ))}
                <div
                  className="flex items-center justify-center bg-gray-100"
                  style={{ width: 130, height: 130 }}
                >
                  <span className="text-gray-400 text-5xl font-bold select-none">?</span>
                </div>
              </div>

              {/* 조각 선택지 4개 */}
              <div className="flex justify-center gap-2">
                {shuffledPieces.map((piece, i) => (
                  <button
                    key={i}
                    onClick={() => handleCaptchaResult(piece.isCorrect)}
                    disabled={locked}
                    className="overflow-hidden rounded-lg border-2 border-gray-200 hover:border-blue-400 hover:scale-105 active:scale-95 transition-all focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    <Quadrant src={puzzleSet.imageUrl} quadrant={piece.quadrant} size={65} />
                  </button>
                ))}
              </div>

              <ErrorBox message={captchaError} />
            </div>
          )}

          {/* ─── STEP 3: 성공 ─── */}
          {step === 'success' && (
            <div className="text-center py-10 space-y-4">
              <div className="text-7xl animate-bounce">✅</div>
              <h2 className="text-2xl font-extrabold text-green-600">인증 성공</h2>
              <p className="text-gray-400 text-sm">잠시 후 자동으로 이동합니다...</p>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
