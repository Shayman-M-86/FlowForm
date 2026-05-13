import { createFileRoute, Outlet, useRouterState, useNavigate } from '@tanstack/react-router'
import { Badge, Button, TabSelector } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'
import { useProject } from '@/api/projects'
import { getMockSurvey } from '@/api/mockData'

const TABS = [
  { id: 'overview',  label: 'Overview' },
  { id: 'builder',   label: 'Builder' },
  { id: 'versions',  label: 'Versions' },
  { id: 'members',   label: 'Members' },
  { id: 'links',     label: 'Links' },
  { id: 'responses', label: 'Responses' },
  { id: 'settings',  label: 'Settings' },
] as const

type TabId = typeof TABS[number]['id']

function SurveyLayout() {
  const { slug, surveySlug } = Route.useParams()
  const { data: project } = useProject(slug)
  const survey = getMockSurvey(slug, surveySlug)
  const navigate = useNavigate()

  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const activeTab: TabId = (TABS.find((t) => pathname.endsWith(`/${t.id}`))?.id ?? 'overview') as TabId

  const projectLabel = project?.name ?? slug
  const surveyTitle = survey?.title ?? surveySlug.replace(/-/g, ' ')

  const isPublished = survey?.publishedVersionNumber != null
  const hasDraft = survey?.draftVersionNumber != null
  const hasDraftChanges = isPublished && hasDraft

  return (
    <main className="max-w-7xl px-6 py-10 md:px-16">
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
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {isPublished ? (
                <Badge variant="success" size="xs">Published</Badge>
              ) : (
                <Badge variant="muted" size="xs">Draft</Badge>
              )}
              {hasDraftChanges && (
                <Badge variant="warning" size="xs">Draft changes</Badge>
              )}
              {isPublished && (
                <span className="text-xs text-muted-foreground">v{survey!.publishedVersionNumber} live</span>
              )}
              {hasDraft && (
                <span className="text-xs text-muted-foreground">
                  {hasDraftChanges ? '·' : ''} v{survey!.draftVersionNumber} draft
                </span>
              )}
              {survey && (
                <span className="text-xs text-muted-foreground">· {survey.responses} responses</span>
              )}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button variant="secondary" size="sm">Preview</Button>
            {hasDraft && (
              <Button variant="primary" size="sm">Publish v{survey!.draftVersionNumber}</Button>
            )}
          </div>
        </div>
        <TabSelector
          items={TABS.map((t) => ({ id: t.id, label: t.label }))}
          activeId={activeTab}
          onChange={(id) => navigate({ to: `/projects/${slug}/surveys/${surveySlug}/${id}` as any })}
        />
      </div>

      <div className="mt-6"><Outlet /></div>
    </main>
  )
}

export const Route = createFileRoute('/projects/$slug/surveys/$surveySlug')({
  component: SurveyLayout,
})
