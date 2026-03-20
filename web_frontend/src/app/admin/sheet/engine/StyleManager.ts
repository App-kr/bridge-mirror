/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Style Manager
   Manages per-cell formatting (font, color, bg) with localStorage persistence
   ═══════════════════════════════════════════════════════ */

import type { CellStyle } from './types'

const STORAGE_KEY = 'bridge-sheet-styles'

export class StyleManager {
  private styles = new Map<string, CellStyle>()
  private _getAllIds: (() => string[]) | null = null

  constructor() {
    this.load()
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
    this.persist()
  }

  /** Batch set — only persists once at the end (for bulk operations) */
  batchSet(entries: Array<{ cid: string; colKey: string }>, style: CellStyle): void {
    for (const { cid, colKey } of entries) {
      const k = this.key(cid, colKey)
      const existing = this.styles.get(k) || {}
      this.styles.set(k, { ...existing, ...style })
    }
    this.persist()
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
    this.persist()
  }

  private persist(): void {
    try {
      const obj: Record<string, CellStyle> = {}
      this.styles.forEach((v, k) => { obj[k] = v })
      localStorage.setItem(STORAGE_KEY, JSON.stringify(obj))
    } catch { /* ignore */ }
  }

  private load(): void {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const obj = JSON.parse(raw) as Record<string, CellStyle>
      for (const [k, v] of Object.entries(obj)) {
        this.styles.set(k, v)
      }
    } catch { /* ignore */ }
  }
}
