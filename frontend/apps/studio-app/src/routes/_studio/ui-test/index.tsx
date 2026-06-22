import { createFileRoute } from '@tanstack/react-router'
import { UITestPage } from '@/pages/UITestPage'

export const Route = createFileRoute('/_studio/ui-test/')({
  component: UITestPage,
})
