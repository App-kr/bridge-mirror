import fs from 'fs'
import path from 'path'
import { API_URL } from '@/lib/api'

/**
 * Data access layer -- Render API (primary) + static JSON fallback.
 *
 * On Vercel, the static JSON files in data/ are build-time snapshots and
 * become stale as admins edit content via the Render backend.
 * This module ensures API routes always prefer live DB data.
 */
const DATA_DIR = path.join(process.cwd(), 'data')

/* ── Static JSON fallback (emergency only) ────────────────────────── */

function readJson(filename: string): Record<string, unknown>[] {
  try {
    const filePath = path.join(DATA_DIR, filename)
    if (!fs.existsSync(filePath)) return []
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'))
  } catch {
    return []
  }
}

/**
 * Public jobs fallback -- reads ONLY from ad_only mirror (jobs_clean.json).
 *
 * jobs.json 은 master.db 전체 덤프라 internal_notes 에 PII(한글/메일/전화)가
 * 포함되어 있어 공개 경로에서 쓸 수 없다. 광고 공개 경로는 ad_only 가 유일 소스.
 */
export function getJobs(): Record<string, unknown>[] {
  return readJson('jobs_clean.json')
}

/** Synchronous fallback -- reads from static JSON in data/ directory */
export function getBoardPosts(board: string): Record<string, unknown>[] {
  return readJson(`board-${board}.json`)
}

/* ── Render API proxy (primary) ───────────────────────────────────── */

/**
 * Fetch board posts from Render backend (primary source of truth).
 * Falls back to static JSON if Render is unreachable.
 * @param board - board slug (about, visa, tips, etc.)
 * @param limit - max posts to return
 * @param offset - pagination offset
 * @param category - optional category filter
 */
export async function fetchBoardPostsFromRender(
  board: string,
  limit = 50,
  offset = 0,
  category?: string | null,
): Promise<{ success: boolean; data: { total: number; posts: Record<string, unknown>[] } }> {
  try {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (category) params.set('category', category)
    const res = await fetch(`${API_URL}/api/community/${board}?${params}`, {
      cache: 'no-store',  // 캐시 없음 — 편집 즉시 반영, JSON 폴백이 옛 내용으로 덮지 못하게
    })
    if (res.ok) {
      const json = await res.json()
      // posts.length > 0 체크 제거 — 빈 게시판도 정상 응답으로 반환 (static JSON fallback 방지)
      if (json.success) return json
    }
  } catch { /* Render unreachable -- fall through to static JSON */ }

  // Fallback: static JSON
  const allPosts = getBoardPosts(board)
  let filtered = allPosts
  if (category) filtered = filtered.filter(p => String(p.category ?? '') === category)
  const total = filtered.length
  const paged = filtered.slice(offset, offset + limit)
  const posts = paged.map(r => ({
    id: r.id,
    title: r.title,
    author_hash: r.author_hash,
    pinned: r.pinned,
    views: r.views,
    created_at: r.created_at,
    category: r.category ?? null,
    preview: String(r.body ?? '').slice(0, 300),
    body: category ? String(r.body ?? '') : undefined,
  }))
  return { success: true, data: { total, posts } }
}

/**
 * Fetch a single post from Render backend.
 * Falls back to static JSON if Render is unreachable.
 */
export async function fetchPostFromRender(
  board: string,
  postId: number,
): Promise<{ success: boolean; data?: Record<string, unknown>; message?: string }> {
  try {
    const res = await fetch(`${API_URL}/api/community/${board}/${postId}`, {
      next: { revalidate: 300 },
    })
    if (res.ok) {
      const json = await res.json()
      if (json.success) return json
    }
  } catch { /* Render unreachable */ }

  // Fallback: static JSON
  const posts = getBoardPosts(board)
  const post = posts.find(p => Number(p.id) === postId)
  if (!post) return { success: false, message: 'Post not found' }
  return { success: true, data: post }
}

/**
 * Fetch jobs from Render backend.
 * Falls back to static JSON if Render is unreachable.
 */
export async function fetchJobsFromRender(
  searchParams: URLSearchParams,
): Promise<Response | null> {
  try {
    const res = await fetch(`${API_URL}/api/jobs?${searchParams.toString()}`, {
      next: { revalidate: 1800 },  // 30-minute cache
    })
    if (res.ok) return res
  } catch { /* Render unreachable */ }
  return null
}
