'use client'

/**
 * /admin/resume-converter — 이력서 변환기 v3
 * 5개 파일 섹션 + 드래그 드롭 + 다중 지원자 처리
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { FileText, Upload, Trash2, CheckCircle2, AlertCircle, Loader2, RefreshCw } from 'lucide-react'

const C_PRIMARY = '#1D9E75'
const C_WARN = '#EF9F27'
const C_DANGER = '#E24B4A'

interface FileSection {
  id: 'resume' | 'cover' | 'photo' | 'reference' | 'other'
  label: string
  description: string
  files: File[]
  isDragging: boolean
}

interface ProcessingResult {
  candidateId: string
  status: 'pending' | 'completed' | 'error'
  message: string
}

function ResumeConverterInner() {
  const { headers } = useAdminAuth()
  const [candidateId, setCandidateId] = useState('')
  const [fileSections, setFileSections] = useState<FileSection[]>([
    { id: 'resume', label: '이력서 (Resume)', description: 'PDF, DOCX', files: [], isDragging: false },
    { id: 'cover', label: '커버레터 (Cover Letter)', description: 'PDF, DOCX', files: [], isDragging: false },
    { id: 'photo', label: '사진 (Photo)', description: 'JPG, PNG, WEBP', files: [], isDragging: false },
    { id: 'reference', label: '추천서 (Reference)', description: 'PDF, DOCX', files: [], isDragging: false },
    { id: 'other', label: '기타 (Other)', description: '기타 증명서', files: [], isDragging: false },
  ])
  const [isProcessing, setIsProcessing] = useState(false)
  const [result, setResult] = useState<ProcessingResult | null>(null)
  const fileInputRefs = useRef<{ [key: string]: HTMLInputElement | null }>({})

  // 파일 추가
  const handleFilesAdded = (sectionId: string, newFiles: File[]) => {
    setFileSections(prev =>
      prev.map(section =>
        section.id === sectionId
          ? { ...section, files: [...section.files, ...newFiles] }
          : section
      )
    )
  }

  // 파일 삭제
  const removeFile = (sectionId: string, fileIndex: number) => {
    setFileSections(prev =>
      prev.map(section =>
        section.id === sectionId
          ? { ...section, files: section.files.filter((_, i) => i !== fileIndex) }
          : section
      )
    )
  }

  // 섹션 초기화
  const clearSection = (sectionId: string) => {
    setFileSections(prev =>
      prev.map(section =>
        section.id === sectionId
          ? { ...section, files: [] }
          : section
      )
    )
  }

  // 전체 초기화
  const clearAll = () => {
    setCandidateId('')
    setFileSections(prev => prev.map(s => ({ ...s, files: [] })))
    setResult(null)
  }

  // 드래그 시작
  const handleDragOver = (sectionId: string, e: React.DragEvent) => {
    e.preventDefault()
    setFileSections(prev =>
      prev.map(s => (s.id === sectionId ? { ...s, isDragging: true } : s))
    )
  }

  // 드래그 끝
  const handleDragLeave = (sectionId: string) => {
    setFileSections(prev =>
      prev.map(s => (s.id === sectionId ? { ...s, isDragging: false } : s))
    )
  }

  // 드롭
  const handleDrop = (sectionId: string, e: React.DragEvent) => {
    e.preventDefault()
    setFileSections(prev =>
      prev.map(s => (s.id === sectionId ? { ...s, isDragging: false } : s))
    )
    const dropped = Array.from(e.dataTransfer.files)
    handleFilesAdded(sectionId, dropped)
  }

  // 파일 클릭
  const handleFileClick = (sectionId: string) => {
    fileInputRefs.current[sectionId]?.click()
  }

  // 파일 선택
  const handleFileChange = (sectionId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFilesAdded(sectionId, Array.from(e.target.files))
    }
  }

  // 변환 시작
  const startProcessing = async () => {
    if (!candidateId.trim()) {
      setResult({ candidateId: '', status: 'error', message: '지원자 번호를 입력하세요' })
      return
    }

    const totalFiles = fileSections.reduce((sum, s) => sum + s.files.length, 0)
    if (totalFiles === 0) {
      setResult({ candidateId: '', status: 'error', message: '최소 1개 이상의 파일을 추가하세요' })
      return
    }

    setIsProcessing(true)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('candidate_id', candidateId.trim())

      fileSections.forEach(section => {
        section.files.forEach(file => {
          formData.append(`files_${section.id}`, file)
        })
      })

      const res = await fetch(`${API_URL}/api/resume/process`, {
        method: 'POST',
        headers: headers(),
        body: formData,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      setResult({
        candidateId,
        status: 'completed',
        message: `✓ 처리 완료: PII ${data.pii_count}개 제거됨`,
      })
      clearAll()
    } catch (e) {
      setResult({
        candidateId,
        status: 'error',
        message: `✗ 오류: ${e instanceof Error ? e.message : 'Unknown error'}`,
      })
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#f8f9fa] p-8">
      <div className="max-w-6xl mx-auto">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{ backgroundColor: C_PRIMARY }}
            >
              <FileText size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#202124]">이력서 변환기 v3</h1>
              <p className="text-sm text-[#5F6368]">PII 제거 + 5개 파일 섹션 분할</p>
            </div>
          </div>
          <button
            onClick={clearAll}
            className="px-4 py-2 text-sm font-medium text-[#E24B4A] hover:bg-[#fef2f2] rounded-lg transition-colors"
          >
            초기화
          </button>
        </div>

        {/* 지원자 번호 입력 */}
        <div className="bg-white rounded-2xl border border-[#e8eaed] p-6 mb-6">
          <label className="block text-sm font-semibold text-[#202124] mb-2">지원자 번호</label>
          <input
            type="text"
            value={candidateId}
            onChange={e => setCandidateId(e.target.value)}
            placeholder="예: 3126"
            className="w-full text-sm px-4 py-3 border border-[#e8eaed] rounded-xl outline-none focus:border-[#1D9E75]"
          />
        </div>

        {/* 5개 파일 섹션 */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          {fileSections.map(section => (
            <div key={section.id} className="bg-white rounded-2xl border border-[#e8eaed] p-4">
              {/* 섹션 헤더 */}
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-semibold text-[#202124]">{section.label}</p>
                  <p className="text-xs text-[#5F6368]">{section.description}</p>
                </div>
                {section.files.length > 0 && (
                  <button
                    onClick={() => clearSection(section.id)}
                    className="p-1 text-[#E24B4A] hover:bg-[#fef2f2] rounded-lg"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>

              {/* 드래그 드롭 영역 */}
              <div
                onDragOver={e => handleDragOver(section.id, e)}
                onDragLeave={() => handleDragLeave(section.id)}
                onDrop={e => handleDrop(section.id, e)}
                onClick={() => handleFileClick(section.id)}
                className={`border-2 border-dashed rounded-xl p-3 text-center cursor-pointer transition-all ${
                  section.isDragging
                    ? 'border-[#1D9E75] bg-[#f0fdf4]'
                    : 'border-[#e8eaed] hover:border-[#1D9E75] hover:bg-[#f8fefc]'
                }`}
              >
                <Upload size={20} className="mx-auto mb-1" style={{ color: C_PRIMARY }} />
                <p className="text-xs font-medium text-[#202124]">파일 드래그</p>
                <input
                  ref={el => {
                    if (el) fileInputRefs.current[section.id] = el
                  }}
                  type="file"
                  multiple
                  onChange={e => handleFileChange(section.id, e)}
                  className="hidden"
                  accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.webp"
                />
              </div>

              {/* 파일 목록 */}
              {section.files.length > 0 && (
                <div className="mt-2 space-y-1">
                  {section.files.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-xs px-2 py-1 bg-[#f8f9fa] rounded"
                    >
                      <span className="text-[#202124] truncate">{file.name}</span>
                      <button
                        onClick={() => removeFile(section.id, idx)}
                        className="text-[#E24B4A] hover:text-[#c12020]"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* 파일 개수 */}
              <p className="text-xs text-[#5F6368] mt-2">
                {section.files.length > 0 ? `${section.files.length}개 파일` : '파일 없음'}
              </p>
            </div>
          ))}
        </div>

        {/* 변환 버튼 */}
        <button
          onClick={startProcessing}
          disabled={isProcessing}
          className="w-full py-4 rounded-2xl text-white font-semibold text-lg transition-all disabled:opacity-60"
          style={{ backgroundColor: C_PRIMARY }}
        >
          {isProcessing ? (
            <>
              <Loader2 size={18} className="inline mr-2 animate-spin" />
              처리 중...
            </>
          ) : (
            '변환 시작'
          )}
        </button>

        {/* 결과 메시지 */}
        {result && (
          <div
            className={`mt-6 p-4 rounded-2xl text-sm ${
              result.status === 'completed'
                ? 'bg-[#f0fdf4] text-[#1D9E75] border border-[#1D9E75]'
                : 'bg-[#fef2f2] text-[#E24B4A] border border-[#E24B4A]'
            }`}
          >
            {result.status === 'completed' ? (
              <CheckCircle2 size={18} className="inline mr-2" />
            ) : (
              <AlertCircle size={18} className="inline mr-2" />
            )}
            {result.message}
          </div>
        )}
      </div>
    </div>
  )
}

export default function ResumeConverterPage() {
  const { authed, login, waking } = useAdminAuth()

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return <ResumeConverterInner />
}
