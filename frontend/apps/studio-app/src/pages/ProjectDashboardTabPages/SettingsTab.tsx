import { useState } from 'react'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Button, Card, Input, Modal } from '@flowform/ui'
import { useRenderDebug } from '@/debug/useRenderDebug'

function titleFromSlug(slug: string | undefined) {
  if (!slug) return 'Untitled project'
  return slug
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

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
  const [projectTitle, setProjectTitle] = useState(() => titleFromSlug(slug))
  const [urlSafeName, setUrlSafeName] = useState(() => toUrlSafeName(slug ?? '') || 'untitled-project')
  const [draftTitle, setDraftTitle] = useState(projectTitle)
  const [draftUrlSafeName, setDraftUrlSafeName] = useState(urlSafeName)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState('')

  const trimmedTitle = draftTitle.trim()
  const hasChanges = trimmedTitle !== projectTitle || draftUrlSafeName !== urlSafeName
  const canSave = Boolean(trimmedTitle && draftUrlSafeName && hasChanges)
  const canDelete = deleteConfirm.trim() === projectTitle

  const saveSettings = () => {
    if (!canSave) return
    setProjectTitle(trimmedTitle)
    setUrlSafeName(draftUrlSafeName)
  }

  const resetSettings = () => {
    setDraftTitle(projectTitle)
    setDraftUrlSafeName(urlSafeName)
  }

  const deleteProject = () => {
    if (!canDelete) return
    setDeleteOpen(false)
    setDeleteConfirm('')
    navigate({ to: '/projects' })
  }

  return (
    <section className="grid gap-6 mx-auto max-w-4xl">
      <div>
        <h2 className="text-base font-semibold">Settings</h2>
        <p className="text-sm text-muted-foreground">Manage project identity and destructive actions.</p>
      </div>

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
              value={draftTitle}
              onChange={(event) => setDraftTitle(event.target.value)}
              placeholder="Project title"
            />
            <Input
              label="URL-safe name"
              value={draftUrlSafeName}
              onChange={(event) => setDraftUrlSafeName(toUrlSafeName(event.target.value))}
              placeholder="project-url-name"
            />
          </div>

          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={resetSettings} disabled={!hasChanges}>
              Reset
            </Button>
            <Button variant="primary" onClick={saveSettings} disabled={!canSave}>
              Save changes
            </Button>
          </div>
        </section>
      </Card>

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

      <Modal
        open={deleteOpen}
        onClose={() => {
          setDeleteOpen(false)
          setDeleteConfirm('')
        }}
        title="Delete project"
        width={480}
        footer={(
          <>
            <Button
              variant="secondary"
              className="mr-auto"
              onClick={() => {
                setDeleteOpen(false)
                setDeleteConfirm('')
              }}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={deleteProject} disabled={!canDelete}>
              Delete project
            </Button>
          </>
        )}
      >
        <div className="grid gap-4">
          <p className="text-sm leading-6 text-muted-accent-foreground">
            Type <span className="text-foreground">"{projectTitle}"</span> to confirm deleting this project.
          </p>
          <Input
            label="Project title"
            value={deleteConfirm}
            onChange={(event) => setDeleteConfirm(event.target.value)}
            placeholder={projectTitle}
          />
        </div>
      </Modal>
    </section>
  )
}
