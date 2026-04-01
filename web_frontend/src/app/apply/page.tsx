import { getFormConfig } from '@/lib/form-config-server'
import ApplyForm from './ApplyForm'

export default async function ApplyPage() {
  const config = await getFormConfig('apply')
  return <ApplyForm config={config} />
}
