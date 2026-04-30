import { createFileRoute } from '@tanstack/react-router'
import { UITestPage } from '@/pages/UITestPage'

export const Route = createFileRoute('/ui-test/')({
  component: UITestPage,
})
