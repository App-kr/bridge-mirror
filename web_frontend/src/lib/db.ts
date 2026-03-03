import path from 'path'
import fs from 'fs'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _db: any = null

export async function getDb() {
  if (_db) return _db

  const dbPath = path.join(process.cwd(), 'master.db')
  if (!fs.existsSync(dbPath)) {
    throw new Error(`master.db not found at ${dbPath}`)
  }

  // Dynamic require to avoid Next.js module system conflicts
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const initSqlJs = require('sql.js')
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
