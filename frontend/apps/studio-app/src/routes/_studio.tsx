import { createFileRoute, Outlet } from '@tanstack/react-router'
import { ProtectedApp } from '@/app/ProtectedApp'
import { StudioSidebar } from '@/components/StudioSidebar'
import { useRenderDebug } from '@/debug/useRenderDebug'

function StudioLayout() {
  useRenderDebug('StudioLayout')
  return (
    <div className="app-shell flex min-h-screen bg-sidebar">
      <StudioSidebar />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}

export const Route = createFileRoute('/_studio')({
  component: () => (
    <ProtectedApp>
      <StudioLayout />
    </ProtectedApp>
  ),
})
