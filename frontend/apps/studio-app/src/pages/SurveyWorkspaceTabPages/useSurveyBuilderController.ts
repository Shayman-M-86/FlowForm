import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'
import { findIncompleteNodeIds, type SurveyNode } from '@flowform/builder'
import type { ToastVariant } from '@flowform/ui'
import { useProject } from '@/api/hooks/projects'
import { useSurvey } from '@/api/hooks/surveys'
import { useHasProjectPermission } from '@/api/hooks/permissions'
import {
  useArchiveSurveyVersion,
  useCopyVersionToDraft,
  useCreateSurveyVersion,
  usePublishSurveyVersion,
  useSurveyVersions,
  type SurveyVersionOut,
} from '@/api/hooks/versions'
import {
  nodeKeys,
  useCreateNode,
  useDeleteNode,
  useSurveyNodes,
  useUpdateNode,
  type NodeOut,
} from '@/api/hooks/nodes'
import type { components } from '@/api/generated/schema'
import {
  clearSurveyBuilderDraft,
  loadSurveyBuilderDraft,
  saveSurveyBuilderDraft,
} from '@/lib/storage'

const SORT_KEY_STEP = 100_000

type ToastState = {
  variant: ToastVariant
  message: string
}

type PendingSwitch = {
  versionId: number
}

type SaveNode = SurveyNode & { sort_key: number }
type NodeId = SurveyNode['id']

function logBuilderFailure(message: string, error: unknown, details?: Record<string, unknown>) {
  console.error(`[SurveyBuilder] ${message}`, { error, ...details })
}

function toSurveyNodes(nodes: NodeOut[] | undefined): SurveyNode[] {
  return [...(nodes ?? [])]
    .sort((left, right) => left.sort_key - right.sort_key)
    .map((node) => ({
      id: node.id,
      node_key: node.node_key,
      node_type: node.node_type,
      sort_key: node.sort_key,
      content: node.content,
    } as SurveyNode))
}

function normalizeForCompare(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(normalizeForCompare)
  if (!value || typeof value !== 'object') return value

  return Object.fromEntries(
    Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, entry]) => [key, normalizeForCompare(entry)]),
  )
}

function isEqual(left: unknown, right: unknown): boolean {
  return JSON.stringify(normalizeForCompare(left)) === JSON.stringify(normalizeForCompare(right))
}

function sortedNodes(nodes: SurveyNode[]): SurveyNode[] {
  return [...nodes].sort((left, right) => left.sort_key - right.sort_key)
}

function nextHighSortKey(nodes: SurveyNode[], backendNodes: NodeOut[]): number {
  const maxSortKey = Math.max(0, ...nodes.map((node) => node.sort_key), ...backendNodes.map((node) => node.sort_key))
  return maxSortKey + SORT_KEY_STEP
}

function planSortKeys(nodes: SurveyNode[], backendNodes: NodeOut[]): SaveNode[] {
  const sorted = sortedNodes(nodes)
  const backendById = new Map(backendNodes.map((node) => [node.id, node]))
  const backendByKey = new Map(backendNodes.map((node) => [node.node_key, node]))
  let nextNewSortKey = nextHighSortKey(nodes, backendNodes)

  return sorted.map((node) => {
    const existing = backendById.get(node.id) ?? backendByKey.get(node.node_key)
    if (existing) {
      return { ...node, sort_key: existing.sort_key }
    }

    const planned = { ...node, sort_key: nextNewSortKey }
    nextNewSortKey += SORT_KEY_STEP
    return planned
  })
}

function toUpdateBody(node: SaveNode): components['schemas']['UpdateNodeRequest'] {
  return {
    id: node.id,
    node_key: node.node_key,
    node_type: node.node_type,
    sort_key: node.sort_key,
    content: node.content,
  } as components['schemas']['UpdateNodeRequest']
}

function toCreateBody(node: SaveNode): components['schemas']['CreateNodeRequest'] {
  return {
    id: node.id,
    node_key: node.node_key,
    node_type: node.node_type,
    sort_key: node.sort_key,
    content: node.content,
  } as components['schemas']['CreateNodeRequest']
}

function hasNodeChanged(node: SaveNode, backendNode: NodeOut): boolean {
  return (
    node.node_key !== backendNode.node_key ||
    node.node_type !== backendNode.node_type ||
    node.sort_key !== backendNode.sort_key ||
    !isEqual(node.content, backendNode.content)
  )
}

function pickDefaultVersion(versions: SurveyVersionOut[]): SurveyVersionOut | undefined {
  return (
    versions.find((version) => version.status === 'draft') ??
    versions.find((version) => version.status === 'published') ??
    versions[0]
  )
}

export function useSurveyBuilderController() {
  const queryClient = useQueryClient()
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/builder' })
  const { data: project, isLoading: isProjectLoading, isError: isProjectError } = useProject(slug)
  const { data: survey, isLoading: isSurveyLoading, isError: isSurveyError } = useSurvey(slug, surveySlug)
  const projectId = project?.id ?? null
  const surveyId = survey?.id ?? (surveySlug != null && Number.isInteger(Number(surveySlug)) ? Number(surveySlug) : 0)

  const canEdit = useHasProjectPermission(projectId, 'survey:edit')
  const canPublish = useHasProjectPermission(projectId, 'survey:publish')
  const canArchive = useHasProjectPermission(projectId, 'survey:archive')

  const versionsQuery = useSurveyVersions(projectId ?? 0, surveyId)
  const versions = versionsQuery.data ?? []
  const defaultVersion = pickDefaultVersion(versions)

  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null)
  const selectedVersion = useMemo(() => {
    if (selectedVersionId != null) {
      return versions.find((version) => version.id === selectedVersionId) ?? defaultVersion
    }
    return defaultVersion
  }, [defaultVersion, selectedVersionId, versions])

  const nodesQuery = useSurveyNodes(projectId, surveyId > 0 ? surveyId : null, selectedVersion?.version_number ?? null)
  const backendNodes = nodesQuery.data ?? []

  const createVersion = useCreateSurveyVersion(projectId ?? 0, surveyId)
  const copyVersion = useCopyVersionToDraft(projectId ?? 0, surveyId)
  const publishVersion = usePublishSurveyVersion(projectId ?? 0, surveyId)
  const archiveVersionMutation = useArchiveSurveyVersion(projectId ?? 0, surveyId)
  const createNode = useCreateNode(projectId, surveyId > 0 ? surveyId : null, selectedVersion?.version_number ?? null)
  const updateNode = useUpdateNode(projectId, surveyId > 0 ? surveyId : null, selectedVersion?.version_number ?? null)
  const deleteNode = useDeleteNode(projectId, surveyId > 0 ? surveyId : null, selectedVersion?.version_number ?? null)

  const [nodes, setNodesState] = useState<SurveyNode[]>([])
  const [invalidNodeIds, setInvalidNodeIds] = useState<Set<NodeId>>(() => new Set())
  const [isSaving, setIsSaving] = useState(false)
  const [toast, setToast] = useState<ToastState | null>(null)
  const [pendingSwitch, setPendingSwitch] = useState<PendingSwitch | null>(null)
  const loadedVersionIdRef = useRef<number | null>(null)

  const backendSurveyNodes = useMemo(() => toSurveyNodes(backendNodes), [backendNodes])
  const isDraft = selectedVersion?.status === 'draft'
  const isDirty = isDraft ? !isEqual(sortedNodes(nodes), sortedNodes(backendSurveyNodes)) : false

  const clearCurrentDraft = useCallback(() => {
    if (projectId == null || surveyId <= 0 || selectedVersion == null) return
    clearSurveyBuilderDraft(projectId, surveyId, selectedVersion.id)
  }, [projectId, selectedVersion, surveyId])

  const showToast = useCallback((variant: ToastVariant, message: string) => {
    setToast({ variant, message })
  }, [])

  useEffect(() => {
    if (!selectedVersion || nodesQuery.isLoading) return
    if (loadedVersionIdRef.current === selectedVersion.id) return

    const backend = toSurveyNodes(backendNodes)
    if (selectedVersion.status === 'draft' && projectId != null && surveyId > 0) {
      const recovered = loadSurveyBuilderDraft(projectId, surveyId, selectedVersion.id)
      if (recovered && !isEqual(sortedNodes(recovered.nodes), sortedNodes(backend))) {
        setNodesState(recovered.nodes)
        loadedVersionIdRef.current = selectedVersion.id
        showToast('warning', 'Recovered unsaved builder changes.')
        return
      }
      clearSurveyBuilderDraft(projectId, surveyId, selectedVersion.id)
    }

    setNodesState(backend)
    loadedVersionIdRef.current = selectedVersion.id
  }, [backendNodes, nodesQuery.isLoading, projectId, selectedVersion, showToast, surveyId])

  const setNodes = useCallback((nextNodes: SurveyNode[]) => {
    setNodesState(nextNodes)
    // Once validation has been surfaced (a blocked save), keep the highlights in
    // sync as the user fills fields in — clearing each node as it becomes valid.
    setInvalidNodeIds((current) =>
      current.size === 0 ? current : findIncompleteNodeIds(nextNodes),
    )
    if (projectId == null || surveyId <= 0 || selectedVersion?.status !== 'draft') return

    const backend = toSurveyNodes(backendNodes)
    if (isEqual(sortedNodes(nextNodes), sortedNodes(backend))) {
      clearSurveyBuilderDraft(projectId, surveyId, selectedVersion.id)
    } else {
      saveSurveyBuilderDraft(projectId, surveyId, selectedVersion.id, nextNodes)
    }
  }, [backendNodes, projectId, selectedVersion, surveyId])

  const saveDraft = useCallback(async () => {
    if (!selectedVersion || selectedVersion.status !== 'draft' || projectId == null || surveyId <= 0) return

    const incomplete = findIncompleteNodeIds(nodes)
    if (incomplete.size > 0) {
      setInvalidNodeIds(incomplete)
      showToast('error', 'Fill in all required fields before saving.')
      throw new Error('Validation failed')
    }
    setInvalidNodeIds(new Set())

    setIsSaving(true)
    try {
      const plannedNodes = planSortKeys(nodes, backendNodes)
      const backendById = new Map(backendNodes.map((node) => [node.id, node]))
      const backendByKey = new Map(backendNodes.map((node) => [node.node_key, node]))
      const savedById = new Map(backendNodes.map((node) => [node.id, node]))
      const matchedBackendIds = new Set<NodeId>()

      for (const node of plannedNodes) {
        const existing = backendById.get(node.id) ?? backendByKey.get(node.node_key)
        if (existing) matchedBackendIds.add(existing.id)
      }

      for (const backendNode of backendNodes) {
        if (!matchedBackendIds.has(backendNode.id)) {
          await deleteNode.mutateAsync(backendNode.id)
          savedById.delete(backendNode.id)
        }
      }

      for (const node of plannedNodes) {
        const existing = backendById.get(node.id) ?? backendByKey.get(node.node_key)
        if (!existing) {
          const created = await createNode.mutateAsync(toCreateBody(node))
          savedById.set(created.id, created)
        } else if (hasNodeChanged(node, existing)) {
          const updated = await updateNode.mutateAsync({ nodeId: existing.id, body: toUpdateBody(node) })
          savedById.set(updated.id, updated)
        }
      }

      // The mutations already returned the authoritative server state for every
      // node, so seed the nodes-list cache directly instead of invalidating it —
      // that avoids a redundant refetch GET per saved node.
      const savedNodes = [...savedById.values()]
      queryClient.setQueryData<NodeOut[]>(
        nodeKeys.list(projectId, surveyId, selectedVersion.version_number),
        savedNodes,
      )

      clearSurveyBuilderDraft(projectId, surveyId, selectedVersion.id)
      setNodesState(toSurveyNodes(savedNodes))
      loadedVersionIdRef.current = selectedVersion.id
      showToast('success', 'Draft saved.')
    } catch (error) {
      logBuilderFailure('Failed to save draft.', error, {
        projectId,
        surveyId,
        versionId: selectedVersion.id,
        versionNumber: selectedVersion.version_number,
      })
      showToast('error', 'Failed to save draft.')
      throw new Error('Failed to save draft')
    } finally {
      setIsSaving(false)
    }
  }, [backendNodes, createNode, deleteNode, nodes, projectId, queryClient, selectedVersion, showToast, surveyId, updateNode])

  const selectVersion = useCallback((versionId: number) => {
    if (isDirty && selectedVersion?.status === 'draft' && versionId !== selectedVersion.id) {
      setPendingSwitch({ versionId })
      return
    }

    setSelectedVersionId(versionId)
    loadedVersionIdRef.current = null
  }, [isDirty, selectedVersion])

  const confirmSwitch = useCallback(() => {
    if (!pendingSwitch) return
    clearCurrentDraft()
    setSelectedVersionId(pendingSwitch.versionId)
    loadedVersionIdRef.current = null
    setPendingSwitch(null)
  }, [clearCurrentDraft, pendingSwitch])

  const cancelSwitch = useCallback(() => {
    setPendingSwitch(null)
  }, [])

  const saveAndSwitch = useCallback(async () => {
    if (!pendingSwitch) return
    await saveDraft()
    setSelectedVersionId(pendingSwitch.versionId)
    loadedVersionIdRef.current = null
    setPendingSwitch(null)
  }, [pendingSwitch, saveDraft])

  const createDraft = useCallback(async () => {
    if (projectId == null || surveyId <= 0) return
    try {
      const version = await createVersion.mutateAsync()
      // A freshly created draft is always empty, so prime the nodes cache with an
      // empty list instead of issuing a redundant fetch for content we know isn't there.
      queryClient.setQueryData<NodeOut[]>(
        nodeKeys.list(projectId, surveyId, version.version_number),
        [],
      )
      setSelectedVersionId(version.id)
      loadedVersionIdRef.current = null
      showToast('success', 'New draft created.')
    } catch (error) {
      logBuilderFailure('Failed to create draft.', error, { projectId, surveyId })
      showToast('error', 'Failed to create draft.')
    }
  }, [createVersion, projectId, queryClient, showToast, surveyId])

  const copyToDraft = useCallback(async () => {
    if (!selectedVersion || projectId == null || surveyId <= 0) return
    try {
      const version = await copyVersion.mutateAsync(selectedVersion.version_number)
      setSelectedVersionId(version.id)
      loadedVersionIdRef.current = null
      showToast('success', `v${selectedVersion.version_number} duplicated to a new draft.`)
    } catch (error) {
      logBuilderFailure('Failed to duplicate version.', error, {
        projectId,
        surveyId,
        versionId: selectedVersion.id,
        versionNumber: selectedVersion.version_number,
      })
      showToast('error', 'Failed to duplicate version.')
    }
  }, [copyVersion, projectId, selectedVersion, showToast, surveyId])

  const publishDraft = useCallback(async () => {
    if (!selectedVersion || selectedVersion.status !== 'draft' || projectId == null || surveyId <= 0) return
    try {
      if (isDirty) await saveDraft()
      await publishVersion.mutateAsync(selectedVersion.version_number)
      clearCurrentDraft()
      showToast('success', `v${selectedVersion.version_number} published.`)
    } catch (error) {
      logBuilderFailure('Failed to publish draft.', error, {
        projectId,
        surveyId,
        versionId: selectedVersion.id,
        versionNumber: selectedVersion.version_number,
      })
      showToast('error', 'Failed to publish draft.')
    }
  }, [clearCurrentDraft, isDirty, projectId, publishVersion, saveDraft, selectedVersion, showToast, surveyId])

  const archiveVersion = useCallback(async () => {
    if (!selectedVersion || selectedVersion.status !== 'published' || projectId == null || surveyId <= 0) return
    try {
      await archiveVersionMutation.mutateAsync(selectedVersion.version_number)
      clearCurrentDraft()
      showToast('success', `v${selectedVersion.version_number} archived.`)
    } catch (error) {
      logBuilderFailure('Failed to archive version.', error, {
        projectId,
        surveyId,
        versionId: selectedVersion.id,
        versionNumber: selectedVersion.version_number,
      })
      showToast('error', 'Failed to archive version.')
    }
  }, [archiveVersionMutation, clearCurrentDraft, projectId, selectedVersion, showToast, surveyId])

  const dismissToast = useCallback(() => setToast(null), [])

  return {
    versions,
    selectedVersion,
    selectVersion,
    nodes,
    setNodes,
    invalidNodeIds,
    isLoading: isProjectLoading || isSurveyLoading || versionsQuery.isLoading || nodesQuery.isLoading,
    isError: isProjectError || isSurveyError || versionsQuery.isError || nodesQuery.isError,
    isSaving,
    isCreating: createVersion.isPending,
    isCopying: copyVersion.isPending,
    isPublishing: publishVersion.isPending,
    isArchiving: archiveVersionMutation.isPending,
    canEdit,
    canPublish,
    canArchive,
    isDirty,
    pendingSwitch,
    confirmSwitch,
    cancelSwitch,
    saveAndSwitch,
    createDraft,
    copyToDraft,
    saveDraft,
    publishDraft,
    archiveVersion,
    toast,
    dismissToast,
  }
}
