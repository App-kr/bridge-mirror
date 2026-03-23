import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'About Bridge | Bridge',
  description:
    'ESL teacher recruitment agency connecting qualified English teachers with schools in Korea',
  openGraph: {
    title: 'About Bridge | Bridge',
    description:
      'ESL teacher recruitment agency connecting qualified English teachers with schools in Korea',
    type: 'website',
  },
}

export default function AboutLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
