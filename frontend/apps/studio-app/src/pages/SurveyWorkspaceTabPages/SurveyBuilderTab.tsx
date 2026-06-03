import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'
import { useParams } from '@tanstack/react-router'
import { MemoryRouter } from 'react-router-dom'
import { NodePage } from '@flowform/builder'
import type { SurveyNode } from '@flowform/builder'
import { Badge, Button, Card, DropdownMenu, Modal, Spinner, Toast } from '@flowform/ui'
import type { ToastVariant } from '@flowform/ui'
import { Archive, ChevronDown, Copy, Eye, Rocket, RotateCcw } from 'lucide-react'
import { useProject } from '@/api/hooks/projects'
import { useSurvey } from '@/api/hooks/surveys'
import { useHasProjectPermission } from '@/api/hooks/permissions'
import {
  useArchiveSurveyVersion,
  useCopyVersionToDraft,
  useCreateSurveyVersion,
  usePublishSurveyVersion,
  useSurveyVersions,
} from '@/api/hooks/versions'
import type { SurveyVersionOut } from '@/api/hooks/versions'
import {
  useCreateNode,
  useDeleteNode,
  useSurveyNodes,
  useUpdateNode,
} from '@/api/hooks/nodes'
import { useRenderDebug } from '@/debug/useRenderDebug'

function formatVersionDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function StatusBadge({ status }: { status: SurveyVersionOut['status'] }) {
  if (status === 'published') return <Badge variant="success" size="xs">Published</Badge>
  if (status === 'draft') return <Badge variant="warning" size="xs">Draft</Badge>
  return <Badge variant="muted" size="xs">Archived</Badge>
}

// ── Version selector dropdown ─────────────────────────────────────────────────

function VersionSelector({
  versions,
  selectedVersion,
  onSelect,
}: {
  versions: SurveyVersionOut[]
  selectedVersion: SurveyVersionOut | undefined
  onSelect: (version: SurveyVersionOut) => void
}) {
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)

  const label = selectedVersion ? `v${selectedVersion.version_number}` : 'No versions'

  const sections = [{
    actions: versions.map((v) => ({
      key: String(v.id),
      closeOnSelect: true,
      content: (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={`my-0.5 flex w-full items-center justify-start gap-2 px-2 ${v.id === selectedVersion?.id ? 'bg-accent/20' : ''}`}
        >
          <StatusBadge status={v.status} />
          <span className="w-6 pl-1 text-start font-semibold text-foreground">v{v.version_number}</span>
          <span className="mr-auto flex items-center gap-1 text-xs text-muted-foreground">
            {formatVersionDate(v.created_at)}
          </span>
        </Button>
      ),
      onSelect: () => onSelect(v),
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
        onClick={() => setOpen((o) => !o)}
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

// ── Version toolbar ───────────────────────────────────────────────────────────

function VersionToolbar({
  versions,
  selectedVersion,
  onSelectVersion,
  onCreateDraft,
  isCreating,
  onCopyToDraft,
  isCopying,
  onSave,
  isSaving,
  onPublish,
  isPublishing,
  onArchive,
  canEdit,
  canPublish,
  canArchive,
}: {
  versions: SurveyVersionOut[]
  selectedVersion: SurveyVersionOut | undefined
  onSelectVersion: (v: SurveyVersionOut) => void
  onCreateDraft: () => void
  isCreating: boolean
  onCopyToDraft: () => void
  isCopying: boolean
  onSave: () => void
  isSaving: boolean
  onPublish: () => void
  isPublishing: boolean
  onArchive: () => void
  canEdit: boolean
  canPublish: boolean
  canArchive: boolean
}) {
  const moreRef = useRef<HTMLButtonElement>(null)
  const [moreOpen, setMoreOpen] = useState(false)

  const isDraft = selectedVersion?.status === 'draft'
  const isPublished = selectedVersion?.status === 'published'

  const moreActions = [
    ...(isPublished && canArchive ? [{
      key: 'archive',
      content: (
        <span className="flex items-center gap-2">
          <Archive size={14} strokeWidth={2} aria-hidden="true" />
          Archive version
        </span>
      ),
      onSelect: onArchive,
    }] : []),
  ]

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-card px-6 py-3 md:px-16">
      {/* Left: version selector + new draft */}
      <div className="flex items-center gap-2">
        <VersionSelector
          versions={versions}
          selectedVersion={selectedVersion}
          onSelect={onSelectVersion}
        />
        {canEdit && (
          <Button
            variant="secondary"
            size="sm"
            icon="plus"
            disabled={isCreating}
            onClick={onCreateDraft}
          >
            New draft
          </Button>
        )}
        {canEdit && selectedVersion && (
          <Button
            variant="secondary"
            size="sm"
            icon="copy"
            disabled={isCopying}
            onClick={onCopyToDraft}
          >
            Duplicate
          </Button>
        )}
        {selectedVersion?.status === 'published' && (
          <span className="hidden text-xs italic text-muted-foreground sm:inline">
            Read-only
          </span>
        )}
      </div>

      {/* Right: contextual actions */}
      <div className="flex items-center gap-2">
        {!selectedVersion && canEdit && (
          <Button variant="primary" size="sm" disabled={isCreating} onClick={onCreateDraft}>
            <RotateCcw size={14} strokeWidth={2} aria-hidden="true" />
            New draft
          </Button>
        )}

        {isDraft && canEdit && (
          <Button variant="secondary" size="sm" disabled={isSaving} onClick={onSave}>
            Save
          </Button>
        )}

        {isDraft && (
          <>
            <Button variant="secondary" size="sm">
              <Eye size={14} strokeWidth={2} aria-hidden="true" />
              Preview
            </Button>
            {canPublish && (
              <Button variant="primary" size="sm" disabled={isPublishing} onClick={onPublish}>
                <Rocket size={14} strokeWidth={2} aria-hidden="true" />
                Publish
              </Button>
            )}
          </>
        )}

        {isPublished && canEdit && (
          <Button variant="secondary" size="sm" disabled={isCopying} onClick={onCopyToDraft}>
            <Copy size={14} strokeWidth={2} aria-hidden="true" />
            New draft copy
          </Button>
        )}

        {canEdit && moreActions.length > 0 && (
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
              onClick={() => setMoreOpen((o) => !o)}
            />
            <DropdownMenu
              open={moreOpen}
              onClose={() => setMoreOpen(false)}
              trigger={moreRef}
              align="right"
              direction="auto"
              fullscreenAt="never"
              width="14rem"
              sections={[{ actions: moreActions }]}
            />
          </>
        )}
      </div>
    </div>
  )
}

// ── No versions panel ─────────────────────────────────────────────────────────

function NoVersionsPanel({
  onCreateDraft,
  isCreating,
  canEdit,
}: {
  onCreateDraft: () => void
  isCreating: boolean
  canEdit: boolean
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
              {isCreating ? 'Creating…' : 'Create draft'}
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}

// ── Published — no draft panel ────────────────────────────────────────────────

function PublishedNoDraftPanel({
  publishedVersion,
  onCopyToDraft,
  isCopying,
  canEdit,
}: {
  publishedVersion: SurveyVersionOut
  onCopyToDraft: () => void
  isCopying: boolean
  canEdit: boolean
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
              {isCopying ? 'Copying…' : 'New draft copy'}
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}

// ── Connected builder (owns node API hooks for a specific draft version) ──────

const DRAFT_STORAGE_KEY = (versionId: number) => `flowform.studio.draft-nodes.${versionId}`

function loadLocalDraft(versionId: number): SurveyNode[] | null {
  try {
    const stored = window.localStorage.getItem(DRAFT_STORAGE_KEY(versionId))
    if (!stored) return null
    return JSON.parse(stored) as SurveyNode[]
  } catch {
    return null
  }
}

function saveLocalDraft(versionId: number, nodes: SurveyNode[]) {
  try {
    window.localStorage.setItem(DRAFT_STORAGE_KEY(versionId), JSON.stringify(nodes))
  } catch {
    // ignore storage failures
  }
}

function clearLocalDraft(versionId: number) {
  try {
    window.localStorage.removeItem(DRAFT_STORAGE_KEY(versionId))
  } catch {
    // ignore
  }
}

function ConnectedNodePage({
  projectId,
  surveyId,
  versionId,
  versionNumber,
  onSaveStart,
  onSaveSuccess,
  onSaveError,
  onValidationFail,
  onDirtyChange,
  saveRef,
}: {
  projectId: number
  surveyId: number
  versionId: number
  versionNumber: number
  onSaveStart: () => void
  onSaveSuccess: () => void
  onSaveError: () => void
  onValidationFail: () => void
  onDirtyChange: (dirty: boolean) => void
  saveRef: RefObject<() => Promise<void>>
}) {
  const { data: backendNodes, isLoading } = useSurveyNodes(projectId, surveyId, versionNumber)
  const createNode = useCreateNode(projectId, surveyId, versionNumber)
  const updateNode = useUpdateNode(projectId, surveyId, versionNumber)
  const deleteNode = useDeleteNode(projectId, surveyId, versionNumber)

  const latestNodesRef = useRef<SurveyNode[]>([])
  const backendNodesRef = useRef(backendNodes)
  backendNodesRef.current = backendNodes
  const validateRef = useRef<(() => boolean) | null>(null)
  const onDirtyChangeRef = useRef(onDirtyChange)
  onDirtyChangeRef.current = onDirtyChange
  const initialEmitDoneRef = useRef(false)

  const syncToBackend = useCallback(async (nodes: SurveyNode[]) => {
    const current = backendNodesRef.current ?? []
    const byKey = new Map(current.map((n) => [n.question_key, n]))
    const incomingKeys = new Set(nodes.map((n) => n.content.id))

    const ops: Promise<unknown>[] = []

    for (const backendNode of current) {
      if (!incomingKeys.has(backendNode.question_key)) {
        ops.push(deleteNode.mutateAsync(backendNode.id))
      }
    }

    for (const node of nodes) {
      const existing = byKey.get(node.content.id)
      if (!existing) {
        ops.push(createNode.mutateAsync({
          type: node.type,
          sort_key: node.sort_key,
          content: node.content as never,
        }))
      } else if (
        existing.sort_key !== node.sort_key ||
        JSON.stringify(existing.question_schema) !== JSON.stringify(node.content)
      ) {
        ops.push(updateNode.mutateAsync({
          nodeId: existing.id,
          body: { sort_key: node.sort_key, content: node.content as never },
        }))
      }
    }

    await Promise.all(ops)
  }, [createNode, updateNode, deleteNode])

  const handleSave = useCallback(async () => {
    if (validateRef.current && !validateRef.current()) {
      onValidationFail()
      return
    }
    onSaveStart()
    try {
      await syncToBackend(latestNodesRef.current)
      clearLocalDraft(versionId)
      onDirtyChangeRef.current(false)
      onSaveSuccess()
    } catch {
      onSaveError()
    }
  }, [syncToBackend, onSaveStart, onSaveSuccess, onSaveError, onValidationFail, versionId])

  saveRef.current = handleSave

  const backendNodesJson = JSON.stringify(backendNodes ?? [])

  // Seed latestNodesRef once backend data arrives, preferring any local draft
  useEffect(() => {
    if (!backendNodes) return
    const local = loadLocalDraft(versionId)
    if (local) {
      latestNodesRef.current = local
      onDirtyChangeRef.current(true)
    } else {
      latestNodesRef.current = backendNodes.map((n) => ({
        type: n.node_type as 'question' | 'rule',
        sort_key: n.sort_key,
        content: n.question_schema as never,
      }))
      onDirtyChangeRef.current(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [versionId, backendNodesJson])

  const initialNodes: SurveyNode[] | undefined = backendNodes?.map((n) => ({
    type: n.node_type as 'question' | 'rule',
    sort_key: n.sort_key,
    content: n.question_schema as never,
  }))

  if (isLoading || !initialNodes) {
    return (
      <div className="flex justify-center py-16">
        <Spinner size={20} />
      </div>
    )
  }

  const localDraft = loadLocalDraft(versionId)
  const seedNodes = localDraft ?? initialNodes

  return (
    <MemoryRouter initialEntries={['/node']}>
      <NodePage
        initialNodes={seedNodes}
        onNodesChange={(nodes) => {
          latestNodesRef.current = nodes
          if (!initialEmitDoneRef.current) {
            initialEmitDoneRef.current = true
            return
          }
          saveLocalDraft(versionId, nodes)
          const backendSchemas = [...(backendNodesRef.current ?? [])]
            .sort((a, b) => a.sort_key - b.sort_key)
            .map((n) => n.question_schema)
          const currentSchemas = nodes.map((n) => n.content)
          onDirtyChangeRef.current(JSON.stringify(backendSchemas) !== JSON.stringify(currentSchemas))
        }}
        validateRef={validateRef}
        showDebug
      />
    </MemoryRouter>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────────

export function SurveyBuilderTab() {
  useRenderDebug('SurveyBuilderTab')
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/builder' })

  const { data: project } = useProject(slug)
  const { data: survey } = useSurvey(slug, surveySlug)

  const projectId = project?.id ?? null
  // useSurvey returns no id in design-preview/auth-bypass mode — fall back to survey_id from versions
  const surveyIdFromSurvey = survey?.id ?? null

  const canEdit    = useHasProjectPermission(projectId, 'survey:edit')
  const canPublish = useHasProjectPermission(projectId, 'survey:publish')
  const canArchive = useHasProjectPermission(projectId, 'survey:archive')

  const { data: versions = [], isLoading: versionsLoading } = useSurveyVersions(projectId ?? 0, surveyIdFromSurvey ?? 0)

  const [toast, setToast] = useState<{ variant: ToastVariant; message: string } | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  function showToast(variant: ToastVariant, message: string) {
    setToast({ variant, message })
  }

  const surveyId = surveyIdFromSurvey ?? versions[0]?.survey_id ?? 0

  const createVersion  = useCreateSurveyVersion(projectId ?? 0, surveyId)
  const copyToDraft    = useCopyVersionToDraft(projectId ?? 0, surveyId)
  const publishVersion = usePublishSurveyVersion(projectId ?? 0, surveyId)
  const archiveVersion = useArchiveSurveyVersion(projectId ?? 0, surveyId)

  const readyToMutate = projectId != null && surveyId > 0

  const nodeSaveRef = useRef<() => Promise<void>>(async () => {})

  const draftVersion     = versions.find((v) => v.status === 'draft')
  const publishedVersion = versions.find((v) => v.status === 'published')

  const defaultSelected = draftVersion ?? publishedVersion ?? versions[0]
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const selectedVersion = selectedId != null
    ? (versions.find((v) => v.id === selectedId) ?? defaultSelected)
    : defaultSelected

  const [isDirty, setIsDirty] = useState(false)
  // When the user tries to switch versions while dirty, we hold the target here
  // and show the unsaved-changes modal instead of switching immediately.
  const [pendingSwitchId, setPendingSwitchId] = useState<number | null>(null)

  function requestSelectVersion(id: number) {
    if (isDirty && selectedVersion?.status === 'draft' && id !== selectedVersion?.id) {
      setPendingSwitchId(id)
    } else {
      setSelectedId(id)
    }
  }

  function confirmSwitch() {
    if (pendingSwitchId == null) return
    if (selectedVersion) clearLocalDraft(selectedVersion.id)
    setIsDirty(false)
    setSelectedId(pendingSwitchId)
    setPendingSwitchId(null)
  }

  async function saveAndSwitch() {
    if (pendingSwitchId == null) return
    await nodeSaveRef.current()
    // handleSave clears the draft and sets isDirty false on success; just switch.
    setSelectedId(pendingSwitchId)
    setPendingSwitchId(null)
  }

  function cancelSwitch() {
    setPendingSwitchId(null)
  }

  function handleCreateDraft() {
    if (!readyToMutate) return
    createVersion.mutate(undefined, {
      onSuccess: (v) => { setSelectedId(v.id); showToast('success', 'New draft created.') },
      onError: () => showToast('error', 'Failed to create draft.'),
    })
  }

  function handleCopyToDraft() {
    if (!readyToMutate || !selectedVersion) return
    copyToDraft.mutate(selectedVersion.version_number, {
      onSuccess: (v) => { setSelectedId(v.id); showToast('success', `v${selectedVersion.version_number} duplicated to new draft.`) },
      onError: () => showToast('error', 'Failed to duplicate version.'),
    })
  }

  function handlePublish() {
    if (!readyToMutate || !draftVersion) return
    publishVersion.mutate(draftVersion.version_number, {
      onSuccess: () => showToast('success', `v${draftVersion.version_number} published.`),
      onError: () => showToast('error', 'Failed to publish.'),
    })
  }

  function handleArchive() {
    if (!readyToMutate || !selectedVersion || selectedVersion.status !== 'published') return
    archiveVersion.mutate(selectedVersion.version_number, {
      onSuccess: () => showToast('success', `v${selectedVersion.version_number} archived.`),
      onError: () => showToast('error', 'Failed to archive version.'),
    })
  }

  if (versionsLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner size={20} />
      </div>
    )
  }

  if (versions.length === 0) {
    return (
      <NoVersionsPanel
        onCreateDraft={handleCreateDraft}
        isCreating={createVersion.isPending}
        canEdit={canEdit}
      />
    )
  }

  const showBuilder = selectedVersion?.status === 'draft'
  const showPublishedNoDraft = selectedVersion?.status === 'published' && !draftVersion

  return (
    <section className="grid gap-0">
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 max-w-sm">
          <Toast variant={toast.variant} onClose={() => setToast(null)}>
            {toast.message}
          </Toast>
        </div>
      )}

      <Modal
        open={pendingSwitchId != null}
        onClose={cancelSwitch}
        title="Unsaved changes"
        width={420}
        footer={(
          <div className="flex w-full items-center justify-between gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={cancelSwitch}>
              Keep editing
            </Button>
            <div className="flex gap-2">
              <Button type="button" variant="secondary" size="sm" onClick={confirmSwitch}>
                Discard changes
              </Button>
              <Button type="button" variant="primary" size="sm" disabled={isSaving} onClick={() => void saveAndSwitch()}>
                {isSaving ? 'Saving…' : 'Save and switch'}
              </Button>
            </div>
          </div>
        )}
      >
        <p className="text-sm text-muted-foreground">
          You have unsaved changes to this draft. What would you like to do before switching versions?
        </p>
      </Modal>

      <VersionToolbar
        versions={versions}
        selectedVersion={selectedVersion}
        onSelectVersion={(v) => requestSelectVersion(v.id)}
        onCreateDraft={handleCreateDraft}
        isCreating={createVersion.isPending}
        onCopyToDraft={handleCopyToDraft}
        isCopying={copyToDraft.isPending}
        onSave={() => void nodeSaveRef.current()}
        isSaving={isSaving}
        onPublish={handlePublish}
        isPublishing={publishVersion.isPending}
        onArchive={handleArchive}
        canEdit={canEdit}
        canPublish={canPublish}
        canArchive={canArchive}
      />

      {showBuilder && selectedVersion ? (
        <ConnectedNodePage
          key={selectedVersion.id}
          projectId={projectId!}
          surveyId={surveyId}
          versionId={selectedVersion.id}
          versionNumber={selectedVersion.version_number}
          onSaveStart={() => setIsSaving(true)}
          onSaveSuccess={() => { setIsSaving(false); showToast('success', 'Draft saved.') }}
          onSaveError={() => { setIsSaving(false); showToast('error', 'Failed to save.') }}
          onValidationFail={() => showToast('error', 'Fix the highlighted fields before saving.')}
          onDirtyChange={setIsDirty}
          saveRef={nodeSaveRef}
        />
      ) : showPublishedNoDraft ? (
        <PublishedNoDraftPanel
          publishedVersion={selectedVersion}
          onCopyToDraft={handleCopyToDraft}
          isCopying={copyToDraft.isPending}
          canEdit={canEdit}
        />
      ) : selectedVersion?.status === 'archived' ? (
        <div className="px-6 py-8 md:px-16">
          <Card tone="muted" size="sm">
            <p className="text-sm text-muted-foreground">
              v{selectedVersion.version_number} is archived. Select a draft or published version to edit, or create a new draft.
            </p>
          </Card>
        </div>
      ) : null}
    </section>
  )
}
