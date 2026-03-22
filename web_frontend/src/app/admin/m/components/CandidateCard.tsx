'use client'

import { API_URL } from '@/lib/api'

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

interface CandidateCardProps {
  candidate: {
    id: number
    name: string
    email: string | null
    nationality: string | null
    phone: string | null
    photo_url: string | null
    stage: string | null
    submitted_at: string | null
    kakao_id: string | null
  }
  onTap: (id: number) => void
  onStageChange: (id: number, stage: string) => void
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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const month = d.getMonth() + 1
  const day = d.getDate()
  return `${month}/${day}`
}

export default function CandidateCard({ candidate, onTap }: CandidateCardProps) {
  const stageInfo = STAGES.find(s => s.value === candidate.stage) ?? STAGES[0]
  const isNew = candidate.stage === 'new'

  const photoSrc = candidate.photo_url
    ? (candidate.photo_url.startsWith('/') ? `${API}${candidate.photo_url}` : candidate.photo_url)
    : null

  return (
    <button
      type="button"
      onClick={() => onTap(candidate.id)}
      className="w-full bg-white rounded-2xl border border-[#e5e5e7] px-4 py-3 flex items-center gap-3 text-left active:bg-[#f5f5f7] transition-colors min-h-[44px]"
    >
      {/* Photo or Initials */}
      <div className="relative shrink-0">
        {photoSrc ? (
          <img
            src={photoSrc}
            alt={candidate.name}
            className="w-12 h-12 rounded-full object-cover"
          />
        ) : (
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-white text-sm font-bold"
            style={{ backgroundColor: getInitialColor(candidate.name) }}
          >
            {getInitials(candidate.name)}
          </div>
        )}
        {isNew && (
          <span className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full bg-red-500 border-2 border-white" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-[#1d1d1f] truncate">
          {candidate.name}
        </p>
        <p className="text-xs text-[#86868b] truncate">
          {candidate.nationality || 'Unknown'}
          {candidate.submitted_at ? ` \u00B7 ${formatDate(candidate.submitted_at)}` : ''}
        </p>
      </div>

      {/* Stage Badge */}
      <span
        className="text-xs font-semibold px-2.5 py-1 rounded-full shrink-0"
        style={{ color: stageInfo.color, backgroundColor: stageInfo.bg }}
      >
        {stageInfo.label}
      </span>
    </button>
  )
}
