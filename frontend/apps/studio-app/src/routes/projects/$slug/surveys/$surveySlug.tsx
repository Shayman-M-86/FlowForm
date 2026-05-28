import { createFileRoute, Outlet, useRouterState, useNavigate } from '@tanstack/react-router'
import { Button, TabSelector } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'
import { useProject } from '@/api/project/projects/hooks'
import { useSurvey } from '@/api/project/surveys/hooks'
import { useHasProjectPermission } from '@/api/project/permissions/hooks'
import { PERMISSION_REQUIRED_TOOLTIP } from '@/api/project/permissions/types'
import { useRenderDebug } from '@/debug/useRenderDebug'

const TAB_IDS = ['overview', 'builder', 'access', 'responses', 'settings'] as const
type TabId = typeof TAB_IDS[number]

function SurveyLayout() {
  useRenderDebug('SurveyLayout')
  const { slug, surveySlug } = Route.useParams()
  const { data: project } = useProject(slug)
  const { data: survey } = useSurvey(slug, surveySlug)
  const navigate = useNavigate()

  const projectId = project?.id ?? null
  const canEditSurvey    = useHasProjectPermission(projectId, 'survey:edit')
  const canViewResponses = useHasProjectPermission(projectId, 'submission:view')
  const canArchiveSurvey = useHasProjectPermission(projectId, 'survey:archive')
  const canDeleteSurvey  = useHasProjectPermission(projectId, 'survey:delete')
  const canPublishSurvey = useHasProjectPermission(projectId, 'survey:publish')

  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const activeTab: TabId = (TAB_IDS.find((id) => pathname.endsWith(`/${id}`)) ?? 'overview') as TabId
  const isBuilderTab = activeTab === 'builder'

  const projectLabel = project?.name ?? slug
  const surveyTitle = survey?.title ?? surveySlug.replace(/-/g, ' ')

  const tabs = [
    { id: 'overview',  label: 'Overview' },
    { id: 'builder',   label: 'Builder',   disabled: !canEditSurvey,                                                       tooltip: PERMISSION_REQUIRED_TOOLTIP.surveyBuilder },
    { id: 'access',    label: 'Access' },
    { id: 'responses', label: 'Responses', disabled: !canViewResponses,                                                    tooltip: PERMISSION_REQUIRED_TOOLTIP.surveyResponses },
    { id: 'settings',  label: 'Settings',  disabled: !canEditSurvey && !canArchiveSurvey && !canDeleteSurvey && !canPublishSurvey, tooltip: PERMISSION_REQUIRED_TOOLTIP.surveySettings },
  ]

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
            items={tabs}
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
