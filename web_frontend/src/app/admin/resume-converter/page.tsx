'use client'

/**
 * /admin/resume-converter — 이력서 변환기
 * Admin HMAC 인증 후 접근 가능
 * FastAPI: POST /api/resume/process | GET /api/resume/preview/{job_id} | GET /api/resume/download/{job_id}
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { FileText, Upload, Eye, Download, Loader2, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react'

// ── 타입 ──────────────────────────────────────────────────────────────────
interface JobStatus {
  job_id:     string
  status:     'pending' | 'processing' | 'completed' | 'error'
  step:       string
  pii_count:  number
  output_file?: string
  error?:     string
}

interface UnprocessedRow {
  id:     string
  name:   string
  status: string
}

// ── 컬러 팔레트 ────────────────────────────────────────────────────────────
const C_PRIMARY = '#1D9E75'
const C_WARN    = '#EF9F27'
const C_DANGER  = '#E24B4A'

// ── 메인 컴포넌트 ──────────────────────────────────────────────────────────
function ResumeConverterInner() {
  const { headers } = useAdminAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef      = useRef<NodeJS.Timeout | null>(null)

  const [candidateId,  setCandidateId]  = useState('')
  const [files,        setFiles]        = useState<File[]>([])
  const [isDragging,   setIsDragging]   = useState(false)
  const [jobStatus,    setJobStatus]    = useState<JobStatus | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [unprocessed,  setUnprocessed]  = useState<UnprocessedRow[]>([])
  const [previewUrl,   setPreviewUrl]   = useState<string | null>(null)
  const [piiText,      setPiiText]      = useState<string>('')

  // ── 미처리 목록 로드 ─────────────────────────────────────────────────
  const loadUnprocessed = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/resume/unprocessed`, { headers: headers() })
      if (res.ok) {
        const data = await res.json()
        setUnprocessed(data.rows || [])
      }
    } catch {
      /* silent */
    }
  }, [headers])

  useEffect(() => { loadUnprocessed() }, [loadUnprocessed])

  // ── 파일 드롭 ────────────────────────────────────────────────────────
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = Array.from(e.dataTransfer.files)
    setFiles(prev => [...prev, ...dropped])
  }, [])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(prev => [...prev, ...Array.from(e.target.files!)])
    }
  }

  const removeFile = (idx: number) => setFiles(prev => prev.filter((_, i) => i !== idx))

  // ── 처리 시작 ──────────────────────────────────────────────────────
  const startProcessing = async () => {
    if (!candidateId.trim()) { alert('강사 번호를 입력하세요.'); return }
    if (files.length === 0)  { alert('파일을 추가하세요.'); return }

    setIsProcessing(true)
    setJobStatus(null)
    setPiiText('')

    const formData = new FormData()
    formData.append('candidate_id', candidateId.trim())
    files.forEach(f => formData.append('files', f))

    try {
      const res = await fetch(`${API_URL}/api/resume/process`, {
        method: 'POST',
        headers: headers(),
        body: formData,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setJobStatus(data)
      _pollStatus(data.job_id)
    } catch (e) {
      setJobStatus({ job_id: '', status: 'error', step: '', pii_count: 0, error: String(e) })
      setIsProcessing(false)
    }
  }

  // ── 폴링 ────────────────────────────────────────────────────────────
  const _pollStatus = (jobId: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res  = await fetch(`${API_URL}/api/resume/preview/${jobId}`, { headers: headers() })
        if (!res.ok) return
        const data: JobStatus = await res.json()
        setJobStatus(data)
        if (data.pii_count !== undefined && data.step) {
          setPiiText(`단계: ${data.step} | PII 제거: ${data.pii_count}개`)
        }
        if (data.status === 'completed' || data.status === 'error') {
          clearInterval(pollRef.current!)
          setIsProcessing(false)
        }
      } catch { /* silent */ }
    }, 1500)
  }

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  // ── 다운로드 ────────────────────────────────────────────────────────
  const downloadFile = async () => {
    if (!jobStatus?.job_id) return
    const res = await fetch(`${API_URL}/api/resume/download/${jobStatus.job_id}`, { headers: headers() })
    if (!res.ok) return
    const blob = await res.blob()
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = jobStatus.output_file || 'output.pdf'
    a.click()
    URL.revokeObjectURL(url)
  }

  // ── 파일 타입 배지 ──────────────────────────────────────────────────
  const getFileBadge = (name: string) => {
    const n = name.toLowerCase()
    if (/\.(jpg|jpeg|png|webp)$/.test(n)) return { label: '사진',    color: '#5B7CF6' }
    if (/cover/.test(n))                  return { label: '커버레터', color: C_WARN }
    if (/(rec|recommend|reference)/.test(n)) return { label: '추천서', color: C_DANGER }
    return { label: '이력서', color: C_PRIMARY }
  }

  // ── 렌더 ────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#f8f9fa] p-6">
      <div className="max-w-5xl mx-auto">

        {/* 헤더 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                 style={{ backgroundColor: C_PRIMARY }}>
              <FileText size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#202124]">이력서 변환기</h1>
              <p className="text-[12px] text-[#5F6368]">PII 제거 + 증명사진 크롭 + PDF 조립</p>
            </div>
          </div>
          <button
            onClick={loadUnprocessed}
            className="flex items-center gap-1.5 text-[12px] text-[#5F6368] hover:text-[#202124] transition-colors"
          >
            <RefreshCw size={14} />
            목록 새로고침
          </button>
        </div>

        <div className="grid grid-cols-3 gap-4">

          {/* 좌측: 입력 */}
          <div className="col-span-2 space-y-4">

            {/* 강사 번호 */}
            <div className="bg-white rounded-2xl border border-[#e8eaed] p-4">
              <label className="block text-[12px] font-semibold text-[#202124] mb-2">강사 번호</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={candidateId}
                  onChange={e => setCandidateId(e.target.value)}
                  placeholder="예: 3126"
                  className="flex-1 text-[13px] px-3 py-2 border border-[#e8eaed] rounded-xl outline-none focus:border-[#1D9E75]"
                />
                <select
                  value={candidateId}
                  onChange={e => setCandidateId(e.target.value)}
                  className="text-[12px] px-2 py-2 border border-[#e8eaed] rounded-xl outline-none bg-white"
                >
                  <option value="">미처리 목록</option>
                  {unprocessed.map(r => (
                    <option key={r.id} value={r.id}>{r.id} — {r.name}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* 파일 드롭 영역 */}
            <div
              onDrop={onDrop}
              onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
              onClick={() => fileInputRef.current?.click()}
              className={`bg-white rounded-2xl border-2 border-dashed cursor-pointer transition-all p-8 text-center ${
                isDragging
                  ? 'border-[#1D9E75] bg-[#f0fdf4]'
                  : 'border-[#e8eaed] hover:border-[#1D9E75] hover:bg-[#f8fefc]'
              }`}
            >
              <Upload size={28} className="mx-auto mb-2" style={{ color: C_PRIMARY }} />
              <p className="text-[13px] font-medium text-[#202124]">파일 드래그 또는 클릭</p>
              <p className="text-[11px] text-[#5F6368] mt-1">사진 / 이력서 / 커버레터 / 추천서</p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={onFileChange}
              />
            </div>

            {/* 파일 목록 */}
            {files.length > 0 && (
              <div className="bg-white rounded-2xl border border-[#e8eaed] p-4">
                <p className="text-[12px] font-semibold text-[#202124] mb-3">첨부 파일</p>
                <div className="space-y-2">
                  {files.map((f, i) => {
                    const badge = getFileBadge(f.name)
                    return (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-[#f0f0f0] last:border-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] px-2 py-0.5 rounded-full text-white font-semibold"
                                style={{ backgroundColor: badge.color }}>
                            {badge.label}
                          </span>
                          <span className="text-[12px] text-[#202124]">{f.name}</span>
                          <span className="text-[10px] text-[#aaa]">({(f.size/1024).toFixed(0)}KB)</span>
                        </div>
                        <button
                          onClick={() => removeFile(i)}
                          className="text-[11px] text-[#E24B4A] hover:underline"
                        >삭제</button>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* PII 결과 */}
            {piiText && (
              <div className="bg-white rounded-2xl border border-[#e8eaed] p-4">
                <p className="text-[12px] font-semibold text-[#202124] mb-2">처리 현황</p>
                <p className="text-[12px] text-[#5F6368] font-mono">{piiText}</p>
              </div>
            )}

            {/* 실행 버튼 */}
            <button
              onClick={startProcessing}
              disabled={isProcessing}
              className="w-full py-3 rounded-2xl text-white font-semibold text-[14px] transition-all flex items-center justify-center gap-2 disabled:opacity-60"
              style={{ backgroundColor: C_PRIMARY }}
            >
              {isProcessing
                ? <><Loader2 size={16} className="animate-spin" /> 처리 중...</>
                : <>이력서 변환 시작</>
              }
            </button>
          </div>

          {/* 우측: 결과 */}
          <div className="space-y-4">

            {/* 상태 카드 */}
            {jobStatus && (
              <div className={`rounded-2xl border p-4 ${
                jobStatus.status === 'completed' ? 'border-[#1D9E75] bg-[#f0fdf4]'
                : jobStatus.status === 'error'   ? 'border-[#E24B4A] bg-[#fef2f2]'
                : 'border-[#e8eaed] bg-white'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  {jobStatus.status === 'completed' && <CheckCircle2 size={16} color={C_PRIMARY} />}
                  {jobStatus.status === 'error'     && <AlertCircle  size={16} color={C_DANGER} />}
                  {jobStatus.status === 'processing'&& <Loader2 size={16} className="animate-spin" color={C_WARN} />}
                  <span className="text-[12px] font-semibold text-[#202124]">
                    {jobStatus.status === 'completed' ? '완료'
                     : jobStatus.status === 'error'   ? '오류'
                     : '처리 중'}
                  </span>
                </div>
                <p className="text-[11px] text-[#5F6368]">단계: {jobStatus.step}</p>
                <p className="text-[11px] text-[#5F6368]">PII 제거: {jobStatus.pii_count}개</p>
                {jobStatus.output_file && (
                  <p className="text-[11px] text-[#202124] font-mono mt-1 break-all">{jobStatus.output_file}</p>
                )}
                {jobStatus.error && (
                  <p className="text-[11px] text-[#E24B4A] mt-1">{jobStatus.error}</p>
                )}
              </div>
            )}

            {/* 다운로드 */}
            {jobStatus?.status === 'completed' && (
              <button
                onClick={downloadFile}
                className="w-full py-3 rounded-2xl border border-[#1D9E75] text-[#1D9E75] font-semibold text-[13px] hover:bg-[#f0fdf4] transition-all flex items-center justify-center gap-2"
              >
                <Download size={15} />
                PDF 다운로드
              </button>
            )}

            {/* 미처리 목록 */}
            <div className="bg-white rounded-2xl border border-[#e8eaed] p-4">
              <p className="text-[12px] font-semibold text-[#202124] mb-2">미처리 목록</p>
              {unprocessed.length === 0
                ? <p className="text-[11px] text-[#aaa]">없음</p>
                : unprocessed.slice(0, 10).map(r => (
                    <div key={r.id}
                         onClick={() => setCandidateId(r.id)}
                         className="py-1.5 cursor-pointer hover:text-[#1D9E75] transition-colors border-b border-[#f0f0f0] last:border-0">
                      <span className="text-[12px] font-semibold">{r.id}</span>
                      <span className="text-[11px] text-[#5F6368] ml-2">{r.name}</span>
                    </div>
                  ))
              }
            </div>

          </div>
        </div>
      </div>
    </div>
  )
}

export default function ResumeConverterPage() {
  return (
    <AdminAuth>
      <ResumeConverterInner />
    </AdminAuth>
  )
}
