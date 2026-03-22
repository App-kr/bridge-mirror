'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { X, Phone, MessageCircle, Mail, Camera, Loader2 } from 'lucide-react'

const API = API_URL

const STAGES = [
  { value: 'new', label: 'New', color: '#3b82f6', bg: '#eff6ff' },
  { value: 'review', label: 'Review', color: '#8b5cf6', bg: '#f5f3ff' },
  { value: 'contacted', label: 'Contacted', color: '#06b6d4', bg: '#ecfeff' },
  { value: 'interview', label: 'Interview', color: '#f59e0b', bg: '#fffbeb' },
  { value: 'offer', label: 'Offer', color: '#10b981', bg: '#ecfdf5' },
  { value: 'contract', label: 'Contract', color: '#059669', bg: '#d1fae5' },
  { value: 'hired', label: 'Hired', color: '#047857', bg: '#d1fae5' },
  { value: 'rejected', label: 'Rejected', color: '#ef4444', bg: '#fef2f2' },
  { value: 'on_hold', label: 'On Hold', color: '#6b7280', bg: '#f9fafb' },
]

interface CandidateDetailProps {
  candidateId: number
  onClose: () => void
  onStageChange: (id: number, stage: string) => void
}

interface CandidateData {
  id: number
  name: string
  email: string | null
  phone: string | null
  nationality: string | null
  photo_url: string | null
  stage: string | null
  submitted_at: string | null
  kakao_id: string | null
  visa_type: string | null
  education: string | null
  experience: string | null
  preferred_location: string | null
  age: string | null
  gender: string | null
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

function getInitialColor(name: string): string {
  const colors = ['#0071e3', '#34c759', '#ff9f0a', '#af52de', '#ff3b30', '#5ac8fa', '#ff2d55']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

export default function CandidateDetail({ candidateId, onClose, onStageChange }: CandidateDetailProps) {
  const { adminFetch, signedFetch } = useAdminAuth()
  const [data, setData] = useState<CandidateData | null>(null)
  const [loading, setLoading] = useState(true)
  const [stageUpdating, setStageUpdating] = useState(false)
  const [visible, setVisible] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Trigger slide-up animation
    requestAnimationFrame(() => setVisible(true))
  }, [])

  const handleClose = useCallback(() => {
    setVisible(false)
    setTimeout(onClose, 300) // wait for animation
  }, [onClose])

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const res = await adminFetch(`${API}/api/admin/candidates/${candidateId}`)
        const json = await res.json()
        if (json.success) setData(json.data)
      } catch {
        // silent
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [candidateId, adminFetch])

  const handleStageChange = useCallback(async (newStage: string) => {
    if (!data || stageUpdating) return
    setStageUpdating(true)
    try {
      const res = await signedFetch(`${API}/api/admin/candidates/${data.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ stage: newStage }),
      })
      const json = await res.json()
      if (json.success) {
        setData(prev => prev ? { ...prev, stage: newStage } : prev)
        onStageChange(data.id, newStage)
      }
    } catch {
      // silent
    } finally {
      setStageUpdating(false)
    }
  }, [data, stageUpdating, signedFetch, onStageChange])

  const handlePhotoUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !data) return
    const formData = new FormData()
    formData.append('photo', file)
    try {
      const res = await signedFetch(`${API}/api/admin/candidates/${data.id}/photo`, {
        method: 'POST',
        body: formData,
      })
      const json = await res.json()
      if (json.success && json.data?.photo_url) {
        setData(prev => prev ? { ...prev, photo_url: json.data.photo_url } : prev)
      }
    } catch {
      // silent
    }
    // reset file input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [data, signedFetch])

  const photoSrc = data?.photo_url
    ? (data.photo_url.startsWith('/') ? `${API}${data.photo_url}` : data.photo_url)
    : null

  const currentStage = data?.stage || 'new'

  const infoFields = data ? [
    { label: 'Email', value: data.email },
    { label: 'Phone', value: data.phone },
    { label: 'Visa', value: data.visa_type },
    { label: 'Education', value: data.education },
    { label: 'Experience', value: data.experience },
    { label: 'Location', value: data.preferred_location },
    { label: 'Age', value: data.age },
    { label: 'Gender', value: data.gender },
  ] : []

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      {/* Backdrop */}
      <div
        className={`absolute inset-0 bg-black transition-opacity duration-300 ${visible ? 'opacity-40' : 'opacity-0'}`}
        onClick={handleClose}
      />

      {/* Panel */}
      <div
        className={`relative bg-white rounded-t-3xl max-h-[85vh] overflow-y-auto transition-transform duration-300 ease-out ${
          visible ? 'translate-y-0' : 'translate-y-full'
        }`}
      >
        {/* Handle bar */}
        <div className="sticky top-0 bg-white rounded-t-3xl z-10 pt-3 pb-2 px-4 flex justify-center">
          <div className="w-9 h-1 rounded-full bg-[#d1d1d6]" />
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-[#86868b]" />
          </div>
        ) : !data ? (
          <div className="text-center py-20 text-[#86868b] text-sm">
            Candidate not found
          </div>
        ) : (
          <div className="px-4 pb-8">
            {/* Close button */}
            <button
              type="button"
              onClick={handleClose}
              className="absolute top-4 right-4 w-8 h-8 rounded-full bg-[#f5f5f7] flex items-center justify-center z-20"
            >
              <X size={16} className="text-[#86868b]" />
            </button>

            {/* ── Header ── */}
            <div className="flex items-center gap-4 mb-6 mt-2">
              {photoSrc ? (
                <img
                  src={photoSrc}
                  alt={data.name}
                  className="w-20 h-20 rounded-full object-cover border-2 border-[#e5e5e7]"
                />
              ) : (
                <div
                  className="w-20 h-20 rounded-full flex items-center justify-center text-white text-xl font-bold"
                  style={{ backgroundColor: getInitialColor(data.name) }}
                >
                  {getInitials(data.name)}
                </div>
              )}
              <div>
                <h2 className="text-xl font-bold text-[#1d1d1f]">{data.name}</h2>
                <p className="text-sm text-[#86868b]">{data.nationality || 'Unknown nationality'}</p>
                {data.submitted_at && (
                  <p className="text-xs text-[#86868b] mt-0.5">
                    {new Date(data.submitted_at).toLocaleDateString('ko-KR', {
                      year: 'numeric', month: 'long', day: 'numeric',
                    })}
                  </p>
                )}
              </div>
            </div>

            {/* ── Stage Selector ── */}
            <div className="mb-6">
              <h3 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider mb-2">
                Stage
              </h3>
              <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                {STAGES.map((s) => {
                  const isActive = currentStage === s.value
                  return (
                    <button
                      key={s.value}
                      type="button"
                      disabled={stageUpdating}
                      onClick={() => handleStageChange(s.value)}
                      className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all min-h-[36px] ${
                        stageUpdating ? 'opacity-50' : ''
                      }`}
                      style={{
                        color: isActive ? '#fff' : s.color,
                        backgroundColor: isActive ? s.color : s.bg,
                        border: isActive ? 'none' : `1px solid ${s.bg}`,
                      }}
                    >
                      {s.label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* ── Info Grid ── */}
            <div className="mb-6">
              <h3 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider mb-2">
                Information
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {infoFields.map((field) => (
                  <div key={field.label} className="bg-[#f5f5f7] rounded-xl px-3 py-2.5">
                    <p className="text-[10px] text-[#86868b] uppercase tracking-wider font-medium">
                      {field.label}
                    </p>
                    <p className="text-sm text-[#1d1d1f] font-medium mt-0.5 truncate">
                      {field.value || '-'}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* ── Action Buttons ── */}
            <div className="grid grid-cols-4 gap-3">
              {/* Call */}
              <a
                href={data.phone ? `tel:${data.phone}` : undefined}
                className={`flex flex-col items-center justify-center gap-1.5 py-3 rounded-2xl min-h-[44px] ${
                  data.phone
                    ? 'bg-[#34c759]/10 text-[#34c759] active:bg-[#34c759]/20'
                    : 'bg-[#f5f5f7] text-[#d1d1d6] pointer-events-none'
                } transition-colors`}
              >
                <Phone size={20} />
                <span className="text-[10px] font-medium">Call</span>
              </a>

              {/* KakaoTalk */}
              <a
                href="https://open.kakao.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center justify-center gap-1.5 py-3 rounded-2xl bg-[#FEE500]/20 text-[#3C1E1E] active:bg-[#FEE500]/30 transition-colors min-h-[44px]"
              >
                <MessageCircle size={20} />
                <span className="text-[10px] font-medium">Kakao</span>
              </a>

              {/* Email */}
              <a
                href={data.email ? `mailto:${data.email}` : undefined}
                className={`flex flex-col items-center justify-center gap-1.5 py-3 rounded-2xl min-h-[44px] ${
                  data.email
                    ? 'bg-[#0071e3]/10 text-[#0071e3] active:bg-[#0071e3]/20'
                    : 'bg-[#f5f5f7] text-[#d1d1d6] pointer-events-none'
                } transition-colors`}
              >
                <Mail size={20} />
                <span className="text-[10px] font-medium">Email</span>
              </a>

              {/* Camera / Photo Upload */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex flex-col items-center justify-center gap-1.5 py-3 rounded-2xl bg-[#ff9f0a]/10 text-[#ff9f0a] active:bg-[#ff9f0a]/20 transition-colors min-h-[44px]"
              >
                <Camera size={20} />
                <span className="text-[10px] font-medium">Photo</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handlePhotoUpload}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
