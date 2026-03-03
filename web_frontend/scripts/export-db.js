/**
 * Build-time script: master.db → JSON files for Vercel serverless
 * Run: node scripts/export-db.js
 */
const initSqlJs = require('sql.js')
const fs = require('fs')
const path = require('path')

const DB_CANDIDATES = [
  path.join(__dirname, '..', 'master.db'),
  path.join(__dirname, '..', '..', 'master.db'),
]

const BOARDS = ['about', 'korea', 'visa', 'support', 'support_kr', 'tips', 'testimonials']
const OUT_DIR = path.join(__dirname, '..', 'data')

async function main() {
  let dbPath = ''
  for (const p of DB_CANDIDATES) {
    if (fs.existsSync(p)) { dbPath = p; break }
  }
  if (!dbPath) { console.error('master.db not found'); process.exit(1) }

  const SQL = await initSqlJs()
  const buf = fs.readFileSync(dbPath)
  const db = new SQL.Database(buf)

  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true })

  // ── Export jobs ──
  const jobs = []
  const jobStmt = db.prepare(
    "SELECT * FROM jobs WHERE status = 'open' AND is_deleted = 0 ORDER BY is_hot DESC, created_at DESC"
  )
  while (jobStmt.step()) jobs.push(jobStmt.getAsObject())
  jobStmt.free()
  fs.writeFileSync(path.join(OUT_DIR, 'jobs.json'), JSON.stringify(jobs))
  console.log(`Exported ${jobs.length} jobs`)

  // ── Export community posts (per board) ──
  for (const board of BOARDS) {
    const posts = []
    const stmt = db.prepare(
      `SELECT id, title, body, author_hash, pinned, views, created_at, category
       FROM community_posts WHERE board = ? AND is_deleted = 0
       ORDER BY pinned DESC, created_at DESC`
    )
    stmt.bind([board])
    while (stmt.step()) posts.push(stmt.getAsObject())
    stmt.free()
    fs.writeFileSync(path.join(OUT_DIR, `board-${board}.json`), JSON.stringify(posts))
    console.log(`Exported ${posts.length} posts for ${board}`)
  }

  db.close()
  console.log('Done! Files in', OUT_DIR)
}

main().catch(e => { console.error(e); process.exit(1) })
