import initSqlJs, { type Database } from 'sql.js'
import path from 'path'
import fs from 'fs'

let _db: Database | null = null

function findDb(): string {
  const candidates = [
    path.join(process.cwd(), 'master.db'),
    path.join(process.cwd(), '..', 'master.db'),
    path.resolve('master.db'),
    path.resolve('..', 'master.db'),
  ]

  for (const p of candidates) {
    try { if (fs.existsSync(p)) return p } catch { /* skip */ }
  }

  throw new Error(`master.db not found. cwd=${process.cwd()}, tried: ${candidates.join(', ')}`)
}

export async function getDb(): Promise<Database> {
  if (_db) return _db

  const dbPath = findDb()
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
    results.push(stmt.getAsObject() as Record<string, unknown>)
  }
  stmt.free()
  return results
}

/** Run SELECT query and return first row */
export async function queryOne(sql: string, params: (string | number | null)[] = []): Promise<Record<string, unknown> | null> {
  const rows = await query(sql, params)
  return rows[0] ?? null
}
