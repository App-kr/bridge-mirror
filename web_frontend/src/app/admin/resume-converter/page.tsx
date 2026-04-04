'use client'

/**
 * /admin/resume-converter — 이력서 변환기 v5
 * 통합 드롭존: 파일을 한번에 드롭 → 자동분류 → 한 사람당 하나의 파일 목록
 */

import { useRef, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { FileText, Upload, CheckCircle2, AlertCircle, Loader2, Download, Plus, X, Image as ImageIcon, File } from 'lucide-react'

const C_PRIMARY = '#1D9E75'

const CATEGORIES = [
  { id: 'resume',    label: '이력서',   color: '#1D9E75', bg: '#f0fdf4' },
  { id: 'cover',     label: '커버레터', color: '#3B82F6', bg: '#eff6ff' },
  { id: 'photo',     label: '사진',     color: '#F59E0B', bg: '#fffbeb' },
  { id: 'reference', label: '추천서',   color: '#8B5CF6', bg: '#f5f3ff' },
  { id: 'other',     label: '기타',     color: '#6B7280', bg: '#f9fafb' },
] as const

type CategoryId = typeof CATEGORIES[number]['id']

interface FileEntry {
  file: File
  category: CategoryId
}

interface Candidate {
  uid: string
  candidateId: string
  files: FileEntry[]
  isDragging: boolean
  status: 'idle' | 'processing' | 'done' | 'error'
  message: string
  processedFiles: ProcessedFile[]
}

interface ProcessedFile {
  fileName: string
  fileType: string
  piiCount: number
  data: string
  section: string
}

function autoCategory(file: File): CategoryId {
  const name = file.name.toLowerCase()
  const ext = name.split('.').pop() || ''

  if (['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'].includes(ext)) return 'photo'
  if (/cover|커버|자기\s?소개/.test(name)) return 'cover'
  if (/ref|recom|추천/.test(name)) return 'reference'
  if (/resume|cv|이력서/.test(name)) return 'resume'
  if (['pdf', 'docx', 'doc'].includes(ext)) return 'resume'
  return 'other'
}

function getCat(id: CategoryId) {
  return CATEGORIES.find(c => c.id === id) ?? CATEGORIES[4]
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

function makeCandidate(): Candidate {
  return {
    uid: crypto.randomUUID(),
    candidateId: '',
    files: [],
    isDragging: false,
    status: 'idle',
    message: '',
    processedFiles: [],
  }
}

// ────────────────────────────────────────────────────────────
// 지원자 1명 카드 — 통합 드롭존 + 파일 목록
// ────────────────────────────────────────────────────────────
function CandidateCard({
  candidate,
  index,
  onUpdate,
  onRemove,
}: {
  candidate: Candidate
  index: number
  onUpdate: (uid: string, updater: (c: Candidate) => Candidate) => void
  onRemove: (uid: string) => void
}) {
  const inputRef = useRef<HTMLInputElement | null>(null)

  const addFiles = (newFiles: File[]) => {
    const entries: FileEntry[] = newFiles.map(f => ({ file: f, category: autoCategory(f) }))
    onUpdate(candidate.uid, c => ({ ...c, files: [...c.files, ...entries] }))
  }

  const removeFile = (idx: number) => {
    onUpdate(candidate.uid, c => ({
      ...c,
      files: c.files.filter((_, i) => i !== idx),
    }))
  }

  const changeCategory = (idx: number, cat: CategoryId) => {
    onUpdate(candidate.uid, c => ({
      ...c,
      files: c.files.map((f, i) => i === idx ? { ...f, category: cat } : f),
    }))
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onUpdate(candidate.uid, c => ({ ...c, isDragging: true }))
  }

  const handleDragLeave = (e: React.DragEvent) => {
    if (e.relatedTarget && (e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) return
    onUpdate(candidate.uid, c => ({ ...c, isDragging: false }))
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onUpdate(candidate.uid, c => ({ ...c, isDragging: false }))
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) addFiles(files)
  }

  const statusColor =
    candidate.status === 'done'  ? '#1D9E75' :
    candidate.status === 'error' ? '#E24B4A' : '#5F6368'

  const fileIcon = (entry: FileEntry) => {
    const ext = entry.file.name.split('.').pop()?.toLowerCase() || ''
    if (['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'].includes(ext))
      return <ImageIcon size={14} className="shrink-0" style={{ color: getCat(entry.category).color }} />
    return <File size={14} className="shrink-0" style={{ color: getCat(entry.category).color }} />
  }

  return (
    <div className={`bg-white rounded-2xl border-2 transition-colors ${
      candidate.status === 'done'  ? 'border-[#1D9E75]' :
      candidate.status === 'error' ? 'border-[#E24B4A]' : 'border-[#e8eaed]'
    }`}>
      {/* 카드 헤더 */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#e8eaed]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold"
               style={{ backgroundColor: C_PRIMARY }}>
            {index + 1}
          </div>
          <div>
            <span className="text-sm font-semibold text-[#202124]">지원자 {index + 1}</span>
            {candidate.files.length > 0 && (
              <span className="ml-2 text-xs text-[#5F6368]">파일 {candidate.files.length}개</span>
            )}
          </div>
          {candidate.status !== 'idle' && (
            <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                  style={{ color: statusColor, backgroundColor: `${statusColor}15` }}>
              {candidate.status === 'processing' ? '처리 중...' :
               candidate.status === 'done'  ? '완료' : '오류'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={candidate.candidateId}
            onChange={e => onUpdate(candidate.uid, c => ({ ...c, candidateId: e.target.value }))}
            placeholder="지원자 번호 (예: 3126)"
            className="text-sm px-3 py-1.5 border border-[#e8eaed] rounded-lg outline-none focus:border-[#1D9E75] w-44"
          />
          <button
            onClick={() => onRemove(candidate.uid)}
            className="p-1.5 text-[#9AA0A6] hover:text-[#E24B4A] hover:bg-[#fef2f2] rounded-lg transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* 통합 드롭존 */}
      <div className="p-4">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all select-none ${
            candidate.isDragging
              ? 'border-[#1D9E75] bg-[#f0fdf4]'
              : 'border-[#e8eaed] hover:border-[#1D9E75] hover:bg-[#f8fefc]'
          }`}
        >
          <Upload size={24} className="mx-auto mb-2 pointer-events-none" style={{ color: C_PRIMARY }} />
          <p className="text-sm font-medium text-[#202124] pointer-events-none">
            파일을 여기에 드래그하거나 클릭하여 선택
          </p>
          <p className="text-xs text-[#9AA0A6] mt-1 pointer-events-none">
            이력서, 커버레터, 사진, 추천서 등 모든 파일을 한번에 넣으세요
          </p>
          <input
            ref={inputRef}
            type="file"
            multiple
            onChange={e => { if (e.target.files) { addFiles(Array.from(e.target.files)); e.target.value = '' } }}
            className="hidden"
            accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.webp"
          />
        </div>

        {/* 파일 목록 (통합) */}
        {candidate.files.length > 0 && (
          <div className="mt-3 border border-[#e8eaed] rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-[#f8f9fa] border-b border-[#e8eaed]">
              <span className="text-xs font-semibold text-[#202124]">
                첨부 파일 ({candidate.files.length})
              </span>
              <button
                onClick={() => onUpdate(candidate.uid, c => ({ ...c, files: [] }))}
                className="text-xs text-[#E24B4A] hover:text-[#c12020] font-medium"
              >
                전체 삭제
              </button>
            </div>
            <div className="divide-y divide-[#f0f0f2]">
              {candidate.files.map((entry, idx) => {
                const cat = getCat(entry.category)
                return (
                  <div key={idx} className="flex items-center gap-2 px-3 py-2 group hover:bg-[#fafafa]">
                    {fileIcon(entry)}
                    <span className="text-xs text-[#202124] truncate flex-1 min-w-0" title={entry.file.name}>
                      {entry.file.name}
                    </span>
                    <span className="text-xs text-[#9AA0A6] shrink-0">{formatSize(entry.file.size)}</span>
                    <select
                      value={entry.category}
                      onChange={e => changeCategory(idx, e.target.value as CategoryId)}
                      className="text-xs font-medium px-1.5 py-0.5 rounded-md border-0 outline-none cursor-pointer shrink-0"
                      style={{ color: cat.color, backgroundColor: cat.bg }}
                    >
                      {CATEGORIES.map(c => (
                        <option key={c.id} value={c.id}>{c.label}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => removeFile(idx)}
                      className="text-[#9AA0A6] hover:text-[#E24B4A] opacity-0 group-hover:opacity-100 shrink-0 p-0.5"
                    >
                      <X size={12} />
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* 처리 결과 메시지 */}
      {candidate.message && (
        <div className={`mx-4 mb-4 px-3 py-2 rounded-xl text-xs flex items-center gap-2 ${
          candidate.status === 'done'
            ? 'bg-[#f0fdf4] text-[#1D9E75]'
            : 'bg-[#fef2f2] text-[#E24B4A]'
        }`}>
          {candidate.status === 'done'
            ? <CheckCircle2 size={14} />
            : <AlertCircle size={14} />}
          {candidate.message}
        </div>
      )}

      {/* 처리된 파일 다운로드 */}
      {candidate.processedFiles.length > 0 && (
        <div className="mx-4 mb-4 border border-[#e8eaed] rounded-xl overflow-hidden">
          <div className="px-3 py-2 bg-[#f8f9fa] border-b border-[#e8eaed]">
            <span className="text-xs font-semibold text-[#202124]">처리된 파일</span>
          </div>
          {candidate.processedFiles.map((pf, i) => (
            <DownloadRow key={i} pf={pf} />
          ))}
        </div>
      )}
    </div>
  )
}

function DownloadRow({ pf }: { pf: ProcessedFile }) {
  const cat = getCat((pf.section as CategoryId) || 'resume')

  const download = () => {
    try {
      const byteChars = atob(pf.data)
      const byteArr = new Uint8Array(byteChars.length)
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

  return (
    <div className="flex items-center justify-between px-3 py-2 hover:bg-[#f8f9fa]">
      <div className="flex items-center gap-2 min-w-0">
        <FileText size={14} style={{ color: cat.color }} className="shrink-0" />
        <div className="min-w-0">
          <p className="text-xs font-medium text-[#202124] truncate">{pf.fileName}</p>
          <p className="text-xs text-[#9AA0A6]">
            PII {pf.piiCount}개 제거
            <span className="ml-1.5 font-medium" style={{ color: cat.color }}>{cat.label}</span>
          </p>
        </div>
      </div>
      <button
        onClick={download}
        className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white rounded-lg ml-3 shrink-0 transition-opacity hover:opacity-80"
        style={{ backgroundColor: C_PRIMARY }}
      >
        <Download size={12} />
        다운로드
      </button>
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 메인 컴포넌트
// ────────────────────────────────────────────────────────────
function ResumeConverterInner() {
  const { headers } = useAdminAuth()
  const [candidates, setCandidates] = useState<Candidate[]>([makeCandidate()])
  const [isProcessingAll, setIsProcessingAll] = useState(false)

  const updateCandidate = (uid: string, updater: (c: Candidate) => Candidate) => {
    setCandidates(prev => prev.map(c => c.uid === uid ? updater(c) : c))
  }

  const removeCandidate = (uid: string) => {
    setCandidates(prev => prev.length > 1 ? prev.filter(c => c.uid !== uid) : prev)
  }

  const addCandidate = () => {
    setCandidates(prev => [...prev, makeCandidate()])
  }

  const clearAll = () => {
    setCandidates([makeCandidate()])
    setIsProcessingAll(false)
  }

  const processOne = async (candidate: Candidate): Promise<Partial<Candidate>> => {
    if (!candidate.candidateId.trim()) {
      return { status: 'error', message: '지원자 번호를 입력하세요' }
    }
    if (candidate.files.length === 0) {
      return { status: 'error', message: '파일을 1개 이상 추가하세요' }
    }

    const formData = new FormData()
    formData.append('candidate_id', candidate.candidateId.trim())
    candidate.files.forEach(entry => {
      formData.append(`files_${entry.category}`, entry.file)
    })

    const res = await fetch(`${API_URL}/api/resume/process`, {
      method: 'POST',
      headers: headers(),
      body: formData,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()

    const collected: ProcessedFile[] = []
    for (const sectionId of ['resume', 'cover', 'reference', 'other'] as const) {
      const fileResults: any[] = data.files_processed?.[sectionId] ?? []
      for (const fr of fileResults) {
        if (fr.processed && fr.processed_data) {
          collected.push({
            fileName: fr.file_name,
            fileType: fr.file_type,
            piiCount: fr.pii_count ?? 0,
            data: fr.processed_data,
            section: sectionId,
          })
        }
      }
    }

    return {
      status: 'done',
      message: `PII ${data.pii_count}개 제거, ${collected.length}개 파일 준비됨`,
      processedFiles: collected,
    }
  }

  const processAll = async () => {
    setIsProcessingAll(true)

    for (const candidate of candidates) {
      updateCandidate(candidate.uid, c => ({ ...c, status: 'processing', message: '' }))
      try {
        const result = await processOne(candidate)
        updateCandidate(candidate.uid, c => ({ ...c, ...result }))
      } catch (e) {
        updateCandidate(candidate.uid, c => ({
          ...c,
          status: 'error',
          message: `오류: ${e instanceof Error ? e.message : 'Unknown error'}`,
        }))
      }
    }

    setIsProcessingAll(false)
  }

  const totalFiles = candidates.reduce((sum, c) => sum + c.files.length, 0)
  const doneCount  = candidates.filter(c => c.status === 'done').length
  const errorCount = candidates.filter(c => c.status === 'error').length

  return (
    <div className="min-h-screen bg-[#f8f9fa] p-8">
      <div className="max-w-5xl mx-auto">

        {/* 헤더 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                 style={{ backgroundColor: C_PRIMARY }}>
              <FileText size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#202124]">BRIDGE Converter v5</h1>
              <p className="text-sm text-[#5F6368]">
                파일을 드롭하면 자동 분류 + PII 제거
                {candidates.length > 1 && (
                  <span className="ml-2 font-medium" style={{ color: C_PRIMARY }}>
                    {candidates.length}명
                  </span>
                )}
              </p>
            </div>
          </div>
          <button
            onClick={clearAll}
            className="px-4 py-2 text-sm font-medium text-[#E24B4A] hover:bg-[#fef2f2] rounded-lg transition-colors"
          >
            전체 초기화
          </button>
        </div>

        {/* 진행 상황 */}
        {(doneCount > 0 || errorCount > 0) && (
          <div className="flex items-center gap-4 mb-6 p-4 bg-white rounded-2xl border border-[#e8eaed]">
            <div className="flex items-center gap-2 text-sm">
              <CheckCircle2 size={16} className="text-[#1D9E75]" />
              <span className="font-medium text-[#202124]">완료 {doneCount}명</span>
            </div>
            {errorCount > 0 && (
              <div className="flex items-center gap-2 text-sm">
                <AlertCircle size={16} className="text-[#E24B4A]" />
                <span className="font-medium text-[#202124]">오류 {errorCount}명</span>
              </div>
            )}
            <div className="flex items-center gap-2 text-sm text-[#5F6368]">
              <FileText size={16} />
              <span>총 {totalFiles}개 파일</span>
            </div>
          </div>
        )}

        {/* 지원자 카드 목록 */}
        <div className="space-y-4 mb-6">
          {candidates.map((candidate, index) => (
            <CandidateCard
              key={candidate.uid}
              candidate={candidate}
              index={index}
              onUpdate={updateCandidate}
              onRemove={removeCandidate}
            />
          ))}
        </div>

        {/* 지원자 추가 버튼 */}
        <button
          onClick={addCandidate}
          className="w-full py-3 rounded-2xl border-2 border-dashed border-[#e8eaed] text-sm font-medium text-[#5F6368] hover:border-[#1D9E75] hover:text-[#1D9E75] hover:bg-[#f8fefc] transition-all flex items-center justify-center gap-2 mb-6"
        >
          <Plus size={18} />
          지원자 추가
        </button>

        {/* 변환 버튼 */}
        <button
          onClick={processAll}
          disabled={isProcessingAll}
          className="w-full py-4 rounded-2xl text-white font-semibold text-lg transition-all disabled:opacity-60 flex items-center justify-center gap-2"
          style={{ backgroundColor: C_PRIMARY }}
        >
          {isProcessingAll ? (
            <><Loader2 size={20} className="animate-spin" />처리 중...</>
          ) : (
            <>
              <Upload size={20} />
              {candidates.length > 1
                ? `${candidates.length}명 전체 변환 시작`
                : '변환 시작'}
            </>
          )}
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
