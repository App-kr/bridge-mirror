import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Teaching Jobs in Korea | Bridge',
  description:
    'Browse ESL teaching positions in South Korea. Find English teaching jobs at schools, academies, and universities',
  openGraph: {
    title: 'Teaching Jobs in Korea | Bridge',
    description:
      'Browse ESL teaching positions in South Korea. Find English teaching jobs at schools, academies, and universities',
    type: 'website',
  },
}

export default function JobsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
