/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Grid Engine v4
   Pure Canvas rendering: header, rows, photos, stages, tags
   Ghost-div scrollbar, column resize, DPR scaling
   v4: Google Sheets style — row numbers (no checkbox),
       corner select-all, stage dropdown, tag toggle,
       photo wheel, cell styles, filter icons, header context menu,
       per-row variable heights, drag-to-resize rows
   ═══════════════════════════════════════════════════════ */

import type { ColDef, DataRow, GridCallbacks, CellRef } from './types'
import { HEADER_H, FONT, HEADER_FONT, STAGES, MTAGS, colAlphabet } from './types'
import { SelectionManager } from './SelectionManager'
import { EditManager } from './EditManager'
import { StyleManager } from './StyleManager'

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
const ROW_RESIZE_ZONE = 5
const ROW_NUM_BG      = '#f8f9fa'
const ROW_NUM_SEL_BG  = '#d3e3fd'
const KEY_COLS = new Set(['email', 'name'])
const KEY_COL_FONT = '14px -apple-system,"Segoe UI",sans-serif'
const KEY_HEADER_FONT = '13px -apple-system,"Segoe UI",sans-serif'

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
  styleManager: StyleManager

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
  private defaultRowH = 36

  /* ── Per-row heights ── */
  private rowHeights = new Map<string, number>()  // cid → height
  private rowYs: number[] = []                     // prefix sum: rowYs[i] = top Y of row i
  private totalContentH = 0

  /* ── Interaction ── */
  private hoverRow = -1
  private sortKey = ''
  private sortDir: 'asc' | 'desc' = 'asc'
  private colResizeDrag: { visIdx: number; startX: number; startW: number } | null = null
  private rowResizeDrag: { rowIdx: number; startClientY: number; startH: number; cid: string } | null = null
  private colDrag: { srcVisIdx: number; startX: number; currentX: number; dragging: boolean } | null = null

  /* ── ColReorder callback ── */
  onColReorder: ((cols: ColDef[]) => void) | null = null

  /* ── Photo cache ── */
  private photoCache = new Map<string, HTMLImageElement>()
  private photoLoading = new Set<string>()

  /* ── RAF ── */
  private rafId = 0
  private destroyed = false
  private ro: ResizeObserver
  private getHeaders: (() => Record<string, string>) | null = null

  /** Snap a CSS-pixel coordinate to the nearest physical pixel center for crisp 1px lines */
  private snap(v: number): number {
    const d = this.dpr
    return (Math.round(v * d) + 0.5) / d
  }

  constructor(container: HTMLDivElement, cb: GridCallbacks) {
    this.container = container
    this.cb = cb
    this.dpr = window.devicePixelRatio || 1
    this.selection = new SelectionManager()
    this.editor = new EditManager(container)
    this.styleManager = new StyleManager()

    container.style.position = 'relative'
    container.style.overflow = 'hidden'

    this.canvas = document.createElement('canvas')
    this.canvas.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;'
    this.ctx = this.canvas.getContext('2d')!
    container.appendChild(this.canvas)

    this.headerHit = document.createElement('div')
    this.headerHit.style.cssText = `position:absolute;top:0;left:0;right:0;height:${HEADER_H}px;z-index:2;cursor:default;`
    container.appendChild(this.headerHit)

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
    this.computeRowYs()
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

  /** Set default row height (toolbar selector) */
  setRowHeight(h: number): void {
    this.defaultRowH = h
    this.computeRowYs()
    this.updateSizer()
    this.requestRender()
  }

  /** Load per-row custom heights (from localStorage) */
  setRowHeights(heights: Record<string, number>): void {
    this.rowHeights.clear()
    for (const [cid, h] of Object.entries(heights)) {
      this.rowHeights.set(cid, h)
    }
    this.computeRowYs()
    this.updateSizer()
    this.requestRender()
  }

  setHeaderGetter(fn: () => Record<string, string>): void { this.getHeaders = fn }

  getVisibleCols(): ColDef[] { return this.visCols }

  scrollToRow(idx: number): void {
    this.ghost.scrollTop = idx < this.rowYs.length ? this.rowYs[idx] : 0
  }

  refresh(): void { this.requestRender() }

  /** Return all custom row heights as a plain object */
  getRowHeightsMap(): Record<string, number> {
    const out: Record<string, number> = {}
    for (const [cid, h] of this.rowHeights) out[cid] = h
    return out
  }

  destroy(): void {
    this.destroyed = true
    this.ro.disconnect()
    if (this.rafId) cancelAnimationFrame(this.rafId)
    this.editor.destroy()
    document.removeEventListener('mousemove', this.onDocMouseMove)
    document.removeEventListener('mouseup', this.onDocMouseUp)
    document.removeEventListener('keydown', this.onKeyDown)
    this.canvas.remove()
    this.headerHit.remove()
    this.ghost.remove()
  }

  /* ══════════════════════════════════════════════
     ROW HEIGHT HELPERS
     ══════════════════════════════════════════════ */

  /** Get height for a specific row */
  private getRowH(rowIdx: number): number {
    const row = this.rows[rowIdx]
    if (!row) return this.defaultRowH
    const cid = String(row._cid ?? row.id)
    return this.rowHeights.get(cid) ?? this.defaultRowH
  }

  /** Compute prefix sum of row Y positions */
  private computeRowYs(): void {
    const n = this.rows.length
    this.rowYs = new Array(n + 1)
    this.rowYs[0] = 0
    for (let i = 0; i < n; i++) {
      this.rowYs[i + 1] = this.rowYs[i] + this.getRowH(i)
    }
    this.totalContentH = n > 0 ? this.rowYs[n] : 0
  }

  /** Binary search: find row index at content Y coordinate */
  private rowAtY(contentY: number): number {
    if (this.rows.length === 0) return -1
    let lo = 0, hi = this.rows.length - 1
    while (lo <= hi) {
      const mid = (lo + hi) >> 1
      if (this.rowYs[mid + 1] <= contentY) lo = mid + 1
      else if (this.rowYs[mid] > contentY) hi = mid - 1
      else return mid
    }
    return Math.min(lo, this.rows.length - 1)
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
    this.sizer.style.width = totalW + 'px'
    this.sizer.style.height = this.totalContentH + 'px'
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
    this.ghost.addEventListener('wheel', this.onGhostWheel, { passive: false })
    this.headerHit.addEventListener('mousedown', this.onHeaderMouseDown)
    this.headerHit.addEventListener('mousemove', this.onHeaderMouseMove)
    this.headerHit.addEventListener('click', this.onHeaderClick)
    this.headerHit.addEventListener('dblclick', this.onHeaderDblClick)
    this.headerHit.addEventListener('contextmenu', this.onHeaderContextMenu)
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

  /** Get content-space mouse position from event */
  private ghostMousePos(e: MouseEvent): { mx: number; my: number } {
    const rect = this.ghost.getBoundingClientRect()
    return {
      mx: e.clientX - rect.left + this.scrollLeft,
      my: e.clientY - rect.top + this.scrollTop,
    }
  }

  private hitCell(e: MouseEvent): { row: number; visCol: number; localX: number; localY: number } | null {
    const { mx, my } = this.ghostMousePos(e)
    const row = this.rowAtY(my)
    if (row < 0 || row >= this.rows.length) return null
    const rowTop = this.rowYs[row]
    let cx = 0
    for (let i = 0; i < this.visCols.length; i++) {
      if (mx >= cx && mx < cx + this.visCols[i].w) {
        return { row, visCol: i, localX: mx - cx, localY: my - rowTop }
      }
      cx += this.visCols[i].w
    }
    return null
  }

  /** Check if mouse is near the bottom border of a row (for row resize) */
  private nearRowBorder(e: MouseEvent): number {
    const { my } = this.ghostMousePos(e)
    // Check if near any row's bottom edge
    const row = this.rowAtY(my)
    if (row < 0 || row >= this.rows.length) return -1
    const rowBottom = this.rowYs[row + 1]
    if (Math.abs(my - rowBottom) <= ROW_RESIZE_ZONE) return row
    // Also check the row above (in case cursor is just past the border)
    if (row > 0) {
      const prevBottom = this.rowYs[row]
      if (Math.abs(my - prevBottom) <= ROW_RESIZE_ZONE) return row - 1
    }
    return -1
  }


  private hitTag(val: string, localX: number): string | null {
    if (!val) return null
    const { ctx } = this
    ctx.save()
    ctx.font = '10px -apple-system,"Segoe UI",sans-serif'
    let tx = 4
    for (const k of val.split(',').filter(Boolean)) {
      const tag = MTAGS.find(m => m.key === k.trim())
      if (!tag) continue
      const tw = ctx.measureText(tag.label).width + 10
      if (localX >= tx && localX < tx + tw) { ctx.restore(); return tag.key }
      tx += tw + 3
    }
    ctx.restore()
    return null
  }

  private onGhostMouseDown = (e: MouseEvent): void => {
    if (this.editor.isEditing()) return
    // 우클릭(button=2)은 contextmenu 핸들러에서 처리 — 다중 선택 보존
    if (e.button === 2) return

    // Check for row resize drag first
    const resizeRow = this.nearRowBorder(e)
    if (resizeRow >= 0) {
      e.preventDefault()
      const row = this.rows[resizeRow]
      const cid = String(row?._cid ?? row?.id ?? '')
      this.rowResizeDrag = {
        rowIdx: resizeRow,
        startClientY: e.clientY,
        startH: this.getRowH(resizeRow),
        cid,
      }
      return
    }

    const hit = this.hitCell(e)
    if (!hit) return

    const col = this.visCols[hit.visCol]

    // Row number click → select row (Google Sheets style)
    if (col && col.type === 'idx') {
      this.selection.selectedCols.clear()  // 열 선택 해제
      this.selection.selectRow(hit.row, e.ctrlKey || e.metaKey, e.shiftKey)
      this.cb.onSelectionChange(this.selection.getSelectedRows())
      this.requestRender()
      return
    }

    // Tag cell click → 팝업으로 위임 (롤선택 방식)
    if (col && col.type === 'tags') {
      const row = this.rows[hit.row]
      if (row) {
        // mousedown 직후 click 이벤트가 document에 버블링되어 팝업 즉시 닫힘 방지
        const stopOpeningClick = (ev: MouseEvent) => ev.stopPropagation()
        this.ghost.addEventListener('click', stopOpeningClick, { capture: true, once: true })

        this.selection.selectRow(hit.row, e.ctrlKey || e.metaKey, e.shiftKey)
        this.selection.selectCell(hit.row, hit.visCol)
        this.cb.onSelectionChange(this.selection.getSelectedRows())
        this.cb.onTagCellClick(hit.row, row, e.clientX, e.clientY)
        this.requestRender()
        return
      }
    }

    // Mail button click
    if (col && col.type === 'mail') {
      const row = this.rows[hit.row]
      if (row) this.cb.onMailClick(hit.row, row)
      return
    }

    this.selection.selectedCols.clear()  // 열 선택 해제
    this.selection.selectRow(hit.row, e.ctrlKey || e.metaKey, e.shiftKey)
    this.selection.selectCell(hit.row, hit.visCol)
    this.cb.onSelectionChange(this.selection.getSelectedRows())
    this.requestRender()
  }

  private onGhostMouseMove = (e: MouseEvent): void => {
    // During row resize drag, don't change hover
    if (this.rowResizeDrag) return

    const hit = this.hitCell(e)
    const newHover = hit ? hit.row : -1
    if (newHover !== this.hoverRow) { this.hoverRow = newHover; this.requestRender() }

    // Row resize cursor
    const resizeRow = this.nearRowBorder(e)
    if (resizeRow >= 0) {
      this.ghost.style.cursor = 'row-resize'
      return
    }

    // Clickable area cursors
    if (hit) {
      const col = this.visCols[hit.visCol]
      if (col && (col.type === 'tags' || col.type === 'mail')) {
        this.ghost.style.cursor = 'pointer'
      } else {
        this.ghost.style.cursor = 'default'
      }
    } else {
      this.ghost.style.cursor = 'default'
    }
  }

  private onGhostDblClick = (e: MouseEvent): void => {
    const hit = this.hitCell(e)
    if (!hit) return
    const col = this.visCols[hit.visCol]
    const row = this.rows[hit.row]
    if (!col || !row) return

    if (col.type === 'idx') return
    if (col.type === 'mail') { this.cb.onMailClick(hit.row, row); return }
    if (col.type === 'tags') return

    if (col.type === 'photo') {
      this.cb.onPhotoUpload(hit.row)
      return
    }

    if (col.type === 'stage') {
      const cellRect = this.getCellRect(hit.row, hit.visCol)
      if (!cellRect) return
      const stageOpts = STAGES.map(s => s.label)
      const curStage = STAGES.find(s => s.key === String(row.stage)) || STAGES[0]
      this.editor.startEdit(cellRect, 'dropdown', curStage.label, stageOpts).then(result => {
        if (result.committed) {
          const selected = STAGES.find(s => s.label === result.value)
          if (selected) this.cb.onStageChange(hit.row, selected.key)
        }
        this.requestRender()
      })
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

  private onGhostWheel = (e: WheelEvent): void => {
    const hit = this.hitCell(e as unknown as MouseEvent)
    if (!hit) return
    const col = this.visCols[hit.visCol]
    if (col && col.type === 'photo') {
      e.preventDefault()
      this.cb.onPhotoWheel(hit.row, e.deltaY < 0 ? 5 : -5)
    }
  }

  private getCellRect(rowIdx: number, visColIdx: number): { x: number; y: number; w: number; h: number } | null {
    const col = this.visCols[visColIdx]
    if (!col) return null
    const isFrozen = visColIdx < this.frozenCols
    const cx = this.colX(visColIdx)
    const x = isFrozen ? cx : cx - this.scrollLeft
    const rowTop = rowIdx < this.rowYs.length ? this.rowYs[rowIdx] : 0
    const y = HEADER_H + rowTop - this.scrollTop
    const h = this.getRowH(rowIdx)
    return { x, y, w: col.w, h }
  }

  /* ── Header events ── */
  private headerHitVisCol(e: MouseEvent): { visCol: number; nearBorder: boolean; localX: number; localY: number } | null {
    const rect = this.headerHit.getBoundingClientRect()
    const mx = e.clientX - rect.left + this.scrollLeft
    const my = e.clientY - rect.top
    let cx = 0
    for (let i = 0; i < this.visCols.length; i++) {
      cx += this.visCols[i].w
      if (Math.abs(mx - cx) <= RESIZE_ZONE) return { visCol: i, nearBorder: true, localX: mx - (cx - this.visCols[i].w), localY: my }
      if (mx < cx) return { visCol: i, nearBorder: false, localX: mx - (cx - this.visCols[i].w), localY: my }
    }
    return null
  }

  private onHeaderMouseDown = (e: MouseEvent): void => {
    const hit = this.headerHitVisCol(e)
    if (!hit) return
    if (hit.nearBorder) {
      e.preventDefault()
      this.colResizeDrag = { visIdx: hit.visCol, startX: e.clientX, startW: this.visCols[hit.visCol].w }
      return
    }
    // 컬럼 드래그 시작 (리사이즈 존 아닌 경우 — 알파벳 행 localY < 20)
    if (hit.localY < 20 && this.visCols[hit.visCol]?.type !== 'idx') {
      e.preventDefault()
      this.colDrag = { srcVisIdx: hit.visCol, startX: e.clientX, currentX: e.clientX, dragging: false }
    }
  }

  private onHeaderMouseMove = (e: MouseEvent): void => {
    const hit = this.headerHitVisCol(e)
    this.headerHit.style.cursor = hit?.nearBorder ? 'col-resize' : 'default'
  }

  private onHeaderClick = (e: MouseEvent): void => {
    if (this.colResizeDrag) return
    const hit = this.headerHitVisCol(e)
    if (!hit || hit.nearBorder) return
    const col = this.visCols[hit.visCol]
    if (!col) return

    if (col.type === 'idx') {
      this.cb.onHeaderCheckToggle()
      this.requestRender()
      return
    }

    // Alphabet row click (top 20px) → select entire column
    if (hit.localY < 20) {
      this.selection.selectColumn(hit.visCol, this.rows.length)
      this.cb.onSelectionChange(this.selection.getSelectedRows())
      this.requestRender()
      return
    }

    if (hit.localX > col.w - 18 && col.type !== 'photo' && col.type !== 'mail') {
      const rect = this.headerHit.getBoundingClientRect()
      const cx = this.colX(hit.visCol) - this.scrollLeft
      this.cb.onFilterClick(col.key, rect.left + cx + col.w, rect.top + HEADER_H)
      return
    }

    // Column name click: select only (sort moved to dblclick)
    this.selection.selectAll(this.rows.length)
    this.selection.selectCell(0, hit.visCol)
    this.cb.onSelectionChange(this.selection.getSelectedRows())
    this.requestRender()
  }

  private onHeaderDblClick = (e: MouseEvent): void => {
    const hit = this.headerHitVisCol(e)
    if (!hit || hit.nearBorder) return
    const col = this.visCols[hit.visCol]
    if (!col || col.type === 'idx') return
    // Column name row only (localY >= 20)
    if (hit.localY >= 20) {
      this.cb.onSort(col.key)
      this.requestRender()
    }
  }

  private onHeaderContextMenu = (e: MouseEvent): void => {
    e.preventDefault()
    const hit = this.headerHitVisCol(e)
    if (!hit) return
    const col = this.visCols[hit.visCol]
    if (col) this.cb.onHeaderContextMenu(e, col.key)
  }

  private onDocMouseMove = (e: MouseEvent): void => {
    // Column drag reorder
    if (this.colDrag) {
      const dx = Math.abs(e.clientX - this.colDrag.startX)
      if (dx > 5) this.colDrag.dragging = true
      this.colDrag.currentX = e.clientX
      if (this.colDrag.dragging) {
        this.headerHit.style.cursor = 'grabbing'
        this.requestRender()
      }
      return
    }

    // Column resize drag
    if (this.colResizeDrag) {
      const dx = e.clientX - this.colResizeDrag.startX
      const newW = Math.max(4, this.colResizeDrag.startW + dx)
      this.visCols[this.colResizeDrag.visIdx].w = newW
      const key = this.visCols[this.colResizeDrag.visIdx].key
      const src = this.cols.find(c => c.key === key)
      if (src) src.w = newW
      this.updateSizer()
      this.requestRender()
      return
    }

    // Row resize drag — apply to all selected rows if the dragged row is selected
    if (this.rowResizeDrag) {
      const dy = e.clientY - this.rowResizeDrag.startClientY
      const newH = Math.max(4, this.rowResizeDrag.startH + dy)
      const selectedRows = this.selection.getSelectedRows()
      if (selectedRows.has(this.rowResizeDrag.rowIdx) && selectedRows.size > 1) {
        for (const ri of selectedRows) {
          const row = this.rows[ri]
          if (row) this.rowHeights.set(String(row._cid ?? row.id), newH)
        }
      } else {
        this.rowHeights.set(this.rowResizeDrag.cid, newH)
      }
      this.computeRowYs()
      this.updateSizer()
      this.requestRender()
      return
    }
  }

  private onDocMouseUp = (e: MouseEvent): void => {
    // Column drag reorder
    if (this.colDrag) {
      this.headerHit.style.cursor = 'default'
      if (this.colDrag.dragging) {
        const tgtVisIdx = this.getDropColIdx(e.clientX)
        if (tgtVisIdx !== null && tgtVisIdx !== this.colDrag.srcVisIdx) {
          // Reorder visCols
          const newVisCols = [...this.visCols]
          const [moved] = newVisCols.splice(this.colDrag.srcVisIdx, 1)
          const insertAt = tgtVisIdx > this.colDrag.srcVisIdx ? tgtVisIdx - 1 : tgtVisIdx
          newVisCols.splice(insertAt, 0, moved)
          this.visCols = newVisCols
          // Sync to cols (full list)
          const newCols: ColDef[] = []
          const usedKeys = new Set(newVisCols.map(c => c.key))
          for (const vc of newVisCols) newCols.push(vc)
          for (const c of this.cols) { if (!usedKeys.has(c.key)) newCols.push(c) }
          this.cols = newCols
          if (this.onColReorder) this.onColReorder([...newCols])
        }
      }
      this.colDrag = null
      this.requestRender()
      return
    }

    if (this.colResizeDrag) {
      const col = this.visCols[this.colResizeDrag.visIdx]
      this.cb.onColumnResize(col.key, col.w)
      this.colResizeDrag = null
      return
    }

    if (this.rowResizeDrag) {
      const { cid } = this.rowResizeDrag
      const finalH = this.rowHeights.get(cid) ?? this.defaultRowH
      // Signal callback — React side reads full map via getRowHeightsMap()
      this.cb.onRowHeightChange(cid, finalH)
      this.rowResizeDrag = null
      return
    }
  }

  private onKeyDown = (e: KeyboardEvent): void => {
    if (this.editor.isEditing()) return
    const t = e.target as HTMLElement
    if (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT') return

    if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
      e.preventDefault()
      this.selection.selectAll(this.rows.length)
      this.cb.onSelectionChange(this.selection.getSelectedRows())
      this.requestRender()
      return
    }

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
    const y = cell.row < this.rowYs.length ? this.rowYs[cell.row] : 0
    const h = this.getRowH(cell.row)
    const ghostH = this.ghost.clientHeight
    if (y < this.scrollTop) this.ghost.scrollTop = y
    else if (y + h > this.scrollTop + ghostH) this.ghost.scrollTop = y + h - ghostH
  }

  /* ══════════════════════════════════════════════
     RENDERING
     ══════════════════════════════════════════════ */

  /** 마우스 X 좌표에서 드롭 대상 열 인덱스 계산 (열 경계 기준) */
  private getDropColIdx(clientX: number): number | null {
    const rect = this.headerHit.getBoundingClientRect()
    const mx = clientX - rect.left + this.scrollLeft
    let cx = 0
    for (let i = 0; i <= this.visCols.length; i++) {
      if (mx < cx + (i < this.visCols.length ? this.visCols[i].w / 2 : 0)) return i
      if (i < this.visCols.length) cx += this.visCols[i].w
    }
    return this.visCols.length
  }

  private requestRender(): void {
    if (this.rafId || this.destroyed) return
    this.rafId = requestAnimationFrame(() => { this.rafId = 0; this.draw() })
  }

  private draw(): void {
    const { ctx, viewW, viewH } = this
    ctx.clearRect(0, 0, viewW, viewH)
    if (this.visCols.length === 0) return

    const frozenW = this.getFrozenWidth()
    const frozenN = Math.min(this.frozenCols, this.visCols.length)
    const dataH = viewH - HEADER_H

    // Find visible row range using binary search
    const startRow = Math.max(0, this.rowAtY(this.scrollTop))
    let endRow = startRow
    while (endRow < this.rows.length && this.rowYs[endRow] < this.scrollTop + dataH + 100) endRow++
    endRow = Math.min(endRow + 1, this.rows.length)

    // ── PASS 1: Scrollable cell content (NO per-cell clip — eliminates anti-alias artifacts) ──
    ctx.save()
    ctx.beginPath()
    ctx.rect(frozenW, HEADER_H, viewW - frozenW, dataH)
    ctx.clip()
    for (let r = startRow; r < endRow; r++) {
      const rowH = this.getRowH(r)
      const y = Math.round(HEADER_H + this.rowYs[r] - this.scrollTop)
      this.drawRowBg(r, y, frozenW, viewW, rowH)
      let cx = Math.round(-this.scrollLeft)
      for (let c = 0; c < this.visCols.length; c++) {
        const col = this.visCols[c]
        if (c < frozenN) { cx += col.w; continue }
        this.drawCell(this.rows[r], col, cx, y, col.w, rowH, r)
        cx += col.w
      }
    }
    ctx.restore()

    // ── PASS 2: Scrollable grid lines (snap to physical pixels) ──
    ctx.save()
    ctx.beginPath()
    ctx.rect(frozenW, HEADER_H, viewW - frozenW, dataH)
    ctx.clip()
    ctx.strokeStyle = GRID_LINE; ctx.lineWidth = 1
    { let lx = Math.round(-this.scrollLeft)
      for (let c = 0; c < this.visCols.length; c++) {
        if (c < frozenN) { lx += this.visCols[c].w; continue }
        lx += this.visCols[c].w
        const sx = this.snap(lx)
        ctx.beginPath(); ctx.moveTo(sx, HEADER_H); ctx.lineTo(sx, viewH); ctx.stroke()
      }
    }
    for (let r = startRow; r < endRow; r++) {
      const sy = this.snap(HEADER_H + this.rowYs[r + 1] - this.scrollTop)
      ctx.beginPath(); ctx.moveTo(frozenW, sy); ctx.lineTo(viewW, sy); ctx.stroke()
    }
    ctx.restore()

    // ── PASS 3: Frozen cell content (NO per-cell clip) ──
    if (frozenN > 0) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(0, HEADER_H, frozenW, dataH)
      ctx.clip()
      for (let r = startRow; r < endRow; r++) {
        const rowH = this.getRowH(r)
        const y = Math.round(HEADER_H + this.rowYs[r] - this.scrollTop)
        this.drawRowBg(r, y, 0, frozenW, rowH)
        let cx = 0
        for (let c = 0; c < frozenN; c++) {
          const col = this.visCols[c]
          this.drawCell(this.rows[r], col, cx, y, col.w, rowH, r)
          cx += col.w
        }
      }
      ctx.restore()

      // Frozen grid lines (snap to physical pixels)
      ctx.save()
      ctx.beginPath()
      ctx.rect(0, HEADER_H, frozenW, dataH)
      ctx.clip()
      ctx.strokeStyle = GRID_LINE; ctx.lineWidth = 1
      { let fx = 0
        for (let c = 0; c < frozenN; c++) {
          fx += this.visCols[c].w
          const sx = this.snap(fx)
          ctx.beginPath(); ctx.moveTo(sx, HEADER_H); ctx.lineTo(sx, viewH); ctx.stroke()
        }
      }
      for (let r = startRow; r < endRow; r++) {
        const sy = this.snap(HEADER_H + this.rowYs[r + 1] - this.scrollTop)
        ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(frozenW, sy); ctx.stroke()
      }
      ctx.restore()

      ctx.strokeStyle = FROZEN_SEP; ctx.lineWidth = 2
      ctx.beginPath(); ctx.moveTo(frozenW, HEADER_H); ctx.lineTo(frozenW, viewH); ctx.stroke()
    }

    this.drawHeader(frozenW, frozenN)

    // ── 열 드래그 인디케이터 ──
    if (this.colDrag?.dragging) {
      const rect = this.headerHit.getBoundingClientRect()
      const mx = this.colDrag.currentX - rect.left + this.scrollLeft
      // 드롭 위치 계산 → 파란 세로선
      let cx = 0, lineX = 0
      for (let i = 0; i < this.visCols.length; i++) {
        const mid = cx + this.visCols[i].w / 2
        if (mx < mid) { lineX = cx - this.scrollLeft; break }
        cx += this.visCols[i].w
        lineX = cx - this.scrollLeft
      }
      ctx.strokeStyle = '#1a73e8'; ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(lineX, 0)
      ctx.lineTo(lineX, viewH)
      ctx.stroke()
      // 드래그 중인 열 반투명 오버레이
      let srcX = -this.scrollLeft
      for (let i = 0; i < this.colDrag.srcVisIdx; i++) srcX += this.visCols[i].w
      const srcW = this.visCols[this.colDrag.srcVisIdx]?.w ?? 0
      ctx.fillStyle = 'rgba(26,115,232,0.12)'
      ctx.fillRect(srcX, 0, srcW, viewH)
    }
  }

  private drawRowBg(rowIdx: number, y: number, x0: number, x1: number, rowH: number): void {
    const { ctx } = this
    const row = this.rows[rowIdx]

    // 진행단계 배경색 (선택/호버보다 낮은 우선순위)
    if (row) {
      const stageInfo = STAGES.find(s => s.key === String(row.stage ?? ''))
      if (stageInfo && stageInfo.key !== 'none') {
        ctx.fillStyle = stageInfo.color + '55'  // 33% opacity
        ctx.fillRect(x0, y, x1 - x0, rowH)
      } else if (rowIdx % 2 === 1) {
        ctx.fillStyle = '#fafafa'; ctx.fillRect(x0, y, x1 - x0, rowH)
      }
    } else if (rowIdx % 2 === 1) {
      ctx.fillStyle = '#fafafa'; ctx.fillRect(x0, y, x1 - x0, rowH)
    }

    // 열 선택 모드에서는 행 전체 하이라이트 없음 (열 단위 그라데이션은 drawCell에서)
    if (!this.selection.hasColSelection() && this.selection.isRowSelected(rowIdx)) {
      ctx.fillStyle = SELECTED_BG; ctx.fillRect(x0, y, x1 - x0, rowH)
    } else if (rowIdx === this.hoverRow) {
      ctx.fillStyle = HOVER_BG; ctx.fillRect(x0, y, x1 - x0, rowH)
    }

    const ac = this.selection.getActiveCell()
    if (ac && ac.row === rowIdx) {
      const rect = this.getCellRect(rowIdx, ac.col)
      if (rect) {
        ctx.save()
        ctx.strokeStyle = ACTIVE_BORDER; ctx.lineWidth = 2
        ctx.strokeRect(rect.x + 1, rect.y + 1, rect.w - 2, rect.h - 2)
        ctx.restore()
      }
    }
  }

  /* ── Cell Drawing — fillText/fillRect only, stroke 절대 금지 ── */
  private drawCell(row: DataRow, col: ColDef, x: number, y: number, w: number, h: number, rowIdx: number): void {
    const { ctx } = this
    const val = String(row[col.key] ?? '')
    const cid = String(row._cid ?? '')

    // 셀 배경색 (사용자 서식) — fillRect only
    if (col.type === 't' || col.type === 'long' || col.type === 'dropdown') {
      const s = this.styleManager.getStyle(cid, col.key)
      if (s?.bgColor) { ctx.fillStyle = s.bgColor; ctx.fillRect(x, y, w, h) }
    }

    // 열 선택 오버레이
    if (this.selection.hasColSelection()) {
      const visIdx = this.visCols.indexOf(col)
      if (visIdx >= 0 && this.selection.isColSelected(visIdx)) {
        ctx.fillStyle = 'rgba(219,234,254,0.6)'; ctx.fillRect(x, y, w, h)
      }
    }

    // 행 선택 오버레이
    if (!this.selection.hasColSelection() && this.selection.isRowSelected(rowIdx) && col.type !== 'idx') {
      ctx.fillStyle = 'rgba(219,234,254,0.5)'; ctx.fillRect(x, y, w, h)
    }

    const style = (col.type === 't' || col.type === 'long' || col.type === 'dropdown')
      ? this.styleManager.getStyle(cid, col.key) : undefined
    const fontSize = style?.fontSize || 13

    switch (col.type) {
      case 'idx':
        this.drawRowNum(row, x, y, w, h, rowIdx)
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
        this.drawWrappedText(val, x, y, w - 12, h, {
          fontSize, bold: style?.bold, italic: style?.italic,
          color: style?.color, strikethrough: style?.strikethrough,
          singleLine: true,
        })
        // dropdown arrow
        ctx.fillStyle = '#94a3b8'; ctx.font = '10px sans-serif'
        ctx.textBaseline = 'middle'
        ctx.fillText('\u25BE', x + w - 14, y + h / 2)
        ctx.font = FONT
        break
      case 'long':
        this.drawWrappedText(val, x, y, w, h, {
          fontSize, bold: style?.bold, italic: style?.italic,
          color: style?.color || '#334155', strikethrough: style?.strikethrough,
        })
        break
      default: {
        const isKey = KEY_COLS.has(col.key)
        this.drawWrappedText(val, x, y, w, h, {
          fontSize: isKey ? 14 : fontSize,
          bold: style?.bold, italic: style?.italic,
          color: style?.color,
          strikethrough: style?.strikethrough,
          align: style?.align || (isKey ? 'center' : 'left'),
        })
      }
    }
    ctx.font = FONT
  }

  /** Google Sheets style row number cell — 순수 행번호 1,2,3... */
  private drawRowNum(_row: DataRow, x: number, y: number, w: number, h: number, rowIdx: number): void {
    const { ctx } = this
    ctx.fillStyle = this.selection.isRowSelected(rowIdx) ? ROW_NUM_SEL_BG : ROW_NUM_BG
    ctx.fillRect(x, y, w, h)
    ctx.fillStyle = '#555'
    ctx.font = '11px -apple-system,"Segoe UI",sans-serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText(String(rowIdx + 1), x + w / 2, y + h / 2)
    ctx.textAlign = 'left'; ctx.font = FONT
  }

  private drawTruncated(text: string, x: number, y: number, maxW: number): void {
    const { ctx } = this
    if (!text || maxW <= 0) return
    if (ctx.measureText(text).width <= maxW) { ctx.fillText(text, x, y); return }
    let t = text
    while (t.length > 1 && ctx.measureText(t + '\u2026').width > maxW) t = t.slice(0, -1)
    ctx.fillText(t + '\u2026', x, y)
  }

  /**
   * drawWrappedText — 셀 텍스트 렌더링 (fillText만 사용, stroke 절대 금지)
   * CJK(한국어) + 영문 혼합 줄바꿈, 말줄임, 취소선 처리
   */
  private drawWrappedText(
    rawText: string | number | null | undefined,
    cellX: number, cellY: number, cellW: number, cellH: number,
    styleOpts: {
      fontSize?: number; bold?: boolean; italic?: boolean;
      fontFamily?: string; color?: string; align?: string;
      strikethrough?: boolean; singleLine?: boolean
    } = {}
  ): void {
    if (rawText === null || rawText === undefined || rawText === '') return
    let text = String(rawText)
    if (!text.trim()) return

    const { ctx } = this

    // Font setup
    const fs = styleOpts.fontSize || 13
    const fontStr = [
      styleOpts.italic ? 'italic' : '',
      styleOpts.bold ? 'bold' : '',
      fs + 'px',
      styleOpts.fontFamily || '-apple-system,"Segoe UI",sans-serif'
    ].filter(Boolean).join(' ')
    ctx.font = fontStr
    ctx.fillStyle = styleOpts.color || '#1e293b'
    ctx.textBaseline = 'top'

    const PAD = 3
    const maxW = Math.max(1, cellW - PAD * 2)
    const maxH = Math.max(1, cellH - PAD * 2)
    const lineH = Math.ceil(fs * 1.5)
    const forceSingle = !!styleOpts.singleLine
    if (forceSingle) text = text.replace(/[\r\n]+/g, ' ').trim()
    const maxLines = forceSingle ? 1 : Math.max(1, Math.floor(maxH / lineH))

    // Line-building: handles CJK (no spaces) + English (word-level) + mixed
    const buildLines = (t: string): string[] => {
      const paragraphs = t.split(/\r?\n/)
      const result: string[] = []
      for (const para of paragraphs) {
        if (result.length >= maxLines) break
        if (!para) { result.push(''); continue }
        if (ctx.measureText(para).width <= maxW) { result.push(para); continue }
        const hasSpaces = para.includes(' ')
        if (hasSpaces) {
          // English/mixed: word-level wrapping
          const words = para.split(' ')
          let cur = ''
          for (const w of words) {
            const test = cur ? cur + ' ' + w : w
            if (ctx.measureText(test).width > maxW && cur) {
              result.push(cur)
              if (result.length >= maxLines) break
              cur = w
            } else { cur = test }
          }
          if (result.length < maxLines && cur) result.push(cur)
        } else {
          // CJK/no-space: character-level wrapping
          let cur = ''
          for (const ch of para) {
            const test = cur + ch
            if (ctx.measureText(test).width > maxW && cur) {
              result.push(cur)
              if (result.length >= maxLines) break
              cur = ch
            } else { cur = test }
          }
          if (result.length < maxLines && cur) result.push(cur)
        }
      }
      return result
    }

    let lines: string[]

    if (forceSingle) {
      // singleLine 또는 좁은 컬럼: 문자 단위 직접 잘림 + 말줄임 (word-wrap 건너뜀)
      if (ctx.measureText(text).width <= maxW) {
        lines = [text]
      } else {
        let t = text
        while (t.length > 1 && ctx.measureText(t + '\u2026').width > maxW) t = t.slice(0, -1)
        lines = [t + '\u2026']
      }
    } else {
      lines = buildLines(text)

      // Ellipsis for overflow
      if (lines.length > maxLines) {
        lines = lines.slice(0, maxLines)
        let last = lines[maxLines - 1] || ''
        while (last.length > 0 && ctx.measureText(last + '\u2026').width > maxW) last = last.slice(0, -1)
        lines[maxLines - 1] = last + (last ? '\u2026' : '')
      }
    }

    // Alignment
    const align = styleOpts.align || 'left'
    ctx.textAlign = align as CanvasTextAlign
    let baseX: number
    if (align === 'right') baseX = cellX + cellW - PAD
    else if (align === 'center') baseX = cellX + cellW / 2
    else baseX = cellX + PAD

    // Render text — fillText ONLY, no stroke/line/rect, no maxWidth param (avoids browser scaling artifacts)
    for (let i = 0; i < lines.length; i++) {
      const lineY = cellY + PAD + i * lineH
      if (lineY >= cellY + cellH) break
      ctx.fillText(lines[i], baseX, lineY)
    }

    // Strikethrough — only when explicitly requested, uses fillRect (no stroke)
    if (styleOpts.strikethrough === true && lines.length > 0) {
      for (let li = 0; li < lines.length; li++) {
        const strikeY = Math.round(cellY + PAD + li * lineH + fs * 0.55)
        if (strikeY >= cellY + cellH) break
        const textW = Math.min(ctx.measureText(lines[li]).width, maxW)
        const sx = align === 'center' ? cellX + (cellW - textW) / 2
                : align === 'right' ? cellX + cellW - PAD - textW
                : cellX + PAD
        ctx.fillRect(sx, strikeY, textW, 1)
      }
    }

    ctx.textAlign = 'left'
    ctx.textBaseline = 'middle'
  }

  private drawPhoto(row: DataRow, x: number, y: number, w: number, h: number): void {
    const { ctx } = this
    const url = String(row.photoUrl ?? '')
    if (!url) {
      ctx.fillStyle = '#e2e8f0'
      ctx.fillRect(x, y, w, h)
      ctx.fillStyle = '#94a3b8'; ctx.font = '10px sans-serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText('\uD83D\uDCF7', x + w / 2, y + h / 2)
      ctx.font = FONT; ctx.textAlign = 'left'
      return
    }
    const cached = this.photoCache.get(url)
    if (cached) {
      try {
        // object-fit: cover — crop source to fill destination while preserving aspect ratio
        const iw = cached.naturalWidth || cached.width
        const ih = cached.naturalHeight || cached.height
        if (iw > 0 && ih > 0) {
          const scale = Math.max(w / iw, h / ih)
          const sw = w / scale
          const sh = h / scale
          const sx = (iw - sw) / 2
          const sy = (ih - sh) / 2
          ctx.save()
          ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip()
          ctx.drawImage(cached, sx, sy, sw, sh, x, y, w, h)
          ctx.restore()
        } else {
          ctx.drawImage(cached, x, y, w, h)
        }
      } catch { /* */ }
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
    if (!val) {
      ctx.fillStyle = '#d1d5db'
      ctx.font = '11px -apple-system,"Segoe UI",sans-serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText('+ \uD0DC\uADF8', x + w / 2, y + h / 2)
      ctx.font = FONT; ctx.textAlign = 'left'
      return
    }
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
    ctx.save()
    ctx.fillStyle = '#eff6ff'; this.roundRect(bx, by, bw, bh, 4); ctx.fill()
    ctx.strokeStyle = '#93c5fd'; ctx.lineWidth = 1; this.roundRect(bx, by, bw, bh, 4); ctx.stroke()
    ctx.fillStyle = '#2563eb'; ctx.font = '11px -apple-system,"Segoe UI",sans-serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText('\u2709 \uBC1C\uC1A1', bx + bw / 2, by + bh / 2)
    ctx.restore()
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

  /* ── Header (2-row: alphabet + column name) ── */
  private drawHeader(frozenW: number, frozenN: number): void {
    const { ctx, viewW } = this
    // Header background
    ctx.fillStyle = HEADER_BG; ctx.fillRect(0, 0, viewW, HEADER_H)
    // Alphabet row separator line at y=20
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(0, 20.5); ctx.lineTo(viewW, 20.5); ctx.stroke()
    // Header bottom border
    ctx.strokeStyle = HEADER_BORDER; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(0, HEADER_H - 0.5); ctx.lineTo(viewW, HEADER_H - 0.5); ctx.stroke()
    ctx.font = HEADER_FONT; ctx.textBaseline = 'middle'; ctx.fillStyle = '#1e293b'

    ctx.save()
    ctx.beginPath(); ctx.rect(frozenW, 0, viewW - frozenW, HEADER_H); ctx.clip()
    let cx = -this.scrollLeft
    for (let i = 0; i < this.visCols.length; i++) {
      const col = this.visCols[i]
      if (i < frozenN) { cx += col.w; continue }
      this.drawHeaderCell(col, cx, col.w, i); cx += col.w
    }
    ctx.restore()

    if (frozenN > 0) {
      ctx.fillStyle = HEADER_BG; ctx.fillRect(0, 0, frozenW, HEADER_H)
      let fx = 0
      for (let i = 0; i < frozenN; i++) {
        this.drawHeaderCell(this.visCols[i], fx, this.visCols[i].w, i); fx += this.visCols[i].w
      }
      ctx.strokeStyle = FROZEN_SEP; ctx.lineWidth = 2
      ctx.beginPath(); ctx.moveTo(frozenW, 0); ctx.lineTo(frozenW, HEADER_H); ctx.stroke()
    }
  }

  private drawHeaderCell(col: ColDef, x: number, w: number, colIndex: number): void {
    const { ctx } = this
    const nameY = 38  // vertical center of the column-name row (20..56 → center ≈ 38)
    const isColSel = this.selection.isColSelected(colIndex)

    if (col.type === 'idx') {
      // Corner select-all button (Google Sheets style)
      ctx.fillStyle = '#f0f0f2'
      ctx.fillRect(x, 0, w, HEADER_H)
      ctx.strokeStyle = HEADER_BORDER; ctx.lineWidth = 1
      ctx.beginPath(); ctx.moveTo(x + w - 0.5, 4); ctx.lineTo(x + w - 0.5, HEADER_H - 4); ctx.stroke()
      return
    }

    // 열 선택 시 헤더 하이라이트
    if (isColSel) {
      ctx.fillStyle = '#1a73e8'
      ctx.fillRect(x, 0, w, HEADER_H)
    }

    // ── Alphabet row (top 0-20px) ──
    ctx.font = '10px system-ui, -apple-system, sans-serif'
    ctx.fillStyle = isColSel ? '#fff' : '#999'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText(colAlphabet(colIndex), x + w / 2, 10)

    // ── Column name row (20-56px) ──
    ctx.fillStyle = isColSel ? '#fff' : '#1e293b'
    ctx.font = HEADER_FONT
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    this.drawTruncated(col.label, x + w / 2, nameY, w - 24)
    ctx.textAlign = 'left'

    if (col.key === this.sortKey) {
      ctx.fillStyle = isColSel ? '#cce0ff' : SORT_ARROW; ctx.font = '10px sans-serif'; ctx.textAlign = 'right'
      ctx.fillText(this.sortDir === 'asc' ? '\u25B2' : '\u25BC', x + w - 16, nameY)
      ctx.font = HEADER_FONT; ctx.textAlign = 'left'
    }

    if (col.type !== 'photo' && col.type !== 'mail') {
      ctx.fillStyle = isColSel ? 'rgba(255,255,255,0.7)' : '#94a3b8'; ctx.font = '8px sans-serif'; ctx.textAlign = 'right'
      ctx.fillText('\u25BC', x + w - 5, nameY)
      ctx.font = HEADER_FONT; ctx.textAlign = 'left'
    }

    ctx.strokeStyle = isColSel ? 'rgba(255,255,255,0.3)' : HEADER_BORDER; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(x + w - 0.5, 4); ctx.lineTo(x + w - 0.5, HEADER_H - 4); ctx.stroke()
  }
}
