import { useState } from 'react'
import { Button, Badge, Modal, Table, type TableColumn } from '@flowform/ui'
import { mockProjectMembers, type MockProjectMember } from '@/api/mockData'

const memberColumns: TableColumn<MockProjectMember>[] = [
  {
    key: 'member',
    header: 'Member',
    minWidth: 200,
    cell: (row) => (
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-foreground">{row.name}</p>
        <p className="truncate text-xs text-muted-foreground">{row.email}</p>
      </div>
    ),
  },
  {
    key: 'role',
    header: 'Role',
    minWidth: 100,
    cell: (row) => <Badge variant="muted" size="xs">{row.role}</Badge>,
  },
]

export function MembersTab() {
  const [members, setMembers] = useState<MockProjectMember[]>(mockProjectMembers)
  const [modalOpen, setModalOpen] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newRole, setNewRole] = useState<MockProjectMember['role']>('Viewer')

  const addMember = () => {
    const email = newEmail.trim()
    if (!email) return
    const name = email.split('@')[0].replace(/[._-]+/g, ' ')
    setMembers((current) => [
      ...current,
      {
        id: Date.now(),
        name: name.replace(/\b\w/g, (letter) => letter.toUpperCase()),
        email,
        role: newRole,
      },
    ])
    setNewEmail('')
    setNewRole('Viewer')
  }

  return (
    <section className="grid max-w-6xl gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Members</h2>
          <p className="text-sm text-muted-foreground">{members.length} total</p>
        </div>
        <Button variant="primary" size="sm" icon="plus" onClick={() => setModalOpen(true)}>
          Add member
        </Button>
      </div>

      <Table
        columns={memberColumns}
        rows={members}
        getRowKey={(row) => row.id}
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Edit members">
        <div className="grid gap-5">
          <div className="grid gap-3 sm:grid-cols-[1fr_130px_auto]">
            <input
              className="min-h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-ring"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="Email address"
            />
            <select
              className="min-h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-ring"
              value={newRole}
              onChange={(e) => setNewRole(e.target.value as MockProjectMember['role'])}
            >
              <option>Viewer</option>
              <option>Editor</option>
              <option>Owner</option>
            </select>
            <Button variant="secondary" size="sm" onClick={addMember}>Add</Button>
          </div>
          <div className="divide-y divide-border">
            {members.map((member) => (
              <div key={member.id} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-foreground">{member.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{member.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="muted" size="xs">{member.role}</Badge>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setMembers((c) => c.filter((m) => m.id !== member.id))}
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Modal>
    </section>
  )
}
