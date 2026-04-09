'use client'

/**
 * /talents/login — 인재 게시판 접근 요청 (사업자 인증 포함)
 * - 사업자등록번호 + 사업자등록증명원 파일 업로드 필수
 * - "사업자등록증명원이 뭐예요?" 안내 모달 포함
 * - 이미 신청/승인된 이메일 구분 처리
 */

import { useRef, useState } from 'react'
import { API_URL } from '@/lib/api'

/* ── 사업자등록증명원 안내 모달 ─────────────────────────────────────── */
function BizDocModal({ onClose }: { onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
        padding: '0 0 0 0',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: '20px 20px 0 0',
          width: '100%', maxWidth: 480,
          padding: '28px 24px 36px',
          boxShadow: '0 -8px 40px rgba(0,0,0,0.18)',
        }}
      >
        {/* 드래그 핸들 */}
        <div style={{ width: 40, height: 4, background: '#E5E7EB', borderRadius: 99, margin: '0 auto 20px' }} />

        <h3 style={{ fontSize: 17, fontWeight: 800, marginBottom: 10, textAlign: 'center' }}>
          사업자등록증명원이 뭐예요?
        </h3>

        {/* 비교 이미지 영역 */}
        <div style={{
          display: 'flex', gap: 12, marginBottom: 16,
          padding: '12px', background: '#F9FAFB', borderRadius: 12,
          justifyContent: 'center',
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: 80, height: 100, border: '2px solid #10B981', borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: '#ECFDF5', fontSize: 11, color: '#065F46', fontWeight: 700,
              flexDirection: 'column', gap: 4,
            }}>
              <span style={{ fontSize: 24 }}>✓</span>
              <span>사업자등록증명원</span>
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: 80, height: 100, border: '2px solid #EF4444', borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: '#FEF2F2', fontSize: 11, color: '#991B1B', fontWeight: 700,
              flexDirection: 'column', gap: 4,
            }}>
              <span style={{ fontSize: 24 }}>✕</span>
              <span>사업자등록증</span>
            </div>
          </div>
        </div>

        <p style={{
          background: '#F0FDF4', border: '1px solid #86EFAC',
          borderRadius: 10, padding: '12px 14px',
          fontSize: 13, color: '#065F46', lineHeight: 1.6, marginBottom: 20,
        }}>
          사업자등록증과 달리 <strong>위조 방지용 번호</strong>와 <strong>발급 일자</strong>가 기재되어 있어요!
          홈택스에서 무료로 즉시 발급 가능합니다.
        </p>

        <a
          href="https://www.gov.kr/mw/AA020InfoCappView.do?HighCtgCD=&CappBizCD=12100000016"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'block', width: '100%', padding: '13px 0',
            background: '#111', color: '#fff', border: 'none',
            borderRadius: 10, fontWeight: 700, fontSize: 14,
            cursor: 'pointer', textAlign: 'center', textDecoration: 'none',
            marginBottom: 10, boxSizing: 'border-box',
          }}
        >
          사업자등록증명원 발급하기
        </a>

        <button
          onClick={onClose}
          style={{
            display: 'block', width: '100%', padding: '12px 0',
            background: '#F3F4F6', color: '#374151', border: 'none',
            borderRadius: 10, fontWeight: 600, fontSize: 14,
            cursor: 'pointer', textAlign: 'center',
          }}
        >
          닫기
        </button>

        <p style={{ marginTop: 14, fontSize: 11, color: '#9CA3AF', textAlign: 'center' }}>
          기업 인증은 서비스 이용 전 필수입니다.
        </p>
      </div>
    </div>
  )
}

/* ── 파일 드롭존 ────────────────────────────────────────────────────── */
function FileDropZone({
  file,
  onChange,
}: {
  file: File | null
  onChange: (f: File | null) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [drag, setDrag] = useState(false)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDrag(false)
    const f = e.dataTransfer.files[0]
    if (f) onChange(f)
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      style={{
        border: `2px dashed ${drag ? '#111' : file ? '#10B981' : '#D1D5DB'}`,
        borderRadius: 10, padding: '18px 16px',
        background: drag ? '#F9FAFB' : file ? '#F0FDF4' : '#fff',
        cursor: 'pointer', textAlign: 'center', transition: 'all 0.15s',
        userSelect: 'none',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        style={{ display: 'none' }}
        onChange={e => onChange(e.target.files?.[0] ?? null)}
      />
      {file ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <span style={{ fontSize: 20 }}>📄</span>
          <div style={{ textAlign: 'left' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#065F46' }}>{file.name}</div>
            <div style={{ fontSize: 11, color: '#6B7280' }}>{(file.size / 1024).toFixed(0)} KB</div>
          </div>
          <button
            type="button"
            onClick={e => { e.stopPropagation(); onChange(null) }}
            style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', color: '#9CA3AF', fontSize: 16 }}
          >×</button>
        </div>
      ) : (
        <div>
          <div style={{ fontSize: 24, marginBottom: 6 }}>📎</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>클릭 또는 파일을 여기에 끌어다 놓으세요</div>
          <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 3 }}>PDF, JPG, PNG · 최대 5MB</div>
        </div>
      )}
    </div>
  )
}

/* ── 메인 페이지 ─────────────────────────────────────────────────────── */
export default function TalentsLoginPage() {
  const [school, setSchool]           = useState('')
  const [bizNumber, setBizNumber]     = useState('')
  const [contactName, setContactName] = useState('')
  const [email, setEmail]             = useState('')
  const [docFile, setDocFile]         = useState<File | null>(null)
  const [status, setStatus]           = useState<'idle' | 'sending' | 'done' | 'error' | 'duplicate'>('idle')
  const [message, setMessage]         = useState('')
  const [showBizModal, setShowBizModal] = useState(false)

  const sending = status === 'sending'

  // 사업자번호 포맷: 000-00-00000
  function formatBizNum(val: string) {
    const digits = val.replace(/\D/g, '').slice(0, 10)
    if (digits.length <= 3) return digits
    if (digits.length <= 5) return `${digits.slice(0, 3)}-${digits.slice(3)}`
    return `${digits.slice(0, 3)}-${digits.slice(3, 5)}-${digits.slice(5)}`
  }

  const isValid = email.trim() && school.trim() && bizNumber.replace(/\D/g, '').length === 10 && docFile

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!isValid || sending) return
    setStatus('sending')
    try {
      const fd = new FormData()
      fd.append('email', email.trim())
      fd.append('company_name', school.trim())
      fd.append('biz_number', bizNumber.replace(/\D/g, ''))
      if (docFile) fd.append('doc_file', docFile)

      const res = await fetch(`${API_URL}/api/public/talent-auth/request`, {
        method: 'POST',
        body: fd,
      })
      const data = await res.json()
      if (!res.ok) {
        setMessage(data?.detail || '오류가 발생했습니다.')
        setStatus('error')
      } else {
        const responseStatus = data?.data?.status
        if (responseStatus === 'pending' || responseStatus === 'sent') {
          setMessage(data?.message || '이미 접수된 요청이 있습니다.')
          setStatus('duplicate')
        } else {
          setMessage(data?.message || '요청이 접수되었습니다.')
          setStatus('done')
        }
      }
    } catch {
      setMessage('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.')
      setStatus('error')
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#fafafa', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px 16px' }}>

      {/* 카드 */}
      <div style={{ background: '#fff', borderRadius: 20, width: '100%', maxWidth: 480, padding: '36px 32px', boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>

        {/* 로고 + 헤더 */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.5px', marginBottom: 6 }}>BRIDGE</div>
          <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0, marginBottom: 4 }}>강사 게시판 접근 신청</h1>
          <p style={{ fontSize: 13, color: '#6B7280', margin: 0 }}>
            학교·학원 담당자 전용 — 사업자 인증 후 이용 가능합니다
          </p>
        </div>

        {/* 완료/에러/중복 상태 */}
        {status === 'done' && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#F0FDF4', border: '2px solid #86EFAC', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', fontSize: 26 }}>✓</div>
            <p style={{ fontWeight: 700, fontSize: 17, marginBottom: 6 }}>요청이 접수되었습니다</p>
            <p style={{ color: '#6B7280', fontSize: 14 }}>서류 확인 후 이메일로 접속 링크를 보내드립니다.</p>
          </div>
        )}

        {status === 'duplicate' && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#FEF9C3', border: '2px solid #FDE68A', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', fontSize: 26 }}>⏳</div>
            <p style={{ fontWeight: 700, fontSize: 17, marginBottom: 6 }}>이미 접수된 요청이 있습니다</p>
            <p style={{ color: '#6B7280', fontSize: 14 }}>{message}</p>
          </div>
        )}

        {(status === 'idle' || status === 'sending' || status === 'error') && (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* 이메일 */}
            <div>
              <label style={labelStyle}>이메일 *</label>
              <input required type="email" placeholder="example@school.com" value={email} onChange={e => setEmail(e.target.value)} style={inputStyle} />
            </div>

            {/* 학교/기관명 */}
            <div>
              <label style={labelStyle}>학교 / 기관명 *</label>
              <input required placeholder="OO초등학교 / OO학원" value={school} onChange={e => setSchool(e.target.value)} style={inputStyle} />
            </div>

            {/* 담당자명 */}
            <div>
              <label style={labelStyle}>담당자명</label>
              <input placeholder="홍길동" value={contactName} onChange={e => setContactName(e.target.value)} style={inputStyle} />
            </div>

            {/* 사업자등록번호 */}
            <div>
              <label style={labelStyle}>사업자등록번호 *</label>
              <input
                required
                placeholder="000-00-00000"
                value={bizNumber}
                onChange={e => setBizNumber(formatBizNum(e.target.value))}
                style={inputStyle}
                inputMode="numeric"
              />
            </div>

            {/* 사업자등록증명원 업로드 */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <label style={labelStyle}>사업자등록증명원 *</label>
                <button
                  type="button"
                  onClick={() => setShowBizModal(true)}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    fontSize: 12, color: '#3B82F6', fontWeight: 600,
                    display: 'flex', alignItems: 'center', gap: 3,
                  }}
                >
                  ❓ 이게 뭐예요?
                </button>
              </div>
              <FileDropZone file={docFile} onChange={setDocFile} />
              <p style={{ fontSize: 11, color: '#9CA3AF', marginTop: 5 }}>
                사업자등록증(✕)이 아닌 <strong>사업자등록증명원(✓)</strong>을 첨부해주세요.
              </p>
            </div>

            {status === 'error' && (
              <p style={{ color: '#DC2626', fontSize: 13, margin: 0 }}>{message}</p>
            )}

            <button
              type="submit"
              disabled={!isValid || sending}
              style={{
                padding: '13px 0', background: isValid && !sending ? '#111' : '#D1D5DB',
                color: '#fff', border: 'none', borderRadius: 10,
                fontWeight: 700, fontSize: 15,
                cursor: isValid && !sending ? 'pointer' : 'not-allowed',
                marginTop: 4, transition: 'background 0.15s',
              }}
            >
              {sending ? '제출 중...' : '접근 신청하기'}
            </button>

            <p style={{ fontSize: 12, color: '#9CA3AF', textAlign: 'center', margin: 0 }}>
              접속 링크는 검토 후 이메일로 발송됩니다 (보통 1영업일 이내)
            </p>
          </form>
        )}
      </div>

      {/* 안내 모달 */}
      {showBizModal && <BizDocModal onClose={() => setShowBizModal(false)} />}
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 13, fontWeight: 600,
  color: '#374151', marginBottom: 5,
}
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 13px', border: '1px solid #D1D5DB',
  borderRadius: 8, fontSize: 14, outline: 'none', boxSizing: 'border-box',
}
