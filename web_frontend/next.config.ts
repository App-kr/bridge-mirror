import type { NextConfig } from 'next'

const securityHeaders = [
  { key: 'X-Content-Type-Options',    value: 'nosniff' },
  { key: 'X-Frame-Options',           value: 'DENY' },
  // X-XSS-Protection deprecated (OWASP 2025) — disabled, CSP takes over
  { key: 'X-XSS-Protection',          value: '0' },
  { key: 'Referrer-Policy',           value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy',        value: 'camera=(), microphone=(), geolocation=(), payment=()' },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload',
  },
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      // unsafe-inline retained for Next.js hydration (nonce upgrade = future)
      "script-src 'self' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com",
      // supabase 제거됨 (f5bd33e) — AWS S3 + Render 전용
      "img-src 'self' data: blob: https://*.amazonaws.com https://*.gstatic.com",
      "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com",
      "connect-src 'self' https://bridgejob.co.kr https://www.bridgejob.co.kr https://*.vercel.app https://*.onrender.com https://*.amazonaws.com",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; '),
  },
]

const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '*.amazonaws.com' },
    ],
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin',  value: 'https://bridgejob.co.kr' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,POST,OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'Content-Type' },
        ],
      },
    ]
  },
}

export default nextConfig
