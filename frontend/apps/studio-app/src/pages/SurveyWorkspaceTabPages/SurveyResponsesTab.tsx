import { useCallback, useMemo, useRef, useState } from 'react'
import { useParams } from '@tanstack/react-router'
import { Badge, Button, Card, DropdownMenu, Modal, Spinner, Table, Toast, type TableColumn } from '@flowform/ui'
import { useProject } from '@/api/hooks/projects'
import { useSurvey } from '@/api/hooks/surveys'
import { useResponses, useDeleteResponse, useExportResponses, type ResponseSummary, type ResponseStatus } from '@/api/hooks/responses'
import { ResponseDetailModal } from './ResponseDetailModal'
import { useRenderDebug } from '@/debug/useRenderDebug'

const STATUS_FILTERS: Array<{ label: string; value: ResponseStatus | null }> = [
  { label: 'All', value: null },
  { label: 'Completed', value: 'completed' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Abandoned', value: 'abandoned' },
]

const STATUS_BADGE_VARIANT: Record<ResponseStatus, 'success' | 'warning' | 'muted'> = {
  completed: 'success',
  in_progress: 'warning',
  abandoned: 'muted',
}

const STATUS_LABEL: Record<ResponseStatus, string> = {
  completed: 'Completed',
  in_progress: 'In Progress',
  abandoned: 'Abandoned',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function truncateUuid(uuid: string): string {
  return uuid.slice(0, 8)
}

const PAGE_SIZE = 25

export function SurveyResponsesTab() {
  useRenderDebug('SurveyResponsesTab')
  const { slug, surveySlug } = useParams({ from: '/_studio/projects/$slug/surveys/$surveySlug/responses' })

  const { data: project } = useProject(slug)
  const { data: survey } = useSurvey(slug, surveySlug)
  const projectId = project?.id ?? 0
  const surveyId = survey?.id ?? 0

  const [statusFilter, setStatusFilter] = useState<ResponseStatus | null>(null)
  const [page, setPage] = useState(1)
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<ResponseSummary | null>(null)
  const [exportToast, setExportToast] = useState<string | null>(null)

  const { data: responsesPage, isLoading } = useResponses(projectId, surveyId, {
    status: statusFilter ?? undefined,
    page,
    pageSize: PAGE_SIZE,
  })

  const items = responsesPage?.items ?? []
  const total = responsesPage?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const deleteResponse = useDeleteResponse(projectId, surveyId)
  const exportResponses = useExportResponses(projectId, surveyId)

  const handleStatusFilter = useCallback((status: ResponseStatus | null) => {
    setStatusFilter(status)
    setPage(1)
  }, [])

  const handleDelete = useCallback(() => {
    if (!deleteTarget) return
    deleteResponse.mutate(deleteTarget.session_id, {
      onSuccess: () => setDeleteTarget(null),
    })
  }, [deleteTarget, deleteResponse])

  const handleExport = useCallback((format: 'csv' | 'json') => {
    const safeName = (survey?.title ?? 'responses').replace(/[^a-zA-Z0-9_-]/g, '_')
    exportResponses.mutate(
      { body: { format, include_history: false, session_ids: null }, filename: `${safeName}.${format}` },
      {
        onSuccess: (result) => {
          setExportToast(`Exported responses as ${result.format.toUpperCase()}.`)
        },
      },
    )
  }, [exportResponses, survey?.title])

  // ── Export dropdown ──────────────────────────────────────────────────────────
  const [exportOpen, setExportOpen] = useState(false)
  const exportTriggerRef = useRef<HTMLButtonElement>(null)

  // ── Table columns ──────────────────────────────────────────────────────────
  const columns = useMemo<TableColumn<ResponseSummary>[]>(() => [
    {
      key: 'session',
      header: 'Session',
      minWidth: 120,
      cell: (row) => (
        <span className="font-mono text-xs text-foreground">{truncateUuid(row.session_id)}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      minWidth: 110,
      cell: (row) => (
        <Badge variant={STATUS_BADGE_VARIANT[row.status]} size="xs">
          {STATUS_LABEL[row.status]}
        </Badge>
      ),
    },
    {
      key: 'started',
      header: 'Started',
      minWidth: 140,
      cell: (row) => (
        <span className="text-xs text-muted-foreground">{formatDate(row.started_at)}</span>
      ),
    },
    {
      key: 'lastActivity',
      header: 'Last Activity',
      minWidth: 140,
      cell: (row) => (
        <span className="text-xs text-muted-foreground">
          {row.completed_at ? formatDate(row.completed_at) : formatDate(row.last_activity_at)}
        </span>
      ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      minWidth: 80,
      maxWidth: 80,
      headerClassName: 'flex justify-center text-right pr-2',
      cellClassName: 'flex justify-center gap-1 px-0',
      cell: (row) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            setDeleteTarget(row)
          }}
        >
          Delete
        </Button>
      ),
    },
  ], [])

  return (
    <section className="grid gap-4">
      {exportToast && (
        <Toast variant="success" onClose={() => setExportToast(null)}>
          {exportToast}
        </Toast>
      )}

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Responses</h2>
          <p className="text-sm text-muted-foreground">{total} total</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            ref={exportTriggerRef}
            variant="secondary"
            size="sm"
            onClick={() => setExportOpen((o) => !o)}
            disabled={total === 0 || exportResponses.isPending}
          >
            {exportResponses.isPending ? 'Exporting…' : 'Export'}
          </Button>
          <DropdownMenu
            open={exportOpen}
            onClose={() => setExportOpen(false)}
            trigger={exportTriggerRef}
            size="sm"
            sections={[{
              actions: [
                { key: 'csv', content: 'Export as CSV', onSelect: () => handleExport('csv') },
                { key: 'json', content: 'Export as JSON', onSelect: () => handleExport('json') },
              ],
            }]}
          />
        </div>
      </div>

      {/* ── Status filter tabs ──────────────────────────────────────────────── */}
      <div className="flex gap-1">
        {STATUS_FILTERS.map((f) => (
          <Button
            key={f.label}
            variant={statusFilter === f.value ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => handleStatusFilter(f.value)}
          >
            {f.label}
          </Button>
        ))}
      </div>

      {/* ── Table ───────────────────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="flex justify-center py-10"><Spinner size={24} /></div>
      ) : items.length === 0 ? (
        <Card tone="muted">
          <p className="text-sm font-medium text-muted-foreground">No responses yet</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Responses will appear here once respondents start filling out the survey.
          </p>
        </Card>
      ) : (
        <>
          <Table
            columns={columns}
            rows={items}
            getRowKey={(row) => row.session_id}
            onRowClick={(row) => setSelectedSessionId(row.session_id)}
          />

          {/* ── Pagination ────────────────────────────────────────────────── */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Detail modal ────────────────────────────────────────────────────── */}
      <ResponseDetailModal
        projectId={projectId}
        surveyId={surveyId}
        sessionId={selectedSessionId}
        onClose={() => setSelectedSessionId(null)}
      />

      {/* ── Delete confirmation ─────────────────────────────────────────────── */}
      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title="Delete response"
        width={420}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)} className="mr-auto">Cancel</Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteResponse.isPending}
            >
              {deleteResponse.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </>
        )}
      >
        {deleteTarget && (
          <p className="text-base leading-6 text-foreground">
            Are you sure you want to delete the response from session{' '}
            <span className="font-mono text-sm">{truncateUuid(deleteTarget.session_id)}</span>?
            This action cannot be undone.
          </p>
        )}
      </Modal>
    </section>
  )
}
