import { createFileRoute, Outlet, useRouterState, useNavigate } from '@tanstack/react-router'
import { Button, TabSelector } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'
import { useProject } from '@/api/projects'
import { useSurvey } from '@/api/surveys'
import { useRenderDebug } from '@/debug/useRenderDebug'

const TABS = [
  { id: 'overview',  label: 'Overview' },
  { id: 'builder',   label: 'Builder' },
  { id: 'versions',  label: 'Versions' },
  { id: 'members',   label: 'Members' },
  { id: 'roles',     label: 'Roles' },
  { id: 'links',     label: 'Links' },
  { id: 'responses', label: 'Responses' },
  { id: 'settings',  label: 'Settings' },
] as const

type TabId = typeof TABS[number]['id']

function SurveyLayout() {
  useRenderDebug('SurveyLayout')
  const { slug, surveySlug } = Route.useParams()
  const { data: project } = useProject(slug)
  const { data: survey } = useSurvey(slug, surveySlug)
  const navigate = useNavigate()

  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const activeTab: TabId = (TABS.find((t) => pathname.endsWith(`/${t.id}`))?.id ?? 'overview') as TabId
  const isBuilderTab = activeTab === 'builder'

  const projectLabel = project?.name ?? slug
  const surveyTitle = survey?.title ?? surveySlug.replace(/-/g, ' ')

  return (
    <main className={isBuilderTab ? 'page-main page-main-builder' : 'page-main'}>
      <div className={isBuilderTab ? 'px-6 pt-14 md:px-16' : undefined}>
        <Breadcrumb segments={[
          { label: 'Projects', to: '/projects' },
          { label: projectLabel, to: `/projects/${slug}` },
          { label: 'Surveys', to: `/projects/${slug}/surveys` },
          { label: surveyTitle, current: true },
        ]} />

        <div className="flex min-h-34 flex-col justify-between">
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h2 className="leading-tight">{surveyTitle}</h2>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Button variant="secondary" size="sm" className='[--ui-color:var(--accent)]'>Preview</Button>
            </div>
          </div>
          <TabSelector
            items={TABS.map((t) => ({ id: t.id, label: t.label }))}
            activeId={activeTab}
            onChange={(id) => navigate({ to: `/projects/${slug}/surveys/${surveySlug}/${id}` as any })}
          />
        </div>
      </div>

      <div className={isBuilderTab ? 'mt-0' : 'mt-6'}><Outlet /></div>
    </main>
  )
}

export const Route = createFileRoute('/projects/$slug/surveys/$surveySlug')({
  component: SurveyLayout,
})
