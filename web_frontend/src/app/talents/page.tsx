'use client'

/**
 * /talents — 공개 강사 게시판
 * talent_visible=1 강사 카드 그리드. PII 없음.
 * PC 3열 / tablet 2열 / mobile 1열
 */

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { API_URL } from '@/lib/api'

/* ── 타입 ── */
interface TalentCard {
  sheet_number: number
  nationality: string
  area_prefs: string | null
  target: string | null
  certification: string | null
  education_level: string | null
  experience: string | null
  desired_salary: string | null
  thumb_url: string | null
  talent_badge: string | null
  talent_reference_star: number | null
  talent_summary: string | null
}

/* ── 배지 색상 ── */
const BADGE_STYLE: Record<string, { bg: string; text: string; shimmer: string }> = {
  '추천':     { bg: '#B8860B', text: '#fff', shimmer: 'shimmer-gold' },
  '교육전공': { bg: '#1565C0', text: '#fff', shimmer: 'shimmer-blue' },
  '경력우수': { bg: '#2E7D32', text: '#fff', shimmer: 'shimmer-green' },
  '라이선스': { bg: '#6A1B9A', text: '#fff', shimmer: 'shimmer-purple' },
}

/* ── 별점 렌더러 ── */
function Stars({ n }: { n: number | null }) {
  const max = 5
  const filled = Math.min(Math.max(n ?? 0, 0), max)
  return (
    <span style={{ fontSize: 13, color: '#F59E0B', letterSpacing: 1 }}>
      {'★'.repeat(filled)}{'☆'.repeat(max - filled)}
    </span>
  )
}

/* ── 문의 모달 ── */
function InquiryModal({
  card,
  onClose,
}: {
  card: TalentCard
  onClose: () => void
}) {
  const [form, setForm] = useState({
    school_name: '',
    contact_name: '',
    email: '',
    phone: '',
    message: '',
  })
  const [status, setStatus] = useState<'idle' | 'sending' | 'done' | 'error'>('idle')
  const backdropRef = useRef<HTMLDivElement>(null)

  function handleBackdrop(e: React.MouseEvent) {
    if (e.target === backdropRef.current) onClose()
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.school_name.trim() || !form.email.trim() || !form.message.trim()) return
    setStatus('sending')
    try {
      const res = await fetch(`${API_URL}/api/public/talent-inquiry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, candidate_ref: card.sheet_number }),
      })
      if (!res.ok) throw new Error('서버 오류')
      setStatus('done')
    } catch {
      setStatus('error')
    }
  }

  return (
    <div
      ref={backdropRef}
      onClick={handleBackdrop}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(0,0,0,0.65)', display: 'flex',
        alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 480,
        padding: '28px 28px 24px', boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        position: 'relative',
      }}>
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 14, right: 16,
            background: 'none', border: 'none', fontSize: 22,
            cursor: 'pointer', color: '#6B7280', lineHeight: 1,
          }}
        >×</button>

        {status === 'done' ? (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>✓</div>
            <p style={{ fontWeight: 700, fontSize: 17, marginBottom: 6 }}>문의가 접수되었습니다</p>
            <p style={{ color: '#6B7280', fontSize: 14 }}>빠른 시일 내에 연락드리겠습니다.</p>
            <button
              onClick={onClose}
              style={{
                marginTop: 20, padding: '10px 28px',
                background: '#111', color: '#fff', border: 'none',
                borderRadius: 8, cursor: 'pointer', fontWeight: 600,
              }}
            >닫기</button>
          </div>
        ) : (
          <>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>강사 채용 문의</h2>
            <p style={{ color: '#6B7280', fontSize: 13, marginBottom: 20 }}>
              강사 #{card.sheet_number} · {card.nationality || ''}
            </p>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <input
                required placeholder="학교/기관명 *"
                value={form.school_name}
                onChange={e => setForm(f => ({ ...f, school_name: e.target.value }))}
                style={inputStyle}
              />
              <input
                placeholder="담당자명"
                value={form.contact_name}
                onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))}
                style={inputStyle}
              />
              <input
                required type="email" placeholder="이메일 *"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                style={inputStyle}
              />
              <input
                placeholder="연락처"
                value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                style={inputStyle}
              />
              <textarea
                required placeholder="문의 내용 *"
                rows={4}
                value={form.message}
                onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
              />
              {status === 'error' && (
                <p style={{ color: '#DC2626', fontSize: 13 }}>
                  전송에 실패했습니다. 잠시 후 다시 시도해주세요.
                </p>
              )}
              <button
                type="submit"
                disabled={status === 'sending'}
                style={{
                  padding: '12px 0', background: '#111', color: '#fff',
                  border: 'none', borderRadius: 8, fontWeight: 700,
                  fontSize: 15, cursor: status === 'sending' ? 'not-allowed' : 'pointer',
                  opacity: status === 'sending' ? 0.7 : 1, marginTop: 4,
                }}
              >
                {status === 'sending' ? '전송 중...' : '문의 보내기'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 13px', border: '1px solid #D1D5DB',
  borderRadius: 8, fontSize: 14, outline: 'none', boxSizing: 'border-box',
}

/* ── 강사 카드 ── */
function TalentCardItem({
  card,
  onInquire,
}: {
  card: TalentCard
  onInquire: (c: TalentCard) => void
}) {
  const badge = card.talent_badge ? BADGE_STYLE[card.talent_badge] : null

  return (
    <div style={{
      background: '#fff', borderRadius: 16, overflow: 'hidden',
      boxShadow: '0 2px 12px rgba(0,0,0,0.08)', display: 'flex',
      flexDirection: 'column', transition: 'transform 0.15s, box-shadow 0.15s',
    }}
      onMouseEnter={e => {
        ;(e.currentTarget as HTMLDivElement).style.transform = 'translateY(-4px)'
        ;(e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 28px rgba(0,0,0,0.14)'
      }}
      onMouseLeave={e => {
        ;(e.currentTarget as HTMLDivElement).style.transform = ''
        ;(e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 12px rgba(0,0,0,0.08)'
      }}
    >
      {/* 썸네일 */}
      <div style={{
        width: '100%', aspectRatio: '4/3', background: '#F3F4F6',
        position: 'relative', overflow: 'hidden',
      }}>
        {card.thumb_url ? (
          <img
            src={card.thumb_url}
            alt={`강사 #${card.sheet_number}`}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <div style={{
            width: '100%', height: '100%', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            color: '#9CA3AF', fontSize: 36,
          }}>👤</div>
        )}
        {/* 강사 번호 */}
        <div style={{
          position: 'absolute', top: 10, left: 10,
          background: 'rgba(0,0,0,0.55)', color: '#fff',
          fontSize: 11, fontWeight: 700, padding: '3px 8px',
          borderRadius: 20, backdropFilter: 'blur(4px)',
        }}>
          #{card.sheet_number}
        </div>
        {/* 배지 */}
        {badge && (
          <div style={{
            position: 'absolute', top: 10, right: 10,
            background: badge.bg, color: badge.text,
            fontSize: 11, fontWeight: 700, padding: '3px 9px',
            borderRadius: 20,
          }}>
            {card.talent_badge}
          </div>
        )}
      </div>

      {/* 카드 본문 */}
      <div style={{ padding: '14px 16px', flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {/* 국적 + 별점 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#111' }}>
            {card.nationality || '—'}
          </span>
          <Stars n={card.talent_reference_star} />
        </div>

        {/* 메타 행 */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 8px' }}>
          {card.area_prefs && (
            <Tag icon="📍" text={card.area_prefs} />
          )}
          {card.target && (
            <Tag icon="🎯" text={card.target} />
          )}
          {card.certification && (
            <Tag icon="📜" text={card.certification} />
          )}
        </div>

        {/* 경력 / 학력 */}
        {(card.experience || card.education_level) && (
          <div style={{ fontSize: 12, color: '#6B7280', lineHeight: 1.5 }}>
            {card.education_level && <span>{card.education_level}</span>}
            {card.education_level && card.experience && ' · '}
            {card.experience && <span>{card.experience}</span>}
          </div>
        )}

        {/* 희망 급여 */}
        {card.desired_salary && (
          <div style={{ fontSize: 12, color: '#374151' }}>
            💰 {card.desired_salary}
          </div>
        )}

        {/* 강사 소개 */}
        {card.talent_summary && (
          <p style={{
            fontSize: 13, color: '#4B5563', lineHeight: 1.55,
            margin: '4px 0 0', display: '-webkit-box',
            WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}>
            {card.talent_summary}
          </p>
        )}

        {/* 문의 버튼 */}
        <button
          onClick={() => onInquire(card)}
          style={{
            width: '100%', padding: '10px 0', marginTop: 12,
            background: '#111', color: '#fff', border: 'none',
            borderRadius: 8, fontWeight: 600, fontSize: 13,
            cursor: 'pointer', transition: 'background 0.15s',
          }}
          onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = '#374151')}
          onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = '#111')}
        >
          채용 문의
        </button>
      </div>
    </div>
  )
}

function Tag({ icon, text }: { icon: string; text: string }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 3,
      background: '#F3F4F6', borderRadius: 6,
      padding: '2px 7px', fontSize: 11, color: '#374151',
    }}>
      {icon} {text}
    </span>
  )
}

/* ── 메인 페이지 ── */
export default function TalentsPage() {
  const router = useRouter()
  const [cards, setCards] = useState<TalentCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [inquiryCard, setInquiryCard] = useState<TalentCard | null>(null)

  // 필터 상태
  const [filterNat, setFilterNat] = useState('')
  const [filterArea, setFilterArea] = useState('')
  const [filterTarget, setFilterTarget] = useState('')
  const [filterNum, setFilterNum] = useState('')

  // 세션 만료 검증 (미들웨어 통과 후 실제 서버 검증)
  useEffect(() => {
    fetch('/api/talent-auth/check', { cache: 'no-store' })
      .then(r => r.json())
      .then(d => { if (!d?.valid) router.replace('/talents/login') })
      .catch(() => {}) // 네트워크 오류는 무시 (중단하지 않음)
  }, [router])

  useEffect(() => {
    const params = new URLSearchParams()
    if (filterNat.trim()) params.set('nationality', filterNat.trim())
    if (filterArea.trim()) params.set('area', filterArea.trim())
    if (filterTarget.trim()) params.set('target', filterTarget.trim())
    if (filterNum.trim()) params.set('q', filterNum.trim())

    setLoading(true)
    fetch(`${API_URL}/api/public/talents?${params}`)
      .then(r => r.json())
      .then(d => {
        setCards(d.data ?? [])
        setError(null)
      })
      .catch(() => setError('데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }, [filterNat, filterArea, filterTarget, filterNum])

  // 필터에서 선택 가능한 유니크 값들
  const natOptions = Array.from(new Set(cards.map(c => c.nationality).filter(Boolean))).sort()
  const areaOptions = Array.from(new Set(cards.map(c => c.area_prefs).filter(Boolean))).sort()
  const targetOptions = Array.from(new Set(cards.map(c => c.target).filter(Boolean))).sort()

  return (
    <>
      {/* shimmer CSS */}
      <style>{`
        @keyframes shimmer {
          0%   { background-position: -200% center; }
          100% { background-position:  200% center; }
        }
        .talent-page { min-height: 100vh; background: #F9FAFB; }
      `}</style>

      <div className="talent-page">
        {/* 헤더 배너 */}
        <div style={{
          background: 'linear-gradient(135deg, #111 0%, #1e293b 100%)',
          color: '#fff', textAlign: 'center', padding: '60px 24px 48px',
        }}>
          <h1 style={{ fontSize: 'clamp(24px, 5vw, 40px)', fontWeight: 800, margin: 0 }}>
            Teacher Board
          </h1>
          <p style={{ marginTop: 12, fontSize: 15, color: '#94A3B8', maxWidth: 480, marginInline: 'auto' }}>
            BRIDGE가 검증한 원어민 강사 풀 — 학교·학원 담당자 전용
          </p>
        </div>

        {/* 필터 바 */}
        <div style={{
          background: '#fff', borderBottom: '1px solid #E5E7EB',
          padding: '16px 24px', display: 'flex', flexWrap: 'wrap', gap: 10,
          position: 'sticky', top: 0, zIndex: 100,
        }}>
          <select
            value={filterNat}
            onChange={e => setFilterNat(e.target.value)}
            style={filterSelectStyle}
          >
            <option value="">🌍 국적 전체</option>
            {natOptions.map(n => (
              <option key={n} value={n!}>{n}</option>
            ))}
          </select>

          <select
            value={filterArea}
            onChange={e => setFilterArea(e.target.value)}
            style={filterSelectStyle}
          >
            <option value="">📍 지역 전체</option>
            {areaOptions.map(a => (
              <option key={a} value={a!}>{a}</option>
            ))}
          </select>

          <select
            value={filterTarget}
            onChange={e => setFilterTarget(e.target.value)}
            style={filterSelectStyle}
          >
            <option value="">🎯 타겟 전체</option>
            {targetOptions.map(t => (
              <option key={t} value={t!}>{t}</option>
            ))}
          </select>

          <input
            type="number"
            placeholder="강사 번호 검색"
            value={filterNum}
            onChange={e => setFilterNum(e.target.value)}
            style={{ ...filterSelectStyle, width: 140 }}
          />

          {(filterNat || filterArea || filterTarget || filterNum) && (
            <button
              onClick={() => {
                setFilterNat(''); setFilterArea('')
                setFilterTarget(''); setFilterNum('')
              }}
              style={{
                padding: '8px 14px', background: '#F3F4F6', border: '1px solid #D1D5DB',
                borderRadius: 8, fontSize: 13, cursor: 'pointer', color: '#374151',
              }}
            >
              초기화
            </button>
          )}
        </div>

        {/* 카드 그리드 */}
        <div style={{ maxWidth: 1200, marginInline: 'auto', padding: '32px 20px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '80px 0', color: '#6B7280', fontSize: 15 }}>
              강사 목록을 불러오는 중...
            </div>
          ) : error ? (
            <div style={{ textAlign: 'center', padding: '80px 0', color: '#DC2626', fontSize: 15 }}>
              {error}
            </div>
          ) : cards.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '80px 0', color: '#6B7280', fontSize: 15 }}>
              조건에 맞는 강사가 없습니다.
            </div>
          ) : (
            <>
              <p style={{ color: '#6B7280', fontSize: 13, marginBottom: 20 }}>
                총 {cards.length}명의 강사
              </p>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                gap: 20,
              }}>
                {cards.map(card => (
                  <TalentCardItem
                    key={card.sheet_number}
                    card={card}
                    onInquire={setInquiryCard}
                  />
                ))}
              </div>
            </>
          )}
        </div>

        {/* 푸터 안내 */}
        <div style={{
          background: '#111', color: '#94A3B8',
          textAlign: 'center', padding: '32px 24px', fontSize: 13,
        }}>
          <p style={{ margin: 0 }}>
            강사 정보는 채용 검토 목적으로만 제공됩니다. 무단 배포 금지.
          </p>
          <p style={{ marginTop: 6, margin: '6px 0 0' }}>
            채용 의뢰:{' '}
            <a href="/inquiry" style={{ color: '#60A5FA', textDecoration: 'none' }}>
              구인 의뢰 페이지
            </a>
          </p>
        </div>
      </div>

      {/* 문의 모달 */}
      {inquiryCard && (
        <InquiryModal
          card={inquiryCard}
          onClose={() => setInquiryCard(null)}
        />
      )}
    </>
  )
}

const filterSelectStyle: React.CSSProperties = {
  padding: '8px 12px', border: '1px solid #D1D5DB', borderRadius: 8,
  fontSize: 13, background: '#fff', cursor: 'pointer', outline: 'none',
  color: '#374151',
}
