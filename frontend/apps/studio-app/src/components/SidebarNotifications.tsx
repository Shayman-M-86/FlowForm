import { useRef, useState } from 'react'
import { Button, Badge, Modal } from '@flowform/ui'
import { useMyInvitations, useAcceptInvitation, useDeclineInvitation } from '@/api/members/hooks'
import type { ProjectInvitationOut } from '@/api/members/types'

// ── Icon ──────────────────────────────────────────────────────────────────────

function IconMail() {
  return (
    <svg
      width={16}
      height={16}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  )
}

// ── Single invitation modal ───────────────────────────────────────────────────

function InvitationModal({
  invitation,
  onClose,
}: {
  invitation: ProjectInvitationOut
  onClose: () => void
}) {
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()
  const projectName = invitation.project_name ?? `Project #${invitation.project_id}`

  return (
    <Modal
      open
      onClose={onClose}
      title="Project invitation"
      width={440}
      footer={
        <>
          <Button
            variant="secondary"
            onClick={() => decline.mutate(invitation.id, { onSuccess: onClose })}
            disabled={decline.isPending || accept.isPending}
          >
            {decline.isPending ? 'Declining…' : 'Decline'}
          </Button>
          <Button
            variant="primary"
            onClick={() => accept.mutate(invitation.id, { onSuccess: onClose })}
            disabled={accept.isPending || decline.isPending}
          >
            {accept.isPending ? 'Accepting…' : 'Accept'}
          </Button>
        </>
      }
    >
      <div className="grid gap-3">
        <p className="text-sm text-foreground leading-relaxed">
          You've been invited to join <span className="font-semibold">{projectName}</span>.
        </p>
        {invitation.invited_by_display && (
          <p className="text-xs text-muted-foreground">
            Invited by <span className="font-medium text-foreground">{invitation.invited_by_display}</span>
          </p>
        )}
        {invitation.invite_message && (
          <blockquote className="border-l-2 border-border pl-3 text-sm text-muted-foreground italic leading-relaxed">
            {invitation.invite_message}
          </blockquote>
        )}
      </div>
    </Modal>
  )
}

// ── All invitations modal ─────────────────────────────────────────────────────

function AllInvitationsModal({
  invitations,
  onClose,
}: {
  invitations: ProjectInvitationOut[]
  onClose: () => void
}) {
  const [viewing, setViewing] = useState<ProjectInvitationOut | null>(null)

  if (viewing) {
    return (
      <InvitationModal
        invitation={viewing}
        onClose={() => setViewing(null)}
      />
    )
  }

  return (
    <Modal open onClose={onClose} title="Invitations" width={480}>
      <ul className="flex flex-col divide-y divide-border -my-2">
        {invitations.map((inv) => {
          const projectName = inv.project_name ?? `Project #${inv.project_id}`
          return (
            <li key={inv.id} className="flex items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground truncate">{projectName}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {inv.invited_by_display ? `From ${inv.invited_by_display}` : 'Invited as a member'}
                </p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => setViewing(inv)}>
                Review
              </Button>
            </li>
          )
        })}
      </ul>
    </Modal>
  )
}

// ── Sidebar notifications button ──────────────────────────────────────────────

interface Props {
  collapsed: boolean
}

export function SidebarNotifications({ collapsed: _collapsed }: Props) {
  const { data: invitations = [] } = useMyInvitations()
  const [open, setOpen] = useState(false)
  const count = invitations.length

  const handleClick = () => {
    if (count === 0) return
    setOpen(true)
  }

  const activeInvitation = count === 1 ? invitations[0] : null

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        aria-label={
          count === 0
            ? 'Notifications'
            : count === 1
              ? '1 pending invitation'
              : `${count} pending invitations`
        }
        className="sidebar-nav-item"
        data-active="false"
        disabled={count === 0}
      >
        <span className="sidebar-nav-item__icon relative">
          <IconMail />
          {count > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground leading-none">
              {count > 9 ? '9+' : count}
            </span>
          )}
        </span>
        <span className="sidebar-nav-item__label">
          Notifications
          {count > 0 && (
            <Badge size="xs" className="ml-2">{count}</Badge>
          )}
        </span>
      </button>

      {open && count > 0 && (
        activeInvitation ? (
          <InvitationModal invitation={activeInvitation} onClose={() => setOpen(false)} />
        ) : (
          <AllInvitationsModal invitations={invitations} onClose={() => setOpen(false)} />
        )
      )}
    </>
  )
}
