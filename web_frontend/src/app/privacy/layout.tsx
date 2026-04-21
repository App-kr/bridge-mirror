import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy | BRIDGE Recruitment',
  description: 'BRIDGE Recruitment privacy policy — Korean PIPA compliant, international data protection.',
}

export default function PrivacyLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
