import { NextRequest, NextResponse } from 'next/server'
import { getDb } from '@/lib/db'

const VALID_BOARDS = ['about', 'korea', 'visa', 'support', 'support_kr', 'tips', 'testimonials']

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ board: string }> },
) {
  try {
    const { board } = await params
    if (!VALID_BOARDS.includes(board)) {
      return NextResponse.json(
        { success: false, message: 'Invalid board' },
        { status: 400 },
      )
    }

    const { searchParams } = request.nextUrl
    const limit = Math.min(Number(searchParams.get('limit') ?? 30), 100)
    const offset = Number(searchParams.get('offset') ?? 0)

    const db = getDb()

    const countRow = db.prepare(
      'SELECT COUNT(*) as cnt FROM community_posts WHERE board = ? AND is_deleted = 0',
    ).get(board) as { cnt: number }
    const total = countRow?.cnt ?? 0

    const rows = db.prepare(
      `SELECT id, title, body, author_hash, pinned, views, created_at
       FROM community_posts
       WHERE board = ? AND is_deleted = 0
       ORDER BY pinned DESC, created_at DESC
       LIMIT ? OFFSET ?`,
    ).all(board, limit, offset) as Record<string, unknown>[]

    const posts = rows.map((r) => ({
      id:          r.id,
      title:       r.title,
      author_hash: r.author_hash,
      pinned:      r.pinned,
      views:       r.views,
      created_at:  r.created_at,
      preview:     ((r.body as string) ?? '').slice(0, 300),
    }))

    return NextResponse.json({ success: true, message: 'ok', data: { total, posts } })
  } catch (e) {
    console.error('API /api/community error:', e)
    return NextResponse.json(
      { success: false, message: 'Failed to load posts' },
      { status: 500 },
    )
  }
}
