import { type ReactNode } from 'react'
import { useParams, Link, useRouterState } from '@tanstack/react-router'
import { Badge, Button } from '@flowform/ui'
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

interface SurveyWorkspacePageProps {
  children: ReactNode
}

export function SurveyWorkspacePage({ children }: SurveyWorkspacePageProps) {
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/$surveySlug' })
  const { data: project } = useProject(slug)
  const survey = getMockSurvey(slug, surveySlug)

  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const activeTab: TabId = (TABS.find((t) => pathname.endsWith(`/${t.id}`))?.id ?? 'overview') as TabId

  const projectLabel = project?.name ?? slug
  const surveyTitle = survey?.title ?? surveySlug.replace(/-/g, ' ')

  const isPublished = survey?.publishedVersionNumber != null
  const hasDraft = survey?.draftVersionNumber != null
  const hasDraftChanges = isPublished && hasDraft

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Breadcrumb segments={[
        { label: 'Projects', to: '/projects' },
        { label: projectLabel, to: `/projects/${slug}` },
        { label: 'Surveys', to: `/projects/${slug}` },
        { label: surveyTitle, current: true },
      ]} />

      {/* Workspace header */}
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="leading-tight">{surveyTitle}</h1>
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
                to={`/projects/$slug/$surveySlug/${tab.id}`}
                params={{ slug, surveySlug }}
                className={`ui-button-ghost h-full whitespace-nowrap border-0 px-4 py-2 text-sm font-medium ${isActive ? 'text-foreground' : 'text-muted-foreground'}`}
              >
                {tab.label}
              </Link>
              {/* Bottom indicator */}
              <span aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-[10px] overflow-hidden">
                <span className={`absolute inset-x-0 -bottom-px h-1 rounded-full bg-primary transition-transform duration-140 ease-out will-change-transform ${isActive ? 'translate-y-0' : 'translate-y-2'}`} />
              </span>
            </div>
          )
        })}
      </div>
      <div className="h-px bg-border" />

      {/* Tab content */}
      <div className="mt-6">{children}</div>
    </main>
  )
}
