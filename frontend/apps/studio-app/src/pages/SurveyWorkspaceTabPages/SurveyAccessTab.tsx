import { useEffect, useMemo, useRef, useState } from 'react'
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
  Table,
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
  RefreshCw,
  Shield,
  ShieldCheck,
  Users,
} from 'lucide-react'
import {
  getMockPublicLinksForSurvey,
  getMockSurvey,
  mockProjectMembers,
  type MockProjectMember,
  type MockPublicLink,
} from '@/api/mockData'
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
  DEFAULT_SURVEY_ROLE_ASSIGNMENTS,
  PROJECT_ROLE_TO_SURVEY_ROLE_ID,
  SURVEY_PERMISSION_GROUPS,
  SURVEY_PRESET_ROLES,
  permissionsGained,
  roleForId,
  rolePermissions,
  type CustomRole,
  type PermissionKey,
  type RoleWithPermissions,
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
  assignedEmail: string
  expiresAt: string
  requireAuthForGeneralLink: boolean
}

type DisplayPublicLink = MockPublicLink & {
  name?: string
  linkType?: CreatableLinkType
  requiresAuth?: boolean
}

type PermissionPreview = { key: PermissionKey; variant: 'default' | 'warning' }

interface MemberRow extends MockProjectMember {
  overrideRoleId?: string
  effectiveRoleId: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function isCreatableLinkType(entry: SurveyAccessEntry): entry is CreatableLinkType {
  return (CREATABLE_LINK_TYPES as readonly SurveyAccessEntry[]).includes(entry)
}

function createDefaultLinkForm(type: CreatableLinkType): CreateLinkFormState {
  return { type, name: '', assignedEmail: '', expiresAt: '', requireAuthForGeneralLink: false }
}

function publicLinkStatus(link: MockPublicLink): 'active' | 'disabled' | 'expired' {
  if (link.expiresAt && new Date(link.expiresAt).getTime() < Date.now()) return 'expired'
  return link.isActive ? 'active' : 'disabled'
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
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
  onModeChange,
}: {
  mode: SurveyAccessMode
  onModeChange: (mode: SurveyAccessMode) => void
}) {
  const [modalOpen, setModalOpen] = useState(false)
  const [draftMode, setDraftMode] = useState<SurveyAccessMode>(mode)

  function openModal() {
    setDraftMode(mode)
    setModalOpen(true)
  }

  function applyModal() {
    onModeChange(draftMode)
    setModalOpen(false)
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
            <Button variant="secondary" size="sm" className="shrink-0" onClick={openModal}>
              Edit
            </Button>
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
            <Button variant="primary" onClick={applyModal}>Apply</Button>
          </>
        }
      >
        <div className="grid gap-4">
          <p className="text-sm leading-6 text-muted-foreground">
            Choose who can open and complete the survey. The sharing controls adapt to the saved model.
          </p>
          <SurveyAccessModeSelector value={draftMode} onChange={setDraftMode} />
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

function LinkCard({ link }: { link: DisplayPublicLink }) {
  const status = publicLinkStatus(link)
  const moreRef = useRef<HTMLSpanElement>(null)
  const metadataRef = useRef<HTMLDivElement>(null)
  const emailRef = useRef<HTMLDivElement>(null)
  const [moreOpen, setMoreOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [stackUrl, setStackUrl] = useState(false)
  const linkTitle = link.name ?? `Link ${link.tokenPrefix}`

  useEffect(() => {
    const metadata = metadataRef.current
    const email = emailRef.current
    if (!metadata || !email) {
      setStackUrl(false)
      return
    }

    const updateStacking = () => {
      const gap = 12
      const urlColumnWidth = Math.min(metadata.clientWidth, 256)
      setStackUrl(email.scrollWidth + urlColumnWidth + gap > metadata.clientWidth)
    }

    updateStacking()
    const observer = new ResizeObserver(updateStacking)
    observer.observe(metadata)
    observer.observe(email)

    return () => observer.disconnect()
  }, [link.assignedEmail, link.url])

  function copyLink() {
    navigator.clipboard.writeText(link.url).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Card size="sm">
      <div className="grid gap-2">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-wrap items-center gap-1.5">
            <LinkStateBadge state={status} />
            {link.linkType && (
              <Badge variant="muted" size="xs">
                {SURVEY_ACCESS_ENTRIES[link.linkType].label}
              </Badge>
            )}
            <span className="text-xs text-muted-foreground">{link.submissions} submissions</span>
          </div>
          <div className="flex flex-wrap justify-end gap-x-3 gap-y-0.5 text-right text-xs text-muted-foreground">
            <span>Created {formatDate(link.createdAt)}</span>
            <span>Expires {link.expiresAt ? formatDate(link.expiresAt) : 'Never'}</span>
          </div>
        </div>

        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="min-w-3 text-sm font-medium text-foreground">{linkTitle}</p>
            <div ref={metadataRef} className="mt-1 flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
              {link.assignedEmail && (
                <div ref={emailRef} className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
                  <MailCheck size={13} strokeWidth={2} aria-hidden="true" className="shrink-0 text-muted-foreground" />
                  <span className="truncate">{link.assignedEmail}</span>
                </div>
              )}
              <p
                className={`min-w-[min(100%,16rem)] max-w-full truncate font-mono text-xs text-muted-foreground ${
                  stackUrl ? 'basis-full text-left' : 'ml-auto text-right'
                }`}
              >
                {link.url}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 flex-col items-end justify-between gap-2 pl-2 self-stretch">
            {link.requiresAuth && (
              <span className="text-right text-xs text-muted-foreground">Requires sign-in</span>
            )}
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
                fullscreenAt="never"
                sections={[{
                  actions: [
                    {
                      key: 'toggle',
                      content: (
                        <span className="flex items-center gap-2">
                          {link.isActive
                            ? <><Ban size={13} strokeWidth={2} aria-hidden="true" /> Disable link</>
                            : <><CheckCircle2 size={13} strokeWidth={2} aria-hidden="true" /> Enable link</>
                          }
                        </span>
                      ),
                    },
                    {
                      key: 'regenerate',
                      content: (
                        <span className="flex items-center gap-2">
                          <RefreshCw size={13} strokeWidth={2} aria-hidden="true" /> Regenerate token
                        </span>
                      ),
                    },
                  ],
                }]}
              />
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

function LinksSection({
  slug,
  surveySlug,
  savedAccessMode,
}: {
  slug: string
  surveySlug: string
  savedAccessMode: SurveyAccessMode
}) {
  const survey = getMockSurvey(slug, surveySlug)
  const links = getMockPublicLinksForSurvey(surveySlug)
  const allowedCreateLinkTypes = useMemo(
    () => SURVEY_ACCESS_MODES[savedAccessMode].allowedEntries.filter(isCreatableLinkType),
    [savedAccessMode],
  )
  const firstCreateLinkType = allowedCreateLinkTypes[0] ?? 'authenticated_assigned_link'

  const [createLinkOpen, setCreateLinkOpen] = useState(false)
  const [createdLinks, setCreatedLinks] = useState<DisplayPublicLink[]>([])
  const [form, setForm] = useState<CreateLinkFormState>(() => createDefaultLinkForm(firstCreateLinkType))

  const selectedLinkDef = SURVEY_ACCESS_ENTRIES[form.type]
  const requiresAssignedEmail = form.type !== 'general_link'
  const requiresAuth = form.type === 'authenticated_assigned_link'
  const canCreate = form.name.trim().length > 0 && (!requiresAssignedEmail || form.assignedEmail.trim().length > 0)
  const visibleLinks: DisplayPublicLink[] = [...createdLinks, ...links]

  function openModal() {
    const type = allowedCreateLinkTypes[0]
    if (!type) return
    setForm(createDefaultLinkForm(type))
    setCreateLinkOpen(true)
  }

  function createLink() {
    if (!canCreate) return
    const tokenPrefix = Math.random().toString(36).slice(2, 10)
    setCreatedLinks((current) => [
      {
        id: Date.now(),
        surveySlug,
        tokenPrefix,
        isActive: true,
        assignedEmail: requiresAssignedEmail ? form.assignedEmail.trim() : null,
        expiresAt: form.expiresAt ? `${form.expiresAt}T00:00:00Z` : null,
        submissions: 0,
        createdAt: new Date().toISOString(),
        url: `https://flowform.app/s/${tokenPrefix}`,
        name: form.name.trim(),
        linkType: form.type,
        requiresAuth: requiresAuth || form.requireAuthForGeneralLink,
      },
      ...current,
    ])
    setCreateLinkOpen(false)
  }

  const canAddLinks = savedAccessMode !== 'private' && allowedCreateLinkTypes.length > 0

  return (
    <div className="grid gap-4">
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

      {savedAccessMode === 'public' && survey && (
        <Card tone="muted" size="sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-md bg-success/10 text-success">
                <Globe2 size={15} strokeWidth={2} aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">Public URL active</p>
                <code className="mt-0.5 block truncate font-mono text-xs text-muted-foreground">
                  https://flowform.app/s/{survey.slug}
                </code>
              </div>
            </div>
            <Button type="button" variant="secondary" size="xs" icon="copy" className="shrink-0">
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

      {visibleLinks.length > 0 ? (
        <CardStack gap="sm">
          {visibleLinks.map((link) => (
            <LinkCard key={link.id} link={link} />
          ))}
        </CardStack>
      ) : (
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
      )}

      <Modal
        open={createLinkOpen}
        onClose={() => setCreateLinkOpen(false)}
        title="Create access link"
        width={560}
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateLinkOpen(false)}>Cancel</Button>
            <Button variant="primary" disabled={!canCreate} onClick={createLink}>Create link</Button>
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
                assignedEmail: nextType === 'general_link' ? '' : current.assignedEmail,
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

          {requiresAssignedEmail && (
            <Input
              label="Assigned participant email"
              type="email"
              value={form.assignedEmail}
              placeholder="participant@example.com"
              hint={requiresAuth
                ? 'The participant must sign in with this email before using the link.'
                : 'Assigned to this participant but does not require sign-in.'}
              onChange={(e) => setForm((current) => ({ ...current, assignedEmail: e.target.value }))}
            />
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
    </div>
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

function MembersSection() {
  const [surveyRoleAssignments, setSurveyRoleAssignments] = useState<Record<number, string>>(
    DEFAULT_SURVEY_ROLE_ASSIGNMENTS,
  )
  const [customSurveyRoles, setCustomSurveyRoles] = useState<CustomRole[]>([])
  const [editingRole, setEditingRole] = useState<RoleEditorState | null>(null)
  const selectCreatedRoleRef = useRef<((roleId: string) => void) | null>(null)

  const surveyRoles = useMemo<RoleWithPermissions[]>(
    () => [...SURVEY_PRESET_ROLES, ...customSurveyRoles],
    [customSurveyRoles],
  )

  const rows = useMemo<MemberRow[]>(
    () =>
      mockProjectMembers.map((member) => {
        const overrideRoleId = surveyRoleAssignments[member.id]
        return {
          ...member,
          overrideRoleId,
          effectiveRoleId: overrideRoleId ?? PROJECT_ROLE_TO_SURVEY_ROLE_ID[member.role],
        }
      }),
    [surveyRoleAssignments],
  )

  const addSurveyRole = (selectRole: (roleId: string) => void) => {
    const id = `survey-custom-${Date.now()}`
    selectCreatedRoleRef.current = selectRole
    setEditingRole({ id, custom: true, name: 'New survey role', description: 'Custom survey role.', permissions: new Set() })
  }

  const saveSurveyRole = () => {
    if (!editingRole) return
    const next = {
      name: editingRole.name.trim(),
      description: editingRole.description.trim(),
      permissions: [...editingRole.permissions],
    }
    if (!next.name) return
    setCustomSurveyRoles((current) =>
      current.some((r) => r.id === editingRole.id)
        ? current.map((r) => r.id === editingRole.id ? { ...r, ...next } : r)
        : [...current, { id: editingRole.id, ...next }],
    )
    selectCreatedRoleRef.current?.(editingRole.id)
    selectCreatedRoleRef.current = null
    setEditingRole(null)
  }

  const deleteSurveyRole = () => {
    if (!editingRole?.custom) return
    setCustomSurveyRoles((current) => current.filter((r) => r.id !== editingRole.id))
    setSurveyRoleAssignments((current) => {
      const next = { ...current }
      for (const [memberId, roleId] of Object.entries(next)) {
        if (roleId === editingRole.id) delete next[Number(memberId)]
      }
      return next
    })
    selectCreatedRoleRef.current = null
    setEditingRole(null)
  }

  const surveyPermissionPreview = (member: MemberRow, roleId: string): PermissionPreview[] => {
    const gained = permissionsGained(surveyRoles, PROJECT_ROLE_TO_SURVEY_ROLE_ID[member.role], roleId)
    return rolePermissions(surveyRoles, roleId).map((permission) => ({
      key: permission,
      variant: gained.includes(permission) ? 'warning' : 'default',
    }))
  }

  const columns: TableColumn<MemberRow>[] = [
    {
      key: 'member',
      header: 'Member',
      minWidth: 100,
      maxWidth: 200,
      cell: (member) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{member.name}</p>
          <p className="truncate text-2xs text-muted-foreground">{member.email}</p>
        </div>
      ),
    },
    {
      key: 'project-role',
      header: 'Project role',
      minWidth: 65,
      maxWidth: 150,
      cell: (member) => (
        <RoleBadgePreview
          label={member.role}
          permissions={rolePermissions(surveyRoles, PROJECT_ROLE_TO_SURVEY_ROLE_ID[member.role]).map((p) => ({ key: p }))}
        />
      ),
    },
    {
      key: 'survey-role',
      header: 'Survey role override',
      minWidth: 75,
      maxWidth: 160,
      cell: (member) => {
        const gained = permissionsGained(surveyRoles, PROJECT_ROLE_TO_SURVEY_ROLE_ID[member.role], member.effectiveRoleId)
        if (!member.overrideRoleId || gained.length === 0) {
          return <span className="text-xs text-muted-foreground">—</span>
        }
        const role = roleForId(surveyRoles, member.overrideRoleId)
        return (
          <RoleBadgePreview
            label={role?.name ?? 'Custom role'}
            prefix="+"
            variant="warning"
            permissions={gained.map((p) => ({ key: p, variant: 'warning' as const }))}
          />
        )
      },
    },
    {
      key: 'effective',
      header: 'Effective permissions',
      minWidth: 110,
      cell: (member) => (
        <CompactPermissionBadges permissions={surveyPermissionPreview(member, member.effectiveRoleId)} />
      ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      minWidth: 50,
      maxWidth: 50,
      headerClassName: 'flex justify-center pr-2',
      cellClassName: 'flex justify-center px-0',
      cell: (member) => (
        <MemberRoleActions
          memberName={member.name}
          memberEmail={member.email}
          editRoleLabel="Edit survey role"
          roles={surveyRoles}
          selectedRoleId={member.overrideRoleId ?? member.effectiveRoleId}
          onSaveRole={(roleId) =>
            setSurveyRoleAssignments((current) => ({ ...current, [member.id]: roleId }))
          }
          onRemoveRole={
            member.overrideRoleId
              ? () => setSurveyRoleAssignments((current) => {
                const next = { ...current }
                delete next[member.id]
                return next
              })
              : undefined
          }
          removeRoleLabel="Remove survey role"
          onAddRole={addSurveyRole}
          renderEffectivePreview={(roleId) => (
            <PermissionBadges permissions={surveyPermissionPreview(member, roleId)} />
          )}
        />
      ),
    },
  ]

  return (
    <div className="grid gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <SectionLabel
          label="Assignment"
          title="Members and role overrides"
          description="Review project members' inherited roles and apply survey-specific overrides where needed."
        />
        <Button variant="primary" size="sm" icon="plus" className="shrink-0 self-end">
          Add member
        </Button>
      </div>

      <div className="w-full overflow-hidden">
        <Table columns={columns} rows={rows} getRowKey={(member) => member.id} />
      </div>

      <RoleEditorModal
        role={editingRole}
        onClose={() => {
          setEditingRole(null)
          selectCreatedRoleRef.current = null
        }}
        onChange={setEditingRole}
        onSave={saveSurveyRole}
        onDelete={deleteSurveyRole}
        permissionGroups={SURVEY_PERMISSION_GROUPS}
        isNew
      />
    </div>
  )
}

// ── Survey roles reference card ───────────────────────────────────────────────

function SurveyRolesReferenceCard() {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [editingRole, setEditingRole] = useState<RoleEditorState | null>(null)
  const [isNew, setIsNew] = useState(false)
  const [customRoles, setCustomRoles] = useState<CustomRole[]>([])

  const allRoles = [...SURVEY_PRESET_ROLES, ...customRoles]

  function openAddRole() {
    setEditingRole({
      id: `survey-custom-${Date.now()}`,
      custom: true,
      name: 'New survey role',
      description: 'Custom survey role.',
      permissions: new Set(),
    })
    setIsNew(true)
  }

  function saveRole() {
    if (!editingRole) return
    const next = {
      name: editingRole.name.trim(),
      description: editingRole.description.trim(),
      permissions: [...editingRole.permissions],
    }
    if (!next.name) return
    setCustomRoles((current) =>
      current.some((r) => r.id === editingRole.id)
        ? current.map((r) => r.id === editingRole.id ? { ...r, ...next } : r)
        : [...current, { id: editingRole.id, ...next }],
    )
    setExpandedId(editingRole.id)
    setEditingRole(null)
    setIsNew(false)
  }

  function deleteRole() {
    if (!editingRole?.custom) return
    setCustomRoles((current) => current.filter((r) => r.id !== editingRole.id))
    setEditingRole(null)
    setIsNew(false)
  }

  return (
    <>
      <Card size="sm">
        <div className="grid gap-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="mt-0.5 text-lg font-semibold text-foreground">Survey roles</p>
            </div>
            <Button variant="secondary" size="xs" icon="plus" className="shrink-0" onClick={openAddRole}>
              Add role
            </Button>
          </div>
          <div className="grid gap-1.5">
            {allRoles.map((role) => {
              const isExpanded = expandedId === role.id
              const isCustom = customRoles.some((r) => r.id === role.id)
              return (
                <div key={role.id} className="overflow-hidden rounded-md border border-border bg-muted/30">
                  <button
                    type="button"
                    onClick={() => setExpandedId(isExpanded ? null : role.id)}
                    className="ui-button-ghost w-full justify-between rounded-none px-2.5 py-2 text-left"
                    aria-expanded={isExpanded}
                  >
                    <div className="flex min-w-0 items-center gap-1.5">
                      <p className="truncate text-lg font-semibold text-foreground">{role.name}</p>
                      {isCustom && <Badge variant="accent" size="xxs">Custom</Badge>}
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <ChevronRight
                        size={12}
                        strokeWidth={2}
                        aria-hidden="true"
                        className={`text-muted-foreground transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                      />
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="grid gap-2 border-t border-border px-2.5 py-2.5">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex flex-wrap gap-1.5">
                          {role.permissions.map((permission) => (
                            <PermissionBadge key={permission} permission={permission} />
                          ))}
                          {role.permissions.length === 0 && (
                            <p className="text-xs text-muted-foreground">No permissions assigned.</p>
                          )}
                        </div>
                        <Button
                          variant="secondary"
                          size="xs"
                          className="shrink-0"
                          onClick={() => setEditingRole({
                            id: role.id,
                            custom: isCustom,
                            name: role.name,
                            description: role.description,
                            permissions: new Set(role.permissions),
                          })}
                        >
                          Edit
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </Card>

      <RoleEditorModal
        role={editingRole}
        onClose={() => { setEditingRole(null); setIsNew(false) }}
        onChange={setEditingRole}
        onSave={saveRole}
        onDelete={deleteRole}
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
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/access' })

  const [savedAccessMode, setSavedAccessMode] = useState<SurveyAccessMode>('link_only')

  const publicLinks = getMockPublicLinksForSurvey(surveySlug)
  const activeLinkCount = publicLinks.filter((l) => l.isActive).length
  const savedAccessDefinition = SURVEY_ACCESS_MODES[savedAccessMode]

  return (
    <section className="mx-auto grid w-full gap-8">
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
          {/* Section 1: Links */}
          <LinksSection slug={slug} surveySlug={surveySlug} savedAccessMode={savedAccessMode} />

          <SectionDivider />

          {/* Section 3: Members */}
          <MembersSection />
        </div>

        {/* Right column — sticky sidebar */}
        <aside className="grid gap-4 sm:grid-cols-2 xl:sticky xl:top-4 xl:grid-cols-1">
          {/* Access summary */}
          <AccessSidebarSummary mode={savedAccessMode} onModeChange={setSavedAccessMode} />

          {/* Quick reference: survey roles */}
          <SurveyRolesReferenceCard />

        </aside>
      </div>
    </section>
  )
}
