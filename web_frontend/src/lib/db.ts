import Database from 'better-sqlite3'
import path from 'path'
import fs from 'fs'

let _db: Database.Database | null = null

export function getDb(): Database.Database {
  if (_db) return _db

  // Try multiple paths for local dev and Vercel
  const candidates = [
    path.resolve(process.cwd(), 'master.db'),           // repo root is cwd
    path.resolve(process.cwd(), '..', 'master.db'),     // web_frontend is cwd
    path.resolve(__dirname, '..', '..', '..', '..', 'master.db'),
  ]

  let dbPath = ''
  for (const p of candidates) {
    if (fs.existsSync(p)) { dbPath = p; break }
  }

  if (!dbPath) {
    throw new Error(`master.db not found. Tried: ${candidates.join(', ')}`)
  }

  _db = new Database(dbPath, { readonly: true })
  _db.pragma('busy_timeout = 5000')
  return _db
}
