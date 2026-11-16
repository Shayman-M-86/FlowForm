import { useMemo, type ReactNode } from 'react'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Badge, Button, Card } from '@flowform/ui'
import {
  Activity,
  CheckCircle2,
  Circle,
  GitBranch,
  Link2,
  ListChecks,
  PencilLine,
  Radio,
  Rocket,
  Share2,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { useProject } from '@/api/hooks/projects'
import { useSurvey } from '@/api/hooks/surveys'
import { useSurveyVersions, type SurveyVersionOut } from '@/api/hooks/versions'
import { useSurveyNodes } from '@/api/hooks/nodes'
import { usePublicLinks } from '@/api/hooks/links'
import { useSurveyResultSubjects, type ResponseStatus } from '@/api/hooks/results'
import { useHasProjectPermission } from '@/api/hooks/permissions'
import { SURVEY_ACCESS_MODES } from '@/lib/surveyAccessDesign'
import { useRenderDebug } from '@/debug/useRenderDebug'

/** Subjects sampled for the response breakdown (the API's maximum page size). */
const RESPONSE_SAMPLE_SIZE = 100

type Stage = 'empty' | 'draft' | 'live'
type TabPath = 'builder' | 'access' | 'responses'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatRelative(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  return formatDate(iso)
}

function SectionLabel({ icon: Icon, children }: { icon: LucideIcon; children: ReactNode }) {
  return (
    <p className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
      <Icon size={13} strokeWidth={2.2} aria-hidden="true" />
      {children}
    </p>
  )
}

function Stat({ icon: Icon, label, value, detail }: { icon: LucideIcon; label: string; value: ReactNode; detail?: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-border bg-background/60 px-3 py-2.5">
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon size={13} aria-hidden="true" />
        {label}
      </p>
      <p className="mt-1 truncate text-lg font-semibold leading-7 text-foreground">{value}</p>
      {detail && <p className="truncate text-xs text-muted-foreground">{detail}</p>}
    </div>
  )
}

function ChecklistStep({ done, title, detail, action }: { done: boolean; title: string; detail: string; action?: ReactNode }) {
  return (
    <li className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
      {done ? (
        <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-success" aria-label="Done" />
      ) : (
        <Circle size={18} className="mt-0.5 shrink-0 text-muted-foreground" aria-label="To do" />
      )}
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-medium ${done ? 'text-muted-foreground line-through decoration-muted-foreground/50' : 'text-foreground'}`}>
          {title}
        </p>
        <p className="text-xs text-muted-foreground">{detail}</p>
      </div>
      {action}
    </li>
  )
}

const STATUS_SEGMENTS: Array<{ status: ResponseStatus; label: string; className: string }> = [
  { status: 'completed', label: 'Completed', className: 'bg-success' },
  { status: 'in_progress', label: 'In progress', className: 'bg-warning' },
  { status: 'abandoned', label: 'Abandoned', className: 'bg-muted-foreground/40' },
]

export function SurveyOverviewTab() {
  useRenderDebug('SurveyOverviewTab')
  const { slug, surveySlug } = useParams({ from: '/_studio/projects/$slug/surveys/$surveySlug/overview' })
  const navigate = useNavigate()

  const { data: project } = useProject(slug)
  const { data: survey } = useSurvey(slug, surveySlug)
  const projectId = project?.id ?? 0
  const surveyId = survey?.id ?? 0
  const canEdit = useHasProjectPermission(projectId || null, 'survey:edit')
  const canPublish = useHasProjectPermission(projectId || null, 'survey:publish')
  const canViewResults = useHasProjectPermission(projectId || null, 'submission:view')

  const { data: versions = [] } = useSurveyVersions(projectId, surveyId)
  const publishedVersion = versions.find((v) => v.status === 'published')
  const draftVersion = versions.find((v) => v.status === 'draft')
  const stage: Stage = publishedVersion ? 'live' : draftVersion ? 'draft' : 'empty'

  const { data: draftNodes = [] } = useSurveyNodes(projectId || null, surveyId || null, draftVersion?.version_number ?? null)
  const draftQuestionCount = draftNodes.filter((node) => node.node_type === 'question').length

  const { data: links = [] } = usePublicLinks(projectId || null, surveyId || null)
  const activeLinkCount = links.filter((link) => link.is_active).length

  const { data: results } = useSurveyResultSubjects(canViewResults ? projectId : 0, surveyId, { pageSize: RESPONSE_SAMPLE_SIZE })
  const responseStats = useMemo(() => {
    const sessions = (results?.items ?? []).flatMap((subject) => subject.sessions.map((tree) => tree.session))
    const counts: Record<ResponseStatus, number> = { completed: 0, in_progress: 0, abandoned: 0 }
    let lastActivity: string | null = null
    for (const session of sessions) {
      counts[session.status] += 1
      if (!lastActivity || session.last_activity_at > lastActivity) lastActivity = session.last_activity_at
    }
    return { counts, sessions: sessions.length, subjects: results?.total ?? 0, lastActivity, sampled: (results?.total ?? 0) > RESPONSE_SAMPLE_SIZE }
  }, [results])

  const goTo = (tab: TabPath, search?: { status: ResponseStatus }) =>
    void navigate({ to: `/projects/$slug/surveys/$surveySlug/${tab}`, params: { slug, surveySlug }, search })

  const visibility = survey?.visibility ?? 'private'
  const accessMode = SURVEY_ACCESS_MODES[visibility]
  const hasAccessPath = visibility !== 'private' || activeLinkCount > 0
  const currentVersion: SurveyVersionOut | undefined = publishedVersion ?? draftVersion
  const lastEdited = [...versions].sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0]?.updated_at

  const hero = {
    empty: { badge: <Badge variant="muted" size="xs">No versions</Badge>, title: 'Start building your survey', body: 'Add questions in the builder to create your first draft.' },
    draft: {
      badge: <Badge variant="warning" size="xs">Draft</Badge>,
      title: draftQuestionCount > 0 ? 'Ready to publish?' : 'Add your first questions',
      body: 'Finish editing and preview the survey before making it available to participants.',
    },
    live: {
      badge: <Badge variant="success" size="xs">Published</Badge>,
      title: 'Live and collecting responses',
      body: publishedVersion?.published_at ? `v${publishedVersion.version_number} published ${formatDate(publishedVersion.published_at)}.` : 'This survey is accepting responses.',
    },
  }[stage]

  return (
    <section className="grid gap-5">
      {/* ── Summary ─────────────────────────────────────────────────────── */}
      <Card className="bg-linear-to-br from-primary/[0.07] via-card to-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Survey overview</p>
              {hero.badge}
            </div>
            <h3 className="mt-2 text-2xl font-semibold leading-tight text-foreground">{hero.title}</h3>
            <p className="mt-1 max-w-xl text-sm text-muted-foreground">{hero.body}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {stage === 'live' ? (
              <>
                {canViewResults && (
                  <Button variant="primary" size="sm" onClick={() => goTo('responses')}>
                    <Activity size={14} aria-hidden="true" /> View responses
                  </Button>
                )}
                <Button variant="secondary" size="sm" onClick={() => goTo('access')}>
                  <Share2 size={14} aria-hidden="true" /> Share
                </Button>
              </>
            ) : (
              <>
                {canEdit && (
                  <Button variant={stage === 'draft' && draftQuestionCount > 0 && canPublish ? 'secondary' : 'primary'} size="sm" onClick={() => goTo('builder')}>
                    <PencilLine size={14} aria-hidden="true" /> {stage === 'empty' ? 'Open builder' : 'Edit survey'}
                  </Button>
                )}
                {stage === 'draft' && draftQuestionCount > 0 && canPublish && (
                  <Button variant="primary" size="sm" onClick={() => goTo('builder')}>
                    <Rocket size={14} aria-hidden="true" /> Review &amp; publish
                  </Button>
                )}
              </>
            )}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-2.5 md:grid-cols-4">
          <Stat
            icon={GitBranch}
            label="Version"
            value={currentVersion ? `v${currentVersion.version_number}` : '—'}
            detail={publishedVersion && draftVersion ? `Draft v${draftVersion.version_number} in progress` : lastEdited ? `Edited ${formatDate(lastEdited)}` : undefined}
          />
          <Stat
            icon={ListChecks}
            label={stage === 'live' ? 'Status' : 'Questions'}
            value={stage === 'live' ? 'Live' : draftQuestionCount}
            detail={stage === 'live' ? undefined : stage === 'draft' ? 'In current draft' : 'No draft yet'}
          />
          <Stat
            icon={Link2}
            label="Access"
            value={accessMode.label}
            detail={`${activeLinkCount} active link${activeLinkCount === 1 ? '' : 's'}`}
          />
          <Stat
            icon={Users}
            label="Respondents"
            value={canViewResults ? responseStats.subjects : '—'}
            detail={canViewResults ? (responseStats.lastActivity ? `Last activity ${formatRelative(responseStats.lastActivity)}` : 'None yet') : 'No results access'}
          />
        </div>
      </Card>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
        {/* ── Primary column ────────────────────────────────────────────── */}
        <div className="grid gap-5">
          {stage === 'live' ? (
            <Card>
              <SectionLabel icon={Activity}>Responses</SectionLabel>
              {!canViewResults ? (
                <p className="text-sm text-muted-foreground">You don&apos;t have permission to view responses.</p>
              ) : responseStats.sessions === 0 ? (
                <div className="grid gap-3">
                  <p className="text-sm text-muted-foreground">No responses yet. Share the survey to start collecting them.</p>
                  <div><Button variant="secondary" size="sm" onClick={() => goTo('access')}><Share2 size={14} aria-hidden="true" /> Share survey</Button></div>
                </div>
              ) : (
                <div className="grid gap-4">
                  <div className="flex h-2.5 overflow-hidden rounded-full bg-muted" role="img" aria-label="Response status breakdown">
                    {STATUS_SEGMENTS.map((segment) => (
                      <div
                        key={segment.status}
                        className={segment.className}
                        style={{ width: `${(responseStats.counts[segment.status] / responseStats.sessions) * 100}%` }}
                      />
                    ))}
                  </div>
                  <dl className="grid grid-cols-3 gap-3">
                    {STATUS_SEGMENTS.map((segment) => (
                      <div key={segment.status}>
                        <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <span className={`size-2 rounded-full ${segment.className}`} aria-hidden="true" />
                          {segment.label}
                        </dt>
                        <dd className="text-xl font-semibold text-foreground">{responseStats.counts[segment.status]}</dd>
                      </div>
                    ))}
                  </dl>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs text-muted-foreground">
                      {responseStats.sampled ? `Breakdown of the first ${RESPONSE_SAMPLE_SIZE} respondents.` : `${responseStats.sessions} session${responseStats.sessions === 1 ? '' : 's'} in total.`}
                    </p>
                    {responseStats.counts.in_progress > 0 && (
                      <Button variant="secondary" size="sm" onClick={() => goTo('responses', { status: 'in_progress' })}>
                        <Radio size={14} aria-hidden="true" /> Watch live
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </Card>
          ) : (
            <Card>
              <SectionLabel icon={ListChecks}>Next steps</SectionLabel>
              <ol className="divide-y divide-border">
                <ChecklistStep
                  done={draftQuestionCount > 0}
                  title="Add questions"
                  detail={draftQuestionCount > 0 ? `${draftQuestionCount} question${draftQuestionCount === 1 ? '' : 's'} in the draft` : 'Build the survey or generate a draft with AI import.'}
                  action={canEdit && <Button variant="ghost" size="sm" onClick={() => goTo('builder')}>Open builder</Button>}
                />
                <ChecklistStep
                  done={hasAccessPath}
                  title="Choose who can respond"
                  detail={hasAccessPath ? `${accessMode.label} · ${activeLinkCount} active link${activeLinkCount === 1 ? '' : 's'}` : 'Private surveys need an invite link before anyone can respond.'}
                  action={<Button variant="ghost" size="sm" onClick={() => goTo('access')}>Access</Button>}
                />
                <ChecklistStep
                  done={false}
                  title="Preview and publish"
                  detail="Check the respondent view in the builder, then publish."
                  action={canPublish && stage === 'draft' && <Button variant="ghost" size="sm" onClick={() => goTo('builder')}>Publish</Button>}
                />
              </ol>
            </Card>
          )}

          {stage === 'live' && draftVersion && (
            <Card tone="muted" size="sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">Draft v{draftVersion.version_number} in progress</p>
                  <p className="text-xs text-muted-foreground">Respondents keep seeing v{publishedVersion?.version_number} until you publish the draft.</p>
                </div>
                {canEdit && (
                  <Button variant="secondary" size="sm" onClick={() => goTo('builder')}>
                    <PencilLine size={14} aria-hidden="true" /> Continue editing
                  </Button>
                )}
              </div>
            </Card>
          )}
        </div>

        {/* ── Secondary column ──────────────────────────────────────────── */}
        <div className="grid gap-5">
          <Card>
            <SectionLabel icon={Share2}>Sharing</SectionLabel>
            <div className="grid gap-2 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Access</span>
                <span className="font-medium text-foreground">{accessMode.label}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Active links</span>
                <span className="font-medium text-foreground">{activeLinkCount}</span>
              </div>
              {survey?.public_slug && visibility === 'public' && (
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Public URL</span>
                  <span className="truncate font-mono text-xs text-foreground">/{survey.public_slug}</span>
                </div>
              )}
            </div>
            <Button variant="ghost" size="sm" className="mt-3 w-full" onClick={() => goTo('access')}>Manage access</Button>
          </Card>

          <Card>
            <SectionLabel icon={GitBranch}>Version history</SectionLabel>
            {versions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No versions yet.</p>
            ) : (
              <ol className="relative grid gap-3 before:absolute before:bottom-2 before:left-[9px] before:top-2 before:w-px before:bg-border">
                {[...versions].sort((a, b) => b.version_number - a.version_number).slice(0, 4).map((v) => (
                  <li key={v.id} className="relative flex items-start gap-3">
                    <span className="relative z-10 mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border border-border bg-card text-[0.65rem] font-semibold text-muted-foreground">
                      {v.version_number}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-foreground">v{v.version_number} {v.status === 'draft' ? 'draft' : v.status}</p>
                      <p className="text-xs text-muted-foreground">{formatDate(v.published_at ?? v.updated_at)}</p>
                    </div>
                    <Badge variant={v.status === 'published' ? 'success' : v.status === 'draft' ? 'warning' : 'muted'} size="xs">{v.status}</Badge>
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>
      </div>
    </section>
  )
}
