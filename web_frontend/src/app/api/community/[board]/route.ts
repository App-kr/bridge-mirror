import { NextRequest, NextResponse } from 'next/server'
import { fetchBoardPostsFromRender } from '@/lib/db'

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

    // Primary: Render DB, Fallback: static JSON
    const result = await fetchBoardPostsFromRender(board, limit, offset, category)
    return NextResponse.json(result)
  } catch {
    return NextResponse.json({ success: false, message: 'Failed to load posts' }, { status: 500 })
  }
}
