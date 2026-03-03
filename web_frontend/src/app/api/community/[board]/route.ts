import { NextRequest, NextResponse } from 'next/server'
import { getBoardPosts } from '@/lib/db'

const VALID_BOARDS = ['about', 'korea', 'visa', 'support', 'support_kr', 'tips', 'testimonials']

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ board: string }> },
) {
  try {
    const { board } = await params
    if (!VALID_BOARDS.includes(board)) {
      return NextResponse.json({ success: false, message: 'Invalid board' }, { status: 400 })
    }

    const { searchParams } = request.nextUrl
    const limit = Math.min(Number(searchParams.get('limit') ?? 30), 100)
    const offset = Number(searchParams.get('offset') ?? 0)

    const category = searchParams.get('category') ?? null
    let allPosts = getBoardPosts(board)
    if (category) {
      allPosts = allPosts.filter((p) => String(p.category ?? '') === category)
    }
    const total = allPosts.length
    const paged = allPosts.slice(offset, offset + limit)

    const posts = paged.map((r) => ({
      id:          r.id,
      title:       r.title,
      author_hash: r.author_hash,
      pinned:      r.pinned,
      views:       r.views,
      created_at:  r.created_at,
      category:    r.category ?? null,
      preview:     String(r.body ?? '').slice(0, 300),
      body:        category ? String(r.body ?? '') : undefined,
    }))

    return NextResponse.json({ success: true, message: 'ok', data: { total, posts } })
  } catch (e) {
    console.error('API /api/community error:', e)
    return NextResponse.json({ success: false, message: 'Failed to load posts' }, { status: 500 })
  }
}
