/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Preferences Manager v2
   ★ DB 우선 저장 — localStorage는 오프라인 캐시 전용
   ★ 서버 재시작·캐시 삭제·다른 기기에서도 설정 유지
   ═══════════════════════════════════════════════════════ */

import type { ColDef } from './types'

interface StoredPrefs {
  cw: Record<string, number>      // column widths
  cl: Record<string, string>      // column labels
  cv: Record<string, boolean>     // column visibility
  fc: number                       // frozen column count
}

const STORAGE_KEY = 'bridge-canvas-v1'

// ── DB API 헬퍼 ────────────────────────────────────────────────────
async function dbSave(key: string, value: unknown, apiUrl: string, adminKey: string): Promise<void> {
  try {
    await fetch(`${apiUrl}/api/admin/sheet/prefs`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
      body: JSON.stringify({ key, value }),
    })
  } catch {
    /* 네트워크 오류 — localStorage 백업으로 충분 */
  }
}

async function dbSaveBulk(prefs: Record<string, unknown>, apiUrl: string, adminKey: string): Promise<void> {
  try {
    await fetch(`${apiUrl}/api/admin/sheet/prefs/bulk`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
      body: JSON.stringify({ prefs }),
    })
  } catch { /* ignore */ }
}

export class PrefsManager {
  private storageKey: string
  private apiUrl: string = ''
  private adminKey: string = ''
  private saveTimer: ReturnType<typeof setTimeout> | null = null

  constructor(storageKey?: string) {
    this.storageKey = storageKey ?? STORAGE_KEY
  }

  /** API 인증 정보 설정 (BridgeCanvasSheet에서 마운트 시 호출) */
  setAuth(apiUrl: string, adminKey: string): void {
    this.apiUrl = apiUrl
    this.adminKey = adminKey
  }

  /** Apply saved prefs to column definitions */
  load(cols: ColDef[]): { cols: ColDef[]; frozenCols: number } {
    try {
      const raw = localStorage.getItem(this.storageKey)
      if (!raw) return { cols, frozenCols: 3 }
      const p = JSON.parse(raw) as StoredPrefs
      const updated = cols.map(c => ({
        ...c,
        w: p.cw?.[c.key] ?? c.w,
        label: p.cl?.[c.key] || c.label,
        v: p.cv?.[c.key] !== undefined ? (p.cv[c.key] ?? true) : true,
      }))
      return { cols: updated, frozenCols: p.fc ?? 3 }
    } catch {
      return { cols, frozenCols: 3 }
    }
  }

  /** DB에서 모든 prefs 로드 후 localStorage에도 캐싱 */
  async loadFromDB(): Promise<{
    cols?: StoredPrefs
    rowHeights?: Record<string, number>
    cellStyles?: Record<string, unknown>
    tabData?: unknown
    edits?: Record<string, Record<string, string>>
  }> {
    if (!this.apiUrl || !this.adminKey) return {}
    try {
      const res = await fetch(`${this.apiUrl}/api/admin/sheet/prefs`, {
        headers: { 'x-admin-key': this.adminKey },
      })
      if (!res.ok) return {}
      const data = await res.json() as Record<string, unknown>

      // localStorage에도 캐싱 (오프라인 대비)
      for (const [k, v] of Object.entries(data)) {
        try { localStorage.setItem(this.storageKey + '-db-' + k, JSON.stringify(v)) } catch { /* ignore */ }
      }

      return {
        cols: data['col_prefs'] as StoredPrefs | undefined,
        rowHeights: data['row_heights'] as Record<string, number> | undefined,
        cellStyles: data['cell_styles'] as Record<string, unknown> | undefined,
        tabData: data['tab_data'],
        edits: data['edits'] as Record<string, Record<string, string>> | undefined,
      }
    } catch {
      // DB 실패 → localStorage 캐시에서 복구
      return this._loadFromLocalCache()
    }
  }

  private _loadFromLocalCache(): {
    cols?: StoredPrefs
    rowHeights?: Record<string, number>
    cellStyles?: Record<string, unknown>
    tabData?: unknown
    edits?: Record<string, Record<string, string>>
  } {
    const parse = (key: string) => {
      try {
        const r = localStorage.getItem(this.storageKey + '-db-' + key)
        return r ? JSON.parse(r) : undefined
      } catch { return undefined }
    }
    return {
      cols: parse('col_prefs'),
      rowHeights: parse('row_heights'),
      cellStyles: parse('cell_styles'),
      tabData: parse('tab_data'),
      edits: parse('edits'),
    }
  }

  /** Save current prefs — DB 우선, localStorage 동시 저장 */
  save(cols: ColDef[], frozenCols: number): void {
    const cw: Record<string, number> = {}
    const cl: Record<string, string> = {}
    const cv: Record<string, boolean> = {}
    for (const c of cols) {
      cw[c.key] = c.w
      cl[c.key] = c.label
      cv[c.key] = c.v !== false
    }
    const prefs: StoredPrefs = { cw, cl, cv, fc: frozenCols }

    // localStorage 즉시 저장 (동기)
    try { localStorage.setItem(this.storageKey, JSON.stringify(prefs)) } catch { /* ignore */ }
    try { localStorage.setItem(this.storageKey + '-db-col_prefs', JSON.stringify(prefs)) } catch { /* ignore */ }

    // DB 저장 (디바운스 500ms)
    if (this.saveTimer) clearTimeout(this.saveTimer)
    this.saveTimer = setTimeout(() => {
      dbSave('col_prefs', prefs, this.apiUrl, this.adminKey)
    }, 500)
  }

  /** Save edits overlay — DB + localStorage */
  saveEdits(edits: Record<string, Record<string, string>>): void {
    try { localStorage.setItem(this.storageKey + '-edits', JSON.stringify(edits)) } catch { /* ignore */ }
    try { localStorage.setItem(this.storageKey + '-db-edits', JSON.stringify(edits)) } catch { /* ignore */ }
    dbSave('edits', edits, this.apiUrl, this.adminKey)
  }

  loadEdits(): Record<string, Record<string, string>> {
    try {
      return JSON.parse(localStorage.getItem(this.storageKey + '-edits') || '{}') as Record<string, Record<string, string>>
    } catch { return {} }
  }

  /** Save manual tab data — DB + localStorage */
  saveTabData(data: unknown): void {
    try { localStorage.setItem(this.storageKey + '-data', JSON.stringify(data)) } catch { /* ignore */ }
    try { localStorage.setItem(this.storageKey + '-db-tab_data', JSON.stringify(data)) } catch { /* ignore */ }
    dbSave('tab_data', data, this.apiUrl, this.adminKey)
  }

  loadTabData<T>(): T | null {
    try {
      const raw = localStorage.getItem(this.storageKey + '-data')
      if (!raw) return null
      return JSON.parse(raw) as T
    } catch { return null }
  }

  /** Save per-row heights — DB + localStorage */
  saveRowHeights(heights: Record<string, number>): void {
    try { localStorage.setItem(this.storageKey + '-rowheights', JSON.stringify(heights)) } catch { /* ignore */ }
    try { localStorage.setItem(this.storageKey + '-db-row_heights', JSON.stringify(heights)) } catch { /* ignore */ }

    // 디바운스 1초 (행 높이는 드래그 중 연속 호출)
    if ((this as unknown as Record<string, unknown>)['_rhTimer']) {
      clearTimeout((this as unknown as Record<string, unknown>)['_rhTimer'] as ReturnType<typeof setTimeout>)
    }
    ;(this as unknown as Record<string, unknown>)['_rhTimer'] = setTimeout(() => {
      dbSave('row_heights', heights, this.apiUrl, this.adminKey)
    }, 1000)
  }

  loadRowHeights(): Record<string, number> {
    try {
      return JSON.parse(localStorage.getItem(this.storageKey + '-rowheights') || '{}') as Record<string, number>
    } catch { return {} }
  }
}
