/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Grid Engine v2
   Pure Canvas rendering: header, rows, photos, stages, tags
   Ghost-div scrollbar (상하좌우), column resize, DPR scaling
   Configurable row height, updateCallbacks support
   ═══════════════════════════════════════════════════════ */

import type { ColDef, DataRow, GridCallbacks, CellRef } from './types'
import { HEADER_H, FONT, HEADER_FONT, STAGES, MTAGS } from './types'
import { SelectionManager } from './SelectionManager'
import { EditManager } from './EditManager'

/* ── Drawing constants ── */
const HEADER_BG    = '#f8fafc'
const HEADER_BORDER = '#cbd5e1'
const GRID_LINE    = '#e2e8f0'
const SELECTED_BG  = '#dbeafe'
const ACTIVE_BORDER = '#3b82f6'
const HOVER_BG     = '#f1f5f9'
const FROZEN_SEP   = '#94a3b8'
const SORT_ARROW   = '#64748b'
const RESIZE_ZONE  = 5

export class GridEngine {
  /* ── DOM ── */
  private container: HTMLDivElement
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D
  private headerHit: HTMLDivElement
  private ghost: HTMLDivElement
  private sizer: HTMLDivElement

  /* ── External ── */
  private cb: GridCallbacks
  selection: SelectionManager
  editor: EditManager

  /* ── Viewport ── */
  private dpr = 1
  private viewW = 0
  private viewH = 0

  /* ── Scroll ── */
  private scrollTop = 0
  private scrollLeft = 0

  /* ── Data ── */
  private cols: ColDef[] = []
  private visCols: ColDef[] = []
  private rows: DataRow[] = []
  private frozenCols = 3
  private rowH = 36  // configurable row height

  /* ── Interaction ── */
  private hoverRow = -1
  private sortKey = ''
  private sortDir: 'asc' | 'desc' = 'asc'
  private resizeDrag: { visIdx: number; startX: number; startW: number } | null = null

  /* ── Photo cache ── */
  private photoCache = new Map<string, HTMLImageElement>()
  private photoLoading = new Set<string>()

  /* ── RAF ── */
  private rafId = 0
  private destroyed = false
  private ro: ResizeObserver
  private getHeaders: (() => Record<string, string>) | null = null

  constructor(container: HTMLDivElement, cb: GridCallbacks) {
    this.container = container
    this.cb = cb
    this.dpr = window.devicePixelRatio || 1
    this.selection = new SelectionManager()
    this.editor = new EditManager(container)

    container.style.position = 'relative'
    container.style.overflow = 'hidden'

    // Canvas
    this.canvas = document.createElement('canvas')
    this.canvas.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;'
    this.ctx = this.canvas.getContext('2d')!
    container.appendChild(this.canvas)

    // Header hit area
    this.headerHit = document.createElement('div')
    this.headerHit.style.cssText = `position:absolute;top:0;left:0;right:0;height:${HEADER_H}px;z-index:2;cursor:default;`
    container.appendChild(this.headerHit)

    // Ghost scroll div — top: HEADER_H so scrollbar doesn't overlap header
    this.ghost = document.createElement('div')
    this.ghost.style.cssText = `position:absolute;top:${HEADER_H}px;left:0;right:0;bottom:0;overflow:auto;z-index:1;`
    this.sizer = document.createElement('div')
    this.sizer.style.cssText = 'pointer-events:none;'
    this.ghost.appendChild(this.sizer)
    container.appendChild(this.ghost)

    this.ro = new ResizeObserver(() => { if (!this.destroyed) this.handleResize() })
    this.ro.observe(container)
    this.setupEvents()
    this.handleResize()
  }

  /* ══════════════════════════════════════════════
     PUBLIC API
     ══════════════════════════════════════════════ */

  updateCallbacks(cb: GridCallbacks): void { this.cb = cb }

  setData(rows: DataRow[]): void {
    this.rows = rows
    this.updateSizer()
    this.requestRender()
  }

  setCols(cols: ColDef[]): void {
    this.cols = cols
    this.visCols = cols.filter(c => c.v !== false)
    this.updateSizer()
    this.requestRender()
  }

  setFrozenCols(n: number): void { this.frozenCols = n; this.requestRender() }

  setSort(key: string, dir: 'asc' | 'desc'): void {
    this.sortKey = key; this.sortDir = dir; this.requestRender()
  }

  setRowHeight(h: number): void {
    this.rowH = h
    this.updateSizer()
    this.requestRender()
  }

  setHeaderGetter(fn: () => Record<string, string>): void { this.getHeaders = fn }

  getVisibleCols(): ColDef[] { return this.visCols }

  scrollToRow(idx: number): void { this.ghost.scrollTop = idx * this.rowH }

  refresh(): void { this.requestRender() }

  destroy(): void {
    this.destroyed = true
    this.ro.disconnect()
    if (this.rafId) cancelAnimationFrame(this.rafId)
    this.editor.destroy()
    // Remove document-level listeners
    document.removeEventListener('mousemove', this.onDocMouseMove)
    document.removeEventListener('mouseup', this.onDocMouseUp)
    document.removeEventListener('keydown', this.onKeyDown)
    this.canvas.remove()
    this.headerHit.remove()
    this.ghost.remove()
  }

  /* ══════════════════════════════════════════════
     LAYOUT
     ══════════════════════════════════════════════ */

  private handleResize(): void {
    const r = this.container.getBoundingClientRect()
    this.viewW = r.width
    this.viewH = r.height
    this.canvas.width = this.viewW * this.dpr
    this.canvas.height = this.viewH * this.dpr
    this.canvas.style.width = this.viewW + 'px'
    this.canvas.style.height = this.viewH + 'px'
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0)
    this.updateSizer()
    this.requestRender()
  }

  private updateSizer(): void {
    const totalW = this.visCols.reduce((s, c) => s + c.w, 0)
    const totalH = this.rows.length * this.rowH
    this.sizer.style.width = totalW + 'px'
    this.sizer.style.height = totalH + 'px'
  }

  private getFrozenWidth(): number {
    let w = 0
    const n = Math.min(this.frozenCols, this.visCols.length)
    for (let i = 0; i < n; i++) w += this.visCols[i].w
    return w
  }

  private colX(visIdx: number): number {
    let x = 0
    for (let i = 0; i < visIdx; i++) x += this.visCols[i].w
    return x
  }

  /* ══════════════════════════════════════════════
     EVENTS
     ══════════════════════════════════════════════ */

  private setupEvents(): void {
    this.ghost.addEventListener('scroll', this.onScroll, { passive: true })
    this.ghost.addEventListener('mousedown', this.onGhostMouseDown)
    this.ghost.addEventListener('mousemove', this.onGhostMouseMove)
    this.ghost.addEventListener('dblclick', this.onGhostDblClick)
    this.ghost.addEventListener('contextmenu', this.onGhostContextMenu)
    this.headerHit.addEventListener('mousedown', this.onHeaderMouseDown)
    this.headerHit.addEventListener('mousemove', this.onHeaderMouseMove)
    this.headerHit.addEventListener('click', this.onHeaderClick)
    document.addEventListener('mousemove', this.onDocMouseMove)
    document.addEventListener('mouseup', this.onDocMouseUp)
    document.addEventListener('keydown', this.onKeyDown)
  }

  private onScroll = (): void => {
    this.scrollTop = this.ghost.scrollTop
    this.scrollLeft = this.ghost.scrollLeft
    this.requestRender()
    if (this.ghost.scrollTop + this.ghost.clientHeight > this.ghost.scrollHeight - 300) {
      this.cb.onRequestMore()
    }
  }

  private hitCell(e: MouseEvent): { row: number; visCol: number } | null {
    const rect = this.ghost.getBoundingClientRect()
    const mx = e.clientX - rect.left + this.scrollLeft
    const my = e.clientY - rect.top + this.scrollTop
    const row = Math.floor(my / this.rowH)
    if (row < 0 || row >= this.rows.length) return null
    let cx = 0
    for (let i = 0; i < this.visCols.length; i++) {
      if (mx >= cx && mx < cx + this.visCols[i].w) return { row, visCol: i }
      cx += this.visCols[i].w
    }
    return null
  }

  private onGhostMouseDown = (e: MouseEvent): void => {
    if (this.editor.isEditing()) return
    const hit = this.hitCell(e)
    if (!hit) return
    this.selection.selectRow(hit.row, e.ctrlKey || e.metaKey, e.shiftKey)
    this.selection.selectCell(hit.row, hit.visCol)
    this.cb.onSelectionChange(this.selection.getSelectedRows())
    this.requestRender()
  }

  private onGhostMouseMove = (e: MouseEvent): void => {
    const hit = this.hitCell(e)
    const newHover = hit ? hit.row : -1
    if (newHover !== this.hoverRow) { this.hoverRow = newHover; this.requestRender() }
  }

  private onGhostDblClick = (e: MouseEvent): void => {
    const hit = this.hitCell(e)
    if (!hit) return
    const col = this.visCols[hit.visCol]
    const row = this.rows[hit.row]
    if (!col || !row) return

    if (col.type === 'idx' || col.type === 'photo') return
    if (col.type === 'mail') { this.cb.onMailClick(hit.row, row); return }
    if (col.type === 'stage') {
      const stKeys = STAGES.map(s => s.key)
      const cur = stKeys.indexOf(String(row.stage))
      this.cb.onStageChange(hit.row, stKeys[(cur + 1) % stKeys.length])
      return
    }

    const cellRect = this.getCellRect(hit.row, hit.visCol)
    if (!cellRect) return
    const val = String(row[col.key] ?? '')
    this.editor.startEdit(cellRect, col.type, val, col.opts).then(result => {
      if (result.committed && result.value !== val) {
        this.cb.onCellChange(hit.row, col.key, result.value)
      }
      this.requestRender()
    })
  }

  private onGhostContextMenu = (e: MouseEvent): void => {
    e.preventDefault()
    const hit = this.hitCell(e)
    if (!hit) return
    const row = this.rows[hit.row]
    if (!row) return
    if (!this.selection.isRowSelected(hit.row)) {
      this.selection.selectRow(hit.row, false, false)
      this.selection.selectCell(hit.row, hit.visCol)
      this.cb.onSelectionChange(this.selection.getSelectedRows())
    }
    this.cb.onContextMenu(e, hit.row, row)
    this.requestRender()
  }

  private getCellRect(rowIdx: number, visColIdx: number): { x: number; y: number; w: number; h: number } | null {
    const col = this.visCols[visColIdx]
    if (!col) return null
    const isFrozen = visColIdx < this.frozenCols
    const cx = this.colX(visColIdx)
    const x = isFrozen ? cx : cx - this.scrollLeft
    const y = HEADER_H + rowIdx * this.rowH - this.scrollTop
    return { x, y, w: col.w, h: this.rowH }
  }

  /* ── Header events ── */
  private headerHitVisCol(e: MouseEvent): { visCol: number; nearBorder: boolean } | null {
    const rect = this.headerHit.getBoundingClientRect()
    const mx = e.clientX - rect.left + this.scrollLeft
    let cx = 0
    for (let i = 0; i < this.visCols.length; i++) {
      cx += this.visCols[i].w
      if (Math.abs(mx - cx) <= RESIZE_ZONE) return { visCol: i, nearBorder: true }
      if (mx < cx) return { visCol: i, nearBorder: false }
    }
    return null
  }

  private onHeaderMouseDown = (e: MouseEvent): void => {
    const hit = this.headerHitVisCol(e)
    if (!hit || !hit.nearBorder) return
    e.preventDefault()
    this.resizeDrag = { visIdx: hit.visCol, startX: e.clientX, startW: this.visCols[hit.visCol].w }
  }

  private onHeaderMouseMove = (e: MouseEvent): void => {
    const hit = this.headerHitVisCol(e)
    this.headerHit.style.cursor = hit?.nearBorder ? 'col-resize' : 'default'
  }

  private onHeaderClick = (e: MouseEvent): void => {
    if (this.resizeDrag) return
    const hit = this.headerHitVisCol(e)
    if (!hit || hit.nearBorder) return
    const col = this.visCols[hit.visCol]
    if (col) this.cb.onSort(col.key)
  }

  private onDocMouseMove = (e: MouseEvent): void => {
    if (!this.resizeDrag) return
    const dx = e.clientX - this.resizeDrag.startX
    const newW = Math.max(30, this.resizeDrag.startW + dx)
    this.visCols[this.resizeDrag.visIdx].w = newW
    const key = this.visCols[this.resizeDrag.visIdx].key
    const src = this.cols.find(c => c.key === key)
    if (src) src.w = newW
    this.updateSizer()
    this.requestRender()
  }

  private onDocMouseUp = (): void => {
    if (!this.resizeDrag) return
    const col = this.visCols[this.resizeDrag.visIdx]
    this.cb.onColumnResize(col.key, col.w)
    this.resizeDrag = null
  }

  private onKeyDown = (e: KeyboardEvent): void => {
    if (this.editor.isEditing()) return
    const t = e.target as HTMLElement
    if (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT') return
    switch (e.key) {
      case 'ArrowUp':    e.preventDefault(); this.selection.moveActive(-1, 0, this.rows.length, this.visCols.length); break
      case 'ArrowDown':  e.preventDefault(); this.selection.moveActive(1, 0, this.rows.length, this.visCols.length); break
      case 'ArrowLeft':  e.preventDefault(); this.selection.moveActive(0, -1, this.rows.length, this.visCols.length); break
      case 'ArrowRight': e.preventDefault(); this.selection.moveActive(0, 1, this.rows.length, this.visCols.length); break
      case 'Escape':     this.selection.clearSelection(); break
      default: return
    }
    this.cb.onSelectionChange(this.selection.getSelectedRows())
    const ac = this.selection.getActiveCell()
    if (ac) this.ensureVisible(ac)
    this.requestRender()
  }

  private ensureVisible(cell: CellRef): void {
    const y = cell.row * this.rowH
    const ghostH = this.ghost.clientHeight
    if (y < this.scrollTop) this.ghost.scrollTop = y
    else if (y + this.rowH > this.scrollTop + ghostH) this.ghost.scrollTop = y + this.rowH - ghostH
  }

  /* ══════════════════════════════════════════════
     RENDERING
     ══════════════════════════════════════════════ */

  private requestRender(): void {
    if (this.rafId || this.destroyed) return
    this.rafId = requestAnimationFrame(() => { this.rafId = 0; this.draw() })
  }

  private draw(): void {
    const { ctx, viewW, viewH, rowH } = this
    ctx.clearRect(0, 0, viewW, viewH)
    if (this.visCols.length === 0) return

    const frozenW = this.getFrozenWidth()
    const frozenN = Math.min(this.frozenCols, this.visCols.length)
    const dataH = viewH - HEADER_H
    const startRow = Math.max(0, Math.floor(this.scrollTop / rowH))
    const endRow = Math.min(startRow + Math.ceil(dataH / rowH) + 2, this.rows.length)

    // ── Scrollable columns (clipped) ──
    ctx.save()
    ctx.beginPath()
    ctx.rect(frozenW, HEADER_H, viewW - frozenW, dataH)
    ctx.clip()
    for (let r = startRow; r < endRow; r++) {
      const y = HEADER_H + r * rowH - this.scrollTop
      this.drawRowBg(r, y, frozenW, viewW)
      let cx = -this.scrollLeft
      for (let c = 0; c < this.visCols.length; c++) {
        const col = this.visCols[c]
        if (c < frozenN) { cx += col.w; continue }
        this.drawCell(this.rows[r], col, cx, y, col.w, rowH)
        ctx.strokeStyle = GRID_LINE; ctx.lineWidth = 1
        ctx.beginPath(); ctx.moveTo(cx + col.w - 0.5, y); ctx.lineTo(cx + col.w - 0.5, y + rowH); ctx.stroke()
        cx += col.w
      }
      ctx.strokeStyle = GRID_LINE; ctx.lineWidth = 1
      ctx.beginPath(); ctx.moveTo(frozenW, y + rowH - 0.5); ctx.lineTo(viewW, y + rowH - 0.5); ctx.stroke()
    }
    ctx.restore()

    // ── Frozen columns ──
    if (frozenN > 0) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(0, HEADER_H, frozenW, dataH)
      ctx.clip()
      for (let r = startRow; r < endRow; r++) {
        const y = HEADER_H + r * rowH - this.scrollTop
        this.drawRowBg(r, y, 0, frozenW)
        let cx = 0
        for (let c = 0; c < frozenN; c++) {
          const col = this.visCols[c]
          this.drawCell(this.rows[r], col, cx, y, col.w, rowH)
          ctx.strokeStyle = GRID_LINE; ctx.lineWidth = 1
          ctx.beginPath(); ctx.moveTo(cx + col.w - 0.5, y); ctx.lineTo(cx + col.w - 0.5, y + rowH); ctx.stroke()
          cx += col.w
        }
        ctx.strokeStyle = GRID_LINE
        ctx.beginPath(); ctx.moveTo(0, y + rowH - 0.5); ctx.lineTo(frozenW, y + rowH - 0.5); ctx.stroke()
      }
      ctx.restore()
      ctx.strokeStyle = FROZEN_SEP; ctx.lineWidth = 2
      ctx.beginPath(); ctx.moveTo(frozenW, HEADER_H); ctx.lineTo(frozenW, viewH); ctx.stroke()
    }

    // ── Header (always on top) ──
    this.drawHeader(frozenW, frozenN)
  }

  private drawRowBg(rowIdx: number, y: number, x0: number, x1: number): void {
    const { ctx, rowH } = this
    if (this.selection.isRowSelected(rowIdx)) {
      ctx.fillStyle = SELECTED_BG; ctx.fillRect(x0, y, x1 - x0, rowH)
    } else if (rowIdx === this.hoverRow) {
      ctx.fillStyle = HOVER_BG; ctx.fillRect(x0, y, x1 - x0, rowH)
    } else if (rowIdx % 2 === 1) {
      ctx.fillStyle = '#fafafa'; ctx.fillRect(x0, y, x1 - x0, rowH)
    }
    const ac = this.selection.getActiveCell()
    if (ac && ac.row === rowIdx) {
      const rect = this.getCellRect(rowIdx, ac.col)
      if (rect) {
        ctx.strokeStyle = ACTIVE_BORDER; ctx.lineWidth = 2
        ctx.strokeRect(rect.x + 1, rect.y + 1, rect.w - 2, rect.h - 2)
      }
    }
  }

  /* ── Cell Drawing ── */
  private drawCell(row: DataRow, col: ColDef, x: number, y: number, w: number, h: number): void {
    const { ctx } = this
    const val = String(row[col.key] ?? '')
    ctx.font = FONT; ctx.textBaseline = 'middle'
    const ty = y + h / 2

    switch (col.type) {
      case 'idx':
        ctx.fillStyle = '#94a3b8'; ctx.textAlign = 'right'
        ctx.fillText(val, x + w - 8, ty); ctx.textAlign = 'left'
        break
      case 'photo':
        this.drawPhoto(row, x, y, w, h)
        break
      case 'stage':
        this.drawStage(String(row.stage), x, y, w, h)
        break
      case 'tags':
        this.drawTags(val, x, y, w, h)
        break
      case 'mail':
        this.drawMailBtn(x, y, w, h)
        break
      case 'dropdown':
        ctx.fillStyle = '#1e293b'
        this.drawTruncated(val, x + 4, ty, w - 20)
        ctx.fillStyle = '#94a3b8'; ctx.font = '10px sans-serif'
        ctx.fillText('▾', x + w - 14, ty); ctx.font = FONT
        break
      case 'long':
        ctx.fillStyle = '#334155'
        this.drawWrapped(val, x + 4, y + 4, w - 8, h - 8)
        break
      default:
        ctx.fillStyle = '#1e293b'
        this.drawTruncated(val, x + 4, ty, w - 8)
    }
  }

  private drawTruncated(text: string, x: number, y: number, maxW: number): void {
    const { ctx } = this
    if (!text || maxW <= 0) return
    if (ctx.measureText(text).width <= maxW) { ctx.fillText(text, x, y); return }
    let t = text
    while (t.length > 1 && ctx.measureText(t + '…').width > maxW) t = t.slice(0, -1)
    ctx.fillText(t + '…', x, y)
  }

  private drawWrapped(text: string, x: number, y: number, maxW: number, maxH: number): void {
    const { ctx } = this
    if (!text || maxW <= 0) return
    const lineH = 15
    const maxLines = Math.max(1, Math.floor(maxH / lineH))
    let line = 0
    ctx.textBaseline = 'top'
    for (const raw of text.split('\n')) {
      if (line >= maxLines) break
      if (ctx.measureText(raw).width <= maxW) {
        ctx.fillText(raw, x, y + line * lineH); line++
      } else {
        let seg = ''
        for (const ch of raw) {
          if (ctx.measureText(seg + ch).width > maxW) {
            ctx.fillText(seg, x, y + line * lineH); line++
            if (line >= maxLines) break
            seg = ch
          } else { seg += ch }
        }
        if (line < maxLines && seg) { ctx.fillText(seg, x, y + line * lineH); line++ }
      }
    }
    ctx.textBaseline = 'middle'
  }

  private drawPhoto(row: DataRow, x: number, y: number, w: number, h: number): void {
    const { ctx } = this
    const url = String(row.photoUrl ?? '')
    if (!url) {
      ctx.fillStyle = '#e2e8f0'
      const sz = Math.min(w, h) - 8
      ctx.fillRect(x + (w - sz) / 2, y + (h - sz) / 2, sz, sz)
      ctx.fillStyle = '#94a3b8'; ctx.font = '10px sans-serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText('📷', x + w / 2, y + h / 2)
      ctx.font = FONT; ctx.textAlign = 'left'
      return
    }
    const cached = this.photoCache.get(url)
    if (cached) {
      const sz = Math.min(w, h) - 6
      try { ctx.drawImage(cached, x + (w - sz) / 2, y + (h - sz) / 2, sz, sz) } catch { /* */ }
    } else if (!this.photoLoading.has(url)) { this.loadPhoto(url) }
  }

  private loadPhoto(url: string): void {
    this.photoLoading.add(url)
    if (url.includes('/api/') && this.getHeaders) {
      const hdrs = this.getHeaders()
      fetch(url, { headers: hdrs }).then(r => r.blob()).then(blob => {
        const objectUrl = URL.createObjectURL(blob)
        const img = new Image()
        img.onload = () => { this.photoCache.set(url, img); this.photoLoading.delete(url); this.requestRender() }
        img.onerror = () => { this.photoLoading.delete(url) }
        img.src = objectUrl
      }).catch(() => { this.photoLoading.delete(url) })
    } else {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => { this.photoCache.set(url, img); this.photoLoading.delete(url); this.requestRender() }
      img.onerror = () => { this.photoLoading.delete(url) }
      img.src = url
    }
  }

  private drawStage(stageKey: string, x: number, y: number, w: number, h: number): void {
    const { ctx } = this
    const stage = STAGES.find(s => s.key === stageKey)
    if (!stage || stage.key === 'none') return
    const pad = 4
    const bw = Math.min(w - pad * 2, ctx.measureText(stage.label).width + 16)
    const bh = 22
    const bx = x + pad, by = y + (h - bh) / 2
    ctx.fillStyle = stage.color; this.roundRect(bx, by, bw, bh, 4); ctx.fill()
    ctx.fillStyle = stage.text
    ctx.font = '12px -apple-system,"Segoe UI",sans-serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText(stage.label, bx + bw / 2, by + bh / 2)
    ctx.font = FONT; ctx.textAlign = 'left'
  }

  private drawTags(val: string, x: number, y: number, w: number, h: number): void {
    const { ctx } = this
    if (!val) return
    let tx = x + 4
    const tagH = 18, ty = y + (h - tagH) / 2
    ctx.font = '10px -apple-system,"Segoe UI",sans-serif'
    for (const k of val.split(',').filter(Boolean)) {
      const tag = MTAGS.find(m => m.key === k.trim())
      if (!tag) continue
      const tw = ctx.measureText(tag.label).width + 10
      if (tx + tw > x + w) break
      ctx.fillStyle = tag.c + '20'; this.roundRect(tx, ty, tw, tagH, 3); ctx.fill()
      ctx.fillStyle = tag.c; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText(tag.label, tx + tw / 2, ty + tagH / 2)
      tx += tw + 3
    }
    ctx.font = FONT; ctx.textAlign = 'left'
  }

  private drawMailBtn(x: number, y: number, w: number, h: number): void {
    const { ctx } = this
    const bw = Math.min(w - 8, 60), bh = 24
    const bx = x + (w - bw) / 2, by = y + (h - bh) / 2
    ctx.fillStyle = '#eff6ff'; this.roundRect(bx, by, bw, bh, 4); ctx.fill()
    ctx.strokeStyle = '#93c5fd'; ctx.lineWidth = 1; this.roundRect(bx, by, bw, bh, 4); ctx.stroke()
    ctx.fillStyle = '#2563eb'; ctx.font = '11px -apple-system,"Segoe UI",sans-serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText('✉ 발송', bx + bw / 2, by + bh / 2)
    ctx.font = FONT; ctx.textAlign = 'left'
  }

  private roundRect(x: number, y: number, w: number, h: number, r: number): void {
    const { ctx } = this
    ctx.beginPath()
    ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y)
    ctx.quadraticCurveTo(x + w, y, x + w, y + r); ctx.lineTo(x + w, y + h - r)
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h); ctx.lineTo(x + r, y + h)
    ctx.quadraticCurveTo(x, y + h, x, y + h - r); ctx.lineTo(x, y + r)
    ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath()
  }

  /* ── Header ── */
  private drawHeader(frozenW: number, frozenN: number): void {
    const { ctx, viewW } = this
    ctx.fillStyle = HEADER_BG; ctx.fillRect(0, 0, viewW, HEADER_H)
    ctx.strokeStyle = HEADER_BORDER; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(0, HEADER_H - 0.5); ctx.lineTo(viewW, HEADER_H - 0.5); ctx.stroke()
    ctx.font = HEADER_FONT; ctx.textBaseline = 'middle'; ctx.fillStyle = '#1e293b'

    // Scrollable headers
    ctx.save()
    ctx.beginPath(); ctx.rect(frozenW, 0, viewW - frozenW, HEADER_H); ctx.clip()
    let cx = -this.scrollLeft
    for (let i = 0; i < this.visCols.length; i++) {
      const col = this.visCols[i]
      if (i < frozenN) { cx += col.w; continue }
      this.drawHeaderCell(col, cx, col.w); cx += col.w
    }
    ctx.restore()

    // Frozen headers
    if (frozenN > 0) {
      ctx.fillStyle = HEADER_BG; ctx.fillRect(0, 0, frozenW, HEADER_H)
      let fx = 0
      for (let i = 0; i < frozenN; i++) {
        this.drawHeaderCell(this.visCols[i], fx, this.visCols[i].w); fx += this.visCols[i].w
      }
      ctx.strokeStyle = FROZEN_SEP; ctx.lineWidth = 2
      ctx.beginPath(); ctx.moveTo(frozenW, 0); ctx.lineTo(frozenW, HEADER_H); ctx.stroke()
    }
  }

  private drawHeaderCell(col: ColDef, x: number, w: number): void {
    const { ctx } = this
    ctx.fillStyle = '#1e293b'; ctx.font = HEADER_FONT
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
    this.drawTruncated(col.label, x + 6, HEADER_H / 2, w - 18)
    if (col.key === this.sortKey) {
      ctx.fillStyle = SORT_ARROW; ctx.font = '10px sans-serif'; ctx.textAlign = 'right'
      ctx.fillText(this.sortDir === 'asc' ? '▲' : '▼', x + w - 6, HEADER_H / 2)
      ctx.font = HEADER_FONT; ctx.textAlign = 'left'
    }
    ctx.strokeStyle = HEADER_BORDER; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(x + w - 0.5, 4); ctx.lineTo(x + w - 0.5, HEADER_H - 4); ctx.stroke()
  }
}
