import { useState } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { Button, Card, CardStack, Modal, Toast } from '@flowform/ui'
import { useCreateProject, useProjects } from '@/api/projects/hooks'
import { CreateProjectForm } from '@/components/CreateProjectForm'
import { useRenderDebug } from '@/debug/useRenderDebug'

function ProjectCardSkeleton() {
  return (
    <Card tone="muted">
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 space-y-2">
          <div className="h-4 w-1/3 animate-pulse rounded bg-muted-foreground/20" />
          <div className="h-3 w-1/4 animate-pulse rounded bg-muted-foreground/10" />
        </div>
      </div>
    </Card>
  )
}

export function ProjectsPage() {
  useRenderDebug('ProjectsPage')
  const navigate = useNavigate()
  const { data: projects, isPending, isError, error } = useProjects()
  const createProject = useCreateProject()
  const [createOpen, setCreateOpen] = useState(false)

  const closeCreateModal = () => {
    setCreateOpen(false)
    createProject.reset()
  }

  const handleCreateProject = async (data: { name: string; slug: string; description?: string }) => {
    const project = await createProject.mutateAsync({
      name: data.name,
      slug: data.slug,
    })

    sessionStorage.setItem('flowform:project-created', project.name)
    closeCreateModal()
    await navigate({ to: '/projects/$slug', params: { slug: project.slug } })
  }

  return (
    <main className="page-main">
      <div className="flex items-center justify-between gap-4">
        <h1>Projects</h1>
        <Button variant="primary" onClick={() => setCreateOpen(true)}>
          New project
        </Button>
      </div>

      <CardStack className="mt-8">
        {isPending && (
          <>
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
          </>
        )}

        {isError && (
          <Card tone="muted">
            <p className="text-sm text-destructive">{error.message}</p>
          </Card>
        )}

        {projects?.length === 0 && (
          <Card tone="muted">
            <div className="flex flex-col items-start gap-3 py-2">
              <div>
                <p className="font-semibold text-foreground">No projects yet</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Create your first project to start designing surveys and collecting responses.
                </p>
              </div>
              <Button variant="primary" size="sm" icon="plus" onClick={() => setCreateOpen(true)}>
                New project
              </Button>
            </div>
          </Card>
        )}

        {projects?.map((project) => (
          <Link
            key={project.id}
            to="/projects/$slug"
            params={{ slug: project.slug }}
            className="block no-underline"
          >
            <Card interactive>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="font-semibold text-foreground">{project.name}</p>
                  <p className="text-sm text-muted-foreground mt-0.5">{project.slug}</p>
                </div>
                <span className="text-muted-foreground text-sm shrink-0">→</span>
              </div>
            </Card>
          </Link>
        ))}
      </CardStack>

      <Modal open={createOpen} onClose={closeCreateModal} title="New project">
        <div className="flex flex-col gap-4">
          {createProject.isError && (
            <Toast variant="error" onClose={() => createProject.reset()}>
              {createProject.error?.message}
            </Toast>
          )}
          <CreateProjectForm onSubmit={handleCreateProject} />
        </div>
      </Modal>
    </main>
  )
}
