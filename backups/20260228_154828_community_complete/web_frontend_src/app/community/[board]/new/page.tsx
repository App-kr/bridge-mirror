'use client'

import { useParams } from 'next/navigation'
import NewPostForm from '@/components/NewPostForm'
import { getBoardConfig } from '@/lib/boards'
import Link from 'next/link'

export default function NewBoardPost() {
  const { board } = useParams<{ board: string }>()
  const config = getBoardConfig(board)

  if (!config) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center text-gray-500">
        <p>Board not found.</p>
        <Link href="/community" className="text-blue-600 mt-2 block">← Back to Community</Link>
      </div>
    )
  }

  return (
    <NewPostForm
      board={board}
      boardLabel={`${config.emoji} ${config.label}`}
      accentClass={config.accentColor}
    />
  )
}
