import { getFormConfig } from '@/lib/form-config-server'
import InquiryForm from './InquiryForm'

export default async function InquiryPage() {
  const config = await getFormConfig('inquiry')
  return <InquiryForm config={config} />
}
