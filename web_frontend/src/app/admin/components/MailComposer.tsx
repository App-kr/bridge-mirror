'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { EmployerApp } from './DocBlock'

/* ── 발신자 ── */
const SENDERS = [
  { label: 'Gmail', value: 'bridgejobkr@gmail.com' },
  { label: 'Naver', value: 'bridgejobkr@naver.com' },
]

/* ── 메일 양식 ── */
interface MailTemplate { name: string; subject: string; body: string }

const TEMPLATES: MailTemplate[] = [
  {
    name: '📢 소개발송',
    subject: '📢 BRIDGE 원어민 강사 소식 — 국내/해외 프로필 확인하세요',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>BRIDGE 원어민 강사 프로필을 공유드립니다.<br/>Start date and preferences noted. Reference provided for review only.</p>
<hr style="border:none;border-top:1px solid #ddd;margin:16px 0;"/>
<p><em>아래 프로필을 확인해 주시고, 관심 있으신 경우 회신 부탁드립니다.</em></p>
<p>&nbsp;</p>
<p style="font-size:12px;color:#888;">💡 If you are not the intended recipient or no longer in this role, please notify us and delete this email. Additionally, let us know if any contact should be removed due to a change in management.</p>`,
  },
  {
    name: '기본안내',
    subject: '[BRIDGE] 안내드립니다',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>BRIDGE 리크루팅입니다.</p>
<p>&nbsp;</p>
<p>감사합니다.<br/><strong>BRIDGE Recruitment Team</strong></p>`,
  },
  {
    name: '요금안내',
    subject: '[BRIDGE] 서비스 요금 안내',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>요청하신 서비스 요금을 안내드립니다.</p>
<p>&nbsp;</p>
<p>감사합니다.<br/><strong>BRIDGE</strong></p>`,
  },
  {
    name: '체결안내',
    subject: '[BRIDGE] 계약 체결 안내',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>계약 체결 관련 안내드립니다.</p>
<p>&nbsp;</p>
<p>감사합니다.<br/><strong>BRIDGE Recruitment Team</strong></p>`,
  },
  {
    name: '확정안내',
    subject: '[BRIDGE] 채용 확정 안내',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>채용이 확정되었음을 안내드립니다.</p>
<p>&nbsp;</p>
<p>감사합니다.<br/><strong>BRIDGE Recruitment Team</strong></p>`,
  },
  {
    name: '입국안내',
    subject: '[BRIDGE] 입국 관련 안내',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>입국 일정 관련 안내드립니다.</p>
<p>&nbsp;</p>
<p>감사합니다.<br/><strong>BRIDGE Recruitment Team</strong></p>`,
  },
  {
    name: '출입국업무',
    subject: '[BRIDGE] 출입국 업무 안내',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>출입국 업무 관련 안내드립니다.</p>
<p>&nbsp;</p>
<p>감사합니다.<br/><strong>BRIDGE Recruitment Team</strong></p>`,
  },
  {
    name: '채용정보접수',
    subject: '[BRIDGE] 채용 정보 접수 확인',
    body: `<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p>
<p>채용 정보를 접수하였습니다.</p>
<p>&nbsp;</p>
<p>감사합니다.<br/><strong>BRIDGE Recruitment Team</strong></p>`,
  },
  {
    name: '직접작성',
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

/* ── execCommand helper ── */
function execCmd(cmd: string, val?: string) {
  document.execCommand(cmd, false, val)
}

/* ── 수신자 이메일 파싱 ── */
function parseEmails(raw: string): string[] {
  return raw
    .split(/[,;\n\r\s]+/)
    .map(e => e.trim().toLowerCase())
    .filter(e => e.includes('@') && e.includes('.') && e.length > 4)
}

/* ── 색상 팔레트 ── */
const TEXT_COLORS = [
  { label: '검정', value: '#000000' },
  { label: '빨강', value: '#dc2626' },
  { label: '파랑', value: '#2563eb' },
  { label: '초록', value: '#16a34a' },
  { label: '주황', value: '#ea580c' },
  { label: '노랑', value: '#ca8a04' },
  { label: '보라', value: '#9333ea' },
  { label: '분홍', value: '#db2777' },
  { label: '청록', value: '#0891b2' },
  { label: '회색', value: '#6b7280' },
]

const BG_COLORS = [
  { label: '없음', value: 'transparent' },
  { label: '옅은노랑', value: '#fefce8' },
  { label: '노랑', value: '#fef08a' },
  { label: '옅은빨강', value: '#fef2f2' },
  { label: '연분홍', value: '#fecdd3' },
  { label: '연두', value: '#bbf7d0' },
  { label: '옅은파랑', value: '#eff6ff' },
  { label: '하늘', value: '#bae6fd' },
  { label: '옅은보라', value: '#faf5ff' },
  { label: '연보라', value: '#e9d5ff' },
  { label: '주황', value: '#fed7aa' },
]

const FONTS = ['Nanum Gothic', 'Malgun Gothic', 'Arial', 'Georgia', 'Verdana', 'Courier New']

const SIZES = [
  { label: '12', value: '1' }, { label: '14', value: '2' }, { label: '16', value: '3' },
  { label: '18', value: '4' }, { label: '20', value: '5' }, { label: '24', value: '6' },
  { label: '36', value: '7' },
]

const LINE_SPACINGS = [
  { label: '1.0', value: '1.0' }, { label: '1.2', value: '1.2' }, { label: '1.5', value: '1.5' },
  { label: '1.8', value: '1.8' }, { label: '2.0', value: '2.0' }, { label: '2.5', value: '2.5' },
]

/* ── 파일 아이콘 ── */
function fileIcon(f: File): string {
  if (f.type.startsWith('image/')) return '🖼'
  if (f.type.includes('pdf')) return '📄'
  if (f.type.includes('video')) return '🎥'
  if (f.type.includes('word') || f.name.endsWith('.doc') || f.name.endsWith('.docx')) return '📝'
  return '📎'
}

/* ── 파일 크기 표시 ── */
function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

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

  // 팔레트 표시 상태
  const [showTextColor, setShowTextColor] = useState(false)
  const [showBgColor, setShowBgColor] = useState(false)

  // 링크 패널
  const [showLinkPanel, setShowLinkPanel] = useState(false)
  const [linkUrl, setLinkUrl] = useState('https://')
  const [linkText, setLinkText] = useState('')
  const savedRangeRef = useRef<Range | null>(null)

  // 수동 수신자
  const [recipientInput, setRecipientInput] = useState('')
  const [manualEmails, setManualEmails] = useState<string[]>([])

  // 이미지 리사이즈
  const [selectedImg, setSelectedImg] = useState<HTMLImageElement | null>(null)
  const [imgRect, setImgRect] = useState<DOMRect | null>(null)
  const [imgWidth, setImgWidth] = useState('')
  const resizingRef = useRef(false)
  const resizeStartRef = useRef({ x: 0, width: 0 })

  const editorRef = useRef<HTMLDivElement>(null)
  const attachInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)

  /* 템플릿 변경 */
  const selectTemplate = useCallback((idx: number) => {
    setTemplateIdx(idx)
    setSubject(TEMPLATES[idx].subject)
    if (editorRef.current) editorRef.current.innerHTML = TEMPLATES[idx].body
  }, [])

  /* 초기화 */
  useEffect(() => {
    if (editorRef.current) editorRef.current.innerHTML = TEMPLATES[0].body
  }, [])

  /* 미리보기 0.5초 갱신 */
  useEffect(() => {
    const timer = setInterval(() => {
      if (editorRef.current) setPreviewHtml(editorRef.current.innerHTML)
    }, 500)
    return () => clearInterval(timer)
  }, [])

  /* 이미지 붙여넣기 (Ctrl+V) */
  useEffect(() => {
    const editor = editorRef.current
    if (!editor) return
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of Array.from(items)) {
        if (item.type.startsWith('image/')) {
          e.preventDefault()
          const file = item.getAsFile()
          if (!file) continue
          const reader = new FileReader()
          reader.onload = (ev) => {
            const dataUrl = ev.target?.result as string
            editorRef.current?.focus()
            execCmd('insertHTML', `<img src="${dataUrl}" style="max-width:100%;height:auto;display:block;margin:6px 0;" alt="image"/>`)
          }
          reader.readAsDataURL(file)
          break
        }
      }
    }
    editor.addEventListener('paste', handlePaste)
    return () => editor.removeEventListener('paste', handlePaste)
  }, [])

  /* 이미지 선택 outline 관리 */
  useEffect(() => {
    editorRef.current?.querySelectorAll('img').forEach(img => {
      (img as HTMLImageElement).style.outline = ''
    })
    if (selectedImg) {
      selectedImg.style.outline = '2px solid #0071E3'
      selectedImg.style.outlineOffset = '2px'
    }
  }, [selectedImg])

  /* 이미지 리사이즈 드래그 */
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!resizingRef.current || !selectedImg) return
      const dx = e.clientX - resizeStartRef.current.x
      const newW = Math.max(40, resizeStartRef.current.width + dx)
      selectedImg.style.width = `${newW}px`
      selectedImg.style.height = 'auto'
      setImgRect(selectedImg.getBoundingClientRect())
      setImgWidth(String(Math.round(newW)))
    }
    const onUp = () => { resizingRef.current = false }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [selectedImg])

  /* 이미지 클릭 감지 */
  const handleEditorClick = (e: React.MouseEvent) => {
    closePopovers()
    const target = e.target as HTMLElement
    if (target.tagName === 'IMG') {
      const img = target as HTMLImageElement
      setSelectedImg(img)
      setImgRect(img.getBoundingClientRect())
      setImgWidth(String(img.offsetWidth))
    } else {
      setSelectedImg(null)
      setImgRect(null)
    }
  }

  /* 이미지 크기 설정 */
  const applyImgWidth = (w: string | number) => {
    if (!selectedImg) return
    selectedImg.style.width = typeof w === 'number' ? `${w}px` : w
    selectedImg.style.height = 'auto'
    setImgRect(selectedImg.getBoundingClientRect())
    setImgWidth(String(selectedImg.offsetWidth))
  }

  /* 이미지 삭제 */
  const deleteSelectedImg = () => {
    selectedImg?.remove()
    setSelectedImg(null)
    setImgRect(null)
  }

  /* 첨부파일 추가 */
  const addFiles = (files: FileList | File[]) => {
    setAttachments(prev => [...prev, ...Array.from(files)])
  }

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    addFiles(e.dataTransfer.files)
  }

  const removeAttachment = (idx: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== idx))
  }

  /* 이미지를 본문에 삽입 */
  const insertImageFromFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string
      editorRef.current?.focus()
      execCmd('insertHTML', `<img src="${dataUrl}" style="max-width:100%;height:auto;display:block;margin:6px 0;" alt="${file.name}"/>`)
    }
    reader.readAsDataURL(file)
  }

  /* 링크 패널 열기 (선택 영역 저장) */
  const openLinkPanel = () => {
    const sel = window.getSelection()
    if (sel && sel.rangeCount > 0) {
      savedRangeRef.current = sel.getRangeAt(0).cloneRange()
      setLinkText(sel.toString())
    }
    setShowLinkPanel(true)
    setShowTextColor(false)
    setShowBgColor(false)
  }

  /* 링크 삽입 */
  const applyLink = () => {
    if (!linkUrl) return
    const sel = window.getSelection()
    if (savedRangeRef.current) {
      sel?.removeAllRanges()
      sel?.addRange(savedRangeRef.current)
    }
    editorRef.current?.focus()
    if (linkText && (!sel || sel.toString() === '')) {
      execCmd('insertHTML', `<a href="${linkUrl}">${linkText}</a>`)
    } else {
      execCmd('createLink', linkUrl)
    }
    setShowLinkPanel(false)
    setLinkUrl('https://')
    setLinkText('')
    savedRangeRef.current = null
  }

  /* 줄간격 적용 */
  const applyLineSpacing = (value: string) => {
    const sel = window.getSelection()
    if (!sel || !sel.rangeCount || !editorRef.current) return
    const range = sel.getRangeAt(0)
    let node: Node | null = range.commonAncestorContainer
    while (node && node !== editorRef.current) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        const el = node as HTMLElement
        if (['P', 'DIV', 'LI', 'H1', 'H2', 'H3'].includes(el.tagName)) {
          el.style.lineHeight = value
          return
        }
      }
      node = node.parentNode
    }
    editorRef.current.style.lineHeight = value
  }

  /* 수신자 텍스트 파싱 */
  const parseRecipientInput = () => {
    if (!recipientInput.trim()) return
    const emails = parseEmails(recipientInput)
    const newEmails = emails.filter(e => !manualEmails.includes(e))
    if (newEmails.length > 0) setManualEmails(prev => [...prev, ...newEmails])
    setRecipientInput('')
  }

  const removeManualEmail = (email: string) => {
    setManualEmails(prev => prev.filter(e => e !== email))
  }

  /* 미리보기 */
  const firstR = recipients[0]
  const previewProvince = firstR ? extractProvince(firstR.location) : ''
  const previewCity = firstR ? extractCity(firstR.location) : ''
  const previewSubject = firstR ? subVars(subject, firstR, previewProvince, previewCity) : subject
  const previewBody = firstR ? subVars(previewHtml, firstR, previewProvince, previewCity) : previewHtml

  const totalRecipients = recipients.length + manualEmails.length

  /* 발송 */
  const handleSend = async () => {
    if (sending || totalRecipients === 0) return
    setSending(true)
    try {
      const bodyHtml = editorRef.current?.innerHTML || ''
      const employerRecips = recipients.map(r => ({
        email: r.email,
        name: r.school_name || r.name,
        region: extractProvince(r.location),
        city: extractCity(r.location),
        teachingAge: r.teaching_age || '',
      }))
      const manualRecips = manualEmails.map(email => ({
        email,
        name: email,
        region: '',
        city: '',
        teachingAge: '',
      }))
      const payload = {
        sender,
        subject,
        body_html: bodyHtml,
        recipients: [...employerRecips, ...manualRecips],
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

  /* 팔레트/패널 닫기 */
  const closePopovers = () => {
    setShowTextColor(false)
    setShowBgColor(false)
    setShowLinkPanel(false)
  }

  /* 발송 완료 화면 */
  if (sent) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <div className="bg-white rounded-2xl shadow-2xl p-10 text-center max-w-sm">
          <div className="text-5xl mb-4">&#9989;</div>
          <h3 className="text-[18px] font-bold text-[#1d1d1f]">발송 완료</h3>
          <p className="text-[13px] text-gray-500 mt-2">{totalRecipients}명에게 개별 발송되었습니다.</p>
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
          {/* ── 좌측: 작성 ── */}
          <div className="flex-1 overflow-y-auto p-5 space-y-3 border-r border-gray-100">

            {/* 메일 양식 */}
            <div>
              <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">메일 양식</label>
              <div className="flex flex-wrap gap-1.5">
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
                받는 사람 ({totalRecipients}명)
              </label>
              {/* 선택된 업체 칩 */}
              {recipients.length > 0 && (
                <div className="flex flex-wrap gap-1.5 max-h-14 overflow-y-auto mb-2">
                  {recipients.map(r => (
                    <span key={r.id} className="inline-flex items-center px-2 py-1 bg-blue-50 text-[11px] text-blue-700 rounded-lg">
                      {r.school_name || r.name}
                    </span>
                  ))}
                </div>
              )}
              {/* 이메일 직접 입력/붙여넣기 */}
              <input
                type="text"
                value={recipientInput}
                onChange={e => setRecipientInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' || e.key === ',') {
                    e.preventDefault()
                    parseRecipientInput()
                  }
                }}
                onBlur={parseRecipientInput}
                onPaste={() => setTimeout(parseRecipientInput, 50)}
                placeholder="이메일 직접 추가 — 콤마·세미콜론·줄바꿈으로 여러 개 붙여넣기 가능"
                className="w-full px-3 py-2 text-[12px] border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0071E3]/30 focus:border-[#0071E3]"
              />
              {manualEmails.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-1.5 max-h-14 overflow-y-auto">
                  {manualEmails.map(email => (
                    <span key={email} className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-[11px] text-gray-700 rounded-lg">
                      {email}
                      <button type="button" onClick={() => removeManualEmail(email)} className="text-red-400 hover:text-red-600 ml-0.5">&#10005;</button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* 첨부파일 (제목 위) */}
            <div>
              <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">첨부파일</label>
              <div
                className="border-2 border-dashed border-gray-200 rounded-lg px-3 py-2 flex items-center gap-2 hover:border-blue-300 hover:bg-blue-50/30 transition-colors cursor-pointer"
                onDragOver={e => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => attachInputRef.current?.click()}
              >
                <span className="text-[18px]">📎</span>
                <span className="text-[12px] text-gray-400 flex-1">파일 드래그 또는 클릭 &middot; 이미지·동영상·PDF·Word 등 모든 형식 &middot; 대용량 가능 &middot; 여러 개 첨부</span>
                <input
                  ref={attachInputRef}
                  type="file"
                  multiple
                  accept="*/*"
                  className="hidden"
                  onChange={e => { if (e.target.files) { addFiles(e.target.files); e.currentTarget.value = '' } }}
                />
              </div>
              {attachments.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {attachments.map((f, i) => (
                    <span key={`${f.name}-${i}`} className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-[11px] text-gray-600 rounded">
                      {fileIcon(f)} {f.name}
                      <span className="text-gray-400 ml-0.5">({fmtSize(f.size)})</span>
                      <button type="button" onClick={() => removeAttachment(i)} className="text-red-400 hover:text-red-600 ml-0.5">&#10005;</button>
                    </span>
                  ))}
                </div>
              )}
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

            {/* 본문 에디터 */}
            <div>
              <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">본문</label>

              {/* ── 툴바 ── */}
              <div className="flex flex-wrap items-center gap-0.5 p-1.5 bg-gray-50 border border-gray-200 rounded-t-lg border-b-0">

                {/* 폰트 */}
                <select
                  onChange={e => execCmd('fontName', e.target.value)}
                  className="text-[11px] px-1 py-1 border border-gray-200 rounded bg-white max-w-[100px]"
                  defaultValue=""
                >
                  <option value="" disabled>폰트</option>
                  {FONTS.map(f => <option key={f} value={f}>{f}</option>)}
                </select>

                {/* 크기 */}
                <select
                  onChange={e => execCmd('fontSize', e.target.value)}
                  className="text-[11px] px-1 py-1 border border-gray-200 rounded bg-white"
                  defaultValue=""
                >
                  <option value="" disabled>크기</option>
                  {SIZES.map(s => <option key={s.label} value={s.value}>{s.label}px</option>)}
                </select>

                {/* 줄간격 */}
                <select
                  onChange={e => applyLineSpacing(e.target.value)}
                  className="text-[11px] px-1 py-1 border border-gray-200 rounded bg-white"
                  defaultValue=""
                >
                  <option value="" disabled>줄간격</option>
                  {LINE_SPACINGS.map(ls => <option key={ls.value} value={ls.value}>{ls.label}</option>)}
                </select>

                <span className="w-px h-5 bg-gray-200 mx-0.5" />

                {/* B / I / U / S */}
                <button type="button" onClick={() => execCmd('bold')} className="w-7 h-7 flex items-center justify-center text-[13px] font-bold rounded hover:bg-gray-200" title="굵게">B</button>
                <button type="button" onClick={() => execCmd('italic')} className="w-7 h-7 flex items-center justify-center text-[13px] italic rounded hover:bg-gray-200" title="기울임">I</button>
                <button type="button" onClick={() => execCmd('underline')} className="w-7 h-7 flex items-center justify-center text-[13px] underline rounded hover:bg-gray-200" title="밑줄">U</button>
                <button type="button" onClick={() => execCmd('strikeThrough')} className="w-7 h-7 flex items-center justify-center text-[13px] line-through rounded hover:bg-gray-200" title="취소선">S</button>

                <span className="w-px h-5 bg-gray-200 mx-0.5" />

                {/* 글자 색 */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => { setShowTextColor(v => !v); setShowBgColor(false); setShowLinkPanel(false) }}
                    className="w-7 h-7 flex items-center justify-center text-[13px] font-bold rounded hover:bg-gray-200"
                    title="글자 색"
                  >
                    <span className="font-bold" style={{ borderBottom: '3px solid #dc2626' }}>A</span>
                  </button>
                  {showTextColor && (
                    <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-2 flex flex-wrap gap-1 z-50 w-[130px]">
                      {TEXT_COLORS.map(c => (
                        <button
                          key={c.value}
                          type="button"
                          onClick={() => { execCmd('foreColor', c.value); setShowTextColor(false) }}
                          className="w-6 h-6 rounded-full border border-gray-200 hover:scale-110 transition-transform"
                          style={{ backgroundColor: c.value }}
                          title={c.label}
                        />
                      ))}
                    </div>
                  )}
                </div>

                {/* 배경 색 */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => { setShowBgColor(v => !v); setShowTextColor(false); setShowLinkPanel(false) }}
                    className="w-7 h-7 flex items-center justify-center rounded hover:bg-gray-200"
                    title="배경 색"
                  >
                    <span className="w-4 h-4 rounded border border-gray-300 block" style={{ background: 'linear-gradient(135deg, #fef08a 50%, #bae6fd 50%)' }} />
                  </button>
                  {showBgColor && (
                    <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-2 flex flex-wrap gap-1 z-50 w-[110px]">
                      {BG_COLORS.map(c => (
                        <button
                          key={c.value}
                          type="button"
                          onClick={() => {
                            document.execCommand('styleWithCSS', false, 'true')
                            execCmd('hiliteColor', c.value === 'transparent' ? 'transparent' : c.value)
                            setShowBgColor(false)
                          }}
                          className="w-6 h-6 rounded border border-gray-300 hover:scale-110 transition-transform flex items-center justify-center"
                          style={{ backgroundColor: c.value === 'transparent' ? '#fff' : c.value }}
                          title={c.label}
                        >
                          {c.value === 'transparent' && <span className="text-[9px] text-gray-400 font-bold">✕</span>}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <span className="w-px h-5 bg-gray-200 mx-0.5" />

                {/* 정렬 */}
                <button type="button" onClick={() => execCmd('justifyLeft')} className="w-7 h-7 flex items-center justify-center text-[10px] rounded hover:bg-gray-200" title="좌측 정렬">&#9776;</button>
                <button type="button" onClick={() => execCmd('justifyCenter')} className="w-7 h-7 flex items-center justify-center text-[11px] rounded hover:bg-gray-200" title="가운데">&#8801;</button>
                <button type="button" onClick={() => execCmd('justifyRight')} className="w-7 h-7 flex items-center justify-center text-[10px] rounded hover:bg-gray-200" title="우측 정렬" style={{ transform: 'scaleX(-1)' }}>&#9776;</button>

                <span className="w-px h-5 bg-gray-200 mx-0.5" />

                {/* 목록 */}
                <button type="button" onClick={() => execCmd('insertUnorderedList')} className="w-7 h-7 flex items-center justify-center text-[11px] rounded hover:bg-gray-200" title="글머리 목록">&#8226;&#8801;</button>
                <button type="button" onClick={() => execCmd('insertOrderedList')} className="w-7 h-7 flex items-center justify-center text-[11px] rounded hover:bg-gray-200" title="번호 목록">1&#8801;</button>

                {/* 구분선 */}
                <button
                  type="button"
                  onClick={() => execCmd('insertHorizontalRule')}
                  className="w-7 h-7 flex items-center justify-center text-[11px] rounded hover:bg-gray-200"
                  title="구분선"
                >
                  &#8212;
                </button>

                <span className="w-px h-5 bg-gray-200 mx-0.5" />

                {/* 링크 삽입 */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={openLinkPanel}
                    className="w-7 h-7 flex items-center justify-center text-[12px] rounded hover:bg-gray-200"
                    title="링크 삽입"
                  >
                    &#128279;
                  </button>
                  {showLinkPanel && (
                    <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-xl p-3 z-50 w-[280px] space-y-2">
                      <p className="text-[11px] font-semibold text-gray-500">링크 삽입</p>
                      <input
                        type="text"
                        value={linkText}
                        onChange={e => setLinkText(e.target.value)}
                        placeholder="표시 텍스트 (선택사항)"
                        className="w-full px-2 py-1.5 text-[12px] border border-gray-200 rounded focus:outline-none focus:border-blue-400"
                      />
                      <input
                        type="text"
                        value={linkUrl}
                        onChange={e => setLinkUrl(e.target.value)}
                        placeholder="https://..."
                        className="w-full px-2 py-1.5 text-[12px] border border-gray-200 rounded focus:outline-none focus:border-blue-400"
                        autoFocus
                        onKeyDown={e => { if (e.key === 'Enter') applyLink() }}
                      />
                      <div className="flex gap-2">
                        <button type="button" onClick={applyLink} className="flex-1 px-3 py-1.5 bg-[#0071E3] text-white text-[12px] font-semibold rounded hover:bg-[#005ec7]">삽입</button>
                        <button type="button" onClick={() => setShowLinkPanel(false)} className="px-3 py-1.5 text-[12px] border border-gray-200 rounded hover:bg-gray-50">취소</button>
                      </div>
                    </div>
                  )}
                </div>

                {/* 이미지 본문 삽입 */}
                <button
                  type="button"
                  onClick={() => imageInputRef.current?.click()}
                  className="w-7 h-7 flex items-center justify-center text-[12px] rounded hover:bg-gray-200"
                  title="이미지 삽입 (본문에 직접)"
                >
                  &#128444;
                </button>
                <input
                  ref={imageInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={e => {
                    const file = e.target.files?.[0]
                    if (file) insertImageFromFile(file)
                    e.currentTarget.value = ''
                  }}
                />

                {/* 서식 제거 */}
                <button
                  type="button"
                  onClick={() => execCmd('removeFormat')}
                  className="w-7 h-7 flex items-center justify-center text-[11px] font-bold rounded hover:bg-gray-200 text-red-400"
                  title="서식 제거"
                >
                  Tx
                </button>
              </div>

              {/* contentEditable 본문 */}
              <div
                ref={editorRef}
                contentEditable
                suppressContentEditableWarning
                onClick={handleEditorClick}
                className="w-full min-h-[240px] max-h-[360px] overflow-y-auto px-4 py-3 text-[13px] border border-gray-200 rounded-b-lg focus:outline-none focus:ring-2 focus:ring-[#0071E3]/20 bg-white leading-relaxed"
                style={{ fontFamily: 'Nanum Gothic, sans-serif' }}
              />
              <p className="text-[10px] text-gray-400 mt-1">
                변수: {'{{name}}'} {'{{region}}'} {'{{city}}'} {'{{teachingAge}}'} {'{{email}}'} &middot; 이미지 Ctrl+V 또는 🖼 버튼으로 본문에 직접 삽입 · 브라우저에서 이미지 클릭 시 크기 조정 가능
              </p>
            </div>
          </div>

          {/* ── 우측: 미리보기 ── */}
          <div className="w-[380px] shrink-0 overflow-y-auto p-5 bg-gray-50">
            <h3 className="text-[12px] font-bold text-gray-500 uppercase tracking-wider mb-3">미리보기</h3>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 space-y-1.5">
                <div className="text-[11px]">
                  <span className="text-gray-400 font-medium">From:</span>
                  <span className="text-gray-700 ml-1">BRIDGE &lt;{sender}&gt;</span>
                </div>
                <div className="text-[11px]">
                  <span className="text-gray-400 font-medium">To:</span>
                  <span className="text-gray-700 ml-1">
                    {firstR
                      ? (firstR.school_name || firstR.name)
                      : manualEmails[0] || '—'}
                    {totalRecipients > 1 && (
                      <span className="text-gray-400 ml-1">(+{totalRecipients - 1}명 개별발송)</span>
                    )}
                  </span>
                </div>
                <div className="text-[11px]">
                  <span className="text-gray-400 font-medium">Subject:</span>
                  <span className="text-gray-700 ml-1 font-medium">{previewSubject}</span>
                </div>
              </div>
              <div
                className="px-4 py-4 text-[13px] leading-relaxed"
                style={{ fontFamily: 'Nanum Gothic, sans-serif' }}
                dangerouslySetInnerHTML={{ __html: previewBody }}
              />
              {attachments.length > 0 && (
                <div className="px-4 py-2 border-t border-gray-100">
                  <span className="text-[10px] text-gray-400 font-medium">첨부 ({attachments.length}개)</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {attachments.map((f, i) => (
                      <span key={`p-${f.name}-${i}`} className="text-[10px] text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded">
                        {fileIcon(f)} {f.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── 이미지 선택 툴바 (fixed overlay) ── */}
        {selectedImg && imgRect && (
          <>
            {/* 툴바 */}
            <div
              style={{
                position: 'fixed',
                left: Math.max(4, imgRect.left),
                top: Math.max(4, imgRect.top - 40),
                zIndex: 10000,
                background: '#1d1d1f',
                borderRadius: '8px',
                padding: '4px 8px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
              }}
              onMouseDown={e => e.preventDefault()}
            >
              {/* 프리셋 */}
              {[
                { label: '원본', value: 'auto' },
                { label: '25%', value: '25%' },
                { label: '50%', value: '50%' },
                { label: '75%', value: '75%' },
                { label: '100%', value: '100%' },
              ].map(p => (
                <button
                  key={p.label}
                  type="button"
                  onMouseDown={e => { e.preventDefault(); applyImgWidth(p.value) }}
                  style={{
                    background: 'rgba(255,255,255,0.12)',
                    border: 'none',
                    borderRadius: '4px',
                    color: '#fff',
                    fontSize: '11px',
                    padding: '2px 7px',
                    cursor: 'pointer',
                  }}
                >
                  {p.label}
                </button>
              ))}
              <span style={{ width: '1px', height: '14px', background: 'rgba(255,255,255,0.2)' }} />
              {/* 픽셀 직접입력 */}
              <input
                type="number"
                value={imgWidth}
                onChange={e => setImgWidth(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') applyImgWidth(Number(imgWidth)) }}
                onBlur={() => { if (imgWidth) applyImgWidth(Number(imgWidth)) }}
                style={{
                  width: '52px', background: 'rgba(255,255,255,0.12)',
                  border: 'none', borderRadius: '4px', color: '#fff',
                  fontSize: '11px', padding: '2px 5px', outline: 'none', textAlign: 'center',
                }}
                placeholder="px"
              />
              <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px' }}>px</span>
              <span style={{ width: '1px', height: '14px', background: 'rgba(255,255,255,0.2)' }} />
              {/* 삭제 */}
              <button
                type="button"
                onMouseDown={e => { e.preventDefault(); deleteSelectedImg() }}
                style={{
                  background: 'rgba(239,68,68,0.3)', border: 'none',
                  borderRadius: '4px', color: '#fca5a5',
                  fontSize: '11px', padding: '2px 7px', cursor: 'pointer',
                }}
              >
                삭제
              </button>
            </div>
            {/* 우하단 리사이즈 핸들 */}
            <div
              style={{
                position: 'fixed',
                left: imgRect.right - 9,
                top: imgRect.bottom - 9,
                width: 16,
                height: 16,
                background: '#0071E3',
                border: '2px solid #fff',
                borderRadius: '3px',
                cursor: 'se-resize',
                zIndex: 10000,
                boxShadow: '0 1px 4px rgba(0,0,0,0.4)',
              }}
              onMouseDown={e => {
                e.preventDefault()
                resizingRef.current = true
                resizeStartRef.current = { x: e.clientX, width: selectedImg.offsetWidth }
              }}
            />
          </>
        )}

        {/* 하단 발송 바 */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between shrink-0 bg-white">
          <p className="text-[11px] text-gray-400">
            From: {sender} &middot; 각 수신자에게 1:1 개별 발송 &middot; 타인 정보 절대 미노출
          </p>
          <button
            type="button"
            onClick={handleSend}
            disabled={sending || totalRecipients === 0}
            className="px-5 py-2.5 bg-[#03c75a] text-white text-[13px] font-semibold rounded-xl hover:bg-[#02a84a] transition-colors disabled:opacity-50 shadow-sm"
          >
            {sending ? '발송 중...' : `보내기 (${totalRecipients}명 개별발송)`}
          </button>
        </div>
      </div>
    </div>
  )
}
