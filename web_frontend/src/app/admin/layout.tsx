"use client"

import { useEffect, useRef } from "react"
import AdminSidebar from "@/components/admin/AdminSidebar"
import { useAdminAuth } from "@/hooks/useAdminAuth"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { authed } = useAdminAuth()
  const overlayRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    document.body.style.filter = ""
  }, [])

  // Admin capture prevention
  useEffect(() => {
    if (!authed) return

    // Black overlay helper
    function showBlackScreen() {
      if (overlayRef.current) return
      const el = document.createElement("div")
      el.id = "admin-capture-shield"
      Object.assign(el.style, {
        position: "fixed", inset: "0", zIndex: "999999",
        background: "#000", opacity: "1",
      })
      document.body.appendChild(el)
      overlayRef.current = el
    }
    function hideBlackScreen() {
      if (overlayRef.current) {
        overlayRef.current.remove()
        overlayRef.current = null
      }
    }

    // 1. PrintScreen + print shortcut block
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "PrintScreen") {
        e.preventDefault()
        showBlackScreen()
        setTimeout(hideBlackScreen, 1500)
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "p") {
        e.preventDefault()
      }
    }

    // 2. Window blur → black screen (screen capture tools)
    function onBlur() { showBlackScreen() }
    function onFocus() { hideBlackScreen() }

    // 3. Visibility change (mobile tab switch)
    function onVisibility() {
      if (document.visibilityState === "hidden") showBlackScreen()
      else hideBlackScreen()
    }

    // 4. Right-click block
    function onContext(e: MouseEvent) { e.preventDefault() }

    // 5. Copy block
    function onCopy(e: ClipboardEvent) { e.preventDefault() }

    // 6. Print block via CSS
    const style = document.createElement("style")
    style.id = "admin-print-block"
    style.textContent = "@media print { body { display: none !important; } }"
    document.head.appendChild(style)

    window.addEventListener("keydown", onKeyDown)
    window.addEventListener("blur", onBlur)
    window.addEventListener("focus", onFocus)
    document.addEventListener("visibilitychange", onVisibility)
    document.addEventListener("contextmenu", onContext)
    document.addEventListener("copy", onCopy)

    return () => {
      window.removeEventListener("keydown", onKeyDown)
      window.removeEventListener("blur", onBlur)
      window.removeEventListener("focus", onFocus)
      document.removeEventListener("visibilitychange", onVisibility)
      document.removeEventListener("contextmenu", onContext)
      document.removeEventListener("copy", onCopy)
      style.remove()
      hideBlackScreen()
    }
  }, [authed])

  if (!authed) {
    return (
      <div className="min-h-screen bg-[#f5f5f7]">
        <div className="max-w-6xl mx-auto px-4 py-6">
          {children}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#f5f5f7] flex">
      <AdminSidebar />
      <main className="flex-1 min-w-0">
        <div className="max-w-6xl mx-auto px-4 lg:px-8 py-6 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  )
}
