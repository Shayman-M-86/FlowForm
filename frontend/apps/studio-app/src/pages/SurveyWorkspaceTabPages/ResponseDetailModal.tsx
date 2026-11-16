import { Badge, Card, Modal } from '@flowform/ui'
import type { AnswerSlot, SessionTree } from '@/api/hooks/results'
import { orderAnswers, presentAnswer } from '@/lib/responsePresentation'

type Props = {
  sessionTree: SessionTree | null
  onClose: () => void
}

const STATUS_BADGE_VARIANT = {
  completed: 'success',
  in_progress: 'warning',
  abandoned: 'muted',
} as const

const STATUS_LABEL = {
  completed: 'Completed',
  in_progress: 'In Progress',
  abandoned: 'Abandoned',
} as const

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function AnswerCard({ answer, index }: { answer: AnswerSlot; index: number }) {
  const presented = presentAnswer(answer)
  return (
    <Card size="sm" tone="muted">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Question {index + 1}</p>
        <div className="flex items-center gap-1.5">
          {presented.family && (
            <Badge variant="muted" size="xs">{presented.family}</Badge>
          )}
          {answer.state ? (
            <Badge variant={answer.state === 'answered' ? 'success' : 'warning'} size="xs">
              {answer.state}
            </Badge>
          ) : (
            <Badge variant="muted" size="xs">
              {answer.has_encrypted_answer ? 'encrypted' : 'no answer'}
            </Badge>
          )}
        </div>
      </div>
      {presented.section && <p className="mt-2 text-xs text-muted-foreground">{presented.section}</p>}
      <p className="mt-2 text-sm font-semibold leading-6 text-foreground">{presented.question}</p>
      <div className="mt-3 rounded-md border border-border bg-background p-3">
        <p className="mb-1.5 text-[0.7rem] font-semibold uppercase tracking-wide text-muted-foreground">Answer</p>
        {presented.lines.length === 1 ? (
          <p className="whitespace-pre-wrap break-words text-sm text-foreground">{presented.lines[0]}</p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm text-foreground">
            {presented.lines.map((line, lineIndex) => <li key={`${lineIndex}-${line}`}>{line}</li>)}
          </ul>
        )}
        {presented.hint && <p className="mt-2 text-xs text-muted-foreground">{presented.hint}</p>}
      </div>
    </Card>
  )
}

export function ResponseDetailModal({ sessionTree, onClose }: Props) {
  const session = sessionTree?.session
  const answers = orderAnswers(sessionTree?.answers ?? [])

  return (
    <Modal
      open={sessionTree != null}
      onClose={onClose}
      title="Response detail"
      width={640}
    >
      {session ? (
        <div className="grid gap-4">
          {/* ── Session metadata ────────────────────────────────────────── */}
          <div className="grid gap-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={STATUS_BADGE_VARIANT[session.status]} size="xs">
                {STATUS_LABEL[session.status]}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Session</span>
              <span className="font-mono text-xs text-foreground">{session.session_id.slice(0, 8)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Started</span>
              <span className="text-foreground">{formatTimestamp(session.started_at)}</span>
            </div>
            {session.completed_at && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Completed</span>
                <span className="text-foreground">{formatTimestamp(session.completed_at)}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Last activity</span>
              <span className="text-foreground">{formatTimestamp(session.last_activity_at)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Version record</span>
              <span className="text-foreground">#{session.survey_version_id}</span>
            </div>
          </div>

          {/* ── Answers ─────────────────────────────────────────────────── */}
          <div>
            <h3 className="mb-2 text-sm font-semibold">
              Answers ({answers.length})
            </h3>
            {answers.length === 0 ? (
              <p className="text-xs text-muted-foreground">No answers recorded for this session.</p>
            ) : (
              <div className="grid gap-2">
                {answers.map((answer, index) => (
                  <AnswerCard key={answer.question_node_id} answer={answer} index={index} />
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
