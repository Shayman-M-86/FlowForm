import { useRef, useState } from 'react'
import { useParams } from '@tanstack/react-router'
import { MemoryRouter } from 'react-router-dom'
import { NodePage } from '@flowform/builder'
import { Badge, Button, Card, DropdownMenu, Spinner } from '@flowform/ui'
import { Archive, Copy, Eye, Rocket, RotateCcw, Trash2 } from 'lucide-react'
import { useProject } from '@/api/project/projects/hooks'
import { useSurvey } from '@/api/project/surveys/hooks'
import {
  useArchiveSurveyVersion,
  useCopyVersionToDraft,
  useCreateSurveyVersion,
  usePublishSurveyVersion,
  useSurveyVersions,
} from '@/api/survey/versions/hooks'
import type { SurveyVersionOut } from '@/api/survey/versions/types'
import { useRenderDebug } from '@/debug/useRenderDebug'

function versionStatusBadge(status: SurveyVersionOut['status']) {
  if (status === 'published') return <Badge variant="success" size="xs">Published</Badge>
  if (status === 'draft') return <Badge variant="warning" size="xs">Draft</Badge>
  return <Badge variant="muted" size="xs">Archived</Badge>
}

function formatVersionDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function DraftVersionBar({
  version,
  onPublish,
  isPublishing,
}: {
  version: SurveyVersionOut
  onPublish: () => void
  isPublishing: boolean
}) {
  const moreRef = useRef<HTMLButtonElement>(null)
  const [moreOpen, setMoreOpen] = useState(false)

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          {versionStatusBadge(version.status)}
          <span className="text-sm font-semibold text-foreground">v{version.version_number}</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>Created {formatVersionDate(version.created_at)}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm">
          <Eye size={14} strokeWidth={2} aria-hidden="true" />
          Preview
        </Button>
        <Button variant="primary" size="sm" disabled={isPublishing} onClick={onPublish}>
          <Rocket size={14} strokeWidth={2} aria-hidden="true" />
          {isPublishing ? 'Publishing…' : 'Publish'}
        </Button>
        <Button
          ref={moreRef}
          type="button"
          variant="icon"
          size="sm"
          icon="ellipsis"
          aria-label="More version actions"
          aria-haspopup="menu"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen((o) => !o)}
        />
        <DropdownMenu
          open={moreOpen}
          onClose={() => setMoreOpen(false)}
          trigger={moreRef}
          align="right"
          direction="auto"
          fullscreenAt="never"
          width="13rem"
          sections={[{
            actions: [
              {
                key: 'delete',
                content: (
                  <span className="flex items-center gap-2 text-destructive">
                    <Trash2 size={14} strokeWidth={2} aria-hidden="true" /> Delete draft
                  </span>
                ),
                onSelect: () => {},
              },
            ],
          }]}
        />
      </div>
    </div>
  )
}

function PublishedVersionBar({
  version,
  onCopyToDraft,
  isCopying,
  onArchive,
  isArchiving,
}: {
  version: SurveyVersionOut
  onCopyToDraft: () => void
  isCopying: boolean
  onArchive: () => void
  isArchiving: boolean
}) {
  const moreRef = useRef<HTMLButtonElement>(null)
  const [moreOpen, setMoreOpen] = useState(false)

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          {versionStatusBadge(version.status)}
          <span className="text-sm font-semibold text-foreground">v{version.version_number}</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {version.published_at && <span>Published {formatVersionDate(version.published_at)}</span>}
          <span className="italic">Read-only — create a new draft to make changes</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" disabled={isCopying} onClick={onCopyToDraft}>
          <Copy size={14} strokeWidth={2} aria-hidden="true" />
          {isCopying ? 'Copying…' : 'New draft copy'}
        </Button>
        <Button
          ref={moreRef}
          type="button"
          variant="icon"
          size="sm"
          icon="ellipsis"
          aria-label="More version actions"
          aria-haspopup="menu"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen((o) => !o)}
        />
        <DropdownMenu
          open={moreOpen}
          onClose={() => setMoreOpen(false)}
          trigger={moreRef}
          align="right"
          direction="auto"
          fullscreenAt="never"
          width="13rem"
          sections={[{
            actions: [
              {
                key: 'archive',
                content: (
                  <span className="flex items-center gap-2">
                    <Archive size={14} strokeWidth={2} aria-hidden="true" />
                    {isArchiving ? 'Archiving…' : 'Archive'}
                  </span>
                ),
                onSelect: onArchive,
              },
            ],
          }]}
        />
      </div>
    </div>
  )
}

function NoDraftPanel({
  publishedVersion,
  onCreateDraft,
  isCreating,
}: {
  publishedVersion: SurveyVersionOut | undefined
  onCreateDraft: () => void
  isCreating: boolean
}) {
  return (
    <div className="grid gap-4">
      <Card tone="muted" size="sm">
        <div className="flex flex-col items-start gap-3">
          <div>
            <p className="text-sm font-semibold text-foreground">No draft version</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {publishedVersion
                ? `v${publishedVersion.version_number} is published and locked. Create a new draft to start editing.`
                : 'Create a draft to start building your survey.'}
            </p>
          </div>
          <Button variant="primary" size="sm" disabled={isCreating} onClick={onCreateDraft}>
            <RotateCcw size={14} strokeWidth={2} aria-hidden="true" />
            {isCreating ? 'Creating…' : 'Create new draft'}
          </Button>
        </div>
      </Card>
    </div>
  )
}

export function SurveyBuilderTab() {
  useRenderDebug('SurveyBuilderTab')
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/builder' })

  const { data: project } = useProject(slug)
  const { data: survey } = useSurvey(slug, surveySlug)

  const projectId = project?.id ?? 0
  const surveyId = survey?.id ?? 0

  const { data: versions = [], isLoading: versionsLoading } = useSurveyVersions(projectId, surveyId)

  const createVersion = useCreateSurveyVersion(projectId, surveyId)
  const copyToDraft = useCopyVersionToDraft(projectId, surveyId)
  const publishVersion = usePublishSurveyVersion(projectId, surveyId)
  const archiveVersion = useArchiveSurveyVersion(projectId, surveyId)

  const draftVersion = versions.find((v) => v.status === 'draft')
  const publishedVersion = versions.find((v) => v.status === 'published')
  const activeVersion = draftVersion ?? publishedVersion

  function handleCreateDraft() {
    createVersion.mutate()
  }

  function handleCopyToDraft() {
    if (!publishedVersion) return
    copyToDraft.mutate(publishedVersion.version_number)
  }

  function handlePublish() {
    if (!draftVersion) return
    publishVersion.mutate(draftVersion.version_number)
  }

  function handleArchive() {
    if (!publishedVersion) return
    archiveVersion.mutate(publishedVersion.version_number)
  }

  if (versionsLoading) {
    return (
      <div className="flex justify-center py-16 px-6 md:px-16">
        <Spinner size={20} />
      </div>
    )
  }

  return (
    <section className="grid gap-0">
      {/* Version bar — shown above the builder in the padded zone */}
      <div className="px-6 pb-4 md:px-16">
        <div className="grid gap-2">
          {draftVersion && (
            <DraftVersionBar
              version={draftVersion}
              onPublish={handlePublish}
              isPublishing={publishVersion.isPending}
            />
          )}
          {publishedVersion && (
            <PublishedVersionBar
              version={publishedVersion}
              onCopyToDraft={handleCopyToDraft}
              isCopying={copyToDraft.isPending}
              onArchive={handleArchive}
              isArchiving={archiveVersion.isPending}
            />
          )}
          {!activeVersion && (
            <NoDraftPanel
              publishedVersion={undefined}
              onCreateDraft={handleCreateDraft}
              isCreating={createVersion.isPending}
            />
          )}
        </div>
      </div>

      {/* Builder — full-width below the version bar */}
      {draftVersion ? (
        <MemoryRouter initialEntries={['/node']}>
          <NodePage />
        </MemoryRouter>
      ) : publishedVersion ? (
        <div className="px-6 md:px-16">
          <NoDraftPanel
            publishedVersion={publishedVersion}
            onCreateDraft={handleCopyToDraft}
            isCreating={copyToDraft.isPending}
          />
        </div>
      ) : null}
    </section>
  )
}
