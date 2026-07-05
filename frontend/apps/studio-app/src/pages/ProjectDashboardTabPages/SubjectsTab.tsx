import { useCallback, useMemo, useState } from 'react'
import { Badge, Button, Card, Input, Modal, Spinner, Table, Toast, type TableColumn } from '@flowform/ui'
import { useSubjects, useParticipants, useCreateParticipant, useUpdateParticipant, useDeleteParticipant } from '@/api/hooks/subjects'
import type { SubjectOut, ParticipantOut } from '@/api/hooks/subjects'

type Props = { projectId: number }

type View = 'subjects' | 'participants'

const PAGE_SIZE = 20

export function SubjectsTab({ projectId }: Props) {
  const [view, setView] = useState<View>('subjects')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  // ── Create participant modal ───────────────────────────────────────────────
  const [createOpen, setCreateOpen] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newCode, setNewCode] = useState('')
  const createParticipant = useCreateParticipant(projectId)

  // ── Edit participant modal ─────────────────────────────────────────────────
  const [editing, setEditing] = useState<ParticipantOut | null>(null)
  const [editEmail, setEditEmail] = useState('')
  const [editCode, setEditCode] = useState('')
  const updateParticipant = useUpdateParticipant(projectId)

  // ── Delete participant modal ───────────────────────────────────────────────
  const [toDelete, setToDelete] = useState<ParticipantOut | null>(null)
  const deleteParticipant = useDeleteParticipant(projectId)

  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const searchParam = search.trim() || undefined

  const subjectsQuery = useSubjects(
    view === 'subjects' ? projectId : null,
    { search: searchParam, page, page_size: PAGE_SIZE },
  )
  const participantsQuery = useParticipants(
    view === 'participants' ? projectId : null,
    { search: searchParam, page, page_size: PAGE_SIZE },
  )

  const activeQuery = view === 'subjects' ? subjectsQuery : participantsQuery
  const total = view === 'subjects' ? (subjectsQuery.data?.total ?? 0) : (participantsQuery.data?.total ?? 0)
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const switchView = useCallback((v: View) => {
    setView(v)
    setPage(1)
  }, [])

  const onSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value)
    setPage(1)
  }, [])

  // ── Subject table columns ──────────────────────────────────────────────────
  const subjectColumns = useMemo<TableColumn<SubjectOut>[]>(() => [
    {
      key: 'subject_code',
      header: 'Subject code',
      minWidth: 160,
      cell: (row) => <span className="text-sm font-medium text-foreground">{row.subject_code}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      minWidth: 120,
      cell: (row) => (
        <div className="flex items-center gap-2">
          <Badge variant={row.is_participant ? 'success' : 'default'} size="xs">
            {row.is_participant ? 'Participant' : 'Subject only'}
          </Badge>
          {row.canonical_subject_id && (
            <Badge variant="warning" size="xs">Alias</Badge>
          )}
        </div>
      ),
    },
    {
      key: 'identities',
      header: 'Identities',
      minWidth: 80,
      cell: (row) => <span className="text-sm text-muted-foreground">{row.active_identity_count}</span>,
    },
    {
      key: 'created_at',
      header: 'Created',
      minWidth: 120,
      cell: (row) => (
        <span className="text-sm text-muted-foreground">
          {new Date(row.created_at).toLocaleDateString()}
        </span>
      ),
    },
  ], [])

  // ── Participant table columns ──────────────────────────────────────────────
  const participantColumns = useMemo<TableColumn<ParticipantOut>[]>(() => [
    {
      key: 'subject_code',
      header: 'Subject code',
      minWidth: 160,
      cell: (row) => <span className="text-sm font-medium text-foreground">{row.subject_code}</span>,
    },
    {
      key: 'email',
      header: 'Email',
      minWidth: 200,
      cell: (row) => <span className="text-sm text-muted-foreground">{row.email ?? '—'}</span>,
    },
    {
      key: 'created_at',
      header: 'Created',
      minWidth: 120,
      cell: (row) => (
        <span className="text-sm text-muted-foreground">
          {new Date(row.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      minWidth: 120,
      maxWidth: 120,
      headerClassName: 'flex justify-end pr-2',
      cellClassName: 'flex justify-end gap-1 px-0',
      cell: (row) => (
        <>
          <Button variant="ghost" size="sm" onClick={() => { setEditing(row); setEditEmail(row.email ?? ''); setEditCode(row.subject_code) }}>
            Edit
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setToDelete(row)}>
            Delete
          </Button>
        </>
      ),
    },
  ], [])

  const submitCreate = () => {
    const email = newEmail.trim()
    if (!email) return
    createParticipant.mutate(
      { email, subject_code: newCode.trim() || null },
      {
        onSuccess: () => {
          setSuccessMsg(`Participant created for ${email}`)
          setNewEmail('')
          setNewCode('')
          setCreateOpen(false)
        },
      },
    )
  }

  const submitEdit = () => {
    if (!editing) return
    updateParticipant.mutate(
      { participantId: editing.id, body: { email: editEmail.trim() || null, subject_code: editCode.trim() || null } },
      {
        onSuccess: () => {
          setSuccessMsg('Participant updated')
          setEditing(null)
        },
      },
    )
  }

  const submitDelete = () => {
    if (!toDelete) return
    deleteParticipant.mutate(toDelete.id, {
      onSuccess: () => {
        setSuccessMsg('Participant deleted')
        setToDelete(null)
      },
      onError: (error) => {
        setToDelete(null)
        const msg = (error as { message?: string })?.message
        setErrorMsg(msg ?? 'Failed to delete participant.')
      },
    })
  }

  return (
    <section className="grid gap-4">
      {errorMsg && (
        <Toast variant="error" onClose={() => setErrorMsg(null)}>
          {errorMsg}
        </Toast>
      )}
      {successMsg && (
        <Toast variant="success" onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Toast>
      )}

      {/* ── Header ────────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Subjects & Participants</h2>
          <p className="text-sm text-muted-foreground">{total} total</p>
        </div>
        {view === 'participants' && (
          <Button variant="primary" size="sm" icon="plus" onClick={() => setCreateOpen(true)}>
            Add participant
          </Button>
        )}
      </div>

      {/* ── View toggle + search ──────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex gap-1">
          <Button variant={view === 'subjects' ? 'primary' : 'secondary'} size="sm" onClick={() => switchView('subjects')}>
            Subjects
          </Button>
          <Button variant={view === 'participants' ? 'primary' : 'secondary'} size="sm" onClick={() => switchView('participants')}>
            Participants
          </Button>
        </div>
        <div className="flex-1 max-w-xs">
          <Input
            placeholder="Search by code or email…"
            value={search}
            onChange={onSearchChange}
          />
        </div>
      </div>

      {/* ── Table ─────────────────────────────────────────────────────────────── */}
      {activeQuery.isLoading ? (
        <div className="flex justify-center py-10"><Spinner size={24} /></div>
      ) : view === 'subjects' ? (
        <Table
          columns={subjectColumns}
          rows={subjectsQuery.data?.subjects ?? []}
          getRowKey={(row) => row.id}
        />
      ) : (
        <Table
          columns={participantColumns}
          rows={participantsQuery.data?.participants ?? []}
          getRowKey={(row) => row.id}
        />
      )}

      {/* ── Pagination ────────────────────────────────────────────────────────── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-1">
            <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </Button>
            <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────────────────────── */}
      {!activeQuery.isLoading && total === 0 && (
        <Card tone="muted" size="sm">
          <p className="text-sm text-muted-foreground">
            {view === 'subjects'
              ? 'No subjects found. Subjects appear here when respondents interact with your project.'
              : 'No participants yet. Add a participant to enroll someone in this project.'}
          </p>
        </Card>
      )}

      {/* ── Create participant modal ──────────────────────────────────────────── */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Add participant"
        width={480}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button variant="primary" onClick={submitCreate} disabled={!newEmail.trim() || createParticipant.isPending}>
              {createParticipant.isPending ? 'Creating…' : 'Create'}
            </Button>
          </>
        )}
      >
        <div className="grid gap-4">
          <Input label="Email address" type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="name@example.com" />
          <Input label="Subject code (optional)" value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="sub_xxx" />
          {createParticipant.isError && (
            <p className="text-sm text-destructive">
              {(createParticipant.error as { message?: string } | null)?.message ?? 'Failed to create participant.'}
            </p>
          )}
        </div>
      </Modal>

      {/* ── Edit participant modal ────────────────────────────────────────────── */}
      <Modal
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        title="Edit participant"
        width={480}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setEditing(null)}>Cancel</Button>
            <Button variant="primary" onClick={submitEdit} disabled={updateParticipant.isPending}>
              {updateParticipant.isPending ? 'Saving…' : 'Save'}
            </Button>
          </>
        )}
      >
        <div className="grid gap-4">
          <Input label="Email address" type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} placeholder="name@example.com" />
          <Input label="Subject code" value={editCode} onChange={(e) => setEditCode(e.target.value)} placeholder="sub_xxx" />
          {updateParticipant.isError && (
            <p className="text-sm text-destructive">
              {(updateParticipant.error as { message?: string } | null)?.message ?? 'Failed to update participant.'}
            </p>
          )}
        </div>
      </Modal>

      {/* ── Delete participant confirmation ───────────────────────────────────── */}
      <Modal
        open={Boolean(toDelete)}
        onClose={() => setToDelete(null)}
        title="Delete participant"
        width={420}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setToDelete(null)} className="mr-auto">Cancel</Button>
            <Button variant="destructive" onClick={submitDelete} disabled={deleteParticipant.isPending}>
              {deleteParticipant.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </>
        )}
      >
        {toDelete && (
          <p className="text-base leading-6 text-foreground">
            Are you sure you want to delete the participant for {toDelete.email ?? toDelete.subject_code}?
            This will remove the participant record but keep the subject.
          </p>
        )}
      </Modal>
    </section>
  )
}
