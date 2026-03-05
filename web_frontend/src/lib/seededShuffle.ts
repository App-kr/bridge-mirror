/**
 * Deterministic shuffle using Linear Congruential Generator (LCG).
 * Same seed always produces the same order.
 */
export function seededShuffle<T>(array: T[], seed: number): T[] {
  const shuffled = [...array]
  let s = seed
  for (let i = shuffled.length - 1; i > 0; i--) {
    s = (s * 16807 + 0) % 2147483647
    const j = s % (i + 1)
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  return shuffled
}
