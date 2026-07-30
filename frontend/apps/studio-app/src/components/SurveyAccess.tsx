import { Badge, Button, Tooltip } from '@flowform/ui'
import { Info } from 'lucide-react'
import {
  SURVEY_ACCESS_CONCEPTS,
  SURVEY_ACCESS_ENTRIES,
  SURVEY_ACCESS_MODE_IDS,
  SURVEY_ACCESS_MODES,
  type SurveyAccessEntry,
  type SurveyAccessMode,
} from '@/lib/surveyAccessDesign'

type SurveyAccessModeSelectorProps = {
  value: SurveyAccessMode
  onChange: (mode: SurveyAccessMode) => void
  compact?: boolean
  showAccessGuide?: boolean
}

function accessEntryLabels(entries: SurveyAccessEntry[]): string {
  return entries.map((entry) => SURVEY_ACCESS_ENTRIES[entry].label).join(', ')
}

function AccessModesGuideContent() {
  return (
    <div className="grid max-w-80 gap-3 p-1 text-left">
      <div>
        <p className="text-sm font-semibold text-foreground">Survey access guide</p>
        <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
          The access mode controls which ways respondents can open the survey.
        </p>
      </div>
      <ul className="grid gap-3">
        {SURVEY_ACCESS_MODE_IDS.map((mode) => {
          const definition = SURVEY_ACCESS_MODES[mode]
          const Icon = definition.icon

          return (
            <li key={mode} className="flex items-start gap-2">
              <span className="mt-0.5 inline-flex size-6 shrink-0 items-center justify-center rounded-sm bg-muted text-muted-foreground">
                <Icon size={14} strokeWidth={2} aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <span className="block text-xs font-semibold text-foreground">{definition.label}</span>
                <span className="mt-0.5 block text-xs leading-5 text-muted-foreground">
                  {definition.shortDescription}
                </span>
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export function SurveyAccessModeSelector({
  value,
  onChange,
  compact = false,
  showAccessGuide = false,
}: SurveyAccessModeSelectorProps) {
  return (
    <div className="grid gap-2">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">How can people access this survey?</p>
          {!compact && (
            <p className="text-xs text-muted-foreground">
              Respondent access controls who can open and complete the survey.
            </p>
          )}
        </div>
        {showAccessGuide && (
          <Tooltip content={<AccessModesGuideContent />} size="sm" pinOnClick>
            <button
              type="button"
              className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <Info size={13} strokeWidth={2} aria-hidden="true" />
              Access guide
            </button>
          </Tooltip>
        )}
      </div>
      <div className={compact ? 'grid gap-2' : 'grid gap-2 sm:grid-cols-3'}>
        {SURVEY_ACCESS_MODE_IDS.map((mode) => {
          const definition = SURVEY_ACCESS_MODES[mode]
          const Icon = definition.icon
          const selected = value === mode

          return (
            <button
              key={mode}
              type="button"
              onClick={() => onChange(mode)}
              aria-pressed={selected}
              className={`flex h-full flex-col items-start rounded-md border p-3 text-left transition-colors ${
                selected
                  ? 'border-accent bg-accent/10 text-foreground'
                  : 'border-border bg-card text-foreground hover:bg-muted'
              }`}
            >
              <span className="flex min-w-0 items-center gap-2">
                <Icon size={15} strokeWidth={2} aria-hidden="true" />
                <span className="text-sm font-semibold">{definition.label}</span>
              </span>
              <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                {definition.shortDescription}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function SurveyAccessSummary({ mode }: { mode: SurveyAccessMode }) {
  const definition = SURVEY_ACCESS_MODES[mode]
  const Icon = definition.icon

  return (
    <div className="flex items-start gap-3 rounded-md border border-border bg-muted/20 p-3">
      <span className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-sm bg-muted text-muted-foreground">
        <Icon size={15} strokeWidth={2} aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-foreground">Respondent access</p>
          <Badge variant="muted" size="xxs">
            {definition.label}
          </Badge>
        </div>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{definition.description}</p>
        <div className="mt-2 grid gap-1 text-xs leading-5 text-muted-foreground">
          <p>
            <span className="font-medium text-foreground">Allowed:</span>{' '}
            {accessEntryLabels(definition.allowedEntries)}
          </p>
          <p>
            <span className="font-medium text-foreground">Not allowed:</span>{' '}
            {definition.blockedEntries.length > 0 ? accessEntryLabels(definition.blockedEntries) : 'None'}
          </p>
        </div>
      </div>
    </div>
  )
}

export function SurveyAccessSettingsPanel({
  mode,
  onModeChange,
}: {
  mode: SurveyAccessMode
  onModeChange: (mode: SurveyAccessMode) => void
}) {
  return (
    <div className="grid gap-4">
      <SurveyAccessModeSelector value={mode} onChange={onModeChange} />
      <SurveyAccessSummary mode={mode} />
    </div>
  )
}

export function PublicSurveyUrlPanel({
  slug,
  baseUrl = 'https://flowform.app/s',
}: {
  slug: string
  baseUrl?: string
}) {
  const definition = SURVEY_ACCESS_MODES.public
  const Icon = definition.icon

  return (
    <div className="grid gap-3 rounded-md border border-border bg-muted/20 p-3">
      <div className="flex items-center gap-2">
        <Icon size={15} strokeWidth={2} aria-hidden="true" />
        <p className="text-sm font-semibold text-foreground">{definition.sharingLabel}</p>
      </div>
      <code className="w-fit max-w-full truncate rounded bg-muted px-2 py-1 text-xs text-foreground">
        {baseUrl}/{slug}
      </code>
      <p className="text-xs text-muted-foreground">
        {definition.shortDescription} Allowed: {accessEntryLabels(definition.allowedEntries)}.
      </p>
    </div>
  )
}

export function LinkOnlyAccessLinksPanel({
  disabled,
  onCreateLink,
}: {
  disabled?: boolean
  onCreateLink?: () => void
}) {
  const definition = SURVEY_ACCESS_MODES.link_only
  const Icon = definition.icon

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-muted/20 p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Icon size={15} strokeWidth={2} aria-hidden="true" />
          <span>{definition.sharingLabel}</span>
        </p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          {definition.description} Allowed: {accessEntryLabels(definition.allowedEntries)}.
        </p>
      </div>
      <Button variant="primary" size="sm" icon="plus" disabled={disabled} onClick={onCreateLink}>
        {definition.primaryAction}
      </Button>
    </div>
  )
}

export function PrivateAccessEmptyState({ onEnableLinkAccess }: { onEnableLinkAccess?: () => void }) {
  const definition = SURVEY_ACCESS_MODES.private
  const Icon = definition.icon

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Icon size={15} strokeWidth={2} aria-hidden="true" />
          <span>{definition.sharingLabel}</span>
        </p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          {definition.description} Allowed: {accessEntryLabels(definition.allowedEntries)}.
        </p>
      </div>
      <Button variant="secondary" size="sm" onClick={onEnableLinkAccess}>
        Enable link access
      </Button>
    </div>
  )
}

export function LinkStateBadge({
  state,
}: {
  state: 'active' | 'disabled' | 'expired' | 'emailBound'
}) {
  const definition = SURVEY_ACCESS_CONCEPTS[state]
  const Icon = definition.icon
  const variant = state === 'active' ? 'success' : state === 'expired' ? 'warning' : 'muted'

  return (
    <Badge variant={variant} size="xs">
      <span className="inline-flex items-center gap-1">
        <Icon size={13} strokeWidth={2} aria-hidden="true" />
        <span>{definition.label}</span>
      </span>
    </Badge>
  )
}
