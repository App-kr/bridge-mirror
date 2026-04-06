'use client'

/**
 * /talents/login — 인재 게시판 접근 요청 페이지 (2026 redesign)
 * 이메일 입력 → 담당자 검토 → Magic Link 이메일 발송
 * API: POST /api/public/talent-auth/request  { email, company_name }
 */

import { useRef, useState } from 'react'
import { API_URL } from '@/lib/api'

export default function TalentsLoginPage() {
  const [school, setSchool]           = useState('')
  const [city, setCity]               = useState('')
  const [contactName, setContactName] = useState('')
  const [jobTitle, setJobTitle]       = useState('')
  const [phone, setPhone]             = useState('')
  const [email, setEmail]             = useState('')
  const [file, setFile]               = useState<File | null>(null)
  const [status, setStatus]           = useState<'idle' | 'sending' | 'done' | 'error'>('idle')
  const [message, setMessage]         = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim() || !school.trim()) return
    setStatus('sending')
    try {
      const res = await fetch(`${API_URL}/api/public/talent-auth/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), company_name: school.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setMessage(data?.detail || '오류가 발생했습니다.')
        setStatus('error')
      } else {
        setMessage(data?.message || '요청이 접수되었습니다.')
        setStatus('done')
      }
    } catch {
      setMessage('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.')
      setStatus('error')
    }
  }

  const sending = status === 'sending'
  const disabled = sending || !email.trim() || !school.trim()

  return (
    <div style={{
      minHeight: '100vh',
      background: '#fafafa',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px 16px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif',
    }}>
      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .tl-card { animation: fadeUp 0.5s ease forwards; }
        .tl-input {
          width: 100%; height: 52px; padding: 0 16px;
          border: 1.5px solid #e5e7eb; border-radius: 12px;
          font-size: 16px; box-sizing: border-box;
          background: #fff; color: #111;
          transition: border-color 0.15s, box-shadow 0.15s;
          outline: none;
        }
        .tl-input:focus {
          border-color: #111;
          box-shadow: 0 0 0 3px rgba(0,0,0,0.07);
        }
        .tl-input:disabled { background: #f9f9f9; color: #999; cursor: not-allowed; }
        .tl-submit {
          width: 100%; height: 52px;
          background: #111; color: #fff; border: none;
          border-radius: 12px; font-size: 16px; font-weight: 700;
          letter-spacing: 0.01em; cursor: pointer;
          transition: transform 0.15s, opacity 0.15s;
        }
        .tl-submit:hover:not(:disabled) { transform: scale(1.02); }
        .tl-submit:active:not(:disabled) { transform: scale(0.99); }
        .tl-submit:disabled { opacity: 0.45; cursor: not-allowed; }
        .tl-file-zone {
          height: 52px; border: 1.5px dashed #d1d5db; border-radius: 12px;
          display: flex; align-items: center; justify-content: center;
          cursor: pointer; font-size: 14px; background: #fafafa;
          transition: border-color 0.15s, background 0.15s;
        }
        .tl-file-zone:hover { border-color: #888; background: #f3f4f6; }
      `}</style>

      <div className="tl-card" style={{
        background: '#fff',
        borderRadius: 20,
        width: '100%',
        maxWidth: 520,
        padding: 'clamp(36px, 5vw, 52px) clamp(28px, 5vw, 48px)',
        boxShadow: '0 2px 40px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.04)',
      }}>

        {status === 'done' ? (
          /* ── 완료 화면 ── */
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: '#f0fdf4', border: '1.5px solid #86efac',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 24px', fontSize: 28, color: '#16a34a',
            }}>
              ✓
            </div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: '#111', marginBottom: 10 }}>
              요청이 접수되었습니다
            </h2>
            <p style={{ color: '#555', fontSize: 15, lineHeight: 1.7 }}>
              {message || '담당자 확인 후 입력하신 이메일로 접속 링크를 보내드립니다.'}
            </p>
            <p style={{ color: '#aaa', fontSize: 13, marginTop: 16 }}>
              링크 발송까지 영업일 기준 1~2일 소요될 수 있습니다.
            </p>
          </div>
        ) : (
          /* ── 입력 폼 ── */
          <>
            {/* Header */}
            <div style={{ marginBottom: 36 }}>
              <h1 style={{
                fontSize: 36, fontWeight: 700, color: '#111',
                letterSpacing: '-0.5px', margin: '0 0 10px',
              }}>
                Teacher Board
              </h1>
              <p style={{ fontSize: 15, color: '#666', lineHeight: 1.6, margin: 0 }}>
                학교·학원 담당자 전용 인재 열람 페이지입니다.<br />
                아래 정보를 입력하시면 검토 후 접속 링크를 보내드립니다.
              </p>
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

              {/* 학원/학교명 */}
              <FormField label="학원 / 학교명 *">
                <input
                  className="tl-input"
                  type="text"
                  required
                  placeholder="OO어학원 / OO초등학교"
                  value={school}
                  onChange={e => setSchool(e.target.value)}
                  disabled={sending}
                />
              </FormField>

              {/* 도시 및 구 */}
              <FormField label="도시 및 구">
                <input
                  className="tl-input"
                  type="text"
                  placeholder="예: 서울 강남구 / 인천 연수구"
                  value={city}
                  onChange={e => setCity(e.target.value)}
                  disabled={sending}
                />
              </FormField>

              {/* 담당자 이름 + 직책 */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <FormField label="담당자 이름">
                  <input
                    className="tl-input"
                    type="text"
                    placeholder="홍길동"
                    value={contactName}
                    onChange={e => setContactName(e.target.value)}
                    disabled={sending}
                  />
                </FormField>
                <FormField label="직책">
                  <input
                    className="tl-input"
                    type="text"
                    placeholder="원장 / 매니저"
                    value={jobTitle}
                    onChange={e => setJobTitle(e.target.value)}
                    disabled={sending}
                  />
                </FormField>
              </div>

              {/* 연락처 */}
              <FormField label="연락처">
                <input
                  className="tl-input"
                  type="tel"
                  placeholder="010-0000-0000"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  disabled={sending}
                />
              </FormField>

              {/* 이메일 */}
              <FormField label="이메일 주소 *">
                <input
                  className="tl-input"
                  type="email"
                  required
                  placeholder="school@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  disabled={sending}
                />
              </FormField>

              {/* 사업자등록증 첨부 */}
              <FormField label="사업자등록증 첨부 (선택)">
                <div
                  className="tl-file-zone"
                  onClick={() => fileRef.current?.click()}
                  style={{ color: file ? '#111' : '#9ca3af', fontWeight: file ? 500 : 400 }}
                >
                  {file ? `${file.name}` : '클릭하여 파일 첨부 (PDF, JPG, PNG)'}
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  style={{ display: 'none' }}
                  onChange={e => setFile(e.target.files?.[0] ?? null)}
                />
              </FormField>

              {/* 에러 메시지 */}
              {status === 'error' && (
                <p style={{ color: '#dc2626', fontSize: 14, margin: 0 }}>
                  {message}
                </p>
              )}

              {/* 제출 버튼 */}
              <button
                type="submit"
                className="tl-submit"
                disabled={disabled}
                style={{ marginTop: 6 }}
              >
                {sending ? '처리 중...' : '열람 신청'}
              </button>
            </form>

            {/* 법적 경고 푸터 */}
            <p style={{
              fontSize: 12, color: '#bbb', textAlign: 'center',
              marginTop: 28, lineHeight: 1.7,
            }}>
              고용주 및 채용관리자 외 무단접근 및 링크 공유 시<br />
              법적 책임이 따를 수 있습니다.
            </p>
          </>
        )}
      </div>
    </div>
  )
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{
        display: 'block', fontSize: 13, fontWeight: 600,
        color: '#374151', marginBottom: 6,
      }}>
        {label}
      </label>
      {children}
    </div>
  )
}
