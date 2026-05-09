/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Style Manager v2
   ★ DB 우선 저장 — localStorage는 오프라인 캐시 전용
   ★ 셀 색상·굵기·기울임 설정이 서버 재시작 후에도 유지
   ═══════════════════════════════════════════════════════ */

import type { CellStyle } from './types'

const STORAGE_KEY = 'bridge-sheet-styles'
const DB_CACHE_KEY = 'bridge-sheet-styles-db'

export class StyleManager {
  private styles = new Map<string, CellStyle>()
  private _getAllIds: (() => string[]) | null = null
  private apiUrl: string = ''
  private adminKey: string = ''
  private _saveTimer: ReturnType<typeof setTimeout> | null = null

  constructor() {
    this._loadFromLocalStorage()
  }

  setAuth(apiUrl: string, adminKey: string): void {
    this.apiUrl = apiUrl
    this.adminKey = adminKey
  }

  setGetAllIds(fn: () => string[]): void {
    this._getAllIds = fn
  }

  getAllIds(): string[] {
    return this._getAllIds ? this._getAllIds() : []
  }

  private key(cid: string, colKey: string): string {
    return `${cid}:${colKey}`
  }

  getStyle(cid: string, colKey: string): CellStyle | undefined {
    return this.styles.get(this.key(cid, colKey))
  }

  setStyle(cid: string, colKey: string, style: CellStyle): void {
    const k = this.key(cid, colKey)
    const existing = this.styles.get(k) || {}
    this.styles.set(k, { ...existing, ...style })
    this._persist()
  }

  /** Batch set — only persists once at the end */
  batchSet(entries: Array<{ cid: string; colKey: string }>, style: CellStyle): void {
    for (const { cid, colKey } of entries) {
      const k = this.key(cid, colKey)
      const existing = this.styles.get(k) || {}
      this.styles.set(k, { ...existing, ...style })
    }
    this._persist()
  }

  applyToSelection(cids: string[], colKeys: string[], style: CellStyle): void {
    const entries: Array<{ cid: string; colKey: string }> = []
    for (const cid of cids) {
      for (const colKey of colKeys) {
        entries.push({ cid, colKey })
      }
    }
    this.batchSet(entries, style)
  }

  clearStyle(cid: string, colKey: string): void {
    this.styles.delete(this.key(cid, colKey))
    this._persist()
  }

  /** DB에서 스타일 로드 (마운트 시 한 번 호출) */
  async loadFromDB(dbStyles?: Record<string, unknown>): Promise<void> {
    if (dbStyles && typeof dbStyles === 'object') {
      // PrefsManager가 이미 DB에서 가져온 데이터 재사용
      this._applyObj(dbStyles as Record<string, CellStyle>)
    } else if (this.apiUrl && this.adminKey) {
      try {
        const res = await fetch(`${this.apiUrl}/api/admin/sheet/prefs`, {
          headers: { 'x-admin-key': this.adminKey },
        })
        if (res.ok) {
          const data = await res.json() as Record<string, unknown>
          if (data['cell_styles']) {
            this._applyObj(data['cell_styles'] as Record<string, CellStyle>)
          }
        }
      } catch { /* localStorage 캐시 사용 */ }
    }

    // DB 값이 없으면 localStorage 캐시에서 복구
    if (this.styles.size === 0) {
      this._loadFromLocalStorage()
    }
  }

  private _applyObj(obj: Record<string, CellStyle>): void {
    this.styles.clear()
    for (const [k, v] of Object.entries(obj)) {
      this.styles.set(k, v)
    }
    // localStorage도 갱신
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(obj)) } catch { /* ignore */ }
    try { localStorage.setItem(DB_CACHE_KEY, JSON.stringify(obj)) } catch { /* ignore */ }
  }

  private _persist(): void {
    const obj: Record<string, CellStyle> = {}
    this.styles.forEach((v, k) => { obj[k] = v })

    // localStorage 즉시 저장
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(obj)) } catch { /* ignore */ }
    try { localStorage.setItem(DB_CACHE_KEY, JSON.stringify(obj)) } catch { /* ignore */ }

    // DB 저장 — 디바운스 800ms (셀 연속 클릭 대비)
    if (this._saveTimer) clearTimeout(this._saveTimer)
    this._saveTimer = setTimeout(() => {
      this._saveToDb(obj)
    }, 800)
  }

  private async _saveToDb(obj: Record<string, CellStyle>): Promise<void> {
    if (!this.apiUrl || !this.adminKey) return
    try {
      await fetch(`${this.apiUrl}/api/admin/sheet/prefs`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': this.adminKey },
        body: JSON.stringify({ key: 'cell_styles', value: obj }),
      })
    } catch { /* 네트워크 오류 — localStorage 백업 유지 */ }
  }

  private _loadFromLocalStorage(): void {
    // DB 캐시 우선, 없으면 원래 localStorage
    const sources = [DB_CACHE_KEY, STORAGE_KEY]
    for (const src of sources) {
      try {
        const raw = localStorage.getItem(src)
        if (!raw) continue
        const obj = JSON.parse(raw) as Record<string, CellStyle>
        for (const [k, v] of Object.entries(obj)) {
          this.styles.set(k, v)
        }
        if (this.styles.size > 0) break
      } catch { /* ignore */ }
    }
  }
}
