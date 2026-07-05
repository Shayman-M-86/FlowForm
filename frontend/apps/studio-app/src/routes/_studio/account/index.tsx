import { createFileRoute } from '@tanstack/react-router'
import { AccountSettingsPage } from '@/pages/AccountSettingsPage'

export const Route = createFileRoute('/_studio/account/')({
  component: AccountSettingsPage,
})
