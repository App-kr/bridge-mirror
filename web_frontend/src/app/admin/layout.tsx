"use client"

import { useEffect } from "react"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const blackout = () => { document.body.style.filter = "brightness(0)" }
    const restore = () => { document.body.style.filter = "" }

    const onKey = (e: KeyboardEvent) => {
      if (
        e.key === "PrintScreen" ||
        (e.metaKey && e.shiftKey && ["3", "4", "5"].includes(e.key)) ||
        (e.ctrlKey && e.key === "p")
      ) {
        e.preventDefault()
        blackout()
        setTimeout(restore, 3000)
      }
    }

    const onBlur = () => blackout()
    const onFocus = () => restore()

    const onVisibility = () => {
      if (document.visibilityState === "hidden") blackout()
      else setTimeout(restore, 1000)
    }

    const onContext = (e: MouseEvent) => e.preventDefault()
    const onCopy = (e: ClipboardEvent) => e.preventDefault()

    const printCSS = document.createElement("style")
    printCSS.id = "admin-print-block"
    printCSS.textContent = `
      @media print {
        body * { display: none !important; }
        body::after {
          content: 'CONFIDENTIAL - Printing is not allowed';
          display: block; font-size: 48px; text-align: center; padding-top: 200px;
        }
      }
    `
    document.head.appendChild(printCSS)

    document.addEventListener("keydown", onKey)
    document.addEventListener("keyup", onKey)
    window.addEventListener("blur", onBlur)
    window.addEventListener("focus", onFocus)
    document.addEventListener("visibilitychange", onVisibility)
    document.addEventListener("contextmenu", onContext)
    document.addEventListener("copy", onCopy)

    return () => {
      document.removeEventListener("keydown", onKey)
      document.removeEventListener("keyup", onKey)
      window.removeEventListener("blur", onBlur)
      window.removeEventListener("focus", onFocus)
      document.removeEventListener("visibilitychange", onVisibility)
      document.removeEventListener("contextmenu", onContext)
      document.removeEventListener("copy", onCopy)
      const el = document.getElementById("admin-print-block")
      if (el) document.head.removeChild(el)
      restore()
    }
  }, [])

  return (
    <div
      className="min-h-screen bg-[#f5f5f7]"
      style={{
        WebkitUserSelect: "none",
        userSelect: "none",
        WebkitTouchCallout: "none",
      }}
    >
      <div className="max-w-7xl mx-auto px-4 py-6">
        {children}
      </div>
    </div>
  )
}
