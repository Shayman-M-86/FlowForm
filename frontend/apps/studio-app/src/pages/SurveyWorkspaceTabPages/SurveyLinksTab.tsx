import { useParams } from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import { Button, Card, Input, Modal, Select, Toggle } from '@flowform/ui'
import { getMockPublicLinksForSurvey, getMockSurvey, type MockPublicLink } from '@/api/mockData'
import { useRenderDebug } from '@/debug/useRenderDebug'
import {
  LinkOnlyAccessLinksPanel,
  LinkStateBadge,
  PrivateAccessEmptyState,
  PublicSurveyUrlPanel,
  SurveyAccessSummary,
} from '@/components/SurveyAccess'
import {
  SURVEY_ACCESS_CONCEPTS,
  SURVEY_ACCESS_ENTRIES,
  SURVEY_ACCESS_MODES,
  type SurveyAccessEntry,
  type SurveyAccessMode,
} from '@/lib/surveyAccessDesign'

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

function isCreatableLinkType(entry: SurveyAccessEntry): entry is CreatableLinkType {
  return (CREATABLE_LINK_TYPES as readonly SurveyAccessEntry[]).includes(entry)
}

function createDefaultLinkForm(type: CreatableLinkType): CreateLinkFormState {
  return {
    type,
    name: '',
    assignedEmail: '',
    expiresAt: '',
    requireAuthForGeneralLink: false,
  }
}

function publicLinkStatus(link: MockPublicLink): 'active' | 'disabled' | 'expired' {
  if (link.expiresAt && new Date(link.expiresAt).getTime() < Date.now()) {
    return 'expired'
  }

  return link.isActive ? 'active' : 'disabled'
}

export function SurveyLinksTab() {
  useRenderDebug('SurveyLinksTab')
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/links' })
  const survey = getMockSurvey(slug, surveySlug)
  const links = getMockPublicLinksForSurvey(surveySlug)
  const isPublished = survey?.publishedVersionNumber != null
  const accessMode = (isPublished ? 'link_only' : 'private') as SurveyAccessMode
  const allowedCreateLinkTypes = useMemo(
    () => SURVEY_ACCESS_MODES[accessMode].allowedEntries.filter(isCreatableLinkType),
    [accessMode],
  )
  const firstCreateLinkType = allowedCreateLinkTypes[0] ?? 'authenticated_assigned_link'
  const [createLinkOpen, setCreateLinkOpen] = useState(false)
  const [createdLinks, setCreatedLinks] = useState<DisplayPublicLink[]>([])
  const [createLinkForm, setCreateLinkForm] = useState<CreateLinkFormState>(() => (
    createDefaultLinkForm(firstCreateLinkType)
  ))

  const selectedLinkDefinition = SURVEY_ACCESS_ENTRIES[createLinkForm.type]
  const requiresAssignedEmail = createLinkForm.type !== 'general_link'
  const requiresAuth = createLinkForm.type === 'authenticated_assigned_link'
  const canCreateLink = createLinkForm.name.trim().length > 0
    && (!requiresAssignedEmail || createLinkForm.assignedEmail.trim().length > 0)
  const visibleLinks: DisplayPublicLink[] = [...createdLinks, ...links]

  function openCreateLinkModal() {
    const linkType = allowedCreateLinkTypes[0]
    if (!linkType) return

    setCreateLinkForm(createDefaultLinkForm(linkType))
    setCreateLinkOpen(true)
  }

  function createLink() {
    if (!canCreateLink) return

    const tokenPrefix = Math.random().toString(36).slice(2, 10)
    const nextLink: DisplayPublicLink = {
      id: Date.now(),
      surveySlug,
      tokenPrefix,
      isActive: true,
      assignedEmail: requiresAssignedEmail ? createLinkForm.assignedEmail.trim() : null,
      expiresAt: createLinkForm.expiresAt ? `${createLinkForm.expiresAt}T00:00:00Z` : null,
      submissions: 0,
      createdAt: new Date().toISOString(),
      url: `https://flowform.app/s/${tokenPrefix}`,
      name: createLinkForm.name.trim(),
      linkType: createLinkForm.type,
      requiresAuth: requiresAuth || createLinkForm.requireAuthForGeneralLink,
    }

    setCreatedLinks((current) => [nextLink, ...current])
    setCreateLinkOpen(false)
  }

  return (
    <section className="grid gap-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Respondent access</h2>
          <p className="text-sm text-muted-foreground">Manage how respondents open and complete this survey.</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-start">
        <div className="grid gap-4">
          {!isPublished && (
            <PrivateAccessEmptyState onEnableLinkAccess={openCreateLinkModal} />
          )}

          {isPublished && (
            <LinkOnlyAccessLinksPanel onCreateLink={openCreateLinkModal} />
          )}

          {accessMode === 'public' && survey && <PublicSurveyUrlPanel slug={survey.slug} />}

          {visibleLinks.length > 0 && (
            <div className="grid gap-4">
              {visibleLinks.map((link, i) => (
                <Card key={link.id}>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        {i === 0 && (
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Primary</span>
                        )}
                        <code className="rounded bg-muted px-1.5 py-0.5 text-xs text-foreground">{link.tokenPrefix}</code>
                        <LinkStateBadge state={publicLinkStatus(link)} />
                        {link.linkType && (
                          <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                            {SURVEY_ACCESS_ENTRIES[link.linkType].label}
                          </span>
                        )}
                        {link.assignedEmail && (
                          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                            {(() => {
                              const Icon = SURVEY_ACCESS_CONCEPTS.emailBound.icon
                              return <Icon size={13} strokeWidth={2} aria-hidden="true" />
                            })()}
                            <span>{link.assignedEmail}</span>
                          </span>
                        )}
                      </div>
                      {link.name && <p className="mt-1.5 text-sm font-medium text-foreground">{link.name}</p>}
                      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        <span>Created {new Date(link.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                        <span>Expires {link.expiresAt ? new Date(link.expiresAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Never'}</span>
                        <span>{link.submissions} submissions</span>
                        {link.requiresAuth && <span>Requires sign in</span>}
                      </div>
                      <p className="mt-2 truncate font-mono text-xs text-muted-foreground">{link.url}</p>
                    </div>
                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      <Button variant="secondary" size="xs">Copy link</Button>
                      <Button variant="secondary" size="xs">{link.isActive ? 'Disable' : 'Enable'}</Button>
                      <Button variant="secondary" size="xs">Regenerate</Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {isPublished && visibleLinks.length === 0 && (
            <Card tone="muted">
              <p className="text-sm text-muted-foreground">No public links yet. Create one to start sharing this survey.</p>
            </Card>
          )}
        </div>

        <aside className="lg:sticky lg:top-4">
          <SurveyAccessSummary mode={accessMode} />
        </aside>
      </div>

      <Modal
        open={createLinkOpen}
        onClose={() => setCreateLinkOpen(false)}
        title="Create access link"
        width={560}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setCreateLinkOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" disabled={!canCreateLink} onClick={createLink}>
              Create link
            </Button>
          </>
        )}
      >
        <div className="grid gap-4">
          <Select
            label="Link type"
            value={createLinkForm.type}
            options={allowedCreateLinkTypes.map((type) => ({
              value: type,
              label: SURVEY_ACCESS_ENTRIES[type].label,
            }))}
            onValueChange={(value) => {
              const nextType = value as CreatableLinkType
              setCreateLinkForm((current) => ({
                ...current,
                type: nextType,
                assignedEmail: nextType === 'general_link' ? '' : current.assignedEmail,
                requireAuthForGeneralLink: nextType === 'general_link'
                  ? current.requireAuthForGeneralLink
                  : false,
              }))
            }}
          />

          <div className="rounded-md border border-border bg-muted/20 p-3">
            <p className="text-sm font-semibold text-foreground">{selectedLinkDefinition.label}</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {selectedLinkDefinition.shortDescription}
            </p>
            <ul className="mt-2 grid gap-1 text-xs leading-5 text-muted-foreground">
              {selectedLinkDefinition.details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          </div>

          <Input
            label="Link name"
            value={createLinkForm.name}
            placeholder="Participant A, Batch invite, Pilot group"
            onChange={(event) => setCreateLinkForm((current) => ({
              ...current,
              name: event.target.value,
            }))}
          />

          {requiresAssignedEmail && (
            <Input
              label="Assigned participant email"
              type="email"
              value={createLinkForm.assignedEmail}
              placeholder="participant@example.com"
              hint={requiresAuth
                ? 'The participant must sign in with this email before using the link.'
                : 'The link is assigned to this participant but does not require sign-in.'}
              onChange={(event) => setCreateLinkForm((current) => ({
                ...current,
                assignedEmail: event.target.value,
              }))}
            />
          )}

          {createLinkForm.type === 'general_link' && (
            <Toggle
              label="Require sign in"
              checked={createLinkForm.requireAuthForGeneralLink}
              onChange={(checked) => setCreateLinkForm((current) => ({
                ...current,
                requireAuthForGeneralLink: checked,
              }))}
              hint="General links are not assigned to a participant email."
            />
          )}

          <Input
            label="Expiry date"
            type="date"
            value={createLinkForm.expiresAt}
            onChange={(event) => setCreateLinkForm((current) => ({
              ...current,
              expiresAt: event.target.value,
            }))}
          />
        </div>
      </Modal>
    </section>
  )
}
