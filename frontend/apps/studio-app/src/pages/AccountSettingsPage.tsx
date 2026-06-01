import { useState } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { Badge, Button, Card, Input, Modal, Toast } from '@flowform/ui'
import { useCurrentUser } from '@/auth/UserContext'
import { useRenderDebug } from '@/debug/useRenderDebug'
import {
  useChangePassword,
  useDeleteAccount,
  useMyProfile,
  useResendVerification,
  useUpdateProfile,
} from '@/api/me/hooks'

function SettingsSection({
  title,
  description,
  children,
  className = '',
}: {
  title: string
  description?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <section className={`grid gap-4 ${className}`}>
      <div className="max-w-xl">
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
        {description && <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>}
      </div>
      {children}
    </section>
  )
}

function Avatar({ avatarUrl, displayName }: { avatarUrl: string | null; displayName: string }) {
  const initials = displayName.trim().slice(0, 2).toUpperCase() || '??'

  return (
    <div className="relative shrink-0">
      {avatarUrl ? (
        <img src={avatarUrl} alt="" className="size-16 rounded-full object-cover ring-2 ring-border" />
      ) : (
        <div className="size-16 rounded-full bg-accent flex items-center justify-center ring-2 ring-border">
          <span className="text-xl font-semibold text-accent-foreground">{initials}</span>
        </div>
      )}
    </div>
  )
}

export function AccountSettingsPage() {
  useRenderDebug('AccountSettingsPage')
  const ctx = useCurrentUser()
  const { user: auth0User } = useAuth0()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [draftDisplayNameOverride, setDraftDisplayNameOverride] = useState<string | null>(null)
  const [toast, setToast] = useState<{ message: string; variant: 'success' | 'error' } | null>(null)

  const profile = useMyProfile()
  const updateProfile = useUpdateProfile()
  const changePassword = useChangePassword()
  const resendVerification = useResendVerification()
  const deleteAccount = useDeleteAccount()

  const profileDisplayName = profile.data?.display_name ?? ctx?.displayName ?? ''

  if (!ctx) return null

  const { user, avatarUrl } = ctx
  const updateCurrentUser = ctx.updateUser
  const email = profile.data?.email ?? auth0User?.email ?? user.email
  const emailVerified = typeof auth0User?.email_verified === 'boolean'
    ? auth0User.email_verified
    : profile.data?.email_verified ?? false
  const draftDisplayName = draftDisplayNameOverride ?? profileDisplayName
  const displayName = draftDisplayName.trim() || email
  const canDeleteConfirm = deleteConfirm.trim() === email
  const displayNameDirty = draftDisplayNameOverride !== null && draftDisplayName !== profileDisplayName

  function showToast(message: string, variant: 'success' | 'error') {
    setToast({ message, variant })
    setTimeout(() => setToast(null), 4000)
  }

  async function handleSaveProfile() {
    try {
      const updatedUser = await updateProfile.mutateAsync({ display_name: draftDisplayName, nickname: null, picture: null })
      updateCurrentUser(updatedUser)
      setDraftDisplayNameOverride(null)
      showToast('Profile updated successfully.', 'success')
    } catch {
      showToast('Failed to update profile. Please try again.', 'error')
    }
  }

  async function handleChangePassword() {
    try {
      const ticket = await changePassword.mutateAsync()
      window.location.assign(ticket.ticket_url)
    } catch {
      showToast('Failed to start password change. Please try again.', 'error')
    }
  }

  async function handleResendVerification() {
    try {
      await resendVerification.mutateAsync()
      showToast('Verification email sent.', 'success')
    } catch {
      showToast('Failed to send verification email. Please try again.', 'error')
    }
  }

  async function handleDeleteAccount() {
    try {
      await deleteAccount.mutateAsync()
    } catch {
      showToast('Failed to delete account. Please try again.', 'error')
      setDeleteOpen(false)
      setDeleteConfirm('')
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 grid gap-6">
      {toast && (
        <div className="fixed bottom-6 right-6 z-50">
          <Toast variant={toast.variant} onClose={() => setToast(null)}>{toast.message}</Toast>
        </div>
      )}

      <div>
        <h1 className="text-xl font-semibold text-foreground">Account settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Manage your personal profile and security preferences.</p>
      </div>

      <Card size="lg" className="grid gap-8">
        <SettingsSection
          title="Profile"
          description="Your display name is shown to other team members inside FlowForm."
        >
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
            <Avatar avatarUrl={avatarUrl} displayName={displayName} />
            <div className="grid flex-1 gap-4">
              <Input
                className='max-w-md'
                label="Display name"
                value={draftDisplayName}
                onChange={(e) => setDraftDisplayNameOverride(e.target.value)}
                placeholder="Your name"
                hint="This is separate from your sign-in email address."
              />
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="secondary"
                  disabled={!displayNameDirty || updateProfile.isPending}
                  onClick={() => setDraftDisplayNameOverride(null)}
                >
                  Reset
                </Button>
                <Button
                  variant="primary"
                  disabled={!displayNameDirty || updateProfile.isPending}
                  onClick={() => void handleSaveProfile()}
                >
                  {updateProfile.isPending ? 'Saving…' : 'Save changes'}
                </Button>
              </div>
            </div>
          </div>
        </SettingsSection>

        <SettingsSection
          title="Email"
          description="Your email address is used for sign-in and account notifications."
          className="border-t border-border pt-8"
        >
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <Input className='max-w-md' label="Email address" value={email} disabled />
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant={emailVerified ? 'success' : 'warning'} size="xs">
                {emailVerified ? 'Verified' : 'Not verified'}
              </Badge>
              {!emailVerified && (
                <Button
                  variant="secondary"
                  disabled={resendVerification.isPending}
                  onClick={() => void handleResendVerification()}
                >
                  {resendVerification.isPending ? 'Sending…' : 'Resend verification'}
                </Button>
              )}
            </div>
          </div>
        </SettingsSection>

        <SettingsSection
          title="Password"
          description="Open Auth0's secure password change page for this account."
          className="border-t border-border pt-8"
        >
          <Button
            variant="secondary"
            className="w-fit"
            disabled={changePassword.isPending}
            onClick={() => void handleChangePassword()}
          >
            {changePassword.isPending ? 'Opening…' : 'Change password'}
          </Button>
        </SettingsSection>
      </Card>

      <Card size="lg" className="border border-destructive/30 bg-destructive/5 shadow-none">
        <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
          <div>
            <h2 className="text-sm font-semibold text-destructive">Danger zone</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Permanently delete your account and all associated data. This action cannot be undone.
            </p>
          </div>
          <Button variant="destructive" className="w-fit" onClick={() => setDeleteOpen(true)}>
            Delete account
          </Button>
        </div>
      </Card>

      {/* Delete account modal */}
      <Modal
        open={deleteOpen}
        onClose={() => { setDeleteOpen(false); setDeleteConfirm('') }}
        title="Delete account"
        width={480}
        footer={(
          <>
            <Button variant="secondary" className="mr-auto" onClick={() => { setDeleteOpen(false); setDeleteConfirm('') }}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!canDeleteConfirm || deleteAccount.isPending}
              onClick={() => void handleDeleteAccount()}
            >
              {deleteAccount.isPending ? 'Deleting…' : 'Delete my account'}
            </Button>
          </>
        )}
      >
        <div className="grid gap-4">
          <p className="text-sm leading-6 text-muted-foreground">
            This will permanently delete your account, remove you from all projects, and erase your data.
            Type <span className="font-semibold text-foreground">{email}</span> to confirm.
          </p>
          <Input
            label="Your email address"
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
            placeholder={email}
          />
        </div>
      </Modal>
    </div>
  )
}
