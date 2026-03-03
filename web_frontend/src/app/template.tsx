'use client'

/**
 * Page transition wrapper — wraps every route change with a subtle fade+slide.
 * Next.js `template.tsx` re-mounts on navigation (unlike layout.tsx).
 */

import { motion } from 'framer-motion'
import MegaMenu from '@/components/MegaMenu'

export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <>
      <MegaMenu />
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
