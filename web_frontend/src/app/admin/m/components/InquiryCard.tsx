'use client'

interface InquiryCardProps {
  inquiry: {
    id: number
    school_name: string | null
    contact_name: string | null
    location: string | null
    email: string | null
    phone: string | null
    inbox_status: string | null
    submitted_at: string | null
    memo: string | null
    vacancies: string | null
  }
  onTap: (id: number) => void
  onStatusChange: (id: number, status: string) => void
}

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  new:        { label: '신규', bg: 'bg-blue-100', text: 'text-blue-700' },
  pending:    { label: '대기', bg: 'bg-yellow-100', text: 'text-yellow-700' },
  processing: { label: '처리중', bg: 'bg-violet-100', text: 'text-violet-700' },
  completed:  { label: '완료', bg: 'bg-green-100', text: 'text-green-700' },
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    const m = d.getMonth() + 1
    const day = d.getDate()
    return `${m}/${day}`
  } catch {
    return ''
  }
}

export default function InquiryCard({ inquiry, onTap, onStatusChange }: InquiryCardProps) {
  const status = inquiry.inbox_status || 'new'
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.new

  return (
    <button
      type="button"
      onClick={() => onTap(inquiry.id)}
      className="w-full text-left bg-white rounded-2xl border border-[#e5e5e7] px-4 py-3 active:scale-[0.98] transition-transform"
    >
      {/* Top row: school name + status badge */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {status === 'new' && (
            <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
          )}
          <span className="font-semibold text-[15px] text-[#1d1d1f] truncate" title={inquiry.school_name || ''}>
            {inquiry.school_name || 'Unknown School'}
          </span>
        </div>
        <span
          className={`shrink-0 text-[11px] font-medium px-2 py-0.5 rounded-full ${cfg.bg} ${cfg.text}`}
          onClick={(e) => {
            e.stopPropagation()
            const statuses = ['new', 'pending', 'processing', 'completed']
            const idx = statuses.indexOf(status)
            const next = statuses[(idx + 1) % statuses.length]
            onStatusChange(inquiry.id, next)
          }}
        >
          {cfg.label}
        </span>
      </div>

      {/* Middle: contact + location */}
      <div className="flex items-center gap-2 mt-1.5">
        {inquiry.contact_name && (
          <span className="text-xs text-[#86868b]">{inquiry.contact_name}</span>
        )}
        {inquiry.contact_name && inquiry.location && (
          <span className="text-xs text-[#d2d2d7]">|</span>
        )}
        {inquiry.location && (
          <span className="text-xs text-[#86868b]">{inquiry.location}</span>
        )}
      </div>

      {/* Bottom: date + vacancies */}
      <div className="flex items-center gap-2 mt-1.5">
        {inquiry.submitted_at && (
          <span className="text-[11px] text-[#aeaeb2]">
            {formatDate(inquiry.submitted_at)}
          </span>
        )}
        {inquiry.vacancies && (
          <>
            <span className="text-[11px] text-[#d2d2d7]">|</span>
            <span className="text-[11px] text-[#aeaeb2]">
              {inquiry.vacancies}명 모집
            </span>
          </>
        )}
      </div>
    </button>
  )
}
