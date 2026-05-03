import { useMemo, useState } from 'react'
import { useParams } from '@tanstack/react-router'
import { useProject } from '@/api/projects'
import { Spinner, Card, Button, Modal, Badge } from '@flowform/ui'

type SurveySummary = {
  id: number
  name: string
  status: 'Draft' | 'Published' | 'Paused'
  visibility: 'Private' | 'Link only' | 'Public'
  responses: number
  updatedAt: string
}

type Member = {
  id: number
  name: string
  email: string
  role: 'Owner' | 'Editor' | 'Viewer'
}

type Permission = {
  id: number
  subject: string
  action: 'View' | 'Edit' | 'Manage'
}

const surveys: SurveySummary[] = [
  {
    id: 1,
    name: 'Customer onboarding feedback',
    status: 'Published',
    visibility: 'Link only',
    responses: 128,
    updatedAt: 'Apr 30, 2026',
  },
  {
    id: 2,
    name: 'Product discovery intake',
    status: 'Draft',
    visibility: 'Private',
    responses: 0,
    updatedAt: 'Apr 28, 2026',
  },
  {
    id: 3,
    name: 'Quarterly account health check',
    status: 'Paused',
    visibility: 'Public',
    responses: 54,
    updatedAt: 'Apr 25, 2026',
  },
]

const initialMembers: Member[] = [
  { id: 1, name: 'Testing User', email: 'testing@flowform.local', role: 'Owner' },
  { id: 2, name: 'Amelia Chen', email: 'amelia@example.com', role: 'Editor' },
  { id: 3, name: 'Marcus Lee', email: 'marcus@example.com', role: 'Editor' },
  { id: 4, name: 'Priya Shah', email: 'priya@example.com', role: 'Viewer' },
  { id: 5, name: 'Nora Evans', email: 'nora@example.com', role: 'Viewer' },
]

const initialPermissions: Permission[] = [
  { id: 1, subject: 'Editors', action: 'Edit' },
  { id: 2, subject: 'Viewers', action: 'View' },
]

export function ProjectDashboardPage() {
  const { slug } = useParams({ from: '/projects/$slug/' })
  const { data: project, isPending, isError, error } = useProject(slug)
  const [members, setMembers] = useState(initialMembers)
  const [membersOpen, setMembersOpen] = useState(false)
  const [newMemberEmail, setNewMemberEmail] = useState('')
  const [newMemberRole, setNewMemberRole] = useState<Member['role']>('Viewer')
  const [permissions, setPermissions] = useState(initialPermissions)
  const [permissionsOpen, setPermissionsOpen] = useState(false)
  const [newPermissionSubject, setNewPermissionSubject] = useState('')
  const [newPermissionAction, setNewPermissionAction] = useState<Permission['action']>('View')

  const visibleMembers = useMemo(() => members.slice(0, 3), [members])

  const addMember = () => {
    const email = newMemberEmail.trim()
    if (!email) return

    const name = email.split('@')[0].replace(/[._-]+/g, ' ')
    setMembers((current) => [
      ...current,
      {
        id: Date.now(),
        name: name.replace(/\b\w/g, (letter) => letter.toUpperCase()),
        email,
        role: newMemberRole,
      },
    ])
    setNewMemberEmail('')
    setNewMemberRole('Viewer')
  }

  const addPermission = () => {
    const subject = newPermissionSubject.trim()
    if (!subject) return

    setPermissions((current) => [
      ...current,
      { id: Date.now(), subject, action: newPermissionAction },
    ])
    setNewPermissionSubject('')
    setNewPermissionAction('View')
  }

  if (isPending) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-56px)]">
        <Spinner size={28} />
      </div>
    )
  }

  if (isError) {
    return (
      <main className="max-w-4xl mx-auto px-6 py-12">
        <Card tone="muted">
          <p className="text-sm text-destructive">{error.message}</p>
        </Card>
      </main>
    )
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between gap-4">
        <h1>{project.name}</h1>
        <Button variant="secondary" size="sm">
          Edit
        </Button>
      </div>
      <p className="text-muted-foreground mt-2 text-sm">{project.slug}</p>
      <hr className="my-5 border-border" />

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="grid gap-3">
          <div>
            <h2 className="text-base font-semibold">Surveys</h2>
            <p className="text-sm text-muted-foreground">{surveys.length} in this project</p>
          </div>

          <div className="grid gap-3">
            {surveys.map((survey) => (
              <Card key={survey.id} size="sm">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-foreground">{survey.name}</p>
                      <Badge variant={survey.status === 'Published' ? 'success' : 'muted'} size="xs">
                        {survey.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {survey.visibility} · Updated {survey.updatedAt}
                    </p>
                  </div>
                  <div className="text-xs text-muted-foreground sm:text-right">
                    <p className="font-semibold text-foreground">{survey.responses}</p>
                    <p>Responses</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>

        <div className="grid gap-4">
          <section>
            <Card size="sm">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold">Members</h2>
                  <p className="text-xs text-muted-foreground">
                    {members.length} total · showing {visibleMembers.length}
                  </p>
                </div>
                <Button variant="secondary" size="sm" onClick={() => setMembersOpen(true)}>
                  Edit
                </Button>
              </div>

              <div className="grid gap-2">
                {visibleMembers.map((member) => (
                  <div key={member.id} className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">{member.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{member.email}</p>
                    </div>
                    <Badge variant="muted" size="xs">
                      {member.role}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          </section>

          <section>
            <Card size="sm">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold">Roles</h2>
                  <p className="text-xs text-muted-foreground">{permissions.length} permission rules</p>
                </div>
                <Button variant="secondary" size="sm" onClick={() => setPermissionsOpen(true)}>
                  Manage
                </Button>
              </div>

              <div className="flex flex-wrap gap-2">
                {permissions.map((permission) => (
                  <Badge key={permission.id} variant="muted" size="xs">
                    {permission.subject}: {permission.action}
                  </Badge>
                ))}
              </div>
            </Card>
          </section>
        </div>
      </div>

      <Modal open={membersOpen} onClose={() => setMembersOpen(false)} title="Edit members">
        <div className="grid gap-5">
          <div className="grid gap-3 sm:grid-cols-[1fr_130px_auto]">
            <input
              className="min-h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-ring"
              value={newMemberEmail}
              onChange={(event) => setNewMemberEmail(event.target.value)}
              placeholder="Email address"
            />
            <select
              className="min-h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-ring"
              value={newMemberRole}
              onChange={(event) => setNewMemberRole(event.target.value as Member['role'])}
            >
              <option>Viewer</option>
              <option>Editor</option>
              <option>Owner</option>
            </select>
            <Button variant="secondary" size="sm" onClick={addMember}>
              Add
            </Button>
          </div>

          <div className="divide-y divide-border">
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-foreground">{member.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{member.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="muted" size="xs">
                    {member.role}
                  </Badge>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      setMembers((current) => current.filter((item) => item.id !== member.id))
                    }
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Modal>

      <Modal open={permissionsOpen} onClose={() => setPermissionsOpen(false)} title="Manage roles">
        <div className="grid gap-5">
          <div className="grid gap-3 sm:grid-cols-[1fr_130px_auto]">
            <input
              className="min-h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-ring"
              value={newPermissionSubject}
              onChange={(event) => setNewPermissionSubject(event.target.value)}
              placeholder="Role or member"
            />
            <select
              className="min-h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-ring"
              value={newPermissionAction}
              onChange={(event) =>
                setNewPermissionAction(event.target.value as Permission['action'])
              }
            >
              <option>View</option>
              <option>Edit</option>
              <option>Manage</option>
            </select>
            <Button variant="secondary" size="sm" onClick={addPermission}>
              Add
            </Button>
          </div>

          <div className="divide-y divide-border">
            {permissions.map((permission) => (
              <div
                key={permission.id}
                className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
              >
                <div>
                  <p className="text-sm font-semibold text-foreground">{permission.subject}</p>
                  <p className="text-xs text-muted-foreground">{permission.action} access</p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    setPermissions((current) =>
                      current.filter((item) => item.id !== permission.id),
                    )
                  }
                >
                  Delete
                </Button>
              </div>
            ))}
          </div>
        </div>
      </Modal>
    </main>
  )
}
