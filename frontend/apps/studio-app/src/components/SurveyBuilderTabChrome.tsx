import { useRef, useState } from 'react'
import { Badge, Button, Card, DropdownMenu } from '@flowform/ui'
import { Archive, ChevronDown, Copy, Eye, Rocket, RotateCcw, Sparkles } from 'lucide-react'

export type SurveyVersionStatus = 'draft' | 'published' | 'archived'

export type SurveyVersionView = {
  id: number
  version_number: number
  status: SurveyVersionStatus
  created_at: string
}

function noop() {}

function formatVersionDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function StatusBadge({ status }: { status: SurveyVersionStatus }) {
  if (status === 'published') return <Badge variant="success" size="xs">Published</Badge>
  if (status === 'draft') return <Badge variant="warning" size="xs">Draft</Badge>
  return <Badge variant="muted" size="xs">Archived</Badge>
}

function VersionSelector({
  versions,
  selectedVersion,
  onSelectVersion,
}: {
  versions: SurveyVersionView[]
  selectedVersion: SurveyVersionView | undefined
  onSelectVersion: (versionId: number) => void
}) {
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)

  const label = selectedVersion ? `v${selectedVersion.version_number}` : 'No versions'

  const sections = [{
    actions: versions.map((version) => ({
      key: String(version.id),
      closeOnSelect: true,
      content: (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={`my-0.5 flex w-full items-center justify-start gap-2 px-2 ${
            version.id === selectedVersion?.id ? 'bg-accent/20' : ''
          }`}
        >
          <StatusBadge status={version.status} />
          <span className="w-6 pl-1 text-start font-semibold text-foreground">v{version.version_number}</span>
          <span className="mr-auto flex items-center gap-1 text-xs text-muted-foreground">
            {formatVersionDate(version.created_at)}
          </span>
        </Button>
      ),
      onSelect: () => onSelectVersion(version.id),
    })),
  }]

  return (
    <>
      <Button
        ref={triggerRef}
        type="button"
        variant="secondary"
        size="sm"
        className="gap-2 px-4"
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {selectedVersion && <StatusBadge status={selectedVersion.status} />}
        <span className="w-6 pl-1 text-start font-semibold">{label}</span>
        {selectedVersion && (
          <span className="hidden text-xs text-muted-foreground sm:inline">
            {formatVersionDate(selectedVersion.created_at)}
          </span>
        )}
        <ChevronDown size={13} strokeWidth={2} aria-hidden="true" className="ml-auto shrink-0 text-muted-foreground" />
      </Button>
      <DropdownMenu
        open={open}
        onClose={() => setOpen(false)}
        trigger={triggerRef}
        sections={sections}
        size="auto"
        align="left"
        direction="auto"
        fullscreenAt="never"
        maxHeight="16rem"
      />
    </>
  )
}

export function SurveyBuilderVersionToolbar({
  versions,
  selectedVersion,
  canEdit,
  canPublish,
  canArchive,
  isDirty,
  isCreating,
  isCopying,
  isSaving,
  isPublishing,
  isArchiving,
  onSelectVersion,
  onCreateDraft,
  onCopyToDraft,
  onSave,
  onPreview = noop,
  onAiImport = noop,
  onPublish,
  onArchive,
}: {
  versions: SurveyVersionView[]
  selectedVersion: SurveyVersionView | undefined
  canEdit: boolean
  canPublish: boolean
  canArchive: boolean
  isDirty: boolean
  isCreating: boolean
  isCopying: boolean
  isSaving: boolean
  isPublishing: boolean
  isArchiving: boolean
  onSelectVersion: (versionId: number) => void
  onCreateDraft: () => void
  onCopyToDraft: () => void
  onSave: () => void
  onPreview?: () => void
  onAiImport?: () => void
  onPublish: () => void
  onArchive: () => void
}) {
  const moreRef = useRef<HTMLButtonElement>(null)
  const [moreOpen, setMoreOpen] = useState(false)

  const moreActions = [
    ...(canEdit && selectedVersion?.status === 'draft' ? [{
      key: 'ai-import',
      closeOnSelect: true,
      content: (
        <Button type="button" variant="ghost" size="sm" className="w-full justify-start gap-2">
          <Sparkles size={14} strokeWidth={2} aria-hidden="true" />
          AI import
        </Button>
      ),
      onSelect: onAiImport,
    }] : []),
    {
      key: 'duplicate',
      content: (
        <Button type="button" variant="ghost" size="sm" className="w-full justify-start gap-2" disabled={isCopying}>
          <Copy size={14} strokeWidth={2} aria-hidden="true" />
          {isCopying ? 'Copying...' : 'Duplicate'}
        </Button>
      ),
      onSelect: onCopyToDraft,
    },
    ...(canArchive && selectedVersion?.status === 'published' ? [{
      key: 'archive',
      content: (
        <Button type="button" variant="ghost" size="sm" className="w-full justify-start gap-2" disabled={isArchiving}>
          <Archive size={14} strokeWidth={2} aria-hidden="true" />
          {isArchiving ? 'Archiving...' : 'Archive version'}
        </Button>
      ),
      onSelect: onArchive,
    }] : []),
  ]

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-card px-6 py-3 md:px-16">
      <div className="flex items-center gap-2">
        <VersionSelector versions={versions} selectedVersion={selectedVersion} onSelectVersion={onSelectVersion} />
        {canEdit && (
          <Button variant="secondary" size="sm" icon="plus" disabled={isCreating} onClick={onCreateDraft}>
            {isCreating ? 'Creating...' : 'New draft'}
          </Button>
        )}
        {selectedVersion && (
          <>
            <Button
              ref={moreRef}
              type="button"
              variant="icon"
              size="sm"
              icon="ellipsis"
              aria-label="More version actions"
              aria-haspopup="menu"
              aria-expanded={moreOpen}
              onClick={() => setMoreOpen((current) => !current)}
            />
            <DropdownMenu
              open={moreOpen}
              onClose={() => setMoreOpen(false)}
              trigger={moreRef}
              align="right"
              direction="auto"
              fullscreenAt="never"
              width="11rem"
              sections={[{ actions: moreActions }]}
            />
          </>
        )}
        {selectedVersion?.status === 'published' && (
          <span className="hidden text-xs italic text-muted-foreground sm:inline">
            Read-only
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {selectedVersion?.status === 'draft' && canEdit && (
          <Button variant="secondary" size="sm" disabled={!isDirty || isSaving} onClick={onSave}>
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        )}
        {selectedVersion?.status === 'draft' && (
          <Button variant="secondary" size="sm" onClick={onPreview}>
            <Eye size={14} strokeWidth={2} aria-hidden="true" />
            Preview
          </Button>
        )}
        {selectedVersion?.status === 'draft' && canPublish && (
          <Button variant="primary" size="sm" disabled={isPublishing || isSaving} onClick={onPublish}>
            <Rocket size={14} strokeWidth={2} aria-hidden="true" />
            {isPublishing ? 'Publishing...' : 'Publish'}
          </Button>
        )}
      </div>
    </div>
  )
}

export function SurveyBuilderNoVersionsPanel({
  canEdit,
  isCreating,
  onCreateDraft,
}: {
  canEdit: boolean
  isCreating: boolean
  onCreateDraft: () => void
}) {
  return (
    <div className="px-6 py-8 md:px-16">
      <Card tone="muted" size="sm">
        <div className="flex flex-col items-start gap-3">
          <div>
            <p className="text-sm font-semibold text-foreground">No versions yet</p>
            <p className="mt-1 text-sm text-muted-foreground">Create a draft to start building your survey.</p>
          </div>
          {canEdit && (
            <Button variant="primary" size="sm" disabled={isCreating} onClick={onCreateDraft}>
              <RotateCcw size={14} strokeWidth={2} aria-hidden="true" />
              {isCreating ? 'Creating...' : 'Create draft'}
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}

export function SurveyBuilderPublishedNoDraftPanel({
  publishedVersion,
  canEdit,
  isCopying,
  onCopyToDraft,
}: {
  publishedVersion: SurveyVersionView
  canEdit: boolean
  isCopying: boolean
  onCopyToDraft: () => void
}) {
  return (
    <div className="px-6 py-8 md:px-16">
      <Card tone="muted" size="sm">
        <div className="flex flex-col items-start gap-3">
          <div>
            <p className="text-sm font-semibold text-foreground">v{publishedVersion.version_number} is published and locked</p>
            <p className="mt-1 text-sm text-muted-foreground">Create a new draft to start editing.</p>
          </div>
          {canEdit && (
            <Button variant="primary" size="sm" disabled={isCopying} onClick={onCopyToDraft}>
              <Copy size={14} strokeWidth={2} aria-hidden="true" />
              {isCopying ? 'Copying...' : 'New draft copy'}
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}

export function SurveyBuilderArchivedPanel({ version }: { version: SurveyVersionView }) {
  return (
    <div className="px-6 py-8 md:px-16">
      <Card tone="muted" size="sm">
        <p className="text-sm text-muted-foreground">
          v{version.version_number} is archived. Select a draft or published version to edit, or create a new draft.
        </p>
      </Card>
    </div>
  )
}
