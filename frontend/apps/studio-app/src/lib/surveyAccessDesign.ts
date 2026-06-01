import {
  Ban,
  CheckCircle2,
  Clock,
  Globe2,
  Link,
  LockKeyhole,
  MailCheck,
  UserCheck,
  type LucideIcon,
} from 'lucide-react'

export type SurveyAccessConcept =
  | 'private'
  | 'linkOnly'
  | 'public'
  | 'responseIdentity'
  | 'active'
  | 'disabled'
  | 'expired'
  | 'emailBound'

export const SURVEY_ACCESS_MODE_IDS = ['private', 'link_only', 'public'] as const
export const SURVEY_ACCESS_ENTRY_IDS = [
  'general_link',
  'authenticated_assigned_link',
  'private_invite_link',
  'public_slug',
] as const

export type SurveyAccessMode = typeof SURVEY_ACCESS_MODE_IDS[number]
export type SurveyAccessEntry = typeof SURVEY_ACCESS_ENTRY_IDS[number]

export type SurveyAccessConceptDefinition = {
  label: string
  description: string
  icon: LucideIcon
}

export type SurveyAccessModeDefinition = {
  label: string
  shortDescription: string
  description: string
  allowedEntries: SurveyAccessEntry[]
  blockedEntries: SurveyAccessEntry[]
  primaryAction: string | null
  sharingLabel: string
  icon: LucideIcon
}

export type SurveyAccessEntryDefinition = {
  label: string
  shortDescription: string
  details: string[]
  icon: LucideIcon
}

export const SURVEY_ACCESS_CONCEPTS: Record<SurveyAccessConcept, SurveyAccessConceptDefinition> = {
  private: {
    label: 'Private',
    description: 'Not publicly accessible.',
    icon: LockKeyhole,
  },
  linkOnly: {
    label: 'Link only',
    description: 'Only people with a valid access link can open the survey.',
    icon: Link,
  },
  public: {
    label: 'Public',
    description: 'Anyone with the public URL can open the survey.',
    icon: Globe2,
  },
  responseIdentity: {
    label: 'Response identity',
    description: 'Controls whether responses are anonymous, signed in, or tied to a participant.',
    icon: UserCheck,
  },
  active: {
    label: 'Active',
    description: 'Respondents can use this access link.',
    icon: CheckCircle2,
  },
  disabled: {
    label: 'Disabled',
    description: 'This access link has been manually turned off.',
    icon: Ban,
  },
  expired: {
    label: 'Expired',
    description: 'This access link is past its expiry date.',
    icon: Clock,
  },
  emailBound: {
    label: 'Email-bound',
    description: 'This access link is assigned to a specific participant email.',
    icon: MailCheck,
  },
}

export const SURVEY_ACCESS_ENTRIES: Record<SurveyAccessEntry, SurveyAccessEntryDefinition> = {
  general_link: {
    label: 'General link',
    shortDescription: 'A reusable access link for anyone who has it.',
    details: [
      'No assigned participant email',
      'Sign-in can be optional or off',
      'Multiple uses can be allowed when configured',
    ],
    icon: SURVEY_ACCESS_CONCEPTS.linkOnly.icon,
  },
  authenticated_assigned_link: {
    label: 'Authenticated assigned link',
    shortDescription: 'A single-use link tied to a signed-in participant.',
    details: [
      'Assigned to a specific participant email',
      'Requires sign-in',
      'Single-use',
      'Signed-in email must match the assigned email',
    ],
    icon: SURVEY_ACCESS_CONCEPTS.emailBound.icon,
  },
  private_invite_link: {
    label: 'Private invite link',
    shortDescription: 'A single-use invite link that does not require sign-in.',
    details: [
      'Assigned to a specific participant email',
      'Does not require sign-in',
      'Single-use',
      'No signed-in actor required',
    ],
    icon: SURVEY_ACCESS_CONCEPTS.private.icon,
  },
  public_slug: {
    label: 'Public URL',
    shortDescription: 'The public URL path for openly accessible surveys.',
    details: [
      'Anyone can open the survey URL',
      'Used for open participation and public forms',
      'Separate from participant-specific tracking links',
    ],
    icon: SURVEY_ACCESS_CONCEPTS.public.icon,
  },
}

export const SURVEY_ACCESS_MODES: Record<SurveyAccessMode, SurveyAccessModeDefinition> = {
  private: {
    label: 'Private',
    shortDescription: 'Authenticated assigned links only.',
    description: 'Private surveys require a participant-specific authenticated link.',
    allowedEntries: ['authenticated_assigned_link'],
    blockedEntries: ['private_invite_link', 'general_link', 'public_slug'],
    primaryAction: null,
    sharingLabel: 'No public sharing',
    icon: SURVEY_ACCESS_CONCEPTS.private.icon,
  },
  link_only: {
    label: 'Link only',
    shortDescription: 'Private invite links, authenticated assigned links, and general links are allowed.',
    description: 'Link-only surveys are not available through a public URL.',
    allowedEntries: ['private_invite_link', 'authenticated_assigned_link', 'general_link'],
    blockedEntries: ['public_slug'],
    primaryAction: 'Create link',
    sharingLabel: 'Invite links',
    icon: SURVEY_ACCESS_CONCEPTS.linkOnly.icon,
  },
  public: {
    label: 'Public',
    shortDescription: 'All respondent access methods are allowed.',
    description: 'Public surveys can be opened directly and can still use links for tracking or participant assignment.',
    allowedEntries: [
      'private_invite_link',
      'authenticated_assigned_link',
      'general_link',
      'public_slug',
    ],
    blockedEntries: [],
    primaryAction: 'Copy public URL',
    sharingLabel: 'Public URL',
    icon: SURVEY_ACCESS_CONCEPTS.public.icon,
  },
}
