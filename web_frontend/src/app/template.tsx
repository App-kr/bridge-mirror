'use client'

/**
 * Page transition wrapper — wraps every route change with a subtle fade+slide.
 * Next.js `template.tsx` re-mounts on navigation (unlike layout.tsx).
 */

import { useEffect } from 'react'
import { motion } from 'framer-motion'
import MegaMenu from '@/components/MegaMenu'
import EditModeBar from '@/components/EditModeBar'
import { initSecurityGuard } from '@/utils/securityGuard'

export default function Template({ children }: { children: React.ReactNode }) {
  useEffect(() => { initSecurityGuard() }, [])

  return (
    <>
      <MegaMenu />
      <EditModeBar />
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
      >
        {children}
      </motion.div>
    </>
  )
}
