/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Selection Manager
   Tracks selected rows & active cell
   ═══════════════════════════════════════════════════════ */

import type { CellRef } from './types'

export class SelectionManager {
  private selectedRows = new Set<number>()
  private activeCell: CellRef | null = null
  private anchorRow = -1  // for shift+click range
  selectedCols = new Set<number>()

  /** Single cell selection */
  selectCell(row: number, col: number): void {
    this.activeCell = { row, col }
  }

  /** Row selection with modifier keys */
  selectRow(row: number, ctrl: boolean, shift: boolean): void {
    if (shift && this.anchorRow >= 0) {
      // Range select
      const lo = Math.min(this.anchorRow, row)
      const hi = Math.max(this.anchorRow, row)
      if (!ctrl) this.selectedRows.clear()
      for (let i = lo; i <= hi; i++) this.selectedRows.add(i)
    } else if (ctrl) {
      // Toggle
      if (this.selectedRows.has(row)) this.selectedRows.delete(row)
      else this.selectedRows.add(row)
      this.anchorRow = row
    } else {
      // Single
      this.selectedRows.clear()
      this.selectedRows.add(row)
      this.anchorRow = row
    }
  }

  clearSelection(): void {
    this.selectedRows.clear()
    this.selectedCols.clear()
    this.activeCell = null
    this.anchorRow = -1
  }

  isRowSelected(row: number): boolean {
    return this.selectedRows.has(row)
  }

  isActiveCell(row: number, col: number): boolean {
    return this.activeCell?.row === row && this.activeCell?.col === col
  }

  getSelectedRows(): Set<number> {
    return new Set(this.selectedRows)
  }

  getActiveCell(): CellRef | null {
    return this.activeCell
  }

  getSelectedCount(): number {
    return this.selectedRows.size
  }

  /** Select all rows */
  selectAll(count: number): void {
    this.selectedRows.clear()
    for (let i = 0; i < count; i++) this.selectedRows.add(i)
    this.anchorRow = 0
  }

  /** Check if all rows are selected */
  isAllSelected(count: number): boolean {
    return count > 0 && this.selectedRows.size === count
  }

  /** Toggle a single row (for checkbox click) */
  toggleRow(row: number): void {
    if (this.selectedRows.has(row)) this.selectedRows.delete(row)
    else this.selectedRows.add(row)
    this.anchorRow = row
  }

  /** Select an entire column (alphabet header click) */
  selectColumn(colIndex: number, rowCount: number): void {
    this.selectedRows.clear()
    for (let i = 0; i < rowCount; i++) this.selectedRows.add(i)
    this.selectedCols = new Set([colIndex])
    this.activeCell = { row: 0, col: colIndex }
    this.anchorRow = 0
  }

  /** Move active cell with keyboard arrows */
  moveActive(dr: number, dc: number, maxRow: number, maxCol: number): void {
    if (!this.activeCell) {
      this.activeCell = { row: 0, col: 0 }
      return
    }
    const nr = Math.max(0, Math.min(maxRow - 1, this.activeCell.row + dr))
    const nc = Math.max(0, Math.min(maxCol - 1, this.activeCell.col + dc))
    this.activeCell = { row: nr, col: nc }
    this.selectedRows.clear()
    this.selectedRows.add(nr)
    this.anchorRow = nr
  }
}
