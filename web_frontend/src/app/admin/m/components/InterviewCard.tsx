'use client'

import { Video } from 'lucide-react'

interface InterviewCardProps {
  interview: {
    id: number
    candidate_name: string
    candidate_email: string
    candidate_id: string
    employer_name: string
    interview_date: string
    interview_time: string
    meet_link: string
    status: string
    notes: string
    duration_minutes: number
    email_sent_candidate: number
    email_sent_employer: number
  }
  onStatusChange: (id: number, status: string) => void
}

const STATUS_CONFIG: Record<string, { label: string; color: string; border: string }> = {
  scheduled:  { label: '예정',  color: '#2563eb', border: 'border-l-[#2563eb]' },
  completed:  { label: '완료',  color: '#16a34a', border: 'border-l-[#16a34a]' },
  cancelled:  { label: '취소',  color: '#6b7280', border: 'border-l-[#6b7280]' },
  no_show:    { label: '불참',  color: '#dc2626', border: 'border-l-[#dc2626]' },
}

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

function formatKR(date: string, time: string) {
  const d = new Date(`${date}T${time || '00:00'}`)
  const m = d.getMonth() + 1, day = d.getDate()
  const wd = WEEKDAYS[d.getDay()]
  const [h, min] = (time || '00:00').split(':').map(Number)
  const ampm = h < 12 ? '오전' : '오후'
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h
  return `${m}월 ${day}일 (${wd}) ${ampm} ${h12}:${String(min).padStart(2, '0')}`
}

function getRelativeDay(dateStr: string): string | null {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr + 'T00:00:00')
  target.setHours(0, 0, 0, 0)
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000)
  if (diff === 0) return '오늘'
  if (diff === 1) return '내일'
  if (diff > 1 && diff <= 7) return `${diff}일 후`
  if (diff === -1) return '어제'
  if (diff < -1) return `${Math.abs(diff)}일 전`
  return null
}

export default function InterviewCard({ interview, onStatusChange }: InterviewCardProps) {
  const status = interview.status || 'scheduled'
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.scheduled
  const relDay = getRelativeDay(interview.interview_date)

  return (
    <div
      className="bg-white rounded-2xl border border-[#e5e5e7] border-l-4 px-4 py-3 space-y-2.5"
      style={{ borderLeftColor: cfg.color }}
    >
      {/* Top: status + relative date */}
      <div className="flex items-center justify-between">
        <span
          className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
          style={{
            color: cfg.color,
            backgroundColor: cfg.color + '18',
          }}
        >
          {cfg.label}
        </span>
        {relDay && (
          <span className="text-[11px] font-medium text-[#86868b] bg-[#f5f5f7] px-2 py-0.5 rounded-full">
            {relDay}
          </span>
        )}
      </div>

      {/* Date/Time */}
      <p className="text-base font-bold text-[#1d1d1f]">
        {formatKR(interview.interview_date, interview.interview_time)}
      </p>

      {/* Candidate + employer */}
      <div className="space-y-1">
        <div className="text-sm text-[#1d1d1f]">
          <span className="text-[#86868b]">후보자: </span>
          {interview.candidate_name}
          {interview.candidate_id && (
            <span className="text-[#aeaeb2] text-xs ml-1">#{interview.candidate_id}</span>
          )}
        </div>
        <div className="text-sm text-[#1d1d1f]">
          <span className="text-[#86868b]">학원: </span>
          {interview.employer_name}
        </div>
      </div>

      {/* Duration */}
      {interview.duration_minutes > 0 && (
        <p className="text-xs text-[#aeaeb2]">{interview.duration_minutes}분 소요</p>
      )}

      {/* Notes */}
      {interview.notes && (
        <p className="text-xs text-[#86868b] bg-[#f5f5f7] rounded-xl px-3 py-2 line-clamp-2">
          {interview.notes}
        </p>
      )}

      {/* Email sent indicators */}
      <div className="flex gap-3">
        {interview.email_sent_candidate === 1 && (
          <span className="text-[10px] text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
            후보자 발송완료
          </span>
        )}
        {interview.email_sent_employer === 1 && (
          <span className="text-[10px] text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
            학원 발송완료
          </span>
        )}
      </div>

      {/* Meet link + action buttons */}
      <div className="flex items-center gap-2 pt-1">
        {interview.meet_link && (
          <a
            href={interview.meet_link}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-[#0071e3] text-white text-sm font-medium min-h-[44px] active:opacity-80 transition-opacity"
          >
            <Video size={16} />
            Meet 참가
          </a>
        )}

        {status === 'scheduled' ? (
          <>
            <button
              type="button"
              onClick={() => onStatusChange(interview.id, 'completed')}
              className="px-3 py-2.5 rounded-xl bg-green-50 text-green-700 text-sm font-medium min-h-[44px] active:opacity-80 transition-opacity"
            >
              완료
            </button>
            <button
              type="button"
              onClick={() => onStatusChange(interview.id, 'no_show')}
              className="px-3 py-2.5 rounded-xl bg-red-50 text-red-700 text-sm font-medium min-h-[44px] active:opacity-80 transition-opacity"
            >
              불참
            </button>
            <button
              type="button"
              onClick={() => onStatusChange(interview.id, 'cancelled')}
              className="px-3 py-2.5 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium min-h-[44px] active:opacity-80 transition-opacity"
            >
              취소
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => onStatusChange(interview.id, 'scheduled')}
            className="flex-1 py-2.5 rounded-xl bg-[#f5f5f7] text-[#1d1d1f] text-sm font-medium min-h-[44px] active:opacity-80 transition-opacity"
          >
            재예약
          </button>
        )}
      </div>
    </div>
  )
}
