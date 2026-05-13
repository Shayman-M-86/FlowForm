import { useParams, Link, useRouterState, useNavigate } from '@tanstack/react-router'
import { useProject } from '@/api/projects'
import { Spinner, Card } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'
import { SurveysTab } from './ProjectDashboardTabPages/SurveysTab'
import { MembersTab } from './ProjectDashboardTabPages/MembersTab'
import { RolesTab } from './ProjectDashboardTabPages/RolesTab'
import { ManagementTab } from './ProjectDashboardTabPages/ManagementTab'

const TABS = [
  { id: 'surveys',    label: 'Surveys' },
  { id: 'members',    label: 'Members' },
  { id: 'roles',      label: 'Roles' },
  { id: 'settings', label: 'Settings' },
] as const

type DashboardTab = typeof TABS[number]['id']

export function ProjectDashboardPage() {
  const { slug } = useParams({ strict: false })
  const { data: project, isPending, isError, error } = useProject(slug ?? null)
  const navigate = useNavigate()

  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const activeTab: DashboardTab =
    (TABS.find((t) => pathname.endsWith(`/${t.id}`))?.id ?? 'surveys') as DashboardTab

  if (isPending) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center">
        <Spinner size={28} />
      </div>
    )
  }

  if (isError) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <Card tone="muted">
          <p className="text-sm text-destructive">{error.message}</p>
        </Card>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Breadcrumb segments={[
        { label: 'Projects', to: '/projects' },
        { label: project.name, current: true },
      ]} />
      <div className="mt-3 flex items-center justify-between gap-4">
        <h1>{project.name}</h1>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{project.slug}</p>

      {/* Tab nav */}
      <div className="mt-6 flex items-stretch gap-0 overflow-x-auto scrollbar-none">
        {TABS.map((tab, i) => {
          const isActive = tab.id === activeTab
          return (
            <div key={tab.id} className="relative flex items-center">
              {i > 0 && (
                <div aria-hidden className="my-2 w-px self-stretch bg-border" />
              )}
              <Link
                to={`/projects/$slug/${tab.id}`}
                params={{ slug: slug ?? '' }}
                className={`ui-button-ghost h-full whitespace-nowrap border-0 px-4 py-2 text-sm font-medium ${isActive ? 'text-foreground' : 'text-muted-foreground'}`}
              >
                {tab.label}
              </Link>
              <span aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-2.5 overflow-hidden">
                <span className={`absolute inset-x-0 -bottom-px h-1 rounded-full bg-primary transition-transform duration-140 ease-out will-change-transform ${isActive ? 'translate-y-0' : 'translate-y-2'}`} />
              </span>
            </div>
          )
        })}
      </div>
      <div className="h-px bg-border" />

      <div className="mt-6">
        {activeTab === 'surveys'    && <SurveysTab projectSlug={slug ?? ''} />}
        {activeTab === 'members'    && <MembersTab />}
        {activeTab === 'roles'      && <RolesTab />}
        {activeTab === 'settings'   && <ManagementTab customRoles={[]} onAddRole={() => navigate({ to: '/projects/$slug/roles', params: { slug: slug ?? '' } })} />}
      </div>
    </main>
  )
}
