import type { Metadata } from 'next'
import TermsClient from './TermsClient'

export const metadata: Metadata = {
  title: 'Terms of Use | BRIDGE Recruitment',
  description: 'BRIDGE Recruitment terms of use — service guidelines for teachers and employers.',
}

export default function TermsPage() {
  return <TermsClient />
}
