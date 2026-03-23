import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Contact Us | Bridge',
  description:
    'Contact Bridge for ESL teacher recruitment inquiries. We connect schools in Korea with qualified English teachers',
  openGraph: {
    title: 'Contact Us | Bridge',
    description:
      'Contact Bridge for ESL teacher recruitment inquiries. We connect schools in Korea with qualified English teachers',
    type: 'website',
  },
}

export default function InquiryLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
