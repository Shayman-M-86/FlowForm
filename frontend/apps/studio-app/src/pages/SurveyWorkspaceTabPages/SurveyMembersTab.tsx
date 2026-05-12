import { Badge, Button, Card } from '@flowform/ui'
import { mockSurveyMembers, type MockSurveyMember } from '@/api/mockData'

const ROLE_DESCRIPTIONS: Record<MockSurveyMember['role'], string> = {
  Manager: 'Manage members, settings, and archive',
  Publisher: 'Build, preview, publish, manage links',
  Editor: 'Build and preview drafts',
  Viewer: 'View survey setup and responses',
}

const ROLE_BADGE_VARIANT: Record<MockSurveyMember['role'], 'accent' | 'warning' | 'muted' | 'default'> = {
  Manager: 'accent',
  Publisher: 'warning',
  Editor: 'default',
  Viewer: 'muted',
}

export function SurveyMembersTab() {
  const inherited = mockSurveyMembers.filter((m) => m.inherited)
  const specific = mockSurveyMembers.filter((m) => !m.inherited)

  return (
    <div className="grid gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold">Survey members</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Manage who can view, edit, publish, or manage this survey.
          </p>
        </div>
        <Button variant="primary" size="sm">Add member</Button>
      </div>

      {/* Survey-specific access */}
      <Card>
        <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Survey-specific access
        </p>
        {specific.length === 0 ? (
          <p className="text-sm text-muted-foreground">No survey-specific members yet.</p>
        ) : (
          <div className="divide-y divide-border">
            {specific.map((m) => (
              <div key={m.id} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">{m.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{m.email}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <div className="text-right">
                    <Badge variant={ROLE_BADGE_VARIANT[m.role]} size="xs">{m.role}</Badge>
                    <p className="mt-0.5 text-xs text-muted-foreground">{ROLE_DESCRIPTIONS[m.role]}</p>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="secondary" size="xs">Change role</Button>
                    <Button variant="secondary" size="xs">Remove</Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Inherited from project */}
      <Card tone="muted">
        <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Inherited from project
        </p>
        <div className="divide-y divide-border">
          {inherited.map((m) => (
            <div key={m.id} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{m.name}</p>
                <p className="truncate text-xs text-muted-foreground">{m.email}</p>
              </div>
              <div className="text-right">
                <Badge variant={ROLE_BADGE_VARIANT[m.role]} size="xs">{m.role}</Badge>
                <p className="mt-0.5 text-xs text-muted-foreground">Via project</p>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-muted-foreground">
          Inherited members get access through their project role. To change their survey access, add them as a
          survey-specific member above.
        </p>
      </Card>
    </div>
  )
}
