import initSqlJs, { type Database } from 'sql.js'
import path from 'path'
import fs from 'fs'

let _db: Database | null = null

export async function getDb(): Promise<Database> {
  if (_db) return _db

  const candidates = [
    path.resolve(process.cwd(), 'master.db'),
    path.resolve(process.cwd(), '..', 'master.db'),
  ]

  let dbPath = ''
  for (const p of candidates) {
    if (fs.existsSync(p)) { dbPath = p; break }
  }

  if (!dbPath) {
    throw new Error(`master.db not found. Tried: ${candidates.join(', ')}`)
  }

  const SQL = await initSqlJs()
  const buffer = fs.readFileSync(dbPath)
  _db = new SQL.Database(buffer)
  return _db
}

/** Run SELECT query and return rows as objects */
export async function query(sql: string, params: (string | number | null)[] = []): Promise<Record<string, unknown>[]> {
  const db = await getDb()
  const stmt = db.prepare(sql)
  if (params.length > 0) stmt.bind(params)

  const results: Record<string, unknown>[] = []
  while (stmt.step()) {
    const row = stmt.getAsObject()
    results.push(row as Record<string, unknown>)
  }
  stmt.free()
  return results
}

/** Run SELECT query and return first row */
export async function queryOne(sql: string, params: (string | number | null)[] = []): Promise<Record<string, unknown> | null> {
  const rows = await query(sql, params)
  return rows[0] ?? null
}
