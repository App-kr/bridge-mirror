/**
 * securityGuard.ts — Frontend security monitoring
 *
 * Detects XSS, SQL injection, bot behavior.
 * Reports threats to /api/security/report.
 */

import { API_URL } from '@/lib/api'

const API = API_URL

// ── Types ──────────────────────────────────────────────────────────────────

export interface SecurityEvent {
  type: 'xss' | 'sqli' | 'bot' | 'devtools' | 'tampering'
  detail: string
  url: string
  timestamp: string
  userAgent: string
}

interface CheckResult {
  safe: boolean
  threat?: string
}

// ── Patterns ───────────────────────────────────────────────────────────────

const XSS_PATTERNS = [
  /<script\b/i,
  /javascript\s*:/i,
  /on[a-z]{3,}=/i,
  /\beval\s*\(/i,
  /document\.cookie/i,
  /document\.write/i,
  /\.innerHTML\s*=/i,
  /fromCharCode/i,
  /String\.raw/i,
]

const SQLI_PATTERNS = [
  /UNION\s+SELECT/i,
  /DROP\s+TABLE/i,
  /OR\s+1\s*=\s*1/i,
  /'\s*;\s*--/,
  /INSERT\s+INTO/i,
  /DELETE\s+FROM/i,
  /UPDATE\s+.*\s+SET/i,
  /EXEC\s*\(/i,
  /xp_cmdshell/i,
  /SLEEP\s*\(\s*\d/i,
  /BENCHMARK\s*\(/i,
]

// ── Report queue (debounce) ────────────────────────────────────────────────

const _reportQueue: SecurityEvent[] = []
let _reportTimer: ReturnType<typeof setTimeout> | null = null

export function reportThreat(event: SecurityEvent): void {
  _reportQueue.push(event)
  if (_reportTimer) return
  _reportTimer = setTimeout(async () => {
    const batch = _reportQueue.splice(0, 10)
    _reportTimer = null
    for (const evt of batch) {
      try {
        await fetch(`${API}/api/security/report`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(evt),
        })
      } catch { /* non-blocking */ }
    }
  }, 2000)
}

function _makeEvent(
  type: SecurityEvent['type'],
  detail: string,
): SecurityEvent {
  return {
    type,
    detail: detail.slice(0, 500),
    url: typeof window !== 'undefined' ? window.location.href : '',
    timestamp: new Date().toISOString(),
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
  }
}

// ── Input validation ───────────────────────────────────────────────────────

export function checkInput(value: string): CheckResult {
  if (!value || value.length < 3) return { safe: true }

  for (const pat of XSS_PATTERNS) {
    if (pat.test(value)) {
      return { safe: false, threat: 'xss' }
    }
  }

  for (const pat of SQLI_PATTERNS) {
    if (pat.test(value)) {
      return { safe: false, threat: 'sqli' }
    }
  }

  return { safe: true }
}

// ── URL parameter scanning ─────────────────────────────────────────────────

function _scanUrlParams(): void {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams(window.location.search)
  params.forEach((value, key) => {
    const result = checkInput(value)
    if (!result.safe) {
      reportThreat(_makeEvent(
        result.threat as SecurityEvent['type'],
        `URL param "${key}": ${value.slice(0, 200)}`,
      ))
    }
    const keyResult = checkInput(key)
    if (!keyResult.safe) {
      reportThreat(_makeEvent(
        keyResult.threat as SecurityEvent['type'],
        `URL param key: ${key.slice(0, 200)}`,
      ))
    }
  })
}

// ── Bot detection ──────────────────────────────────────────────────────────

const _formSubmitTimes: number[] = []

export function trackFormSubmit(): void {
  const now = Date.now()
  _formSubmitTimes.push(now)
  // Keep last 10
  if (_formSubmitTimes.length > 10) _formSubmitTimes.shift()

  // 3+ submissions in 10 seconds → bot
  const recent = _formSubmitTimes.filter((t) => now - t < 10000)
  if (recent.length >= 3) {
    reportThreat(_makeEvent('bot', `Rapid form submissions: ${recent.length} in 10s`))
  }
}

// ── Init ───────────────────────────────────────────────────────────────────

let _initialized = false

export function initSecurityGuard(): void {
  if (_initialized || typeof window === 'undefined') return
  _initialized = true

  // Scan URL params on load
  _scanUrlParams()

  // Listen for URL changes (SPA navigation)
  const origPushState = history.pushState.bind(history)
  history.pushState = function (...args: Parameters<typeof history.pushState>) {
    origPushState(...args)
    setTimeout(_scanUrlParams, 100)
  }
}
