import { NextRequest, NextResponse } from 'next/server'
import { getBoardPosts } from '@/lib/db'

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

    const posts = getBoardPosts(board)
    const post = posts.find(p => Number(p.id) === postId)

    if (!post) {
      return NextResponse.json({ success: false, message: 'Post not found' }, { status: 404 })
    }

    return NextResponse.json({ success: true, message: 'ok', data: post })
  } catch {
    return NextResponse.json({ success: false, message: 'Failed to load post' }, { status: 500 })
  }
}
