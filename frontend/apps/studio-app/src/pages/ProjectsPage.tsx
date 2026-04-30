import { useState } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { Button, Card, CardStack, Modal, Spinner } from '@flowform/ui'
import { useCreateProject, useProjects } from '@/api/projects'
import { CreateProjectForm } from '@/components/CreateProjectForm'

export function ProjectsPage() {
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

    closeCreateModal()
    await navigate({ to: '/projects/$slug', params: { slug: project.slug } })
  }

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <div className="flex items-center justify-between gap-4">
        <h1>Projects</h1>
        <Button variant="primary" onClick={() => setCreateOpen(true)}>
          New project
        </Button>
      </div>

      <CardStack className="mt-8">
        {isPending && (
          <div className="flex items-center gap-3 text-muted-foreground">
            <Spinner size={16} />
            <span className="text-sm">Loading projects…</span>
          </div>
        )}

        {isError && (
          <Card tone="muted">
            <p className="text-sm text-destructive">{error.message}</p>
          </Card>
        )}

        {projects?.length === 0 && (
          <Card tone="muted">
            <p className="text-muted-foreground text-sm">No projects yet.</p>
          </Card>
        )}

        {projects?.map((project) => (
          <Link
            key={project.id}
            to="/projects/$slug"
            params={{ slug: project.slug }}
            className="block no-underline"
          >
            <Card className="hover:border-ring/60 transition-colors cursor-pointer">
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
            <Card tone="muted">
              <p className="text-sm text-destructive">{createProject.error.message}</p>
            </Card>
          )}
          <CreateProjectForm onSubmit={handleCreateProject} />
        </div>
      </Modal>
    </main>
  )
}
