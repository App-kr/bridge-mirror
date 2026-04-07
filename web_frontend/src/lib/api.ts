/**
 * API 설정 — 환경변수 NEXT_PUBLIC_API_URL 기반.
 * 미설정 시 Render 기본 URL로 폴백 (빈 문자열 절대 안 됨).
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://bridge-n7hk.onrender.com'
