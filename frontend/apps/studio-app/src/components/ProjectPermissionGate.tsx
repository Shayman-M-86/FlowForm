import { useProject } from '@/api/hooks/projects'
import { useMyProjectPermissions } from '@/api/hooks/permissions'
import type { ProjectPermission } from '@/api/hooks/permissions'
import { useParams } from '@tanstack/react-router'
import type { ReactNode } from 'react'

interface Props {
  /** Renders children when the actor has at least one of these permissions. */
  anyOf: ProjectPermission[]
  children: ReactNode
}

export function ProjectPermissionGate({ anyOf, children }: Props) {
  const { slug } = useParams({ strict: false })
  const { data: project } = useProject(slug ?? null)
  const projectId = project?.id ?? null
  const { data: permissions, isPending } = useMyProjectPermissions(projectId)

  // While permissions are loading (first visit with no cache), render nothing
  // to avoid a flash of the restricted message.
  if (isPending && !permissions) return null

  const allowed = permissions != null && anyOf.some((p) => permissions.includes(p))

  if (!allowed) {
    return (
      <div className="flex min-h-40 flex-col items-center justify-center gap-2 text-center">
        <p className="text-sm font-medium text-foreground">Access restricted</p>
        <p className="text-sm text-muted-foreground">You don't have permission to view this section.</p>
      </div>
    )
  }

  return <>{children}</>
}
