'use client'

/**
 * /admin/resume-converter — 이력서 변환기 v6
 * 컬럼형(목록) 레이아웃: 목록 여러개 가로 나열 → 각 목록 = 1인 서류
 * 스케치: 목록1(이력서/커버레터/사진) | 목록2 | 목록3 | + 추가
 */

import { useRef, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import {
  FileText, Upload, CheckCircle2, AlertCircle,
  Loader2, Download, Plus, X, Image as ImageIcon,
} from 'lucide-react'

const C_PRIMARY = '#1D9E75'

// 문서 슬롯 정의 (각 목록 안에 고정 배치)
const DOC_SLOTS = [
  { id: 'resume',    label: '이력서',   color: '#1D9E75', bg: '#f0fdf4' },
  { id: 'cover',     label: '커버레터', color: '#3B82F6', bg: '#eff6ff' },
  { id: 'photo',     label: '사진',     color: '#F59E0B', bg: '#fffbeb' },
  { id: 'reference', label: '추천서',   color: '#8B5CF6', bg: '#f5f3ff' },
  { id: 'other',     label: '기타',     color: '#6B7280', bg: '#f9fafb' },
] as const

type SlotId = typeof DOC_SLOTS[number]['id']

interface ProcessedFile {
  fileName: string
  fileType: string
  piiCount: number
  data: string
}

interface SlotFile {
  file: File
  processedFile?: ProcessedFile
}

type SlotMap = Record<SlotId, SlotFile | null>

interface CandidateCol {
  uid: string
  candidateId: string
  slots: SlotMap
  status: 'idle' | 'processing' | 'done' | 'error'
  message: string
}

function makeCol(): CandidateCol {
  return {
    uid: crypto.randomUUID(),
    candidateId: '',
    slots: { resume: null, cover: null, photo: null, reference: null, other: null },
    status: 'idle',
    message: '',
  }
}

function getSlot(id: SlotId) {
  return DOC_SLOTS.find(s => s.id === id) ?? DOC_SLOTS[4]
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

function autoSlot(file: File): SlotId {
  const name = file.name.toLowerCase()
  const ext  = name.split('.').pop() || ''
  if (['jpg','jpeg','png','webp','gif','bmp'].includes(ext)) return 'photo'
  if (/cover|커버|자기\s?소개/.test(name)) return 'cover'
  if (/ref|recom|추천/.test(name)) return 'reference'
  if (/resume|cv|이력서/.test(name)) return 'resume'
  if (['pdf','docx','doc'].includes(ext)) return 'resume'
  return 'other'
}

function downloadFile(pf: ProcessedFile) {
  try {
    const byteChars = atob(pf.data)
    const byteArr   = new Uint8Array(byteChars.length)
    for (let i = 0; i < byteChars.length; i++) byteArr[i] = byteChars.charCodeAt(i)
    const mime =
      pf.fileType === 'pdf'  ? 'application/pdf' :
      pf.fileType === 'docx' ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' :
      'application/octet-stream'
    const blob = new Blob([byteArr], { type: mime })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = pf.fileName
    document.body.appendChild(a); a.click()
    document.body.removeChild(a); URL.revokeObjectURL(url)
  } catch (e) { console.error('Download failed:', e) }
}

// ────────────────────────────────────────────────────────────
// 슬롯 행 — 각 문서 타입 1개 드롭존
// ────────────────────────────────────────────────────────────
function SlotRow({
  slot,
  slotFile,
  onDrop,
  onClear,
}: {
  slot: typeof DOC_SLOTS[number]
  slotFile: SlotFile | null
  onDrop: (file: File) => void
  onClear: () => void
}) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const handleDragOver  = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true) }
  const handleDragLeave = () => setIsDragging(false)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) onDrop(files[0])
  }

  return (
    <div className="px-3 py-2 border-b border-[#f4f4f5] last:border-0">
      {/* 슬롯 라벨 */}
      <div className="flex items-center justify-between mb-1.5">
        <span
          className="text-[10px] font-bold px-1.5 py-0.5 rounded-md"
          style={{ color: slot.color, backgroundColor: slot.bg }}
        >
          {slot.label}
        </span>
        {slotFile && (
          <button
            onClick={onClear}
            className="text-[#9AA0A6] hover:text-[#E24B4A] p-0.5 rounded transition-colors"
          >
            <X size={11} />
          </button>
        )}
      </div>

      {/* 드롭존 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !slotFile && inputRef.current?.click()}
        className={`rounded-lg transition-all ${
          slotFile
            ? 'border border-[#e8eaed] bg-[#fafafa]'
            : isDragging
              ? 'border-2 border-dashed cursor-pointer'
              : 'border border-dashed border-[#d4d4d8] cursor-pointer hover:border-[#a1a1aa] hover:bg-[#fafafa]'
        }`}
        style={isDragging ? { borderColor: slot.color, backgroundColor: slot.bg } : {}}
      >
        {slotFile ? (
          <div className="flex items-center gap-1.5 px-2 py-1.5">
            {slot.id === 'photo'
              ? <ImageIcon size={12} style={{ color: slot.color }} className="shrink-0" />
              : <FileText  size={12} style={{ color: slot.color }} className="shrink-0" />
            }
            <span
              className="text-[11px] text-[#202124] truncate flex-1 min-w-0"
              title={slotFile.file.name}
            >
              {slotFile.file.name}
            </span>
            <span className="text-[10px] text-[#9AA0A6] shrink-0">
              {formatSize(slotFile.file.size)}
            </span>
            {slotFile.processedFile && (
              <button
                onClick={e => { e.stopPropagation(); downloadFile(slotFile.processedFile!) }}
                className="shrink-0 p-0.5 rounded hover:bg-[#e8eaed] transition-colors"
                title="변환 결과 다운로드"
              >
                <Download size={11} style={{ color: C_PRIMARY }} />
              </button>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center gap-1 py-2 text-[#a1a1aa]">
            <Upload size={11} />
            <span className="text-[11px]">드롭 또는 클릭</span>
          </div>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.webp"
        onChange={e => {
          if (e.target.files?.[0]) { onDrop(e.target.files[0]); e.target.value = '' }
        }}
      />
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 지원자 컬럼 (목록 1 / 목록 2 / ...)
// ────────────────────────────────────────────────────────────
function CandidateColumn({
  col,
  index,
  onUpdate,
  onRemove,
}: {
  col: CandidateCol
  index: number
  onUpdate: (uid: string, updater: (c: CandidateCol) => CandidateCol) => void
  onRemove: (uid: string) => void
}) {
  const [isDraggingCol, setIsDraggingCol] = useState(false)

  // 컬럼 전체 드롭 → 슬롯 자동 배정
  const handleColumnDrop = (e: React.DragEvent) => {
    e.preventDefault(); setIsDraggingCol(false)
    const files = Array.from(e.dataTransfer.files)
    onUpdate(col.uid, c => {
      const updated = { ...c.slots }
      files.forEach(file => {
        const sid = autoSlot(file)
        updated[sid] = { file }
      })
      return { ...c, slots: updated }
    })
  }

  const setSlot = (slotId: SlotId, file: File) => {
    onUpdate(col.uid, c => ({ ...c, slots: { ...c.slots, [slotId]: { file } } }))
  }

  const clearSlot = (slotId: SlotId) => {
    onUpdate(col.uid, c => ({ ...c, slots: { ...c.slots, [slotId]: null } }))
  }

  const fileCount  = Object.values(col.slots).filter(Boolean).length
  const doneCount  = Object.values(col.slots).filter(s => s?.processedFile).length
  const statusColor =
    col.status === 'done'  ? '#1D9E75' :
    col.status === 'error' ? '#E24B4A' : '#9AA0A6'

  return (
    <div
      className={`flex-shrink-0 w-56 bg-white rounded-2xl border-2 flex flex-col transition-all shadow-sm ${
        col.status === 'done'  ? 'border-[#1D9E75]' :
        col.status === 'error' ? 'border-[#E24B4A]' :
        isDraggingCol          ? 'border-[#1D9E75] shadow-md' : 'border-[#e8eaed]'
      }`}
      onDragOver={e => { e.preventDefault(); setIsDraggingCol(true) }}
      onDragLeave={e => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDraggingCol(false)
      }}
      onDrop={handleColumnDrop}
    >
      {/* 컬럼 헤더 */}
      <div className="px-3 pt-3 pb-2 border-b border-[#f0f0f2]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
              style={{ backgroundColor: C_PRIMARY }}
            >
              {index + 1}
            </div>
            <span className="text-xs font-bold text-[#202124]">목록 {index + 1}</span>
          </div>
          <div className="flex items-center gap-1">
            {col.status !== 'idle' && (
              <span
                className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                style={{ color: statusColor, backgroundColor: `${statusColor}18` }}
              >
                {col.status === 'processing' ? '처리중' :
                 col.status === 'done'  ? '완료' : '오류'}
              </span>
            )}
            <button
              onClick={() => onRemove(col.uid)}
              className="p-0.5 text-[#c4c4c4] hover:text-[#E24B4A] rounded transition-colors"
            >
              <X size={13} />
            </button>
          </div>
        </div>

        {/* 지원자 번호 입력 */}
        <input
          type="text"
          value={col.candidateId}
          onChange={e => onUpdate(col.uid, c => ({ ...c, candidateId: e.target.value }))}
          placeholder="지원자 번호 (예: 3126)"
          className="w-full text-xs px-2.5 py-1.5 border border-[#e8eaed] rounded-lg outline-none focus:border-[#1D9E75] transition-colors"
        />

        {fileCount > 0 && (
          <p className="text-[10px] text-[#9AA0A6] mt-1.5">
            {fileCount}개 파일
            {doneCount > 0 && (
              <span className="ml-1.5 font-semibold" style={{ color: C_PRIMARY }}>
                ({doneCount}개 변환 완료)
              </span>
            )}
          </p>
        )}
      </div>

      {/* 슬롯 목록 */}
      <div className="flex-1 py-1">
        {DOC_SLOTS.map(slot => (
          <SlotRow
            key={slot.id}
            slot={slot}
            slotFile={col.slots[slot.id]}
            onDrop={file => setSlot(slot.id, file)}
            onClear={() => clearSlot(slot.id)}
          />
        ))}
      </div>

      {/* 상태 메시지 */}
      {col.message && (
        <div
          className={`mx-3 mb-3 px-2.5 py-2 rounded-xl text-[11px] flex items-start gap-1.5 ${
            col.status === 'done'
              ? 'bg-[#f0fdf4] text-[#1D9E75]'
              : 'bg-[#fef2f2] text-[#E24B4A]'
          }`}
        >
          {col.status === 'done'
            ? <CheckCircle2 size={12} className="shrink-0 mt-0.5" />
            : <AlertCircle  size={12} className="shrink-0 mt-0.5" />}
          <span className="break-words leading-relaxed">{col.message}</span>
        </div>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 메인 컴포넌트
// ────────────────────────────────────────────────────────────
function ResumeConverterInner() {
  const { headers } = useAdminAuth()
  const [cols, setCols] = useState<CandidateCol[]>([makeCol(), makeCol(), makeCol()])
  const [isProcessingAll, setIsProcessingAll] = useState(false)

  const updateCol = (uid: string, updater: (c: CandidateCol) => CandidateCol) => {
    setCols(prev => prev.map(c => c.uid === uid ? updater(c) : c))
  }

  const removeCol = (uid: string) => {
    setCols(prev => prev.length > 1 ? prev.filter(c => c.uid !== uid) : prev)
  }

  const addCol = () => setCols(prev => [...prev, makeCol()])

  const clearAll = () => {
    setCols([makeCol(), makeCol(), makeCol()])
    setIsProcessingAll(false)
  }

  const processOne = async (col: CandidateCol): Promise<Partial<CandidateCol>> => {
    if (!col.candidateId.trim()) {
      return { status: 'error', message: '지원자 번호를 입력하세요' }
    }
    const hasFile = Object.values(col.slots).some(Boolean)
    if (!hasFile) {
      return { status: 'error', message: '파일을 1개 이상 추가하세요' }
    }

    const formData = new FormData()
    formData.append('candidate_id', col.candidateId.trim())
    for (const [slotId, slotFile] of Object.entries(col.slots)) {
      if (slotFile) formData.append(`files_${slotId}`, slotFile.file)
    }

    const res = await fetch(`${API_URL}/api/resume/process`, {
      method: 'POST',
      headers: headers(),
      body: formData,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()

    // 처리 결과를 각 슬롯에 반영
    const updatedSlots: SlotMap = { ...col.slots }
    let totalPii = 0

    for (const slotId of ['resume', 'cover', 'reference', 'other'] as const) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const fileResults: any[] = data.files_processed?.[slotId] ?? []
      for (const fr of fileResults) {
        if (fr.processed && fr.processed_data && updatedSlots[slotId]) {
          updatedSlots[slotId] = {
            ...updatedSlots[slotId]!,
            processedFile: {
              fileName: fr.file_name,
              fileType: fr.file_type,
              piiCount: fr.pii_count ?? 0,
              data: fr.processed_data,
            },
          }
          totalPii += fr.pii_count ?? 0
        }
      }
    }

    return {
      status: 'done',
      message: `PII ${totalPii}개 제거 완료`,
      slots: updatedSlots,
    }
  }

  const processAll = async () => {
    setIsProcessingAll(true)
    for (const col of cols) {
      updateCol(col.uid, c => ({ ...c, status: 'processing', message: '' }))
      try {
        const result = await processOne(col)
        updateCol(col.uid, c => ({ ...c, ...result }))
      } catch (e) {
        updateCol(col.uid, c => ({
          ...c,
          status: 'error',
          message: `오류: ${e instanceof Error ? e.message : 'Unknown error'}`,
        }))
      }
    }
    setIsProcessingAll(false)
  }

  const doneCount  = cols.filter(c => c.status === 'done').length
  const errorCount = cols.filter(c => c.status === 'error').length
  const totalFiles = cols.reduce(
    (sum, c) => sum + Object.values(c.slots).filter(Boolean).length, 0
  )

  return (
    <div className="min-h-screen bg-[#f0f2f5] flex flex-col">

      {/* 고정 상단 헤더 */}
      <div className="sticky top-0 z-20 bg-white border-b border-[#e8eaed] shadow-sm">
        <div className="flex items-center justify-between px-6 py-3">
          {/* 타이틀 */}
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ backgroundColor: C_PRIMARY }}
            >
              <FileText size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-[#202124] leading-tight">
                BRIDGE Converter
                <span className="ml-2 text-xs font-medium text-[#9AA0A6]">v6</span>
              </h1>
              <p className="text-xs text-[#5F6368]">
                1인 1목록 — 파일이 섞이지 않게 각 목록에 서류 첨부
              </p>
            </div>
          </div>

          {/* 진행 상황 */}
          <div className="flex items-center gap-4">
            {totalFiles > 0 && (
              <div className="flex items-center gap-3 text-xs text-[#5F6368]">
                <span>목록 {cols.length}개 · 파일 {totalFiles}개</span>
                {doneCount > 0 && (
                  <span className="flex items-center gap-1 font-semibold" style={{ color: C_PRIMARY }}>
                    <CheckCircle2 size={13} /> 완료 {doneCount}명
                  </span>
                )}
                {errorCount > 0 && (
                  <span className="flex items-center gap-1 font-semibold text-[#E24B4A]">
                    <AlertCircle size={13} /> 오류 {errorCount}명
                  </span>
                )}
              </div>
            )}

            <button
              onClick={clearAll}
              className="px-3 py-1.5 text-xs font-medium text-[#E24B4A] hover:bg-[#fef2f2] rounded-lg transition-colors"
            >
              전체 초기화
            </button>

            <button
              onClick={processAll}
              disabled={isProcessingAll}
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-white text-sm font-semibold transition-all disabled:opacity-60 shadow-sm"
              style={{ backgroundColor: C_PRIMARY }}
            >
              {isProcessingAll ? (
                <><Loader2 size={15} className="animate-spin" />처리 중...</>
              ) : (
                <><Upload size={15} />{cols.length}명 변환 시작</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 가로 스크롤 컬럼 영역 */}
      <div
        className="flex gap-4 p-6 overflow-x-auto flex-1"
        style={{ alignItems: 'flex-start', minHeight: 'calc(100vh - 65px)' }}
      >
        {cols.map((col, index) => (
          <CandidateColumn
            key={col.uid}
            col={col}
            index={index}
            onUpdate={updateCol}
            onRemove={removeCol}
          />
        ))}

        {/* 목록 추가 버튼 */}
        <button
          onClick={addCol}
          className="flex-shrink-0 w-56 rounded-2xl border-2 border-dashed border-[#d4d4d8] flex flex-col items-center justify-center gap-2 text-[#9AA0A6] hover:border-[#1D9E75] hover:text-[#1D9E75] hover:bg-white transition-all self-start"
          style={{ minHeight: '280px' }}
        >
          <Plus size={28} />
          <span className="text-sm font-medium">목록 추가</span>
        </button>
      </div>
    </div>
  )
}

export default function ResumeConverterPage() {
  const { authed, login, waking } = useAdminAuth()
  if (!authed) return <AdminAuth onLogin={login} waking={waking} />
  return <ResumeConverterInner />
}
