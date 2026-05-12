import { createRootRoute, Outlet, useNavigate, useRouterState } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'
import { ProtectedApp } from '@/components/auth/ProtectedApp'
import { StudioSidebar } from '@/components/StudioSidebar'
import { useCurrentUser } from '@/auth/UserContext'
import { useProject } from '@/api/projects'
import { getActiveProjectSlug } from '@/lib/activeProject'

const navRoutes: Record<string, string> = {
  dashboard: '/',
  'projects-all': '/projects',
}

function AppLayout() {
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const ctx = useCurrentUser()

  const projectSlug = pathname.match(/^\/projects\/([^/]+)/)?.[1]
  const activeProjectSlug = projectSlug ? decodeURIComponent(projectSlug) : getActiveProjectSlug()
  const project = useProject(activeProjectSlug)

  const activeItem = pathname === '/'
    ? 'dashboard'
    : pathname.match(/^\/projects\/[^/]+$/)
      ? 'projects-current'
      : pathname.startsWith('/projects')
        ? 'projects-all'
        : undefined

  return (
    <div className="flex min-h-screen bg-sidebar">
      <StudioSidebar
        activeItem={activeItem}
        projectName={project.data?.name ?? activeProjectSlug ?? undefined}
        projectSlug={activeProjectSlug ?? undefined}
        userName={ctx?.displayName}
        userEmail={ctx?.user.email}
        onNavigate={(item) => {
          if (item.id === 'projects-current' && activeProjectSlug) {
            navigate({ to: '/projects/$slug', params: { slug: activeProjectSlug } })
          } else {
            const route = navRoutes[item.id]
            if (route) navigate({ to: route })
          }
        }}
      />
      <main className="flex min-h-screen flex-1 flex-col border-l border-border rounded-l-3xl bg-background shadow-lg">
        <Outlet />
      </main>
    </div>
  )
}

export const Route = createRootRoute({
  component: () => (
    <ProtectedApp>
      <AppLayout />
      <TanStackRouterDevtools />
    </ProtectedApp>
  ),
})
