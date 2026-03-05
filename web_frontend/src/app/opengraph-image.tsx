import { ImageResponse } from 'next/og'

export const alt = 'BRIDGE — ESL Teaching Jobs in Korea'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)',
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 80,
            height: 80,
            borderRadius: 20,
            background: '#fff',
            marginBottom: 32,
          }}
        >
          <span style={{ fontSize: 48, fontWeight: 800, color: '#1d1d1f' }}>B</span>
        </div>
        <h1 style={{ fontSize: 64, fontWeight: 700, color: '#fff', margin: 0, letterSpacing: '-0.02em' }}>
          BRIDGE
        </h1>
        <p style={{ fontSize: 28, color: 'rgba(255,255,255,0.6)', margin: '16px 0 0', fontWeight: 400 }}>
          ESL Teaching Jobs in Korea
        </p>
        <div
          style={{
            display: 'flex',
            gap: 16,
            marginTop: 40,
          }}
        >
          <span style={{ fontSize: 16, color: 'rgba(255,255,255,0.4)', padding: '8px 20px', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 20 }}>
            bridgejob.co.kr
          </span>
        </div>
      </div>
    ),
    { ...size },
  )
}
