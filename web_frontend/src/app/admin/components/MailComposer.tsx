'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { EmployerApp } from './DocBlock'

/* ── 발신자 목록 ── */
const SENDERS = [
  { label: 'Gmail', value: 'bridgejobkr@gmail.com' },
  { label: 'Naver', value: 'bridgejobkr@naver.com' },
] as const

/* ── 메일 양식 ── */
interface MailTemplate {
  name: string
  subject: string
  body: string
}

const TEMPLATES: MailTemplate[] = [
  {
    name: '채용 안내',
    subject: '[BRIDGE] {{name}}님, 우수 원어민 교사를 소개합니다',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>BRIDGE 채용 플랫폼입니다.</p>
<p>{{region}} {{city}} 지역에서 {{teachingAge}} 과정 원어민 교사를 찾고 계신 것으로 확인되었습니다.</p>
<p>현재 BRIDGE에 등록된 우수한 원어민 교사 후보를 소개해 드리고자 합니다.</p>
<br/>
<p>관심이 있으시면 회신 부탁드립니다.</p>
<p>감사합니다.</p>
<p><strong>BRIDGE 채용팀</strong><br/>bridgejob.co.kr</p>`,
  },
  {
    name: '팔로업',
    subject: '[BRIDGE] {{name}}님, 채용 진행 현황 안내',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>이전에 안내드린 원어민 교사 채용 건 관련하여 진행 현황을 안내드립니다.</p>
<p>혹시 채용이 아직 진행 중이시라면, 적합한 후보를 추가로 소개해 드릴 수 있습니다.</p>
<br/>
<p>궁금하신 점이 있으시면 언제든 문의해 주세요.</p>
<p>감사합니다.</p>
<p><strong>BRIDGE 채용팀</strong></p>`,
  },
  {
    name: '긴급 채용',
    subject: '[BRIDGE] 긴급! {{region}} {{city}} 원어민 교사 즉시 배치 가능',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p><strong style="color:red;">긴급 안내</strong> — {{region}} {{city}} 지역에서 즉시 근무 가능한 원어민 교사가 있습니다.</p>
<p>빠른 배치가 필요하신 경우 즉시 회신해 주시면 우선 매칭해 드리겠습니다.</p>
<br/>
<p><strong>BRIDGE 채용팀</strong><br/>bridgejob.co.kr</p>`,
  },
  {
    name: '직접 작성',
    subject: '',
    body: '<p></p>',
  },
]

/* ── 변수 치환 ── */
function subVars(text: string, r: EmployerApp, province: string, cityVal: string): string {
  return text
    .replace(/\{\{name\}\}/g, r.school_name || r.name || '')
    .replace(/\{\{region\}\}/g, province)
    .replace(/\{\{city\}\}/g, cityVal)
    .replace(/\{\{teachingAge\}\}/g, r.teaching_age || '')
    .replace(/\{\{email\}\}/g, r.email || '')
}

/* ── 에디터 커맨드 ── */
function execCmd(cmd: string, val?: string) {
  document.execCommand(cmd, false, val)
}

/* ── 툴바 색상 ── */
const COLORS = [
  { label: '검정', value: '#000000' },
  { label: '빨강', value: '#dc2626' },
  { label: '파랑', value: '#2563eb' },
  { label: '초록', value: '#16a34a' },
  { label: '노랑', value: '#ca8a04' },
  { label: '보라', value: '#9333ea' },
  { label: '회색', value: '#6b7280' },
]

const FONTS = [
  'Nanum Gothic', 'Malgun Gothic', 'Arial', 'Georgia', 'Verdana', 'Courier New',
]

const SIZES = [
  { label: '12', value: '1' }, { label: '14', value: '2' }, { label: '16', value: '3' },
  { label: '18', value: '4' }, { label: '20', value: '5' }, { label: '24', value: '6' },
  { label: '36', value: '7' },
]

/* ══════════════════════════════════════════════════════════════════
   MailComposer
   ══════════════════════════════════════════════════════════════════ */
interface MailComposerProps {
  recipients: EmployerApp[]
  extractProvince: (loc: string | null | undefined) => string
  extractCity: (loc: string | null | undefined) => string
  onClose: () => void
}

export default function MailComposer({ recipients, extractProvince, extractCity, onClose }: MailComposerProps) {
  const [sender, setSender] = useState(SENDERS[0].value)
  const [templateIdx, setTemplateIdx] = useState(0)
  const [subject, setSubject] = useState(TEMPLATES[0].subject)
  const [attachments, setAttachments] = useState<File[]>([])
  const [previewHtml, setPreviewHtml] = useState('')
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  const [showColorPicker, setShowColorPicker] = useState(false)

  const editorRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  /* 템플릿 변경 */
  const selectTemplate = useCallback((idx: number) => {
    setTemplateIdx(idx)
    setSubject(TEMPLATES[idx].subject)
    if (editorRef.current) {
      editorRef.current.innerHTML = TEMPLATES[idx].body
    }
  }, [])

  /* 초기화 */
  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.innerHTML = TEMPLATES[0].body
    }
  }, [])

  /* 미리보기 0.5초 갱신 */
  useEffect(() => {
    const timer = setInterval(() => {
      if (editorRef.current) {
        setPreviewHtml(editorRef.current.innerHTML)
      }
    }, 500)
    return () => clearInterval(timer)
  }, [])

  /* 첨부파일 */
  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files)
    setAttachments(prev => [...prev, ...files])
  }

  const removeAttachment = (idx: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== idx))
  }

  /* 링크 삽입 */
  const insertLink = () => {
    const url = prompt('URL을 입력하세요:')
    if (url) execCmd('createLink', url)
  }

  /* 미리보기용 첫 번째 수신자 */
  const firstR = recipients[0]
  const previewProvince = firstR ? extractProvince(firstR.location) : ''
  const previewCity = firstR ? extractCity(firstR.location) : ''
  const previewSubject = firstR ? subVars(subject, firstR, previewProvince, previewCity) : subject
  const previewBody = firstR ? subVars(previewHtml, firstR, previewProvince, previewCity) : previewHtml

  /* 발송 */
  const handleSend = async () => {
    if (sending || recipients.length === 0) return
    setSending(true)
    try {
      const bodyHtml = editorRef.current?.innerHTML || ''
      const payload = {
        sender,
        subject,
        body_html: bodyHtml,
        recipients: recipients.map(r => ({
          email: r.email,
          name: r.school_name || r.name,
          region: extractProvince(r.location),
          city: extractCity(r.location),
          teachingAge: r.teaching_age || '',
        })),
      }

      const adminKey = typeof window !== 'undefined' ? localStorage.getItem('bridge_admin_key') || '' : ''
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || ''

      const res = await fetch(`${apiUrl}/api/admin/mail/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify(payload),
      })

      if (res.ok) {
        setSent(true)
        setTimeout(() => onClose(), 2000)
      } else {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
        alert(`발송 실패: ${err.detail || err.message || 'Server error'}`)
      }
    } catch {
      alert('네트워크 오류. 발송 실패.')
    } finally {
      setSending(false)
    }
  }

  /* 발송 완료 화면 */
  if (sent) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <div className="bg-white rounded-2xl shadow-2xl p-10 text-center max-w-sm">
          <div className="text-5xl mb-4">&#9989;</div>
          <h3 className="text-[18px] font-bold text-[#1d1d1f]">발송 완료</h3>
          <p className="text-[13px] text-gray-500 mt-2">{recipients.length}명에게 개별 발송되었습니다.</p>
          <p className="text-[11px] text-gray-400 mt-3">2초 후 자동 닫힘</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-[1100px] max-h-[90vh] overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between shrink-0">
          <h2 className="text-[16px] font-bold text-[#1d1d1f]">메일 작성</h2>
          <button type="button" onClick={onClose} className="w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 text-sm">&#10005;</button>
        </div>

        {/* 메인 (좌: 작성, 우: 미리보기) */}
        <div className="flex flex-1 overflow-hidden min-h-0">
          {/* ── 좌측: 작성 영역 ── */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4 border-r border-gray-100">
            {/* 양식 선택 */}
            <div>
              <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">메일 양식</label>
              <div className="flex gap-2">
                {TEMPLATES.map((t, i) => (
                  <button
                    key={t.name}
                    type="button"
                    onClick={() => selectTemplate(i)}
                    className={`px-3 py-1.5 text-[12px] rounded-lg font-medium transition-colors ${
                      templateIdx === i ? 'bg-[#0071E3] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {t.name}
                  </button>
                ))}
              </div>
            </div>

            {/* 보내는 사람 */}
            <div>
              <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">보내는 사람</label>
              <div className="flex gap-2">
                {SENDERS.map(s => (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => setSender(s.value)}
                    className={`px-3 py-1.5 text-[12px] rounded-lg font-medium transition-colors ${
                      sender === s.value ? 'bg-[#1d1d1f] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
                <span className="text-[12px] text-gray-400 self-center ml-1">{sender}</span>
              </div>
            </div>

            {/* 받는 사람 */}
            <div>
              <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">
                받는 사람 ({recipients.length}명)
              </label>
              <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto">
                {recipients.map(r => (
                  <span key={r.id} className="inline-flex items-center px-2 py-1 bg-gray-100 text-[11px] text-gray-700 rounded-lg">
                    {r.school_name || r.name}
                  </span>
                ))}
              </div>
            </div>

            {/* 제목 */}
            <div>
              <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">제목</label>
              <input
                type="text"
                value={subject}
                onChange={e => setSubject(e.target.value)}
                className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0071E3]/30 focus:border-[#0071E3]"
                placeholder="메일 제목..."
              />
            </div>

            {/* HTML 에디터 */}
            <div>
              <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">본문</label>

              {/* 툴바 */}
              <div className="flex flex-wrap items-center gap-1 p-2 bg-gray-50 border border-gray-200 rounded-t-lg border-b-0">
                {/* 폰트 */}
                <select
                  onChange={e => execCmd('fontName', e.target.value)}
                  className="text-[11px] px-1.5 py-1 border border-gray-200 rounded bg-white"
                  defaultValue=""
                >
                  <option value="" disabled>폰트</option>
                  {FONTS.map(f => <option key={f} value={f}>{f}</option>)}
                </select>

                {/* 크기 */}
                <select
                  onChange={e => execCmd('fontSize', e.target.value)}
                  className="text-[11px] px-1.5 py-1 border border-gray-200 rounded bg-white"
                  defaultValue=""
                >
                  <option value="" disabled>크기</option>
                  {SIZES.map(s => <option key={s.value} value={s.value}>{s.label}px</option>)}
                </select>

                <span className="w-px h-5 bg-gray-200 mx-0.5" />

                {/* B/I/U/S */}
                <button type="button" onClick={() => execCmd('bold')} className="w-7 h-7 flex items-center justify-center text-[13px] font-bold rounded hover:bg-gray-200" title="Bold">B</button>
                <button type="button" onClick={() => execCmd('italic')} className="w-7 h-7 flex items-center justify-center text-[13px] italic rounded hover:bg-gray-200" title="Italic">I</button>
                <button type="button" onClick={() => execCmd('underline')} className="w-7 h-7 flex items-center justify-center text-[13px] underline rounded hover:bg-gray-200" title="Underline">U</button>
                <button type="button" onClick={() => execCmd('strikeThrough')} className="w-7 h-7 flex items-center justify-center text-[13px] line-through rounded hover:bg-gray-200" title="Strikethrough">S</button>

                <span className="w-px h-5 bg-gray-200 mx-0.5" />

                {/* 색상 */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowColorPicker(!showColorPicker)}
                    className="w-7 h-7 flex items-center justify-center text-[13px] rounded hover:bg-gray-200"
                    title="글자 색상"
                  >
                    A
                  </button>
                  {showColorPicker && (
                    <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-2 flex gap-1 z-50">
                      {COLORS.map(c => (
                        <button
                          key={c.value}
                          type="button"
                          onClick={() => { execCmd('foreColor', c.value); setShowColorPicker(false) }}
                          className="w-6 h-6 rounded-full border border-gray-200 hover:scale-110 transition-transform"
                          style={{ backgroundColor: c.value }}
                          title={c.label}
                        />
                      ))}
                    </div>
                  )}
                </div>

                <span className="w-px h-5 bg-gray-200 mx-0.5" />

                {/* 정렬 */}
                <button type="button" onClick={() => execCmd('justifyLeft')} className="w-7 h-7 flex items-center justify-center text-[11px] rounded hover:bg-gray-200" title="좌측">&#9776;</button>
                <button type="button" onClick={() => execCmd('justifyCenter')} className="w-7 h-7 flex items-center justify-center text-[11px] rounded hover:bg-gray-200" title="가운데">&#9776;</button>
                <button type="button" onClick={() => execCmd('justifyRight')} className="w-7 h-7 flex items-center justify-center text-[11px] rounded hover:bg-gray-200" title="우측">&#9776;</button>

                <span className="w-px h-5 bg-gray-200 mx-0.5" />

                {/* 목록 */}
                <button type="button" onClick={() => execCmd('insertUnorderedList')} className="w-7 h-7 flex items-center justify-center text-[12px] rounded hover:bg-gray-200" title="글머리">&#8226;</button>
                <button type="button" onClick={() => execCmd('insertOrderedList')} className="w-7 h-7 flex items-center justify-center text-[12px] rounded hover:bg-gray-200" title="번호">1.</button>

                {/* 링크 */}
                <button type="button" onClick={insertLink} className="w-7 h-7 flex items-center justify-center text-[12px] rounded hover:bg-gray-200" title="링크">&#128279;</button>

                {/* 서식 제거 */}
                <button type="button" onClick={() => execCmd('removeFormat')} className="w-7 h-7 flex items-center justify-center text-[11px] font-bold rounded hover:bg-gray-200 text-red-400" title="서식 제거">Tx</button>
              </div>

              {/* contentEditable */}
              <div
                ref={editorRef}
                contentEditable
                suppressContentEditableWarning
                className="w-full min-h-[250px] max-h-[400px] overflow-y-auto px-4 py-3 text-[13px] border border-gray-200 rounded-b-lg focus:outline-none focus:ring-2 focus:ring-[#0071E3]/20 bg-white leading-relaxed"
                style={{ fontFamily: 'Nanum Gothic, sans-serif' }}
              />

              <p className="text-[10px] text-gray-400 mt-1">
                변수: {'{{name}}'} {'{{region}}'} {'{{city}}'} {'{{teachingAge}}'} {'{{email}}'}
              </p>
            </div>

            {/* 첨부파일 */}
            <div>
              <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">첨부파일</label>
              <div
                className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center hover:border-blue-300 transition-colors cursor-pointer"
                onDragOver={e => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <p className="text-[12px] text-gray-400">파일을 드래그하거나 클릭하여 추가</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={e => {
                    if (e.target.files) setAttachments(prev => [...prev, ...Array.from(e.target.files!)])
                  }}
                />
              </div>
              {attachments.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {attachments.map((f, i) => (
                    <span key={`${f.name}-${i}`} className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-[11px] text-gray-600 rounded">
                      {f.name}
                      <button type="button" onClick={() => removeAttachment(i)} className="text-red-400 hover:text-red-600 ml-0.5">&#10005;</button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── 우측: 미리보기 ── */}
          <div className="w-[400px] shrink-0 overflow-y-auto p-5 bg-gray-50">
            <h3 className="text-[12px] font-bold text-gray-500 uppercase tracking-wider mb-3">미리보기</h3>

            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {/* 헤더 */}
              <div className="px-4 py-3 border-b border-gray-100 space-y-1.5">
                <div className="text-[11px]">
                  <span className="text-gray-400 font-medium">From:</span>
                  <span className="text-gray-700 ml-1">BRIDGE &lt;{sender}&gt;</span>
                </div>
                <div className="text-[11px]">
                  <span className="text-gray-400 font-medium">To:</span>
                  <span className="text-gray-700 ml-1">
                    {firstR ? `${firstR.school_name || firstR.name}` : '—'}
                    {recipients.length > 1 && <span className="text-gray-400 ml-1">(+{recipients.length - 1}명 개별발송)</span>}
                  </span>
                </div>
                <div className="text-[11px]">
                  <span className="text-gray-400 font-medium">Subject:</span>
                  <span className="text-gray-700 ml-1 font-medium">{previewSubject}</span>
                </div>
              </div>

              {/* 본문 */}
              <div
                className="px-4 py-4 text-[13px] leading-relaxed"
                style={{ fontFamily: 'Nanum Gothic, sans-serif' }}
                dangerouslySetInnerHTML={{ __html: previewBody }}
              />

              {/* 첨부파일 */}
              {attachments.length > 0 && (
                <div className="px-4 py-2 border-t border-gray-100">
                  <span className="text-[10px] text-gray-400 font-medium">첨부 ({attachments.length})</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {attachments.map((f, i) => (
                      <span key={`p-${f.name}-${i}`} className="text-[10px] text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded">{f.name}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 하단 발송 바 */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between shrink-0 bg-white">
          <p className="text-[11px] text-gray-400">
            From: {sender} &middot; 각 수신자에게 1:1 개별 발송 &middot; 타인 정보 절대 미노출
          </p>
          <button
            type="button"
            onClick={handleSend}
            disabled={sending || recipients.length === 0}
            className="px-5 py-2.5 bg-[#0071E3] text-white text-[13px] font-semibold rounded-xl hover:bg-[#0066CC] transition-colors disabled:opacity-50 shadow-sm"
          >
            {sending ? '발송 중...' : `메일 발송 (${recipients.length}명 개별 발송)`}
          </button>
        </div>
      </div>
    </div>
  )
}
