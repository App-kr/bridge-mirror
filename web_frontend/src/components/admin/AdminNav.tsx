'use client'

const NAV_ITEMS = [
  { href: '/admin',              label: 'Dashboard',    icon: '📊' },
  { href: '/admin/inbox',        label: 'Inbox',        icon: '📧' },
  { href: '/admin/jobs',          label: 'Jobs',         icon: '💼' },
  { href: '/admin/candidates',   label: 'Candidates',   icon: '👥' },
  { href: '/admin/inquiries',    label: 'Inquiries',    icon: '📩' },
  { href: '/admin/applications', label: 'Applications', icon: '📋' },
  { href: '/admin/interviews',   label: 'Interviews',   icon: '🎥' },
  { href: '/admin/posts',        label: 'Posts',        icon: '📝' },
  { href: '/admin/boards',       label: 'Boards',      icon: '📋' },
  { href: '/admin/banners',      label: 'Banners',     icon: '🖼️' },
  { href: '/admin/ad-posts',     label: 'Ad Posts',     icon: '📢' },
  { href: '/admin/payments',     label: 'Payments',     icon: '💳' },
  { href: '/admin/email-templates', label: 'Templates', icon: '✉️' },
  { href: '/admin/guide-links',    label: 'Links',     icon: '🔗' },
]

interface AdminNavProps {
  active: string
}

export default function AdminNav({ active }: AdminNavProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-13 gap-3 mb-6">
      {NAV_ITEMS.map((nav) => (
        <a
          key={nav.href}
          href={nav.href}
          className={`card !p-3 text-center text-sm font-medium transition-all
            ${nav.href === active
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'hover:border-blue-300 text-gray-600 hover:text-blue-600'}`}
        >
          <span className="text-lg block mb-1">{nav.icon}</span>
          {nav.label}
        </a>
      ))}
    </div>
  )
}
