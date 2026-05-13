import { useNavigate, useParams } from '@tanstack/react-router'
import { Badge, Button } from '@flowform/ui'
import { PRESET_ROLES } from './RolesTab'

export function SettingsTab() {
  const { slug } = useParams({ strict: false })
  const navigate = useNavigate()

  return (
    <section className="grid max-w-6xl gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Settings</h2>
          <p className="text-sm text-muted-foreground">{PRESET_ROLES.length} roles</p>
        </div>
        <Button variant="primary" size="sm" icon="plus"
          onClick={() => navigate({ to: '/projects/$slug/roles', params: { slug: slug ?? '' } })}
        >
          Add role
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {PRESET_ROLES.map((role) => (
          <Badge key={role.id} variant="muted" size="xs">{role.name}</Badge>
        ))}
      </div>
    </section>
  )
}
