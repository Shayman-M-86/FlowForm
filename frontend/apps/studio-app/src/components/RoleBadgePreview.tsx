import { useRef, useState } from 'react'
import { Badge, DropdownMenu } from '@flowform/ui'
import { PermissionBadge } from '@/components/PermissionBadge'
import { type PermissionKey } from '@/pages/ProjectDashboardTabPages/roleDefinitions'

type BadgeVariant = 'default' | 'success' | 'danger' | 'warning' | 'accent' | 'muted'

type PermissionPreview = {
  key: PermissionKey
  variant?: BadgeVariant
}

type RoleBadgePreviewProps = {
  label: string
  permissions: PermissionPreview[]
  variant?: BadgeVariant
  prefix?: string
}

export function RoleBadgePreview({
  label,
  permissions,
  variant = 'default',
  prefix,
}: RoleBadgePreviewProps) {
  const triggerRef = useRef<HTMLSpanElement>(null)
  const [open, setOpen] = useState(false)
  const displayLabel = prefix ? `${prefix} ${label}` : label

  return (
    <>
      <span ref={triggerRef} className="inline-flex">
        <Badge
          variant={variant}
          size="xs"
          onClick={() => setOpen((current) => !current)}
        >
          {displayLabel}
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
        sections={[
          {
            actions: [
              {
                key: 'role-preview',
                closeOnSelect: false,
                content: (
                  <div className="grid w-full gap-3 rounded-sm px-3 py-2 text-left">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">{displayLabel}</p>
                      <p className="text-xs text-muted-foreground">Permissions granted by this role</p>
                    </div>
                    {permissions.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {permissions.map((permission) => (
                          <PermissionBadge
                            key={permission.key}
                            permission={permission.key}
                            variant={permission.variant ?? 'default'}
                          />
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">No permissions assigned.</p>
                    )}
                  </div>
                ),
              },
            ],
          },
        ]}
      />
    </>
  )
}
