import fs from 'fs'
import path from 'path'

const DATA_DIR = path.join(process.cwd(), 'data')

function readJson(filename: string): Record<string, unknown>[] {
  const filePath = path.join(DATA_DIR, filename)
  if (!fs.existsSync(filePath)) return []
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'))
}

export function getJobs(): Record<string, unknown>[] {
  return readJson('jobs.json')
}

export function getBoardPosts(board: string): Record<string, unknown>[] {
  return readJson(`board-${board}.json`)
}
