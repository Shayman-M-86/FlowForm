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
import type { NodeOut } from '@/api/hooks/nodes'
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
const SORT_KEY_STEP = 100000

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

function backendNodesToSurveyNodes(nodes: NodeOut[]): SurveyNode[] {
  return [...nodes]
    .sort((a, b) => a.sort_key - b.sort_key)
    .map((n) => ({
      type: n.node_type as 'question' | 'rule',
      sort_key: n.sort_key,
      content: n.question_schema as never,
    }))
}

function normalizeNodeContentForDirty(content: SurveyNode['content']) {
  if (!content || typeof content !== 'object') return content
  const normalized = structuredClone(content) as unknown as Record<string, unknown>

  if (
    ['choice', 'field', 'matching', 'rating'].includes(String(normalized.family)) &&
    normalized.title == null
  ) {
    normalized.title = ''
  }

  if (normalized.family === 'field') {
    const definition = normalized.definition as { field_type?: string; ui?: { placeholder?: string } } | undefined
    if (definition) {
      const placeholderByType: Record<string, string> = {
        short_text: 'Type a short response',
        long_text: 'Type a longer response',
        email: 'name@example.com',
        phone: '(555) 123-4567',
        number: 'Enter a number',
      }
      if (definition.field_type === 'date') {
        definition.ui = definition.ui ?? {}
      } else if (definition.field_type && definition.ui?.placeholder == null) {
        definition.ui = { ...definition.ui, placeholder: placeholderByType[definition.field_type] ?? '' }
      }
    }
  }

  if (normalized.family === 'rating') {
    const definition = normalized.definition as { variant?: string; words?: boolean } | undefined
    if (definition?.variant === 'emoji' && definition.words == null) {
      definition.words = true
    }
  }

  if ('else' in normalized && normalized.else == null) {
    delete normalized.else
  }

  return normalized
}

function normalizedDirtyNodes(nodes: SurveyNode[]) {
  return nodes.map((node) => ({
    type: node.type,
    content: normalizeNodeContentForDirty(node.content),
  }))
}

function hasUnsavedNodeChanges(nodes: SurveyNode[], backendNodes: SurveyNode[]) {
  return findFirstDifference(normalizedDirtyNodes(nodes), normalizedDirtyNodes(backendNodes)) !== null
}

function nodeDebugSummary(nodes: SurveyNode[]) {
  return nodes.map((node, index) => ({
    index,
    type: node.type,
    sort_key: node.sort_key,
    id: node.content.id,
    family: 'family' in node.content ? node.content.family : 'rule',
  }))
}

function findFirstDifference(left: unknown, right: unknown, path = '$'): { path: string; current: unknown; backend: unknown } | null {
  if (Object.is(left, right)) return null

  if (
    left == null ||
    right == null ||
    typeof left !== 'object' ||
    typeof right !== 'object'
  ) {
    return { path, current: left, backend: right }
  }

  if (Array.isArray(left) || Array.isArray(right)) {
    if (!Array.isArray(left) || !Array.isArray(right)) {
      return { path, current: left, backend: right }
    }

    const length = Math.max(left.length, right.length)
    for (let index = 0; index < length; index += 1) {
      const difference = findFirstDifference(left[index], right[index], `${path}[${index}]`)
      if (difference) return difference
    }
    return null
  }

  const leftRecord = left as Record<string, unknown>
  const rightRecord = right as Record<string, unknown>
  const keys = Array.from(new Set([...Object.keys(leftRecord), ...Object.keys(rightRecord)])).sort()

  for (const key of keys) {
    const difference = findFirstDifference(leftRecord[key], rightRecord[key], `${path}.${key}`)
    if (difference) return difference
  }

  return null
}

function dirtyDebugDetails(nodes: SurveyNode[], backendNodes: SurveyNode[]) {
  const currentNormalizedNodes = normalizedDirtyNodes(nodes)
  const backendNormalizedNodes = normalizedDirtyNodes(backendNodes)
  const currentSnapshot = JSON.stringify(currentNormalizedNodes)
  const backendSnapshot = JSON.stringify(backendNormalizedNodes)
  const firstDifference = findFirstDifference(currentNormalizedNodes, backendNormalizedNodes)
  return {
    dirty: firstDifference !== null,
    firstDifference,
    currentNodes: nodeDebugSummary(nodes),
    backendNodes: nodeDebugSummary(backendNodes),
    currentSnapshot,
    backendSnapshot,
  }
}

function debugSurveyBuilder(message: string, details?: Record<string, unknown>) {
  if (!import.meta.env.DEV) return
  console.debug(`[SurveyBuilderTab] ${message}`, details ?? {})
}

type SortKeyPlanEntry = {
  node: SurveyNode
  index: number
  existing?: NodeOut
}

function findStableSortKeyAnchors(entries: SortKeyPlanEntry[]) {
  const candidates = entries
    .filter((entry): entry is SortKeyPlanEntry & { existing: NodeOut } => Boolean(entry.existing))

  if (candidates.length === 0) return new Set<number>()

  const lengths = Array(candidates.length).fill(1) as number[]
  const previous = Array(candidates.length).fill(-1) as number[]
  let bestIndex = 0

  for (let index = 0; index < candidates.length; index += 1) {
    for (let before = 0; before < index; before += 1) {
      if (
        candidates[before].existing.sort_key < candidates[index].existing.sort_key &&
        lengths[before] + 1 > lengths[index]
      ) {
        lengths[index] = lengths[before] + 1
        previous[index] = before
      }
    }

    if (lengths[index] > lengths[bestIndex]) {
      bestIndex = index
    }
  }

  const anchors = new Set<number>()
  for (let cursor = bestIndex; cursor !== -1; cursor = previous[cursor]) {
    anchors.add(candidates[cursor].index)
  }
  return anchors
}

function findFreeSortKey({
  preferred,
  minimum,
  maximum,
  occupied,
  allowedOwner,
}: {
  preferred: number
  minimum: number
  maximum: number
  occupied: Map<number, string>
  allowedOwner?: string
}) {
  for (let key = Math.max(preferred, minimum); key <= maximum; key += 1) {
    const owner = occupied.get(key)
    if (!owner || owner === allowedOwner) return key
  }
  for (let key = Math.min(preferred - 1, maximum); key >= minimum; key -= 1) {
    const owner = occupied.get(key)
    if (!owner || owner === allowedOwner) return key
  }
  return null
}

function assignSortKeysBetweenAnchors({
  entries,
  lower,
  upper,
  occupied,
  plan,
}: {
  entries: SortKeyPlanEntry[]
  lower: number
  upper: number | null
  occupied: Map<number, string>
  plan: Map<string, number>
}) {
  if (entries.length === 0) return true

  let previous = lower
  if (upper == null) {
    for (const entry of entries) {
      const key = findFreeSortKey({
        preferred: previous + SORT_KEY_STEP,
        minimum: previous + 1,
        maximum: Number.MAX_SAFE_INTEGER,
        occupied,
        allowedOwner: entry.existing?.question_key,
      })
      if (key == null) return false
      plan.set(entry.node.content.id, key)
      previous = key
    }
    return true
  }

  if (upper - lower <= entries.length) return false

  for (let index = 0; index < entries.length; index += 1) {
    const remaining = entries.length - index - 1
    const maximum = upper - remaining - 1
    const preferred = previous + Math.floor((upper - previous) / (remaining + 2))
    const key = findFreeSortKey({
      preferred,
      minimum: previous + 1,
      maximum,
      occupied,
      allowedOwner: entries[index].existing?.question_key,
    })
    if (key == null) return false
    plan.set(entries[index].node.content.id, key)
    previous = key
  }

  return true
}

function createHighSortKeyPlan(nodes: SurveyNode[], current: NodeOut[]) {
  const plan = new Map<string, number>()
  const maxSortKey = Math.max(
    0,
    ...current.map((node) => node.sort_key),
    ...nodes.map((node) => node.sort_key),
  )

  nodes.forEach((node, index) => {
    plan.set(node.content.id, maxSortKey + SORT_KEY_STEP * (index + 1))
  })
  return plan
}

function planSortKeysForSave(nodes: SurveyNode[], current: NodeOut[]) {
  const entries = nodes.map((node, index) => ({
    node,
    index,
    existing: current.find((backendNode) => backendNode.question_key === node.content.id),
  }))
  const incomingKeys = new Set(nodes.map((node) => node.content.id))
  const occupied = new Map(
    current
      .filter((node) => incomingKeys.has(node.question_key))
      .map((node) => [node.sort_key, node.question_key] as const),
  )
  const anchors = findStableSortKeyAnchors(entries)
  const plan = new Map<string, number>()
  let lower = 0
  let pending: SortKeyPlanEntry[] = []

  for (const entry of entries) {
    if (anchors.has(entry.index) && entry.existing) {
      if (!assignSortKeysBetweenAnchors({
        entries: pending,
        lower,
        upper: entry.existing.sort_key,
        occupied,
        plan,
      })) {
        return createHighSortKeyPlan(nodes, current)
      }
      plan.set(entry.node.content.id, entry.existing.sort_key)
      lower = entry.existing.sort_key
      pending = []
      continue
    }

    pending.push(entry)
  }

  if (!assignSortKeysBetweenAnchors({ entries: pending, lower, upper: null, occupied, plan })) {
    return createHighSortKeyPlan(nodes, current)
  }

  return plan
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
  const [savedNodesOverride, setSavedNodesOverride] = useState<SurveyNode[] | null>(null)
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
    const sortKeyPlan = planSortKeysForSave(nodes, current)
    const plannedNodes = nodes.map((node) => ({
      ...node,
      sort_key: sortKeyPlan.get(node.content.id) ?? node.sort_key,
    }))
    const existingNodes = nodes
      .map((node) => ({ node, existing: byKey.get(node.content.id) }))
      .filter((entry): entry is { node: SurveyNode; existing: NodeOut } => Boolean(entry.existing))
    const newNodes = nodes.filter((node) => !byKey.has(node.content.id))

    // Delete first so recreated nodes can reuse the old key/sort slot.
    for (const backendNode of current) {
      if (!incomingKeys.has(backendNode.question_key)) {
        await deleteNode.mutateAsync(backendNode.id)
      }
    }

    for (const { node, existing } of existingNodes) {
      const plannedSortKey = sortKeyPlan.get(node.content.id) ?? node.sort_key
      const contentChanged = findFirstDifference(
        normalizeNodeContentForDirty(existing.question_schema as unknown as SurveyNode['content']),
        normalizeNodeContentForDirty(node.content),
      ) !== null
      if (existing.sort_key !== plannedSortKey || contentChanged) {
        await updateNode.mutateAsync({
          nodeId: existing.id,
          body: { sort_key: plannedSortKey, content: node.content as never },
        })
      }
    }

    for (const node of newNodes) {
      await createNode.mutateAsync({
        type: node.type,
        sort_key: sortKeyPlan.get(node.content.id) ?? node.sort_key,
        content: node.content as never,
      })
    }

    return plannedNodes
  }, [createNode, updateNode, deleteNode])

  const handleSave = useCallback(async () => {
    if (validateRef.current && !validateRef.current()) {
      onValidationFail()
      return
    }
    onSaveStart()
    try {
      const savedNodes = await syncToBackend(latestNodesRef.current)
      latestNodesRef.current = savedNodes
      setSavedNodesOverride(savedNodes)
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
    const initial = backendNodesToSurveyNodes(backendNodes)
    setSavedNodesOverride((current) => (
      current && !hasUnsavedNodeChanges(current, initial) ? null : current
    ))
    const localDetails = local ? dirtyDebugDetails(local, initial) : null
    debugSurveyBuilder('hydrating builder nodes', {
      versionId,
      versionNumber,
      backendNodeCount: initial.length,
      hasLocalDraft: Boolean(local),
      localDraftDirty: localDetails?.dirty ?? false,
      localDraftDetails: localDetails,
    })

    if (local && localDetails?.dirty) {
      latestNodesRef.current = local
      onDirtyChangeRef.current(true)
    } else {
      if (local) clearLocalDraft(versionId)
      latestNodesRef.current = initial
      onDirtyChangeRef.current(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [versionId, backendNodesJson])

  const initialNodes: SurveyNode[] | undefined = savedNodesOverride ?? (backendNodes ? backendNodesToSurveyNodes(backendNodes) : undefined)

  if (isLoading || !initialNodes) {
    return (
      <div className="flex justify-center py-16">
        <Spinner size={20} />
      </div>
    )
  }

  const localDraft = loadLocalDraft(versionId)
  const seedNodes = localDraft && hasUnsavedNodeChanges(localDraft, initialNodes) ? localDraft : initialNodes

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
          const dirty = hasUnsavedNodeChanges(
            nodes,
            backendNodesToSurveyNodes(backendNodesRef.current ?? []),
          )
          debugSurveyBuilder('builder emitted node changes', {
            versionId,
            versionNumber,
            ...dirtyDebugDetails(nodes, backendNodesToSurveyNodes(backendNodesRef.current ?? [])),
          })
          if (dirty) {
            saveLocalDraft(versionId, nodes)
          } else {
            clearLocalDraft(versionId)
          }
          onDirtyChangeRef.current(dirty)
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

  const handleDirtyChange = useCallback((dirty: boolean) => {
    debugSurveyBuilder('dirty state update requested', {
      dirty,
      selectedVersionId: selectedVersion?.id,
      selectedVersionNumber: selectedVersion?.version_number,
      selectedVersionStatus: selectedVersion?.status,
    })
    setIsDirty(dirty)
  }, [selectedVersion?.id, selectedVersion?.version_number, selectedVersion?.status])

  function requestSelectVersion(id: number) {
    const targetVersion = versions.find((v) => v.id === id)
    const willOpenModal = isDirty && selectedVersion?.status === 'draft' && id !== selectedVersion?.id
    debugSurveyBuilder('version selection requested', {
      targetVersionId: id,
      targetVersionNumber: targetVersion?.version_number,
      targetVersionStatus: targetVersion?.status,
      selectedVersionId: selectedVersion?.id,
      selectedVersionNumber: selectedVersion?.version_number,
      selectedVersionStatus: selectedVersion?.status,
      isDirty,
      willOpenModal,
    })

    if (isDirty && selectedVersion?.status === 'draft' && id !== selectedVersion?.id) {
      setPendingSwitchId(id)
    } else {
      setSelectedId(id)
    }
  }

  useEffect(() => {
    if (pendingSwitchId == null) return
    const targetVersion = versions.find((v) => v.id === pendingSwitchId)
    debugSurveyBuilder('unsaved changes modal opened', {
      pendingSwitchId,
      targetVersionNumber: targetVersion?.version_number,
      targetVersionStatus: targetVersion?.status,
      selectedVersionId: selectedVersion?.id,
      selectedVersionNumber: selectedVersion?.version_number,
      selectedVersionStatus: selectedVersion?.status,
      isDirty,
    })
  }, [pendingSwitchId, selectedVersion?.id, selectedVersion?.status, selectedVersion?.version_number, versions, isDirty])

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
          onDirtyChange={handleDirtyChange}
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
