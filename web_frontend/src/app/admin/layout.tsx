"use client"

import { useEffect } from "react"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === "PrintScreen" ||
        (e.metaKey && e.shiftKey && (e.key === "3" || e.key === "4" || e.key === "5")) ||
        e.key === "F12" ||
        (e.ctrlKey && e.shiftKey && e.key === "I")
      ) {
        e.preventDefault()
        document.body.style.filter = "brightness(0)"
        setTimeout(() => { document.body.style.filter = "" }, 3000)
      }
    }

    const handleBlur = () => {
      document.body.style.filter = "brightness(0)"
    }

    const handleFocus = () => {
      document.body.style.filter = ""
    }

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault()
    }

    const handleCopy = (e: ClipboardEvent) => {
      e.preventDefault()
    }

    const handleVisibility = () => {
      if (document.visibilityState === "hidden") {
        document.body.style.filter = "brightness(0)"
      } else {
        setTimeout(() => { document.body.style.filter = "" }, 1000)
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    document.addEventListener("keyup", handleKeyDown)
    window.addEventListener("blur", handleBlur)
    window.addEventListener("focus", handleFocus)
    document.addEventListener("contextmenu", handleContextMenu)
    document.addEventListener("copy", handleCopy)
    document.addEventListener("visibilitychange", handleVisibility)

    const style = document.createElement("style")
    style.textContent = `
      @media print {
        body * { display: none !important; }
        body::after {
          content: 'CONFIDENTIAL - Printing is not allowed';
          display: block;
          font-size: 48px;
          text-align: center;
          padding-top: 200px;
        }
      }
    `
    document.head.appendChild(style)

    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.removeEventListener("keyup", handleKeyDown)
      window.removeEventListener("blur", handleBlur)
      window.removeEventListener("focus", handleFocus)
      document.removeEventListener("contextmenu", handleContextMenu)
      document.removeEventListener("copy", handleCopy)
      document.removeEventListener("visibilitychange", handleVisibility)
      document.head.removeChild(style)
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
