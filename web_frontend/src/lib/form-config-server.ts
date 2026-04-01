/**
 * form-config-server.ts — Server-side ONLY (절대 'use client' 파일에 import 금지)
 *
 * Vercel 서버 컴포넌트에서 Render 내부 엔드포인트를 호출해 폼 옵션을 로드.
 * FORM_CONFIG_READ_KEY 환경변수 (NEXT_PUBLIC_ 아님 → 브라우저 절대 미노출).
 * 키 미설정 또는 API 오류 시 빈 객체 반환 → 폼은 하드코딩 기본값 사용 (무중단).
 */
export type FormConfig = Record<string, string[]>

export async function getFormConfig(formName: 'apply' | 'inquiry'): Promise<FormConfig> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  const svcKey = process.env.FORM_CONFIG_READ_KEY   // server-side only env var
  if (!apiUrl || !svcKey) return {}
  try {
    const res = await fetch(`${apiUrl}/api/internal/form-config/${formName}`, {
      headers: { 'x-service-key': svcKey },
      next: { revalidate: 300 },   // 5분 캐시 — 관리자 수정 후 최대 5분 내 반영
    })
    if (!res.ok) return {}
    const json: { success: boolean; data: FormConfig } = await res.json()
    return json?.data ?? {}
  } catch {
    return {}
  }
}
