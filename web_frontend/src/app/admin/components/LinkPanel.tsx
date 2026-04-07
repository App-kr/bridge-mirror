'use client'

import { useCallback, useEffect, useState } from 'react'
import { X, RefreshCw, FileText, Calendar } from 'lucide-react'
import { API_URL } from '@/lib/api'

function _key() {
  return typeof window !== 'undefined' ? (localStorage.getItem('bridge_admin_key') || '') : ''
}
function _h(): Record<string, string> {
  return { 'x-admin-key': _key() }
}

interface MatchCandidate {
  candidate_id: number
  name: string
  candidate_number?: string
  score: number
  teaching_age?: string
  location?: string
}

interface MatchJob {
  id: number
  title?: string
  company?: string
  school_name?: string
  location?: string
  score: number
}

interface InterviewRecord {
  id: number
  interview_date: string
  interview_time: string
  employer_name: string
  status: string
}

interface LinkPanelProps {
  mode: 'employer' | 'candidate'
  // employer mode
  jobNumber?: string
  jobTitle?: string
  region?: string
  teachingAge?: string
  // candidate mode
  candidateId?: number
  candidateName?: string
  candidateNumber?: string
  onClose: () => void
}

const STATUS_STYLE: Record<string, { bg: string; text: string }> = {
  completed: { bg: '#f0fdf4', text: '#16a34a' },
  cancelled:  { bg: '#fef2f2', text: '#ef4444' },
  no_show:    { bg: '#fff7ed', text: '#c2410c' },
  scheduled:  { bg: '#eff6ff', text: '#2563eb' },
}

export default function LinkPanel({
  mode, jobNumber, jobTitle, region, teachingAge,
  candidateId, candidateName, candidateNumber, onClose,
}: LinkPanelProps) {
  const [candidates, setCandidates] = useState<MatchCandidate[]>([])
  const [jobs, setJobs] = useState<MatchJob[]>([])
  const [interviews, setInterviews] = useState<InterviewRecord[]>([])
  const [resumeUrl, setResumeUrl] = useState<string | null>(null)
  const [loadingMatch, setLoadingMatch] = useState(false)
  const [loadingResume, setLoadingResume] = useState(false)
  const [selectedCandidate, setSelectedCandidate] = useState<MatchCandidate | null>(null)
  const [tab, setTab] = useState<'match' | 'resume' | 'interviews'>('match')

  /* ── 고용주 모드: 매칭 후보 조회 ── */
  const fetchCandidatesForJob = useCallback(async () => {
    if (!jobNumber) return
    setLoadingMatch(true)
    try {
      const p = new URLSearchParams({ job_number: jobNumber })
      if (region) p.set('region', region)
      if (teachingAge) p.set('teaching_age', teachingAge)
      const r = await fetch(`${API_URL}/api/admin/matching/candidates-for-job?${p}`, { headers: _h() })
      const j = await r.json()
      if (j.success) setCandidates(j.data?.candidates || [])
    } catch { /* 네트워크 오류 — 무시 */ }
    setLoadingMatch(false)
  }, [jobNumber, region, teachingAge])

  /* ── 후보자 모드: 매칭 업체 조회 ── */
  const fetchJobsForCandidate = useCallback(async () => {
    if (!candidateId) return
    setLoadingMatch(true)
    try {
      const r = await fetch(`${API_URL}/api/admin/matching/jobs-for-candidate?candidate_id=${candidateId}`, { headers: _h() })
      const j = await r.json()
      if (j.success) setJobs(j.data?.jobs || [])
    } catch { /* 무시 */ }
    setLoadingMatch(false)
  }, [candidateId])

  /* ── 후보자 모드: 인터뷰 이력 조회 ── */
  const fetchInterviews = useCallback(async () => {
    if (!candidateId) return
    try {
      const r = await fetch(`${API_URL}/api/admin/interviews?candidate_id=${candidateId}`, { headers: _h() })
      const j = await r.json()
      if (j.success) setInterviews(j.data?.interviews || j.data || [])
    } catch { /* 무시 */ }
  }, [candidateId])

  useEffect(() => {
    if (mode === 'employer') fetchCandidatesForJob()
    else { fetchJobsForCandidate(); fetchInterviews() }
  }, [mode, fetchCandidatesForJob, fetchJobsForCandidate, fetchInterviews])

  /* ── 이력서 presigned URL 로드 ── */
  const loadResume = async (num: string, cand: MatchCandidate) => {
    setSelectedCandidate(cand)
    setLoadingResume(true)
    setResumeUrl(null)
    setTab('resume')
    try {
      const r = await fetch(`${API_URL}/api/admin/resume/find/${encodeURIComponent(num)}`, { headers: _h() })
      const j = await r.json()
      if (j.success && j.data?.presigned_url) setResumeUrl(j.data.presigned_url)
    } catch { /* 무시 */ }
    setLoadingResume(false)
  }

  /* ── 탭 라벨 ── */
  const tabLabel = (t: string) => {
    if (t === 'match') return mode === 'employer' ? '매칭 후보' : '매칭 업체'
    if (t === 'resume') return '이력서'
    return '인터뷰 이력'
  }

  const tabs = mode === 'employer' ? ['match', 'resume'] : ['match', 'interviews']

  return (
    <div
      onClick={e => e.stopPropagation()}
      style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 420,
        zIndex: 900, display: 'flex', flexDirection: 'column',
        background: '#fff', boxShadow: '-4px 0 24px rgba(0,0,0,0.12)',
        borderLeft: '1px solid #e5e5e7',
      }}
    >
      {/* ── 헤더 ── */}
      <div style={{ padding: '16px 20px 12px', borderBottom: '1px solid #f0f0f2', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1d1d1f', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {mode === 'employer' ? `${jobTitle || jobNumber || '공고'} 연동` : `${candidateName || '후보자'} 연동`}
          </div>
          <div style={{ fontSize: 11, color: '#86868b', marginTop: 2 }}>
            {mode === 'employer' ? '매칭 후보자 · 이력서 미리보기' : '매칭 업체 · 인터뷰 이력'}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{ padding: 6, border: 'none', background: 'none', cursor: 'pointer', color: '#86868b', display: 'flex', alignItems: 'center', borderRadius: 8 }}
          aria-label="닫기"
        >
          <X size={18} />
        </button>
      </div>

      {/* ── 탭 ── */}
      <div style={{ display: 'flex', borderBottom: '1px solid #f0f0f2', padding: '0 20px' }}>
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setTab(t as typeof tab)}
            style={{
              padding: '10px 12px', fontSize: 12, fontWeight: 600,
              border: 'none', background: 'none', cursor: 'pointer',
              color: tab === t ? '#2563eb' : '#86868b',
              borderBottom: tab === t ? '2px solid #2563eb' : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            {tabLabel(t)}
          </button>
        ))}
      </div>

      {/* ── 본문 ── */}
      <div style={{ flex: 1, overflow: 'auto', padding: 14 }}>

        {/* 고용주 모드 — 매칭 후보 탭 */}
        {mode === 'employer' && tab === 'match' && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 11, color: '#86868b' }}>후보 {candidates.length}명</span>
              <button
                onClick={fetchCandidatesForJob}
                style={{ fontSize: 11, color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
              >
                <RefreshCw size={11} /> 새로고침
              </button>
            </div>
            {loadingMatch ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#86868b', fontSize: 13 }}>불러오는 중…</div>
            ) : candidates.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#86868b', fontSize: 13 }}>매칭 후보가 없습니다</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {candidates.map(c => (
                  <div
                    key={c.candidate_id}
                    style={{
                      border: `1px solid ${selectedCandidate?.candidate_id === c.candidate_id ? '#bfdbfe' : '#e5e5e7'}`,
                      borderRadius: 10, padding: '10px 14px',
                      background: selectedCandidate?.candidate_id === c.candidate_id ? '#eff6ff' : '#fafafa',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#1d1d1f' }}>{c.name}</span>
                        {c.candidate_number && (
                          <span style={{ fontSize: 11, color: '#86868b', marginLeft: 6 }}>#{c.candidate_number}</span>
                        )}
                      </div>
                      <span style={{ fontSize: 11, fontWeight: 700, color: '#2563eb', background: '#eff6ff', borderRadius: 6, padding: '2px 7px' }}>
                        {c.score}점
                      </span>
                    </div>
                    {(c.teaching_age || c.location) && (
                      <div style={{ fontSize: 11, color: '#86868b', marginTop: 3 }}>
                        {[c.teaching_age, c.location].filter(Boolean).join(' · ')}
                      </div>
                    )}
                    {c.candidate_number && (
                      <button
                        onClick={() => loadResume(c.candidate_number!, c)}
                        style={{
                          marginTop: 8, fontSize: 11, color: '#2563eb', background: 'none',
                          border: '1px solid #bfdbfe', borderRadius: 6, padding: '3px 10px',
                          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                        }}
                      >
                        <FileText size={11} /> 이력서 보기
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* 고용주 모드 — 이력서 탭 */}
        {mode === 'employer' && tab === 'resume' && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {selectedCandidate && (
              <div style={{ fontSize: 12, color: '#86868b', marginBottom: 4 }}>
                {selectedCandidate.name} 이력서
              </div>
            )}
            {loadingResume ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#86868b', fontSize: 13 }}>이력서 로딩 중…</div>
            ) : resumeUrl ? (
              <>
                <a
                  href={resumeUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: 11, color: '#2563eb' }}
                >
                  새 탭에서 열기 ↗
                </a>
                <iframe
                  src={resumeUrl}
                  style={{ flex: 1, border: 'none', borderRadius: 8, background: '#f8f8f8', minHeight: 400 }}
                  title="resume-preview"
                />
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#86868b', fontSize: 13 }}>
                매칭 후보 탭에서 이력서 보기를 클릭하세요
              </div>
            )}
          </div>
        )}

        {/* 후보자 모드 — 매칭 업체 탭 */}
        {mode === 'candidate' && tab === 'match' && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 11, color: '#86868b' }}>업체 {jobs.length}건</span>
              <button
                onClick={fetchJobsForCandidate}
                style={{ fontSize: 11, color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
              >
                <RefreshCw size={11} /> 새로고침
              </button>
            </div>
            {loadingMatch ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#86868b', fontSize: 13 }}>불러오는 중…</div>
            ) : jobs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#86868b', fontSize: 13 }}>매칭 업체가 없습니다</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {jobs.map(job => (
                  <div
                    key={job.id}
                    style={{ border: '1px solid #e5e5e7', borderRadius: 10, padding: '10px 14px', background: '#fafafa' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: '#1d1d1f' }}>
                        {job.title || job.school_name || job.company || `Job #${job.id}`}
                      </span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: '#2563eb', background: '#eff6ff', borderRadius: 6, padding: '2px 7px' }}>
                        {job.score}점
                      </span>
                    </div>
                    {(job.company || job.location) && (
                      <div style={{ fontSize: 11, color: '#86868b', marginTop: 3 }}>
                        {[job.company, job.location].filter(Boolean).join(' · ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* 후보자 모드 — 인터뷰 이력 탭 */}
        {mode === 'candidate' && tab === 'interviews' && (
          <>
            {interviews.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#86868b', fontSize: 13 }}>인터뷰 이력이 없습니다</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {interviews.map(iv => {
                  const sc = STATUS_STYLE[iv.status] || STATUS_STYLE.scheduled
                  return (
                    <div
                      key={iv.id}
                      style={{ border: '1px solid #e5e5e7', borderRadius: 10, padding: '10px 14px', background: '#fafafa' }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#1d1d1f' }}>{iv.employer_name}</span>
                        <span style={{ fontSize: 11, fontWeight: 600, color: sc.text, background: sc.bg, borderRadius: 6, padding: '2px 7px' }}>
                          {iv.status}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#86868b', marginTop: 3, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Calendar size={10} />
                        {iv.interview_date} {iv.interview_time}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
