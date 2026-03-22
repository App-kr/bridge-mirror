import { NextResponse } from 'next/server'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export async function GET() {
  if (!API) {
    return NextResponse.json({ success: true, data: { partners: [] } })
  }
  try {
    const res = await fetch(`${API}/api/partners`, {
      next: { revalidate: 3600 },
    })
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ success: true, data: { partners: [] } })
  }
}
