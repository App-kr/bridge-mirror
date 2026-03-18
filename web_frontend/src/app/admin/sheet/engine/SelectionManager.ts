/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Selection Manager
   Tracks selected rows & active cell
   ═══════════════════════════════════════════════════════ */

import type { CellRef } from './types'

export class SelectionManager {
  private selectedRows = new Set<number>()
  private activeCell: CellRef | null = null
  private anchorRow = -1  // for shift+click range

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
