import { useMemo, useRef, useState } from 'react'
import { useParams } from '@tanstack/react-router'
import {
  Badge,
  Button,
  Card,
  CardStack,
  DropdownMenu,
  Input,
  Modal,
  Select,
  Spinner,
  Table,
  Toast,
  Toggle,
  Tooltip,
  type TableColumn,
} from '@flowform/ui'
import {
  Ban,
  CheckCircle2,
  ChevronRight,
  Globe2,
  Link,
  LockKeyhole,
  MailCheck,
} from 'lucide-react'
import { useProject } from '@/api/hooks/projects'
import { useProjectMembers } from '@/api/hooks/members'
import { useProjectRoles } from '@/api/hooks/roles'
import { useSurvey, useUpdateSurvey } from '@/api/hooks/surveys'
import { useHasProjectPermission } from '@/api/hooks/permissions'
import { useParticipants, useCreateParticipant } from '@/api/hooks/subjects'
import {
  useCreatePublicLink,
  useDeletePublicLink,
  usePublicLinks,
  useUpdatePublicLink,
} from '@/api/hooks/links'
import {
  useAssignSurveyMemberRole,
  useRemoveSurveyMemberRole,
  useSurveyMembers,
  useUpdateSurveyMemberRole,
} from '@/api/hooks/survey-members'
import {
  useCreateSurveyRole,
  useDeleteSurveyRole,
  useSurveyRoles,
  useUpdateSurveyRole,
} from '@/api/hooks/survey-roles'
import type { CreateSurveyRoleRequest } from '@/api/hooks/survey-roles'
import type { SurveyAccessLinkOut } from '@/api/hooks/links'
import type { ProjectMemberOut } from '@/api/hooks/members'
import {
  LinkStateBadge,
  SurveyAccessModeSelector,
} from '@/components/SurveyAccess'
import { MemberRoleActions } from '@/components/MemberRoleActions'
import { PermissionBadge } from '@/components/PermissionBadge'
import { RoleBadgePreview } from '@/components/RoleBadgePreview'
import { useRenderDebug } from '@/debug/useRenderDebug'
import {
  SURVEY_ACCESS_ENTRIES,
  SURVEY_ACCESS_MODES,
  type SurveyAccessEntry,
  type SurveyAccessMode,
} from '@/lib/surveyAccessDesign'
import { RoleEditorModal, type RoleEditorState } from '../ProjectDashboardTabPages/RoleEditorModal'
import {
  SURVEY_PERMISSION_GROUPS,
  type PermissionKey,
} from '../ProjectDashboardTabPages/roleDefinitions'

// ── Types ─────────────────────────────────────────────────────────────────────

const CREATABLE_LINK_TYPES = [
  'general_link',
  'authenticated_assigned_link',
  'private_invite_link',
] as const
type CreatableLinkType = typeof CREATABLE_LINK_TYPES[number]

type CreateLinkFormState = {
  type: CreatableLinkType
  name: string
  assignedParticipantId: string | null
  expiresAt: string
  requireAuthForGeneralLink: boolean
}

type PermissionPreview = { key: PermissionKey; variant: 'default' | 'warning' }
type SurveyPermissionKey = NonNullable<CreateSurveyRoleRequest['permissions']>[number]

interface MemberRow extends ProjectMemberOut {
  surveyRoleId: number | null
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function isCreatableLinkType(entry: SurveyAccessEntry): entry is CreatableLinkType {
  return (CREATABLE_LINK_TYPES as readonly SurveyAccessEntry[]).includes(entry)
}

function createDefaultLinkForm(type: CreatableLinkType): CreateLinkFormState {
  return { type, name: '', assignedParticipantId: null, expiresAt: '', requireAuthForGeneralLink: false }
}

function publicLinkStatus(link: SurveyAccessLinkOut): 'active' | 'disabled' | 'expired' {
  if (link.expires_at && new Date(link.expires_at).getTime() < Date.now()) return 'expired'
  return link.is_active ? 'active' : 'disabled'
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function isSurveyPermissionKey(permission: PermissionKey): permission is SurveyPermissionKey {
  return SURVEY_PERMISSION_GROUPS.some((group) => group.permissions.includes(permission))
}

function surveyPermissionsFromEditor(role: RoleEditorState): SurveyPermissionKey[] {
  return [...role.permissions].filter(isSurveyPermissionKey)
}

function toUrlSafeName(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionLabel({ label, title, description }: { label: string; title: string; description: string }) {
  return (
    <div className="min-w-0">
      <p className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">{label}</p>
      <h3 className="mt-0.5 text-base font-semibold text-foreground">{title}</h3>
      <p className="mt-1 max-w-prose text-sm leading-6 text-muted-foreground">{description}</p>
    </div>
  )
}

// ── Divider ───────────────────────────────────────────────────────────────────

function SectionDivider() {
  return <div className="h-px w-full bg-border" />
}

// ── Access summary sidebar card ───────────────────────────────────────────────

function AccessSidebarSummary({
  mode,
  publicSlug,
  surveyTitle,
  isSaving,
  canEdit,
  onModeChange,
}: {
  mode: SurveyAccessMode
  publicSlug: string | null
  surveyTitle: string
  isSaving: boolean
  canEdit: boolean
  onModeChange: (mode: SurveyAccessMode, publicSlug: string | null) => Promise<boolean>
}) {
  const [modalOpen, setModalOpen] = useState(false)
  const [draftMode, setDraftMode] = useState<SurveyAccessMode>(mode)
  const [draftPublicSlug, setDraftPublicSlug] = useState(publicSlug ?? '')
  const [slugError, setSlugError] = useState<string | null>(null)

  function openModal() {
    setDraftMode(mode)
    setDraftPublicSlug(publicSlug ?? toUrlSafeName(surveyTitle))
    setSlugError(null)
    setModalOpen(true)
  }

  async function applyModal() {
    const nextPublicSlug = toUrlSafeName(draftPublicSlug)
    if (draftMode === 'public' && !nextPublicSlug) {
      setSlugError('Public mode needs a URL-safe name.')
      return
    }

    const updated = await onModeChange(draftMode, draftMode === 'public' ? nextPublicSlug : null)
    if (updated) setModalOpen(false)
  }

  const def = SURVEY_ACCESS_MODES[mode]
  const Icon = def.icon

  const modeColors: Record<SurveyAccessMode, string> = {
    private: 'text-muted-foreground bg-muted',
    link_only: 'text-accent bg-accent/10',
    public: 'text-success bg-success/10',
  }

  return (
    <>
      <Card size="sm">
        <div className="grid gap-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2.5">
              <span className={`grid size-10 shrink-0 place-items-center rounded-md ${modeColors[mode]}`}>
                <Icon size={20} strokeWidth={2.5} aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="text-md font-semibold uppercase tracking-widest text-muted-foreground">Access mode</p>
                <p className="text-md font-semibold text-foreground">{def.label}</p>
              </div>
            </div>
            {canEdit && (
              <Button variant="secondary" size="sm" className="shrink-0" onClick={openModal}>
                Edit
              </Button>
            )}
          </div>
          <p className="text-xs leading-5 text-muted-foreground">{def.description}</p>
          <div className="grid gap-1.5 border-t border-border pt-3">
            <div>
              <p className="text-[0.68rem] font-semibold uppercase tracking-wider text-muted-foreground">Allowed</p>
              <ul className="mt-1 grid gap-1">
                {def.allowedEntries.map((entry) => {
                  const e = SURVEY_ACCESS_ENTRIES[entry]
                  const EntryIcon = e.icon
                  return (
                    <li key={entry} className="flex items-center gap-1.5 text-xs text-foreground">
                      <EntryIcon size={11} strokeWidth={2} aria-hidden="true" className="shrink-0 text-muted-foreground" />
                      {e.label}
                    </li>
                  )
                })}
              </ul>
            </div>
            {def.blockedEntries.length > 0 && (
              <div className="mt-1">
                <p className="text-[0.68rem] font-semibold uppercase tracking-wider text-muted-foreground">Blocked</p>
                <ul className="mt-1 grid gap-1">
                  {def.blockedEntries.map((entry) => (
                    <li key={entry} className="text-xs text-muted-foreground line-through">
                      {SURVEY_ACCESS_ENTRIES[entry].label}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </Card>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Respondent access model"
        width={560}
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button variant="primary" disabled={isSaving} onClick={applyModal}>
              {isSaving ? 'Applying...' : 'Apply'}
            </Button>
          </>
        }
      >
        <div className="grid gap-4">
          <p className="text-sm leading-6 text-muted-foreground">
            Choose who can open and complete the survey. The sharing controls adapt to the saved model.
          </p>
          <SurveyAccessModeSelector value={draftMode} onChange={setDraftMode} />
          <Input
            label="Public URL slug"
            value={draftPublicSlug}
            disabled={draftMode !== 'public'}
            placeholder="my-survey"
            error={slugError ?? undefined}
            hint={draftMode === 'public'
              ? 'Used in the public survey URL. Use lowercase letters, numbers, and hyphens.'
              : 'This survey is not in public mode, so the public URL is disabled.'}
            onChange={(event) => {
              setSlugError(null)
              setDraftPublicSlug(toUrlSafeName(event.target.value))
            }}
          />
          <div className="rounded-md border border-border bg-muted/20 p-3">
            <p className="text-xs font-semibold text-foreground">{SURVEY_ACCESS_MODES[draftMode].label}</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{SURVEY_ACCESS_MODES[draftMode].description}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Allowed:</span>{' '}
              {SURVEY_ACCESS_MODES[draftMode].allowedEntries.map((e) => SURVEY_ACCESS_ENTRIES[e].label).join(', ')}
            </p>
            {SURVEY_ACCESS_MODES[draftMode].blockedEntries.length > 0 && (
              <p className="mt-1 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">Blocked:</span>{' '}
                {SURVEY_ACCESS_MODES[draftMode].blockedEntries.map((e) => SURVEY_ACCESS_ENTRIES[e].label).join(', ')}
              </p>
            )}
          </div>
        </div>
      </Modal>
    </>
  )
}

// ── Links section ─────────────────────────────────────────────────────────────

function linkUrl(link: SurveyAccessLinkOut): string {
  return `${window.location.origin}/respond/${link.token}`
}

function LinkCard({
  link,
  canEdit,
  onToggle,
  onDelete,
}: {
  link: SurveyAccessLinkOut
  canEdit: boolean
  onToggle: (linkId: string, isActive: boolean) => void
  onDelete: (linkId: string) => void
}) {
  const status = publicLinkStatus(link)
  const moreRef = useRef<HTMLSpanElement>(null)
  const [moreOpen, setMoreOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const url = linkUrl(link)

  function copyLink() {
    navigator.clipboard.writeText(url).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Card size="sm">
      <div className="grid gap-2">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-wrap items-center gap-1.5">
            <LinkStateBadge state={status} />
            {link.link_type === 'authenticated' && (
              <Badge variant="muted" size="xs">Requires sign-in</Badge>
            )}
          </div>
          <div className="flex flex-wrap justify-end gap-x-3 gap-y-0.5 text-right text-xs text-muted-foreground">
            <span>Created {formatDate(link.created_at)}</span>
            <span>Expires {link.expires_at ? formatDate(link.expires_at) : 'Never'}</span>
          </div>
        </div>

        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="min-w-3 text-sm font-medium text-foreground">{link.name}</p>
            <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
              {link.assigned_participant_id && (
                <div className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
                  <MailCheck size={13} strokeWidth={2} aria-hidden="true" className="shrink-0 text-muted-foreground" />
                  <span className="truncate">Assigned</span>
                </div>
              )}
              <p className="min-w-[min(100%,16rem)] max-w-full truncate font-mono text-xs text-muted-foreground ml-auto text-right">
                {url}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 flex-col items-end justify-between gap-2 pl-2 self-stretch">
            <div className="flex items-center gap-1.5 mt-auto">
              <Tooltip content={copied ? 'Copied!' : 'Copy link'} size="sm">
                <Button
                  type="button"
                  variant="icon"
                  size="sm"
                  icon={copied ? 'check' : 'copy'}
                  aria-label={copied ? 'Link copied' : 'Copy link'}
                  onClick={copyLink}
                />
              </Tooltip>
              {canEdit && (
                <>
                  <span ref={moreRef} className="inline-flex">
                    <Tooltip content="More options" size="sm">
                      <Button
                        type="button"
                        variant="icon"
                        size="sm"
                        icon="ellipsis"
                        aria-label="More options"
                        aria-haspopup="menu"
                        aria-expanded={moreOpen}
                        onClick={() => setMoreOpen((o) => !o)}
                      />
                    </Tooltip>
                  </span>
                  <DropdownMenu
                    open={moreOpen}
                    onClose={() => setMoreOpen(false)}
                    trigger={moreRef}
                    align="right"
                    width="15rem"
                    fullscreenAt="never"
                    sections={[{
                      label: 'Link actions',
                      actions: [
                        {
                          key: 'toggle',
                          content: (
                            <Button
                              type="button"
                              role="menuitem"
                              variant="secondary"
                              size="sm"
                              className="w-full justify-start gap-2"
                            >
                              {link.is_active ? (
                                <>
                                  <Ban size={14} strokeWidth={2} aria-hidden="true" />
                                  <span>Disable link</span>
                                </>
                              ) : (
                                <>
                                  <CheckCircle2 size={14} strokeWidth={2} aria-hidden="true" />
                                  <span>Enable link</span>
                                </>
                              )}
                            </Button>
                          ),
                          onSelect: () => onToggle(link.id, !link.is_active),
                        },
                        {
                          key: 'delete',
                          content: (
                            <Button
                              type="button"
                              role="menuitem"
                              variant="destructive"
                              size="sm"
                              className="w-full justify-start gap-2"
                            >
                              <Ban size={14} strokeWidth={2} aria-hidden="true" />
                              <span>Delete link</span>
                            </Button>
                          ),
                          onSelect: () => onDelete(link.id),
                        },
                      ],
                    }]}
                  />
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

function LinksSection({
  projectId,
  surveyId,
  publicSlug,
  savedAccessMode,
  canEdit,
}: {
  projectId: number
  surveyId: number
  publicSlug: string | null
  savedAccessMode: SurveyAccessMode
  canEdit: boolean
}) {
  const { data: links = [], isLoading: linksLoading } = usePublicLinks(projectId, surveyId)
  const createLink = useCreatePublicLink(projectId, surveyId)
  const updateLink = useUpdatePublicLink(projectId, surveyId)
  const deleteLink = useDeletePublicLink(projectId, surveyId)

  const allowedCreateLinkTypes = useMemo(
    () => SURVEY_ACCESS_MODES[savedAccessMode].allowedEntries.filter(isCreatableLinkType),
    [savedAccessMode],
  )
  const firstCreateLinkType = allowedCreateLinkTypes[0] ?? 'authenticated_assigned_link'

  const [createLinkOpen, setCreateLinkOpen] = useState(false)
  const [createdTokenUrl, setCreatedTokenUrl] = useState<string | null>(null)
  const [linkError, setLinkError] = useState<string | null>(null)
  const [form, setForm] = useState<CreateLinkFormState>(() => createDefaultLinkForm(firstCreateLinkType))

  // ── Participant picker state ──────────────────────────────────────────────
  const [participantSearch, setParticipantSearch] = useState('')
  const [showNewParticipant, setShowNewParticipant] = useState(false)
  const [newParticipantEmail, setNewParticipantEmail] = useState('')
  const [newParticipantCode, setNewParticipantCode] = useState('')
  const participantsQuery = useParticipants(projectId, { search: participantSearch.trim() || undefined, page_size: 50 })
  const createParticipant = useCreateParticipant(projectId)

  const selectedLinkDef = SURVEY_ACCESS_ENTRIES[form.type]
  const requiresParticipant = form.type !== 'general_link'
  const requiresAuth = form.type === 'authenticated_assigned_link'
  const canCreate = form.name.trim().length > 0 && (!requiresParticipant || form.assignedParticipantId != null)
  const canAddLinks = canEdit && savedAccessMode !== 'private' && allowedCreateLinkTypes.length > 0

  function openModal() {
    const type = allowedCreateLinkTypes[0]
    if (!type) return
    setForm(createDefaultLinkForm(type))
    setParticipantSearch('')
    setShowNewParticipant(false)
    setNewParticipantEmail('')
    setNewParticipantCode('')
    setCreateLinkOpen(true)
  }

  async function handleCreateLink() {
    if (!canCreate) return
    setLinkError(null)
    try {
      const result = await createLink.mutateAsync({
        name: form.name.trim(),
        link_type: requiresAuth || form.requireAuthForGeneralLink ? 'authenticated' : form.type === 'private_invite_link' ? 'private' : 'general',
        assignment_source: 'manual',
        assigned_participant_id: form.assignedParticipantId,
        expires_at: form.expiresAt ? `${form.expiresAt}T00:00:00Z` : null,
      })
      setCreateLinkOpen(false)
      setCreatedTokenUrl(`${window.location.origin}/respond/${result.link.token}`)
    } catch {
      setLinkError('Failed to create link. Please try again.')
    }
  }

  function handleToggle(linkId: string, isActive: boolean) {
    updateLink.mutate({ linkId, body: { is_active: isActive, name: null, link_type: null, assignment_source: null, assigned_participant_id: null, expires_at: null } })
  }

  function handleDelete(linkId: string) {
    deleteLink.mutate(linkId)
  }

  return (
    <div className="grid gap-4">
      {linkError && (
        <Toast variant="error" onClose={() => setLinkError(null)}>{linkError}</Toast>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <SectionLabel
          label="Sharing"
          title="Links and public entry points"
          description="Create, disable, or regenerate the link methods permitted by the active access model."
        />
        {canAddLinks && (
          <Button variant="primary" size="sm" icon="plus" className="shrink-0 self-end" onClick={openModal}>
            Create link
          </Button>
        )}
      </div>

      {savedAccessMode === 'private' && (
        <Card tone="muted" size="sm">
          <div className="flex items-center gap-3">
            <span className="grid size-8 shrink-0 place-items-center rounded-md bg-muted text-muted-foreground">
              <LockKeyhole size={15} strokeWidth={2} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">No public sharing</p>
              <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
                Private mode only allows authenticated assigned links. No general or invite links can be created.
              </p>
            </div>
          </div>
        </Card>
      )}

      {savedAccessMode === 'public' && publicSlug && (
        <Card tone="muted" size="sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-md bg-success/10 text-success">
                <Globe2 size={15} strokeWidth={2} aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">Public URL active</p>
                <code className="mt-0.5 block truncate font-mono text-xs text-muted-foreground">
                  {window.location.origin}/s/{publicSlug}
                </code>
              </div>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="xs"
              icon="copy"
              className="shrink-0"
              onClick={() => navigator.clipboard.writeText(`${window.location.origin}/s/${publicSlug}`).catch(() => {})}
            >
              Copy URL
            </Button>
          </div>
        </Card>
      )}

      {savedAccessMode === 'link_only' && (
        <Card tone="ghost" size="sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-md bg-accent/10 text-accent">
                <Link size={18} strokeWidth={2} aria-hidden="true" />
              </span>
              <p className="text-sm font-semibold text-foreground">Invite links only</p>
            </div>
            <p className="text-xs leading-5 text-muted-foreground sm:max-w-md sm:text-right">
              No public URL. Respondents need a valid link to access this survey.
            </p>
          </div>
        </Card>
      )}

      {linksLoading ? (
        <div className="flex justify-center py-6"><Spinner size={20} /></div>
      ) : links.length > 0 ? (
        <CardStack gap="sm">
          {links.map((link) => (
            <LinkCard key={link.id} link={link} canEdit={canEdit} onToggle={handleToggle} onDelete={handleDelete} />
          ))}
        </CardStack>
      ) : canEdit ? (
        <button
          type="button"
          onClick={openModal}
          className="ui-button-ghost flex w-full flex-col gap-2 rounded-md border border-dashed border-border bg-muted/20 p-3 text-left sm:flex-row sm:items-center sm:justify-between sm:gap-4"
        >
          <p className="text-sm font-medium text-muted-foreground">No active links</p>
          <p className="text-xs leading-5 text-muted-foreground sm:max-w-md sm:text-right">
            Create invite links to share the survey with respondents.
          </p>
        </button>
      ) : (
        <div className="flex w-full flex-col gap-2 rounded-md border border-dashed border-border bg-muted/20 p-3 text-left sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <p className="text-sm font-medium text-muted-foreground">No active links</p>
        </div>
      )}

      <Modal
        open={createLinkOpen}
        onClose={() => setCreateLinkOpen(false)}
        title="Create access link"
        className="max-h-[90dvh]"
        width={640}
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateLinkOpen(false)}>Cancel</Button>
            <Button
              variant="primary"
              disabled={!canCreate || createLink.isPending}
              onClick={handleCreateLink}
            >
              {createLink.isPending ? 'Creating…' : 'Create link'}
            </Button>
          </>
        }
      >
        <div className="grid gap-4">
          <Select
            label="Link type"
            value={form.type}
            options={allowedCreateLinkTypes.map((type) => ({
              value: type,
              label: SURVEY_ACCESS_ENTRIES[type].label,
            }))}
            onValueChange={(value) => {
              const nextType = value as CreatableLinkType
              setForm((current) => ({
                ...current,
                type: nextType,
                assignedParticipantId: nextType === 'general_link' ? null : current.assignedParticipantId,
                requireAuthForGeneralLink: nextType === 'general_link' ? current.requireAuthForGeneralLink : false,
              }))
            }}
          />

          <div className="rounded-md border border-border bg-muted/20 p-3">
            <p className="text-sm font-semibold text-foreground">{selectedLinkDef.label}</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{selectedLinkDef.shortDescription}</p>
            <ul className="mt-2 grid gap-1 text-xs leading-5 text-muted-foreground">
              {selectedLinkDef.details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          </div>

          <Input
            label="Link name"
            value={form.name}
            placeholder="Participant A, Batch invite, Pilot group"
            onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))}
          />

          {requiresParticipant && (
            <div className="grid gap-3">
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <Input
                    label="Search participants"
                    placeholder="Filter by email or code…"
                    value={participantSearch}
                    onChange={(e) => setParticipantSearch(e.target.value)}
                  />
                </div>
                <Button variant="secondary" size="md" onClick={() => setShowNewParticipant(true)}>
                  New participant
                </Button>
              </div>

              <Select
                label="Assign to participant"
                value={form.assignedParticipantId ?? ''}
                onValueChange={(value) => setForm((current) => ({ ...current, assignedParticipantId: value || null }))}
                options={[
                  { value: '', label: 'Select a participant…' },
                  ...(participantsQuery.data?.participants ?? []).map((p) => ({
                    value: p.id,
                    label: `${p.email ?? 'No email'} — ${p.subject_code}`,
                  })),
                ]}
              />

              <Modal
                open={showNewParticipant}
                onClose={() => setShowNewParticipant(false)}
                title="Create new participant"
                width={420}
                footer={(
                  <div className="flex w-full items-center justify-between gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setShowNewParticipant(false)}>
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={!newParticipantEmail.trim() || createParticipant.isPending}
                      onClick={() => {
                        createParticipant.mutate(
                          { email: newParticipantEmail.trim(), subject_code: newParticipantCode.trim() || null },
                          {
                            onSuccess: (data) => {
                              setForm((current) => ({ ...current, assignedParticipantId: data.id }))
                              setNewParticipantEmail('')
                              setNewParticipantCode('')
                              setShowNewParticipant(false)
                            },
                          },
                        )
                      }}
                    >
                      {createParticipant.isPending ? 'Creating…' : 'Create & select'}
                    </Button>
                  </div>
                )}
              >
                <div className="grid gap-3">
                  <Input
                    label="Email address"
                    type="email"
                    value={newParticipantEmail}
                    onChange={(e) => setNewParticipantEmail(e.target.value)}
                    placeholder="name@example.com"
                  />
                  <Input
                    label="Subject code (optional)"
                    value={newParticipantCode}
                    onChange={(e) => setNewParticipantCode(e.target.value)}
                    placeholder="sub_xxx"
                  />
                  {createParticipant.isError && (
                    <p className="text-sm text-destructive">
                      {(createParticipant.error as { message?: string } | null)?.message ?? 'Failed to create participant.'}
                    </p>
                  )}
                </div>
              </Modal>

              {form.assignedParticipantId && (
                <p className="text-xs text-muted-foreground">
                  {requiresAuth
                    ? 'The participant must sign in with their email before using the link.'
                    : 'Assigned to this participant but does not require sign-in.'}
                </p>
              )}
            </div>
          )}

          {form.type === 'general_link' && (
            <Toggle
              label="Require sign in"
              checked={form.requireAuthForGeneralLink}
              onChange={(checked) => setForm((current) => ({ ...current, requireAuthForGeneralLink: checked }))}
              hint="General links are not assigned to a participant email."
            />
          )}

          <Input
            label="Expiry date"
            type="date"
            value={form.expiresAt}
            onChange={(e) => setForm((current) => ({ ...current, expiresAt: e.target.value }))}
          />
        </div>
      </Modal>

      <CreatedTokenModal url={createdTokenUrl} onClose={() => setCreatedTokenUrl(null)} />
    </div>
  )
}

function CreatedTokenModal({ url, onClose }: { url: string | null; onClose: () => void }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    if (!url) return
    navigator.clipboard.writeText(url).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Modal open={url != null} onClose={onClose} title="Link created" width={560}
      footer={<Button variant="primary" onClick={onClose}>Done</Button>}
    >
      <div className="grid gap-3">
        <p className="text-sm text-muted-foreground">
          Copy this link now — the full token will not be shown again.
        </p>
        <div className="flex items-center gap-2 rounded-md border border-border bg-muted/30 px-3 py-2 overflow-hidden">
          <code className="min-w-0 flex-1 truncate text-sm block">{url}</code>
          <Button variant="ghost" size="sm" className="shrink-0" onClick={handleCopy}>
            {copied ? 'Copied!' : 'Copy'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// ── Members section ───────────────────────────────────────────────────────────

function PermissionBadges({ permissions }: { permissions: PermissionPreview[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {permissions.map((p) => (
        <PermissionBadge key={p.key} permission={p.key} variant={p.variant} />
      ))}
    </div>
  )
}

function CompactPermissionBadges({ permissions, limit = 3 }: { permissions: PermissionPreview[]; limit?: number }) {
  const triggerRef = useRef<HTMLSpanElement>(null)
  const [open, setOpen] = useState(false)
  const visible = permissions.slice(0, limit)
  const hidden = permissions.slice(limit)

  return (
    <div className="flex flex-wrap gap-1.5">
      {visible.map((p) => (
        <PermissionBadge key={p.key} permission={p.key} variant={p.variant} />
      ))}
      {hidden.length > 0 && (
        <>
          <span ref={triggerRef} className="inline-flex">
            <Badge variant="muted" size="xs" onClick={() => setOpen((o) => !o)}>
              +{hidden.length} more
            </Badge>
          </span>
          <DropdownMenu
            open={open}
            onClose={() => setOpen(false)}
            trigger={triggerRef}
            width="18rem"
            align="auto"
            direction="auto"
            fullscreenAt="never"
            sections={[{
              actions: [{
                key: 'all',
                closeOnSelect: false,
                content: (
                  <div className="grid w-full gap-3 rounded-sm px-3 py-2 text-left">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">Effective permissions</p>
                      <p className="text-xs text-muted-foreground">All permissions available to this member</p>
                    </div>
                    <PermissionBadges permissions={permissions} />
                  </div>
                ),
              }],
            }]}
          />
        </>
      )}
    </div>
  )
}

function MembersSection({ projectId, surveyId, canEdit }: { projectId: number; surveyId: number; canEdit: boolean }) {
  const { data: projectMembers = [], isLoading: membersLoading } = useProjectMembers(projectId)
  const { data: projectRoles = [] } = useProjectRoles(projectId > 0 ? projectId : null)
  const { data: surveyAssignments = [] } = useSurveyMembers(projectId, surveyId)
  const { data: surveyRoles = [] } = useSurveyRoles(projectId)

  const assignRole = useAssignSurveyMemberRole(projectId, surveyId)
  const updateRole = useUpdateSurveyMemberRole(projectId, surveyId)
  const removeRole = useRemoveSurveyMemberRole(projectId, surveyId)
  const createSurveyRole = useCreateSurveyRole(projectId)
  const [newRoleEditor, setNewRoleEditor] = useState<RoleEditorState | null>(null)
  const selectCreatedRoleRef = useRef<((roleId: string) => void) | null>(null)

  const assignmentByMembership = useMemo(
    () => new Map(surveyAssignments.map((a) => [a.membership_id, a])),
    [surveyAssignments],
  )

  const rows = useMemo<MemberRow[]>(
    () => projectMembers.map((m) => ({
      ...m,
      surveyRoleId: assignmentByMembership.get(m.id)?.role_id ?? null,
    })),
    [projectMembers, assignmentByMembership],
  )

  function surveyPermissionPreview(roleId: number): PermissionPreview[] {
    const role = surveyRoles.find((r) => r.id === roleId)
    return (role?.permissions ?? []).map((p) => ({ key: p as PermissionKey, variant: 'warning' as const }))
  }

  function projectPermissionPreview(roleId: number | null): PermissionPreview[] {
    const role = projectRoles.find((r) => r.id === roleId)
    return (role?.permissions ?? [])
      .filter((p): p is SurveyPermissionKey => isSurveyPermissionKey(p as PermissionKey))
      .map((p) => ({ key: p, variant: 'default' as const }))
  }

  function effectivePermissionPreview(member: MemberRow, surveyRoleId = member.surveyRoleId): PermissionPreview[] {
    const permissions = new Map<PermissionKey, PermissionPreview>()

    for (const permission of projectPermissionPreview(member.role_id)) {
      permissions.set(permission.key, permission)
    }

    if (surveyRoleId) {
      for (const permission of surveyPermissionPreview(surveyRoleId)) {
        if (!permissions.has(permission.key)) {
          permissions.set(permission.key, permission)
        }
      }
    }

    return [...permissions.values()]
  }

  function handleSaveRole(member: MemberRow, roleId: string) {
    const numericRoleId = Number(roleId)
    const existing = assignmentByMembership.get(member.id)
    if (existing) {
      updateRole.mutate({ membershipId: member.id, body: { role_id: numericRoleId } })
    } else {
      assignRole.mutate({ membership_id: member.id, role_id: numericRoleId })
    }
  }

  function handleRemoveRole(member: MemberRow) {
    removeRole.mutate(member.id)
  }

  function addSurveyRole(selectRole: (roleId: string) => void) {
    selectCreatedRoleRef.current = selectRole
    setNewRoleEditor({
      id: `survey-new-${Date.now()}`,
      custom: true,
      name: 'New survey role',
      description: '',
      permissions: new Set(),
    })
  }

  function saveNewSurveyRole() {
    if (!newRoleEditor) return
    const name = newRoleEditor.name.trim()
    if (!name) return
    const description = newRoleEditor.description.trim() || null

    createSurveyRole.mutate(
      { name, description, permissions: surveyPermissionsFromEditor(newRoleEditor) },
      {
        onSuccess: (role) => {
          selectCreatedRoleRef.current?.(String(role.id))
          selectCreatedRoleRef.current = null
          setNewRoleEditor(null)
        },
      },
    )
  }

  const columns: TableColumn<MemberRow>[] = [
    {
      key: 'member',
      header: 'Member',
      minWidth: 100,
      maxWidth: 200,
      cell: (member) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">
            {member.user.display_name ?? member.user.email}
          </p>
          <p className="truncate text-2xs text-muted-foreground">{member.user.email}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      minWidth: 60,
      maxWidth: 100,
      cell: (member) => (
        <Badge variant={member.status === 'active' ? 'success' : 'muted'} size="xs">
          {member.status === 'active' ? 'Active' : 'Suspended'}
        </Badge>
      ),
    },
    {
      key: 'survey-role',
      header: 'Survey role',
      minWidth: 75,
      maxWidth: 160,
      cell: (member) => {
        if (!member.surveyRoleId) return <span className="text-xs text-muted-foreground">—</span>
        const role = surveyRoles.find((r) => r.id === member.surveyRoleId)
        return (
          <RoleBadgePreview
            label={role?.name ?? 'Role'}
            prefix=""
            variant="warning"
            permissions={surveyPermissionPreview(member.surveyRoleId)}
          />
        )
      },
    },
    {
      key: 'effective',
      header: 'Effective permissions',
      minWidth: 110,
      cell: (member) => (
        <CompactPermissionBadges
          permissions={effectivePermissionPreview(member)}
        />
      ),
    },
    ...(canEdit ? [{
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      minWidth: 50,
      maxWidth: 50,
      headerClassName: 'flex justify-center pr-2',
      cellClassName: 'flex justify-center px-0',
      cell: (member: MemberRow) => (
        <MemberRoleActions
          memberName={member.user.display_name ?? member.user.email}
          memberEmail={member.user.email}
          editRoleLabel="Edit survey role"
          roles={surveyRoles.map((r) => ({
            id: String(r.id),
            name: r.name,
            description: r.description ?? '',
            permissions: r.permissions as PermissionKey[],
          }))}
          selectedRoleId={member.surveyRoleId ? String(member.surveyRoleId) : undefined}
          onSaveRole={(roleId) => handleSaveRole(member, roleId)}
          onRemoveRole={member.surveyRoleId ? () => handleRemoveRole(member) : undefined}
          removeRoleLabel="Remove survey role"
          onAddRole={addSurveyRole}
          renderEffectivePreview={(roleId) => (
            <PermissionBadges permissions={effectivePermissionPreview(member, Number(roleId))} />
          )}
        />
      ),
    }] as TableColumn<MemberRow>[] : []),
  ]

  return (
    <div className="grid gap-4">
      <SectionLabel
        label="Assignment"
        title="Members and role overrides"
        description="Review project members and apply survey-specific role overrides where needed."
      />

      {membersLoading ? (
        <div className="flex justify-center py-6"><Spinner size={20} /></div>
      ) : (
        <div className="w-full overflow-hidden">
          <Table columns={columns} rows={rows} getRowKey={(member) => member.id} />
        </div>
      )}

      <RoleEditorModal
        role={newRoleEditor}
        onClose={() => {
          setNewRoleEditor(null)
          selectCreatedRoleRef.current = null
        }}
        onChange={setNewRoleEditor}
        onSave={saveNewSurveyRole}
        permissionGroups={SURVEY_PERMISSION_GROUPS}
        isNew
      />
    </div>
  )
}

// ── Survey roles reference card ───────────────────────────────────────────────

function SurveyRolesReferenceCard({ projectId, canEdit }: { projectId: number; canEdit: boolean }) {
  const { data: roles = [], isLoading } = useSurveyRoles(projectId)
  const createRole = useCreateSurveyRole(projectId)
  const updateRole = useUpdateSurveyRole(projectId)
  const deleteRoleMutation = useDeleteSurveyRole(projectId)

  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [editingRole, setEditingRole] = useState<RoleEditorState | null>(null)
  const [isNew, setIsNew] = useState(false)

  function openAddRole() {
    setEditingRole({
      id: `survey-new-${Date.now()}`,
      custom: true,
      name: 'New survey role',
      description: '',
      permissions: new Set(),
    })
    setIsNew(true)
  }

  function saveRole() {
    if (!editingRole) return
    const name = editingRole.name.trim()
    if (!name) return
    const description = editingRole.description.trim() || null
    const permissions = surveyPermissionsFromEditor(editingRole)

    if (isNew) {
      createRole.mutate(
        { name, description, permissions },
        { onSuccess: (role) => { setExpandedId(role.id); setEditingRole(null); setIsNew(false) } },
      )
    } else {
      const roleId = Number(editingRole.id)
      updateRole.mutate(
        { roleId, body: { name, description, permissions } },
        { onSuccess: () => { setEditingRole(null) } },
      )
    }
  }

  function deleteRole() {
    if (!editingRole) return
    const roleId = Number(editingRole.id)
    deleteRoleMutation.mutate(roleId, {
      onSuccess: () => {
        if (expandedId === roleId) setExpandedId(null)
        setEditingRole(null)
        setIsNew(false)
      },
    })
  }

  return (
    <>
      <Card size="sm">
        <div className="grid gap-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-lg font-semibold text-foreground">Survey roles</p>
            {canEdit && (
              <Button variant="secondary" size="xs" icon="plus" className="shrink-0" onClick={openAddRole}>
                Add role
              </Button>
            )}
          </div>

          {isLoading ? (
            <div className="flex justify-center py-3"><Spinner size={16} /></div>
          ) : roles.length === 0 ? (
            <p className="text-xs text-muted-foreground">No survey roles defined yet.</p>
          ) : (
            <div className="grid gap-1.5">
              {roles.map((role) => {
                const isExpanded = expandedId === role.id
                return (
                  <div key={role.id} className="overflow-hidden rounded-md border border-border bg-muted/30">
                    <button
                      type="button"
                      onClick={() => setExpandedId(isExpanded ? null : role.id)}
                      className="ui-button-ghost w-full justify-between rounded-none px-2.5 py-2 text-left"
                      aria-expanded={isExpanded}
                    >
                      <p className="truncate text-sm font-semibold text-foreground">{role.name}</p>
                      <ChevronRight
                        size={12}
                        strokeWidth={2}
                        aria-hidden="true"
                        className={`shrink-0 text-muted-foreground transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                      />
                    </button>
                    {isExpanded && (
                      <div className="grid gap-2 border-t border-border px-2.5 py-2.5">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex flex-wrap gap-1.5">
                            {role.permissions.length === 0
                              ? <p className="text-xs text-muted-foreground">No permissions assigned.</p>
                              : role.permissions.map((p) => (
                                <PermissionBadge key={p} permission={p as PermissionKey} variant="warning" />
                              ))
                            }
                          </div>
                          {canEdit && (
                            <Button
                              variant="secondary"
                              size="xs"
                              className="shrink-0"
                              onClick={() => setEditingRole({
                                id: String(role.id),
                                custom: true,
                                name: role.name,
                                description: role.description ?? '',
                                permissions: new Set(role.permissions as PermissionKey[]),
                              })}
                            >
                              Edit
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </Card>

      <RoleEditorModal
        role={editingRole}
        onClose={() => { setEditingRole(null); setIsNew(false) }}
        onChange={setEditingRole}
        onSave={saveRole}
        onDelete={isNew ? undefined : deleteRole}
        permissionGroups={SURVEY_PERMISSION_GROUPS}
        isNew={isNew}
      />
    </>
  )
}

// ── Stat pill ─────────────────────────────────────────────────────────────────



// ── Root ──────────────────────────────────────────────────────────────────────

export function SurveyAccessTab() {
  useRenderDebug('SurveyAccessTab')
  const { slug, surveySlug } = useParams({ from: '/_studio/projects/$slug/surveys/$surveySlug/access' })

  const { data: project } = useProject(slug)
  const { data: survey } = useSurvey(slug, surveySlug)
  const updateSurvey = useUpdateSurvey(project?.id ?? null, surveySlug)
  const [accessToast, setAccessToast] = useState<{ message: string; variant: 'success' | 'error' } | null>(null)

  const projectId = project?.id ?? 0
  const surveyId = survey?.id ?? 0
  const savedAccessMode = (survey?.visibility ?? 'link_only') as SurveyAccessMode
  const canEdit = useHasProjectPermission(project?.id ?? null, 'survey:edit')

  function showAccessToast(message: string, variant: 'success' | 'error') {
    setAccessToast({ message, variant })
    setTimeout(() => setAccessToast(null), 4000)
  }

  async function handleModeChange(mode: SurveyAccessMode, publicSlug: string | null): Promise<boolean> {
    try {
      const updatedSurvey = await updateSurvey.mutateAsync({
        visibility: mode,
        title: null,
        public_slug: mode === 'public' ? publicSlug : null,
      })
      showAccessToast(`Access mode changed to ${SURVEY_ACCESS_MODES[updatedSurvey.visibility].label}.`, 'success')
      return true
    } catch {
      showAccessToast('Failed to change access mode. Please check the public URL slug and try again.', 'error')
      return false
    }
  }

  return (
    <section className="mx-auto grid w-full gap-8">
      {accessToast && (
        <Toast variant={accessToast.variant} onClose={() => setAccessToast(null)}>
          {accessToast.message}
        </Toast>
      )}

      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-semibold text-foreground">Access</h2>
          </div>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
            Control who can open the survey, how links are issued, and which project members can work on it.
          </p>
        </div>
      </div>

      {/* Main two-column layout */}
      <div className="grid gap-8 xl:grid-cols-[minmax(0,78rem)_23rem] xl:justify-between xl:items-start">
        {/* Left column — primary content */}
        <div className="grid gap-8">
          <LinksSection
            projectId={projectId}
            surveyId={surveyId}
            publicSlug={survey?.public_slug ?? null}
            savedAccessMode={savedAccessMode}
            canEdit={canEdit}
          />

          <SectionDivider />

          <MembersSection projectId={projectId} surveyId={surveyId} canEdit={canEdit} />
        </div>

        {/* Right column — sticky sidebar */}
        <aside className="grid gap-4 sm:grid-cols-2 xl:sticky xl:top-4 xl:grid-cols-1">
          <AccessSidebarSummary
            mode={savedAccessMode}
            publicSlug={survey?.public_slug ?? null}
            surveyTitle={survey?.title ?? ''}
            isSaving={updateSurvey.isPending}
            canEdit={canEdit}
            onModeChange={handleModeChange}
          />
          <SurveyRolesReferenceCard projectId={projectId} canEdit={canEdit} />
        </aside>
      </div>
    </section>
  )
}
