'use client'

/**
 * /admin/resume-converter — 이력서 변환기 v4
 * 다중 지원자 지원: 지원자별 파일 묶음 + 일괄 처리
 */

import { useRef, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { FileText, Upload, Trash2, CheckCircle2, AlertCircle, Loader2, Download, Plus, X, User } from 'lucide-react'

const C_PRIMARY = '#1D9E75'
const C_DANGER  = '#E24B4A'

const SECTION_DEFS = [
  { id: 'resume',    label: '이력서',    desc: 'PDF/DOCX' },
  { id: 'cover',     label: '커버레터',  desc: 'PDF/DOCX' },
  { id: 'photo',     label: '사진',      desc: 'JPG/PNG'  },
  { id: 'reference', label: '추천서',    desc: 'PDF/DOCX' },
  { id: 'other',     label: '기타',      desc: '기타 서류' },
] as const

type SectionId = typeof SECTION_DEFS[number]['id']

interface FileSlot {
  id: SectionId
  files: File[]
  isDragging: boolean
}

interface Candidate {
  uid: string
  candidateId: string
  sections: FileSlot[]
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

function makeSections(): FileSlot[] {
  return SECTION_DEFS.map(d => ({ id: d.id, files: [], isDragging: false }))
}

function makeCandidate(): Candidate {
  return {
    uid: crypto.randomUUID(),
    candidateId: '',
    sections: makeSections(),
    status: 'idle',
    message: '',
    processedFiles: [],
  }
}

// ────────────────────────────────────────────────────────────
// 지원자 1명 카드
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
  const fileInputRefs = useRef<{ [key: string]: HTMLInputElement | null }>({})

  const updateSection = (sectionId: SectionId, patch: Partial<FileSlot>) => {
    onUpdate(candidate.uid, c => ({
      ...c,
      sections: c.sections.map(s => s.id === sectionId ? { ...s, ...patch } : s),
    }))
  }

  const addFiles = (sectionId: SectionId, files: File[]) => {
    onUpdate(candidate.uid, c => ({
      ...c,
      sections: c.sections.map(s =>
        s.id === sectionId ? { ...s, files: [...s.files, ...files] } : s
      ),
    }))
  }

  const removeFile = (sectionId: SectionId, idx: number) => {
    onUpdate(candidate.uid, c => ({
      ...c,
      sections: c.sections.map(s =>
        s.id === sectionId ? { ...s, files: s.files.filter((_, i) => i !== idx) } : s
      ),
    }))
  }

  const handleDragOver = (sectionId: SectionId, e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    updateSection(sectionId, { isDragging: true })
  }

  const handleDragLeave = (sectionId: SectionId, e: React.DragEvent) => {
    if (e.relatedTarget && (e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) return
    updateSection(sectionId, { isDragging: false })
  }

  const handleDrop = (sectionId: SectionId, e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    updateSection(sectionId, { isDragging: false })
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) addFiles(sectionId, files)
  }

  const totalFiles = candidate.sections.reduce((sum, s) => sum + s.files.length, 0)

  const statusColor =
    candidate.status === 'done'  ? '#1D9E75' :
    candidate.status === 'error' ? '#E24B4A' : '#5F6368'

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
            {totalFiles > 0 && (
              <span className="ml-2 text-xs text-[#5F6368]">파일 {totalFiles}개</span>
            )}
          </div>
          {/* 상태 표시 */}
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

      {/* 5개 섹션 */}
      <div className="grid grid-cols-5 gap-3 p-4">
        {candidate.sections.map(section => {
          const def = SECTION_DEFS.find(d => d.id === section.id)!
          return (
            <div key={section.id} className="flex flex-col">
              {/* 섹션 레이블 */}
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-[#202124]">{def.label}</span>
                {section.files.length > 0 && (
                  <button
                    onClick={() => onUpdate(candidate.uid, c => ({
                      ...c,
                      sections: c.sections.map(s => s.id === section.id ? { ...s, files: [] } : s),
                    }))}
                    className="text-[#E24B4A] hover:text-[#c12020]"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>

              {/* 드롭 영역 */}
              <div
                onDragOver={e => handleDragOver(section.id, e)}
                onDragLeave={e => handleDragLeave(section.id, e)}
                onDrop={e => handleDrop(section.id, e)}
                onClick={() => fileInputRefs.current[section.id]?.click()}
                className={`border-2 border-dashed rounded-xl p-3 text-center cursor-pointer transition-all select-none ${
                  section.isDragging
                    ? 'border-[#1D9E75] bg-[#f0fdf4]'
                    : 'border-[#e8eaed] hover:border-[#1D9E75] hover:bg-[#f8fefc]'
                }`}
              >
                <Upload size={16} className="mx-auto mb-1 pointer-events-none" style={{ color: C_PRIMARY }} />
                <p className="text-xs text-[#5F6368] pointer-events-none">{def.desc}</p>
                <input
                  ref={el => { if (el) fileInputRefs.current[section.id] = el }}
                  type="file"
                  multiple
                  onChange={e => { if (e.target.files) addFiles(section.id, Array.from(e.target.files)) }}
                  className="hidden"
                  accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.webp"
                />
              </div>

              {/* 파일 목록 */}
              {section.files.length > 0 && (
                <div className="mt-1.5 space-y-1">
                  {section.files.map((file, idx) => (
                    <div key={idx}
                         className="flex items-center gap-1 px-2 py-1 bg-[#f8f9fa] rounded-lg border border-[#e8eaed] group">
                      <span className="text-xs font-mono text-[#9AA0A6] w-4 shrink-0">{idx + 1}</span>
                      <span className="text-xs text-[#202124] truncate flex-1 min-w-0" title={file.name}>
                        {file.name}
                      </span>
                      <button
                        onClick={e => { e.stopPropagation(); removeFile(section.id, idx) }}
                        className="text-[#9AA0A6] hover:text-[#E24B4A] opacity-0 group-hover:opacity-100 shrink-0"
                      >
                        <X size={10} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
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

      {/* 다운로드 */}
      {candidate.processedFiles.length > 0 && (
        <div className="mx-4 mb-4 border border-[#e8eaed] rounded-xl overflow-hidden">
          <div className="px-3 py-2 bg-[#f8f9fa] border-b border-[#e8eaed]">
            <span className="text-xs font-semibold text-[#202124]">처리된 파일</span>
          </div>
          {/* 섹션별 구분 */}
          {SECTION_DEFS.map(def => {
            const sectionFiles = candidate.processedFiles.filter(pf => pf.section === def.id)
            if (sectionFiles.length === 0) return null
            return (
              <div key={def.id} className="border-b border-[#e8eaed] last:border-b-0">
                <div className="px-3 py-1.5 bg-[#f8fefc]">
                  <span className="text-xs font-medium text-[#1D9E75]">{def.label}</span>
                </div>
                {sectionFiles.map((pf, i) => (
                  <DownloadRow key={i} pf={pf} />
                ))}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function DownloadRow({ pf }: { pf: ProcessedFile }) {
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
        <FileText size={14} style={{ color: C_PRIMARY }} className="shrink-0" />
        <div className="min-w-0">
          <p className="text-xs font-medium text-[#202124] truncate">{pf.fileName}</p>
          <p className="text-xs text-[#9AA0A6]">PII {pf.piiCount}개 제거 · {pf.fileType.toUpperCase()}</p>
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
    const totalFiles = candidate.sections.reduce((sum, s) => sum + s.files.length, 0)
    if (totalFiles === 0) {
      return { status: 'error', message: '파일을 1개 이상 추가하세요' }
    }

    const formData = new FormData()
    formData.append('candidate_id', candidate.candidateId.trim())
    candidate.sections.forEach(section => {
      section.files.forEach(file => formData.append(`files_${section.id}`, file))
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

  const totalFiles = candidates.reduce(
    (sum, c) => sum + c.sections.reduce((s2, s) => s2 + s.files.length, 0), 0
  )
  const doneCount  = candidates.filter(c => c.status === 'done').length
  const errorCount = candidates.filter(c => c.status === 'error').length

  return (
    <div className="min-h-screen bg-[#f8f9fa] p-8">
      <div className="max-w-7xl mx-auto">

        {/* 헤더 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                 style={{ backgroundColor: C_PRIMARY }}>
              <FileText size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#202124]">이력서 변환기 v4</h1>
              <p className="text-sm text-[#5F6368]">
                다중 지원자 · 지원자별 PII 제거
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

        {/* 진행 상황 (처리 중이거나 완료된 경우) */}
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
