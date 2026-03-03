import { NextRequest, NextResponse } from 'next/server'
import { queryOne } from '@/lib/db'

const VALID_BOARDS = ['about', 'korea', 'visa', 'support', 'support_kr', 'tips', 'testimonials']

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ board: string; id: string }> },
) {
  try {
    const { board, id } = await params
    if (!VALID_BOARDS.includes(board)) {
      return NextResponse.json({ success: false, message: 'Invalid board' }, { status: 400 })
    }

    const postId = parseInt(id, 10)
    if (isNaN(postId)) {
      return NextResponse.json({ success: false, message: 'Invalid post ID' }, { status: 400 })
    }

    const row = await queryOne(
      `SELECT id, board, title, body, author_hash, pinned, views, created_at, updated_at, image_paths
       FROM community_posts
       WHERE id = ? AND board = ? AND is_deleted = 0`,
      [postId, board],
    )

    if (!row) {
      return NextResponse.json({ success: false, message: 'Post not found' }, { status: 404 })
    }

    return NextResponse.json({ success: true, message: 'ok', data: row })
  } catch (e) {
    console.error('API /api/community/[board]/[id] error:', e)
    return NextResponse.json({ success: false, message: 'Failed to load post' }, { status: 500 })
  }
}
