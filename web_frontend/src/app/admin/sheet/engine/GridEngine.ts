/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Grid Engine v3.1
   Pure Canvas rendering: header, rows, photos, stages, tags
   Ghost-div scrollbar, column resize, DPR scaling
   v3: checkbox, stage dropdown, tag toggle, photo wheel,
       cell styles, filter icons, header context menu
   v3.1: per-row variable heights, drag-to-resize rows
   ═══════════════════════════════════════════════════════ */

import type { ColDef, DataRow, GridCallbacks, CellRef } from './types'
import { HEADER_H, FONT, HEADER_FONT, STAGES, MTAGS } from './types'
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
const CHECKBOX_SIZE = 14
const CHECKBOX_PAD  = 4
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

  private isCheckboxHit(localX: number): boolean {
    return localX < CHECKBOX_SIZE + CHECKBOX_PAD * 2
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

    // Checkbox click in idx column
    if (col && col.type === 'idx' && this.isCheckboxHit(hit.localX)) {
      this.selection.toggleRow(hit.row)
      this.cb.onSelectionChange(this.selection.getSelectedRows())
      this.requestRender()
      return
    }

    // Tag cell click → 팝업으로 위임 (롤선택 방식)
    if (col && col.type === 'tags') {
      const row = this.rows[hit.row]
      if (row) {
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
      if (col && (col.type === 'tags' || col.type === 'mail' || (col.type === 'idx' && this.isCheckboxHit(hit.localX)))) {
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
  private headerHitVisCol(e: MouseEvent): { visCol: number; nearBorder: boolean; localX: number } | null {
    const rect = this.headerHit.getBoundingClientRect()
    const mx = e.clientX - rect.left + this.scrollLeft
    let cx = 0
    for (let i = 0; i < this.visCols.length; i++) {
      cx += this.visCols[i].w
      if (Math.abs(mx - cx) <= RESIZE_ZONE) return { visCol: i, nearBorder: true, localX: mx - (cx - this.visCols[i].w) }
      if (mx < cx) return { visCol: i, nearBorder: false, localX: mx - (cx - this.visCols[i].w) }
    }
    return null
  }

  private onHeaderMouseDown = (e: MouseEvent): void => {
    const hit = this.headerHitVisCol(e)
    if (!hit || !hit.nearBorder) return
    e.preventDefault()
    this.colResizeDrag = { visIdx: hit.visCol, startX: e.clientX, startW: this.visCols[hit.visCol].w }
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

    if (hit.localX > col.w - 18 && col.type !== 'photo' && col.type !== 'mail') {
      const rect = this.headerHit.getBoundingClientRect()
      const cx = this.colX(hit.visCol) - this.scrollLeft
      this.cb.onFilterClick(col.key, rect.left + cx + col.w, rect.top + HEADER_H)
      return
    }

    // 열 헤더 클릭: 전체 행 선택 + active cell을 해당 열로 설정
    // → 이후 색/서식 적용 시 전체 열에 반영됨
    this.selection.selectAll(this.rows.length)
    this.selection.selectCell(0, hit.visCol)
    this.cb.onSelectionChange(this.selection.getSelectedRows())
    this.cb.onSort(col.key)
    this.requestRender()
  }

  private onHeaderContextMenu = (e: MouseEvent): void => {
    e.preventDefault()
    const hit = this.headerHitVisCol(e)
    if (!hit) return
    const col = this.visCols[hit.visCol]
    if (col) this.cb.onHeaderContextMenu(e, col.key)
  }

  private onDocMouseMove = (e: MouseEvent): void => {
    // Column resize drag
    if (this.colResizeDrag) {
      const dx = e.clientX - this.colResizeDrag.startX
      const newW = Math.max(30, this.colResizeDrag.startW + dx)
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
      const newH = Math.max(24, this.rowResizeDrag.startH + dy)
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

  private onDocMouseUp = (): void => {
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

    // ── Scrollable columns (clipped) ──
    ctx.save()
    ctx.beginPath()
    ctx.rect(frozenW, HEADER_H, viewW - frozenW, dataH)
    ctx.clip()
    for (let r = startRow; r < endRow; r++) {
      const rowH = this.getRowH(r)
      const y = HEADER_H + this.rowYs[r] - this.scrollTop
      this.drawRowBg(r, y, frozenW, viewW, rowH)
      let cx = -this.scrollLeft
      for (let c = 0; c < this.visCols.length; c++) {
        const col = this.visCols[c]
        if (c < frozenN) { cx += col.w; continue }
        this.drawCell(this.rows[r], col, cx, y, col.w, rowH, r)
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
        const rowH = this.getRowH(r)
        const y = HEADER_H + this.rowYs[r] - this.scrollTop
        this.drawRowBg(r, y, 0, frozenW, rowH)
        let cx = 0
        for (let c = 0; c < frozenN; c++) {
          const col = this.visCols[c]
          this.drawCell(this.rows[r], col, cx, y, col.w, rowH, r)
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

    this.drawHeader(frozenW, frozenN)
  }

  private drawRowBg(rowIdx: number, y: number, x0: number, x1: number, rowH: number): void {
    const { ctx } = this
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
  private drawCell(row: DataRow, col: ColDef, x: number, y: number, w: number, h: number, rowIdx: number): void {
    const { ctx } = this
    const val = String(row[col.key] ?? '')
    const cid = String(row._cid ?? '')

    if (col.type === 't' || col.type === 'long') {
      const style = this.styleManager.getStyle(cid, col.key)
      if (style?.bgColor) {
        ctx.fillStyle = style.bgColor
        ctx.fillRect(x, y, w, h)
      }
    }

    const style = (col.type === 't' || col.type === 'long') ? this.styleManager.getStyle(cid, col.key) : undefined
    const fontSize = style?.fontSize || 13
    const bold = style?.bold ? 'bold ' : ''
    const italic = style?.italic ? 'italic ' : ''
    const customFont = (style?.fontSize || style?.bold || style?.italic)
      ? `${italic}${bold}${fontSize}px -apple-system,"Segoe UI",sans-serif`
      : FONT

    ctx.font = customFont
    ctx.textBaseline = 'middle'
    const ty = y + h / 2

    switch (col.type) {
      case 'idx':
        this.drawCheckboxCell(row, x, y, w, h, rowIdx)
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
        ctx.fillStyle = style?.color || '#1e293b'
        this.drawTruncated(val, x + 4, ty, w - 20)
        ctx.fillStyle = '#94a3b8'; ctx.font = '10px sans-serif'
        ctx.fillText('\u25BE', x + w - 14, ty); ctx.font = customFont
        break
      case 'long':
        ctx.fillStyle = style?.color || '#334155'
        this.drawWrapped(val, x + 4, y + 4, w - 8, h - 8)
        break
      default:
        if (KEY_COLS.has(col.key)) {
          ctx.font = KEY_COL_FONT
          ctx.fillStyle = style?.color || '#1e293b'
          ctx.textAlign = 'center'
          this.drawTruncated(val, x + w / 2, ty, w - 8)
          ctx.textAlign = 'left'
        } else {
          ctx.fillStyle = style?.color || '#1e293b'
          this.drawTruncated(val, x + 4, ty, w - 8)
        }
    }
    ctx.font = FONT
  }

  private drawCheckboxCell(row: DataRow, x: number, y: number, w: number, h: number, rowIdx: number): void {
    const { ctx } = this
    const isSelected = this.selection.isRowSelected(rowIdx)
    const cbX = x + CHECKBOX_PAD
    const cbY = y + (h - CHECKBOX_SIZE) / 2
    ctx.strokeStyle = isSelected ? '#3b82f6' : '#94a3b8'
    ctx.lineWidth = 1.5
    ctx.strokeRect(cbX, cbY, CHECKBOX_SIZE, CHECKBOX_SIZE)
    if (isSelected) {
      ctx.fillStyle = '#3b82f6'
      ctx.fillRect(cbX, cbY, CHECKBOX_SIZE, CHECKBOX_SIZE)
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(cbX + 3, cbY + CHECKBOX_SIZE / 2)
      ctx.lineTo(cbX + CHECKBOX_SIZE / 2 - 1, cbY + CHECKBOX_SIZE - 3)
      ctx.lineTo(cbX + CHECKBOX_SIZE - 3, cbY + 3)
      ctx.stroke()
    }
    ctx.fillStyle = '#94a3b8'
    ctx.font = '11px -apple-system,"Segoe UI",sans-serif'
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle'
    ctx.fillText(String(row.id), x + w - 4, y + h / 2)
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
    const ps = Math.min(Number(row.photoSize) || 50, Math.min(w, h) - 4)
    if (!url) {
      ctx.fillStyle = '#e2e8f0'
      ctx.fillRect(x + (w - ps) / 2, y + (h - ps) / 2, ps, ps)
      ctx.fillStyle = '#94a3b8'; ctx.font = '10px sans-serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText('\uD83D\uDCF7', x + w / 2, y + h / 2)
      ctx.font = FONT; ctx.textAlign = 'left'
      return
    }
    const cached = this.photoCache.get(url)
    if (cached) {
      try { ctx.drawImage(cached, x + (w - ps) / 2, y + (h - ps) / 2, ps, ps) } catch { /* */ }
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
    ctx.fillStyle = '#eff6ff'; this.roundRect(bx, by, bw, bh, 4); ctx.fill()
    ctx.strokeStyle = '#93c5fd'; ctx.lineWidth = 1; this.roundRect(bx, by, bw, bh, 4); ctx.stroke()
    ctx.fillStyle = '#2563eb'; ctx.font = '11px -apple-system,"Segoe UI",sans-serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText('\u2709 \uBC1C\uC1A1', bx + bw / 2, by + bh / 2)
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

    ctx.save()
    ctx.beginPath(); ctx.rect(frozenW, 0, viewW - frozenW, HEADER_H); ctx.clip()
    let cx = -this.scrollLeft
    for (let i = 0; i < this.visCols.length; i++) {
      const col = this.visCols[i]
      if (i < frozenN) { cx += col.w; continue }
      this.drawHeaderCell(col, cx, col.w); cx += col.w
    }
    ctx.restore()

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

    if (col.type === 'idx') {
      const isAll = this.selection.isAllSelected(this.rows.length)
      const cbX = x + CHECKBOX_PAD
      const cbY = (HEADER_H - CHECKBOX_SIZE) / 2
      ctx.strokeStyle = isAll ? '#3b82f6' : '#94a3b8'
      ctx.lineWidth = 1.5
      ctx.strokeRect(cbX, cbY, CHECKBOX_SIZE, CHECKBOX_SIZE)
      if (isAll) {
        ctx.fillStyle = '#3b82f6'
        ctx.fillRect(cbX, cbY, CHECKBOX_SIZE, CHECKBOX_SIZE)
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(cbX + 3, cbY + CHECKBOX_SIZE / 2)
        ctx.lineTo(cbX + CHECKBOX_SIZE / 2 - 1, cbY + CHECKBOX_SIZE - 3)
        ctx.lineTo(cbX + CHECKBOX_SIZE - 3, cbY + 3)
        ctx.stroke()
      }
      ctx.fillStyle = '#1e293b'; ctx.font = HEADER_FONT
      ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
      ctx.fillText(col.label, cbX + CHECKBOX_SIZE + 3, HEADER_H / 2)
      ctx.strokeStyle = HEADER_BORDER; ctx.lineWidth = 1
      ctx.beginPath(); ctx.moveTo(x + w - 0.5, 4); ctx.lineTo(x + w - 0.5, HEADER_H - 4); ctx.stroke()
      return
    }

    const isKeyCol = KEY_COLS.has(col.key)
    ctx.fillStyle = '#1e293b'
    ctx.font = isKeyCol ? KEY_HEADER_FONT : HEADER_FONT
    ctx.textAlign = isKeyCol ? 'center' : 'left'
    ctx.textBaseline = 'middle'
    this.drawTruncated(col.label, isKeyCol ? x + w / 2 : x + 6, HEADER_H / 2, w - 24)
    ctx.textAlign = 'left'

    if (col.key === this.sortKey) {
      ctx.fillStyle = SORT_ARROW; ctx.font = '10px sans-serif'; ctx.textAlign = 'right'
      ctx.fillText(this.sortDir === 'asc' ? '\u25B2' : '\u25BC', x + w - 16, HEADER_H / 2)
      ctx.font = HEADER_FONT; ctx.textAlign = 'left'
    }

    if (col.type !== 'photo' && col.type !== 'mail') {
      ctx.fillStyle = '#94a3b8'; ctx.font = '8px sans-serif'; ctx.textAlign = 'right'
      ctx.fillText('\u25BC', x + w - 5, HEADER_H / 2)
      ctx.font = HEADER_FONT; ctx.textAlign = 'left'
    }

    ctx.strokeStyle = HEADER_BORDER; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(x + w - 0.5, 4); ctx.lineTo(x + w - 0.5, HEADER_H - 4); ctx.stroke()
  }
}
