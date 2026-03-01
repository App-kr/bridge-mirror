/**
 * Hook: scroll-progress-based transforms for parallax effects
 * Wraps Framer Motion's useScroll + useTransform
 */

'use client'

import { useRef } from 'react'
import { useScroll, useTransform, type MotionValue } from 'framer-motion'

interface ScrollProgressResult {
  ref: React.RefObject<HTMLElement | null>
  scrollYProgress: MotionValue<number>
  opacity: MotionValue<number>
  y: MotionValue<string>
  scale: MotionValue<number>
}

/**
 * Returns scroll-linked opacity, y-translate, and scale values for a ref element.
 * @param fadeRange   - scrollYProgress range where opacity goes 1→0 (default [0, 0.5])
 * @param yRange      - translateY range in percent strings (default ['0%', '30%'])
 */
export function useScrollProgress(
  fadeRange: [number, number] = [0, 0.5],
  yRange: [string, string] = ['0%', '30%'],
): ScrollProgressResult {
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start'],
  })

  const opacity = useTransform(scrollYProgress, fadeRange, [1, 0])
  const y = useTransform(scrollYProgress, [0, 1], yRange)
  const scale = useTransform(scrollYProgress, [0, 1], [1, 1.1])

  return { ref, scrollYProgress, opacity, y, scale }
}
