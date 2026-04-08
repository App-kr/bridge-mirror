/**
 * API 설정 — 환경변수 NEXT_PUBLIC_API_URL 기반.
 * 미설정 시 Render 기본 URL로 폴백 (빈 문자열 절대 안 됨).
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://bridge-n7hk.onrender.com'

/**
 * fetchWithRetry — Render cold start(30~60초) 대응 fetch 래퍼.
 * 500+ 에러 또는 네트워크 오류 시 maxRetries 횟수만큼 재시도.
 * 기존 fetch 호출을 교체할 때 사용 (옵트인).
 */
export async function fetchWithRetry(
  url: string,
  options?: RequestInit,
  maxRetries = 3,
): Promise<Response> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await fetch(url, { ...options, signal: AbortSignal.timeout(15000) })
      if (res.ok || res.status < 500) return res
    } catch (e) {
      if (i === maxRetries - 1) throw e
    }
    await new Promise(r => setTimeout(r, 2000 * (i + 1))) // 2s, 4s, 6s
  }
  throw new Error(`fetchWithRetry: ${maxRetries}회 실패 — ${url}`)
}
