'use client'

import dynamic from 'next/dynamic'

// 전체 페이지를 완전히 클라이언트 전용으로 (hydration #418 완전 차단)
// 프리렌더 완전 제거 — 정적 생성 금지
export const dynamicParams = true

const AdminSheetClient = dynamic(
  () => import('./AdminSheetClient'),
  { ssr: false, loading: () => null }
)

export default function AdminSheetPage() {
  return <AdminSheetClient />
}
