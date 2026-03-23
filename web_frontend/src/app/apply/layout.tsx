import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Apply Now | Bridge',
  description:
    'Apply to teach English in Korea. Submit your application to Bridge for ESL teaching positions across South Korea',
  openGraph: {
    title: 'Apply Now | Bridge',
    description:
      'Apply to teach English in Korea. Submit your application to Bridge for ESL teaching positions across South Korea',
    type: 'website',
  },
}

export default function ApplyLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
