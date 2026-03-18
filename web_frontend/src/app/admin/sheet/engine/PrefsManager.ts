/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Preferences Manager
   Persist column widths, visibility, labels to localStorage
   ═══════════════════════════════════════════════════════ */

import type { ColDef } from './types'

interface StoredPrefs {
  cw: Record<string, number>      // column widths
  cl: Record<string, string>      // column labels
  cv: Record<string, boolean>     // column visibility
  fc: number                       // frozen column count
}

const STORAGE_KEY = 'bridge-canvas-v1'

export class PrefsManager {
  private storageKey: string

  constructor(storageKey?: string) {
    this.storageKey = storageKey ?? STORAGE_KEY
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

  /** Save current prefs */
  save(cols: ColDef[], frozenCols: number): void {
    try {
      const cw: Record<string, number> = {}
      const cl: Record<string, string> = {}
      const cv: Record<string, boolean> = {}
      for (const c of cols) {
        cw[c.key] = c.w
        cl[c.key] = c.label
        cv[c.key] = c.v !== false
      }
      localStorage.setItem(this.storageKey, JSON.stringify({ cw, cl, cv, fc: frozenCols } as StoredPrefs))
    } catch { /* quota exceeded or private mode */ }
  }

  /** Save edits overlay (stage, mailStatus, etc.) */
  saveEdits(edits: Record<string, Record<string, string>>): void {
    try {
      localStorage.setItem(this.storageKey + '-edits', JSON.stringify(edits))
    } catch { /* ignore */ }
  }

  loadEdits(): Record<string, Record<string, string>> {
    try {
      return JSON.parse(localStorage.getItem(this.storageKey + '-edits') || '{}') as Record<string, Record<string, string>>
    } catch { return {} }
  }

  /** Save manual tab data (active/past/blacklist) */
  saveTabData(data: unknown): void {
    try {
      localStorage.setItem(this.storageKey + '-data', JSON.stringify(data))
    } catch { /* ignore */ }
  }

  loadTabData<T>(): T | null {
    try {
      const raw = localStorage.getItem(this.storageKey + '-data')
      if (!raw) return null
      return JSON.parse(raw) as T
    } catch { return null }
  }
}
