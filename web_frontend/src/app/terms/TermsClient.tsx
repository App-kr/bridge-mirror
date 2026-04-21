'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

// ─── 초기 HTML 콘텐츠 (DB 저장값 없을 때 폴백) ─────────────────────────────
const DEFAULT_ARTICLES: Article[] = [
  {
    num: '1',
    key: 'art-1',
    title: 'Service Description',
    content: `<p>BRIDGE provides ESL teacher recruitment and placement services in South Korea. Under Korean employment law, recruitment agencies are permitted to charge fees to job seekers; however, BRIDGE provides its services to foreign teacher candidates entirely free of charge as a courtesy.</p>
<p>In return, we ask that you use our service — and any Korean work visa obtained through it — solely for the purpose of lawful employment. <strong>Abuse of the visa process, misrepresentation of qualifications, or use of a placement to circumvent immigration rules will result in immediate termination of services and may be reported to the relevant authorities.</strong></p>
<p>Placement is not guaranteed. Outcomes depend on your qualifications, availability, employer requirements, and your level of engagement throughout the recruitment process. BRIDGE acts solely as an intermediary — the employment contract is concluded directly between you and the employer following thorough review and dialogue between both parties.</p>`,
  },
  {
    num: '2',
    key: 'art-2',
    title: 'Candidate Guidelines',
    content: `<p>Detailed candidate responsibilities, the step-by-step recruitment process, and our direct contact policy are available on the <a href="/community/support" class="underline text-blue-700 hover:text-blue-900">Support page</a>.</p>`,
  },
  {
    num: '3',
    key: 'art-3',
    title: 'Intellectual Property',
    content: `<p>All content on this website — including employer data, contract information, text, images, logos, and platform design — is the property of BRIDGE Recruitment and may not be reproduced, distributed, or used in any form without prior written consent from BRIDGE.</p>`,
  },
  {
    num: '4',
    key: 'art-4',
    title: 'Prohibited Conduct',
    content: `<ul class="list-disc pl-5 space-y-1">
<li>Attempting to gain unauthorised access to any part of this site or its underlying systems</li>
<li>Using the platform for any unlawful purpose</li>
<li>Submitting false, misleading, or fraudulent information</li>
<li>Circumventing the BRIDGE process to engage directly with any party introduced through our service</li>
<li>Reverse-engineering, scraping, or otherwise reproducing content or data from this platform</li>
</ul>`,
  },
  {
    num: '5',
    key: 'art-5',
    title: 'Amendments',
    content: `<p>BRIDGE reserves the right to amend these Terms at any time. For general updates, the revised Terms will be published on this page with reasonable prior notice. Continued use of our services following the effective date of any amendment constitutes acceptance of the updated Terms.</p>`,
  },
  {
    num: '6',
    key: 'art-6',
    title: 'Governing Law &amp; Dispute Resolution',
    content: `<p>These Terms are governed by the laws of the <strong>Republic of Korea</strong>. Any disputes arising out of or in connection with these Terms or our services shall be subject to the exclusive jurisdiction of the competent courts in the Republic of Korea, in accordance with the location of BRIDGE's registered place of business.</p>`,
  },
]

interface Article {
  num: string
  key: string
  title: string
  content: string
}

type Overrides = Record<string, { content?: string; title?: string }>

export default function TermsClient() {
  const { authed, signedFetch } = useAdminAuth()

  const [editMode, setEditMode] = useState(false)
  const [articles, setArticles] = useState<Article[]>(DEFAULT_ARTICLES)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [draftContent, setDraftContent] = useState('')
  const [draftTitle, setDraftTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 저장된 오버라이드 로드
  useEffect(() => {
    fetch(`${API_URL}/api/page-content/terms`)
      .then(r => r.ok ? r.json() : null)
      .then((json: { success: boolean; data: Overrides } | null) => {
        if (!json?.success) return
        const overrides = json.data
        setArticles(prev =>
          prev.map(a => ({
            ...a,
            title: overrides[a.key]?.title ?? a.title,
            content: overrides[a.key]?.content ?? a.content,
          }))
        )
      })
      .catch(() => {})
  }, [])

  // 편집 시작
  function startEdit(a: Article) {
    setEditingKey(a.key)
    setDraftTitle(a.title)
    setDraftContent(a.content)
    setTimeout(() => textareaRef.current?.focus(), 50)
  }

  // 저장
  async function saveSection(key: string) {
    setSaving(true)
    try {
      const article = articles.find(a => a.key === key)!
      const titleChanged = draftTitle !== article.title
      const contentChanged = draftContent !== article.content

      const saves: Promise<Response>[] = []

      if (titleChanged) {
        saves.push(
          signedFetch(`${API_URL}/api/admin/page-content`, {
            method: 'PATCH',
            body: JSON.stringify({ page: 'terms', section_key: key, field: 'title', value: draftTitle }),
          })
        )
      }
      if (contentChanged) {
        saves.push(
          signedFetch(`${API_URL}/api/admin/page-content`, {
            method: 'PATCH',
            body: JSON.stringify({ page: 'terms', section_key: key, field: 'content', value: draftContent }),
          })
        )
      }

      await Promise.all(saves)

      setArticles(prev =>
        prev.map(a =>
          a.key === key ? { ...a, title: draftTitle, content: draftContent } : a
        )
      )
      setEditingKey(null)
      showToast('저장 완료')
    } catch {
      showToast('저장 실패 — 다시 시도해주세요')
    } finally {
      setSaving(false)
    }
  }

  function showToast(msg: string) {
    setToast(msg)
    setTimeout(() => setToast(null), 2500)
  }

  return (
    <div className="max-w-[860px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">

      {/* Header */}
      <div className="mb-10 pb-6 border-b border-gray-200">
        <span className="inline-block text-[11px] font-semibold text-gray-500 border border-gray-300 rounded px-2 py-0.5 mb-4">Legal</span>
        <h1 className="text-3xl font-bold mb-1">Terms of Use</h1>
        <p className="text-sm text-gray-500">Last updated: May 2026 &nbsp;|&nbsp; Version 3.2</p>
        <p className="mt-3 text-sm text-gray-600 leading-relaxed">
          These Terms of Use (&ldquo;Terms&rdquo;) govern your use of the BRIDGE website at{' '}
          <strong>bridgejob.co.kr</strong> and the recruitment services provided by BRIDGE Agency
          (&ldquo;BRIDGE&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;).
        </p>
      </div>

      <div className="space-y-10 text-sm text-gray-700 leading-7">
        {articles.map(a => (
          <section key={a.key} className="pt-8 border-t border-gray-100 relative group">

            {/* 편집 버튼 (편집 모드 + 현재 편집 중 아닐 때) */}
            {editMode && editingKey !== a.key && (
              <button
                onClick={() => startEdit(a)}
                className="absolute top-8 right-0 text-[11px] px-2 py-0.5 rounded border border-blue-300 text-blue-600 bg-blue-50 hover:bg-blue-100 transition-colors"
              >
                편집
              </button>
            )}

            {/* 제목 */}
            {editMode && editingKey === a.key ? (
              <input
                value={draftTitle}
                onChange={e => setDraftTitle(e.target.value)}
                className="text-base font-bold text-[#1d1d1f] mb-3 border-b border-blue-400 outline-none bg-transparent w-full pr-20"
              />
            ) : (
              <h2 className="text-base font-bold text-[#1d1d1f] mb-3">
                {a.num}. <span dangerouslySetInnerHTML={{ __html: a.title }} />
              </h2>
            )}

            {/* 본문 — 편집 중 */}
            {editMode && editingKey === a.key ? (
              <div className="space-y-2">
                <textarea
                  ref={textareaRef}
                  value={draftContent}
                  onChange={e => setDraftContent(e.target.value)}
                  rows={10}
                  className="w-full text-sm font-mono border border-blue-300 rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-400 resize-y bg-white leading-6"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => saveSection(a.key)}
                    disabled={saving}
                    className="text-xs px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {saving ? '저장 중…' : '저장'}
                  </button>
                  <button
                    onClick={() => setEditingKey(null)}
                    className="text-xs px-3 py-1.5 rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
                  >
                    취소
                  </button>
                </div>
              </div>
            ) : (
              /* 본문 — 일반 표시 */
              <div
                className="space-y-3 text-sm text-gray-700 leading-7"
                dangerouslySetInnerHTML={{ __html: a.content }}
              />
            )}
          </section>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-14 pt-6 border-t border-gray-200 text-xs text-gray-400 space-y-1">
        <p>BRIDGE Recruitment · <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-600">bridgejobkr@gmail.com</a></p>
        <p>
          See also:{' '}
          <Link href="/privacy" className="underline hover:text-gray-600">Privacy Policy</Link>
          {' · '}
          <Link href="/fees" className="underline hover:text-gray-600">Fee Disclosure</Link>
          {' · '}
          <Link href="/contact" className="underline hover:text-gray-600">Contact</Link>
        </p>
      </div>

      {/* 관리자 편집 모드 토글 버튼 */}
      {authed && (
        <button
          onClick={() => {
            setEditMode(v => !v)
            setEditingKey(null)
          }}
          className={`fixed bottom-6 right-6 z-50 text-xs font-semibold px-4 py-2 rounded-full shadow-lg border transition-all ${
            editMode
              ? 'bg-blue-600 text-white border-blue-700 hover:bg-blue-700'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }`}
        >
          {editMode ? '✓ 편집 모드 ON' : '편집 모드'}
        </button>
      )}

      {/* 저장 토스트 */}
      {toast && (
        <div className="fixed bottom-16 right-6 z-50 text-xs bg-gray-900 text-white px-4 py-2 rounded-full shadow-lg animate-fade-in">
          {toast}
        </div>
      )}
    </div>
  )
}
