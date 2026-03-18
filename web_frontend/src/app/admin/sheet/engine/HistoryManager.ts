/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — History Manager
   Undo/Redo stack with configurable depth
   ═══════════════════════════════════════════════════════ */

export class HistoryManager<T> {
  private undoStack: T[] = []
  private redoStack: T[] = []
  private maxDepth: number

  constructor(maxDepth = 20) {
    this.maxDepth = maxDepth
  }

  push(snapshot: T): void {
    this.undoStack.push(snapshot)
    if (this.undoStack.length > this.maxDepth) {
      this.undoStack.shift()
    }
    this.redoStack = []
  }

  undo(current: T): T | null {
    const prev = this.undoStack.pop()
    if (!prev) return null
    this.redoStack.push(current)
    return prev
  }

  redo(current: T): T | null {
    const next = this.redoStack.pop()
    if (!next) return null
    this.undoStack.push(current)
    return next
  }

  get canUndo(): boolean {
    return this.undoStack.length > 0
  }

  get canRedo(): boolean {
    return this.redoStack.length > 0
  }

  clear(): void {
    this.undoStack = []
    this.redoStack = []
  }
}
