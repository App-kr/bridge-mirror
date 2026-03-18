/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Edit Manager
   Handles inline cell editing via HTML overlay
   ═══════════════════════════════════════════════════════ */

import type { ColType } from './types'

export interface EditResult {
  value: string
  committed: boolean
}

export class EditManager {
  private container: HTMLDivElement
  private overlay: HTMLElement | null = null
  private currentResolve: ((r: EditResult) => void) | null = null
  private editing = false

  constructor(container: HTMLDivElement) {
    this.container = container
  }

  isEditing(): boolean {
    return this.editing
  }

  /** Start inline edit — returns a Promise that resolves when editing completes */
  startEdit(
    rect: { x: number; y: number; w: number; h: number },
    colType: ColType,
    value: string,
    opts?: string[],
  ): Promise<EditResult> {
    this.cancelEdit()

    return new Promise<EditResult>((resolve) => {
      this.currentResolve = resolve
      this.editing = true

      if (colType === 'dropdown' && opts && opts.length > 0) {
        this.createDropdown(rect, value, opts)
      } else if (colType === 'long') {
        this.createTextarea(rect, value)
      } else {
        this.createInput(rect, value)
      }
    })
  }

  private createInput(rect: { x: number; y: number; w: number; h: number }, value: string): void {
    const el = document.createElement('input')
    el.type = 'text'
    el.value = value
    el.style.cssText = `
      position:absolute;
      left:${rect.x}px;top:${rect.y}px;
      width:${rect.w}px;height:${rect.h}px;
      border:2px solid #3b82f6;outline:none;
      font:13px -apple-system,"Segoe UI",sans-serif;
      padding:0 4px;box-sizing:border-box;
      background:#fff;z-index:10;
    `
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); this.commit(el.value) }
      if (e.key === 'Escape') { e.preventDefault(); this.cancelEdit() }
      if (e.key === 'Tab') { e.preventDefault(); this.commit(el.value) }
    })
    el.addEventListener('blur', () => {
      setTimeout(() => { if (this.overlay === el) this.commit(el.value) }, 100)
    })
    this.container.appendChild(el)
    this.overlay = el
    requestAnimationFrame(() => { el.focus(); el.select() })
  }

  private createTextarea(rect: { x: number; y: number; w: number; h: number }, value: string): void {
    const el = document.createElement('textarea')
    el.value = value
    const h = Math.max(rect.h, 80)
    el.style.cssText = `
      position:absolute;
      left:${rect.x}px;top:${rect.y}px;
      width:${Math.max(rect.w, 200)}px;height:${h}px;
      border:2px solid #3b82f6;outline:none;
      font:13px -apple-system,"Segoe UI",sans-serif;
      padding:4px;box-sizing:border-box;resize:both;
      background:#fff;z-index:10;
    `
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.preventDefault(); this.cancelEdit() }
      if (e.key === 'Enter' && e.ctrlKey) { e.preventDefault(); this.commit(el.value) }
    })
    el.addEventListener('blur', () => {
      setTimeout(() => { if (this.overlay === el) this.commit(el.value) }, 100)
    })
    this.container.appendChild(el)
    this.overlay = el
    requestAnimationFrame(() => { el.focus(); el.setSelectionRange(el.value.length, el.value.length) })
  }

  private createDropdown(
    rect: { x: number; y: number; w: number; h: number },
    value: string,
    opts: string[],
  ): void {
    const el = document.createElement('select')
    el.style.cssText = `
      position:absolute;
      left:${rect.x}px;top:${rect.y}px;
      width:${Math.max(rect.w, 120)}px;height:${rect.h}px;
      border:2px solid #3b82f6;outline:none;
      font:13px -apple-system,"Segoe UI",sans-serif;
      background:#fff;z-index:10;
    `
    // Empty option
    const emptyOpt = document.createElement('option')
    emptyOpt.value = ''
    emptyOpt.textContent = '—'
    el.appendChild(emptyOpt)

    for (const o of opts) {
      const opt = document.createElement('option')
      opt.value = o
      opt.textContent = o
      if (o === value) opt.selected = true
      el.appendChild(opt)
    }
    el.addEventListener('change', () => this.commit(el.value))
    el.addEventListener('blur', () => {
      setTimeout(() => { if (this.overlay === el) this.commit(el.value) }, 100)
    })
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.preventDefault(); this.cancelEdit() }
    })
    this.container.appendChild(el)
    this.overlay = el
    requestAnimationFrame(() => el.focus())
  }

  private commit(value: string): void {
    if (!this.editing) return
    this.editing = false
    this.destroyOverlay()
    this.currentResolve?.({ value, committed: true })
    this.currentResolve = null
  }

  cancelEdit(): void {
    if (!this.editing) return
    this.editing = false
    this.destroyOverlay()
    this.currentResolve?.({ value: '', committed: false })
    this.currentResolve = null
  }

  private destroyOverlay(): void {
    if (this.overlay && this.overlay.parentNode) {
      this.overlay.parentNode.removeChild(this.overlay)
    }
    this.overlay = null
  }

  destroy(): void {
    this.cancelEdit()
  }
}
