import { useRef, useState, type ReactNode } from 'react'
import { useParams } from '@tanstack/react-router'
import { Badge, Button, Card, DropdownMenu, Table, type TableColumn } from '@flowform/ui'
import {
  Archive,
  Copy,
  Eye,
  ExternalLink,
  Pencil,
  Rocket,
  RotateCcw,
  Trash2,
} from 'lucide-react'
import { getMockVersionsForSurvey, type MockVersion } from '@/api/mockData'
import { useRenderDebug } from '@/debug/useRenderDebug'

function versionBadge(status: MockVersion['status']) {
  if (status === 'published') return <Badge variant="success" size="xs">Published</Badge>
  if (status === 'draft') return <Badge variant="warning" size="xs">Draft</Badge>
  return <Badge variant="muted" size="xs">Archived</Badge>
}

function VersionActionButton({
  children,
  icon,
  variant = 'ghost',
}: {
  children: ReactNode
  icon: ReactNode
  variant?: 'ghost' | 'primary' | 'destructive' | 'secondary'
}) {
  return (
    <Button
      type="button"
      variant={variant}
      size="sm"
      className="mx-1 my-0.5 flex w-[calc(100%-0.5rem)] items-center justify-start gap-2"
    >
      <span className="inline-flex h-[15px] w-[15px] shrink-0 items-center justify-center">
        {icon}
      </span>
      <span>{children}</span>
    </Button>
  )
}

function VersionActionsMenu({ version }: { version: MockVersion }) {
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)

  const iconProps = { size: 15, strokeWidth: 2 }

  const actions =
    version.status === 'draft'
      ? [
          {
            key: 'edit',
            content: <VersionActionButton variant="secondary" icon={<Pencil {...iconProps} />}>Edit</VersionActionButton>,
            onSelect: () => {},
          },
          {
            key: 'preview',
            content: <VersionActionButton variant="secondary" icon={<Eye {...iconProps} />}>Preview</VersionActionButton>,
            onSelect: () => {},
          },
          {
            key: 'publish',
            content: <VersionActionButton variant="primary" icon={<Rocket {...iconProps} />}>Publish</VersionActionButton>,
            onSelect: () => {},
          },
          {
            key: 'delete',
            content: <VersionActionButton variant="destructive" icon={<Trash2 {...iconProps} />}>Delete</VersionActionButton>,
            onSelect: () => {},
          },
        ]
      : version.status === 'published'
        ? [
            {
              key: 'view-live',
              content: <VersionActionButton icon={<ExternalLink {...iconProps} />}>View live</VersionActionButton>,
              onSelect: () => {},
            },
            {
              key: 'create-draft-copy',
              content: <VersionActionButton icon={<Copy {...iconProps} />}>Create draft copy</VersionActionButton>,
              onSelect: () => {},
            },
            {
              key: 'archive',
              content: <VersionActionButton  variant="secondary" icon={<Archive {...iconProps} />}>Archive</VersionActionButton>,
              onSelect: () => {},
            },
          ]
        : [
            {
              key: 'view',
              content: <VersionActionButton icon={<Eye {...iconProps} />}>View</VersionActionButton>,
              onSelect: () => {},
            },
            {
              key: 'restore-as-draft',
              content: <VersionActionButton icon={<RotateCcw {...iconProps} />}>Restore as draft</VersionActionButton>,
              onSelect: () => {},
            },
          ]

  return (
    <>
      <Button
        ref={triggerRef}
        type="button"
        variant="icon"
        size="xs"
        icon="ellipsis"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Actions for version ${version.versionNumber}`}
        onClick={() => setOpen((o) => !o)}
      />
      <DropdownMenu
        open={open}
        onClose={() => setOpen(false)}
        trigger={triggerRef}
        sections={[{ actions }]}

        width={"13rem"}
        align="right"
        direction="auto"
        fullscreenAt="never"
      />
    </>
  )
}

function versionActions(v: MockVersion) {
  return <VersionActionsMenu version={v} />
}

function formatVersionDate(date: string) {
  return new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function SurveyVersionsTab() {
  useRenderDebug('SurveyVersionsTab')
  const { surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/versions' })
  const versions = getMockVersionsForSurvey(surveySlug)
  const versionColumns: TableColumn<MockVersion>[] = [
    {
      key: 'version',
      header: 'Version',
      minWidth: 70,
      targetWidth: 150,
      cell: (v) => <span className="text-sm font-semibold text-foreground">v{v.versionNumber}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      minWidth: 100,
      cell: (v) => (
        <div className="flex items-center gap-2">
          {versionBadge(v.status)}
        </div>
      ),
    },
    {
      key: 'created',
      header: 'Created',
      minWidth: 140,
      cell: (v) => <span className="text-xs text-muted-foreground">{formatVersionDate(v.createdAt)}</span>,
    },
    {
      key: 'published',
      header: 'Published',
      minWidth: 100,
      cell: (v) => (
        <span className="text-xs text-muted-foreground">
          {v.publishedAt ? formatVersionDate(v.publishedAt) : '—'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      minWidth: 70,
      targetWidth: 80,
      cellClassName: 'flex justify-center px-2',
      headerClassName: 'justify-end text-right pl-2',
      cell: versionActions,
    },
  ]

  return (
    <section className="grid gap-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Version history</h2>
          <p className="text-sm text-muted-foreground">{versions.length} versions</p>
        </div>
        <Button variant="primary" size="sm" icon="plus">New draft</Button>
      </div>

      <div className="mx-auto max-w-250">
        <Table
          columns={versionColumns}
          rows={versions}
          getRowKey={(v) => v.id}
        />
      </div>

      <Card tone="muted">
        <p className="text-xs text-muted-foreground">
          Published versions are locked — they cannot be edited directly. To make changes, create a new draft,
          edit it, and publish. The previous published version will be archived automatically.
        </p>
      </Card>
    </section>
  )
}
