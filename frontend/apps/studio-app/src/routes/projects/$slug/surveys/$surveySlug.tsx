import { createFileRoute, Outlet, useRouterState, useNavigate } from '@tanstack/react-router'
import { Button, TabSelector } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'
import { useProject } from '@/api/hooks/projects'
import { useSurvey } from '@/api/hooks/surveys'
import { useHasSurveyPermission, useSurveyPermissions } from '@/api/hooks/permissions'
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
  const surveyId = survey?.id ?? null
  useSurveyPermissions(projectId, surveyId)

  const canEditSurvey    = useHasSurveyPermission(projectId, surveyId, 'survey:edit')
  const canViewResponses = useHasSurveyPermission(projectId, surveyId, 'submission:view')
  const canArchiveSurvey = useHasSurveyPermission(projectId, surveyId, 'survey:archive')
  const canDeleteSurvey  = useHasSurveyPermission(projectId, surveyId, 'survey:delete')
  const canPublishSurvey = useHasSurveyPermission(projectId, surveyId, 'survey:publish')

  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const activeTab: TabId = (TAB_IDS.find((id) => pathname.endsWith(`/${id}`)) ?? 'overview') as TabId
  const isBuilderTab = activeTab === 'builder'

  const projectLabel = project?.name ?? slug
  const surveyTitle = survey?.title ?? surveySlug.replace(/-/g, ' ')

  const tabs = [
    { id: 'overview',  label: 'Overview' },
    { id: 'builder',   label: 'Builder',   disabled: !canEditSurvey,                                                                tooltip: 'You need survey:edit permission to use the builder.' },
    { id: 'access',    label: 'Access' },
    { id: 'responses', label: 'Responses', disabled: !canViewResponses,                                                             tooltip: 'You need submission:view permission to view responses.' },
    { id: 'settings',  label: 'Settings',  disabled: !canEditSurvey && !canArchiveSurvey && !canDeleteSurvey && !canPublishSurvey,  tooltip: 'You need survey:edit, archive, delete, or publish permission to access settings.' },
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
