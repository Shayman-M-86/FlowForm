import { Link } from '@tanstack/react-router'
import { useRenderDebug } from '@/debug/useRenderDebug'

type BreadcrumbSegment =
  | { label: string; to: string }
  | { label: string; current: true }

interface BreadcrumbProps {
  segments: BreadcrumbSegment[]
}

export function Breadcrumb({ segments }: BreadcrumbProps) {
  useRenderDebug('Breadcrumb', { segments })
  return (
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1.5 text-sm">
      {segments.map((segment, index) => (
        <span key={index} className="flex items-center gap-1.5 whitespace-nowrap">
          {index > 0 && (
            <span className="text-muted-foreground/50 select-none" aria-hidden="true">›</span>
          )}
          {'current' in segment ? (
            <span className="font-semibold text-foreground">{segment.label}</span>
          ) : (
            <Link
              to={segment.to}
              className="ui-button-text border-0 font-semibold"
            >
              {segment.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  )
}
