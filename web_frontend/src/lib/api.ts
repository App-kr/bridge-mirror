/**
 * API 설정 — 중앙 집중.
 * Vercel에서는 NEXT_PUBLIC_API_URL 환경변수로 연결.
 * 로컬 개발에서는 fallback으로 localhost:8000 사용.
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
