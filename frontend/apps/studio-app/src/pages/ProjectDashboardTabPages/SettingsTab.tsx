import { useEffect, useState } from 'react'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Button, Card, Input, Modal, Spinner, Toast } from '@flowform/ui'
import { useProject, useUpdateProject, useDeleteProject } from '@/api/project/projects/hooks'
import { useHasProjectPermission } from '@/api/project/permissions/hooks'
import { useRenderDebug } from '@/debug/useRenderDebug'

function toUrlSafeName(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-')
}

export function SettingsTab() {
  useRenderDebug('SettingsTab')
  const { slug } = useParams({ strict: false })
  const navigate = useNavigate()
  const { data: project, isLoading } = useProject(slug ?? null)
  const projectId = project?.id ?? null
  const canEdit = useHasProjectPermission(projectId, 'project:edit')
  const canDeleteProject = useHasProjectPermission(projectId, 'project:delete')

  const [draftName, setDraftName] = useState('')
  const [draftSlug, setDraftSlug] = useState('')
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  useEffect(() => {
    if (project) {
      setDraftName(project.name)
      setDraftSlug(project.slug)
    }
  }, [project])

  const updateProject = useUpdateProject(project?.id ?? 0)
  const deleteProject = useDeleteProject()

  const hasChanges = project
    ? draftName.trim() !== project.name || draftSlug !== project.slug
    : false
  const canSave = Boolean(draftName.trim() && draftSlug && hasChanges)
  const canDelete = deleteConfirm.trim() === project?.name

  const saveSettings = async () => {
    if (!canSave || !project) return
    setSaveError(null)
    setSaveSuccess(false)
    try {
      const updated = await updateProject.mutateAsync({ name: draftName.trim(), slug: draftSlug })
      setSaveSuccess(true)
      if (updated.slug !== project.slug) {
        void navigate({ to: '/projects/$slug/settings', params: { slug: updated.slug } })
      }
    } catch {
      setSaveError('Changes could not be saved. Please try again.')
    }
  }

  const handleDelete = async () => {
    if (!canDelete || !project) return
    setDeleteError(null)
    try {
      await deleteProject.mutateAsync(project.id)
      setDeleteOpen(false)
      void navigate({ to: '/projects' })
    } catch {
      setDeleteError('Project could not be deleted. Please try again.')
    }
  }

  if (isLoading) {
    return <div className="flex justify-center py-10"><Spinner size={24} /></div>
  }

  return (
    <section className="grid gap-6 mx-auto max-w-4xl">
      <div>
        <h2 className="text-base font-semibold">Settings</h2>
        <p className="text-sm text-muted-foreground">Manage project identity and destructive actions.</p>
      </div>

      {saveSuccess && <Toast variant="success" onClose={() => setSaveSuccess(false)}>Project settings saved.</Toast>}
      {saveError && <Toast variant="error" onClose={() => setSaveError(null)}>{saveError}</Toast>}

      {canEdit && (
        <Card>
          <section className="grid gap-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Project details</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Update the display title and the URL-safe project name.
              </p>
            </div>

            <div className="grid max-w-xl gap-4">
              <Input
                label="Project title"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                placeholder="Project title"
              />
              <Input
                label="URL-safe name"
                value={draftSlug}
                onChange={(e) => setDraftSlug(toUrlSafeName(e.target.value))}
                placeholder="project-url-name"
              />
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={() => { setDraftName(project?.name ?? ''); setDraftSlug(project?.slug ?? '') }}
                disabled={!hasChanges || updateProject.isPending}
              >
                Reset
              </Button>
              <Button variant="primary" onClick={saveSettings} disabled={!canSave || updateProject.isPending}>
                Save changes
              </Button>
            </div>
          </section>
        </Card>
      )}

      {canDeleteProject && (
        <section className="grid gap-4 rounded-sm border border-destructive/30 bg-destructive/5 p-5">
          <div>
            <h3 className="text-sm font-semibold text-destructive">Danger zone</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Delete this project and remove access to its surveys, members, and roles.
            </p>
          </div>
          <div>
            <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
              Delete project
            </Button>
          </div>
        </section>
      )}

      <Modal
        open={deleteOpen}
        onClose={() => { setDeleteOpen(false); setDeleteConfirm(''); setDeleteError(null) }}
        title="Delete project"
        width={480}
        footer={(
          <>
            <Button variant="secondary" className="mr-auto" onClick={() => { setDeleteOpen(false); setDeleteConfirm('') }}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={!canDelete || deleteProject.isPending}>
              Delete project
            </Button>
          </>
        )}
      >
        <div className="grid gap-4">
          {deleteError && <Toast variant="error" onClose={() => setDeleteError(null)}>{deleteError}</Toast>}
          <p className="text-sm leading-6 text-muted-accent-foreground">
            Type <span className="text-foreground">"{project?.name}"</span> to confirm deleting this project.
          </p>
          <Input
            label="Project title"
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
            placeholder={project?.name}
          />
        </div>
      </Modal>
    </section>
  )
}
